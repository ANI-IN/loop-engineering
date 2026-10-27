"""The weekly link check: which files and addresses it reads, and how it judges an answer. No
network: every answer comes from httpx's mock transport, and no host name is looked up."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import httpx
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_external_links.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_external_links", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["check_external_links"] = module  # dataclasses look their module up by name
    spec.loader.exec_module(module)
    return module


check_links = _load()


def _client(answer) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(answer), follow_redirects=True)


def _found(url: str) -> object:
    return check_links.Found(url, "page.md:1")


def _no_wait(_seconds: float) -> None:
    return None


def test_addresses_drop_link_ends_punctuation_and_fragments() -> None:
    text = (
        "See [the guide](https://docs.example-site.org/guide#setup).\n"
        "Bare: https://kafka.apache.org/documentation/, then text.\n"
        "Autolink <https://brandur.org/idempotency-keys> and "
        "[a page](https://en.wikipedia.org/wiki/Loop_(computing)) here.\n"
    )
    assert check_links.addresses(text) == [
        (1, "https://docs.example-site.org/guide"),
        (2, "https://kafka.apache.org/documentation/"),
        (3, "https://brandur.org/idempotency-keys"),
        (3, "https://en.wikipedia.org/wiki/Loop_(computing)"),
    ]


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8501",
        "http://127.0.0.1:5432/x",
        "http://192.168.1.10/",
        "http://0.0.0.0:8000",
        "https://example.com/page",
        "https://api.example.org/v1",
        "http://postgres:5432",
        "https://host.docker.internal/",
        "https://smith.langchain.com/o/<organisation>/projects",
        "https://{host}/path",
    ],
)
def test_local_and_placeholder_addresses_are_not_fetched(url: str) -> None:
    assert check_links.is_local_or_placeholder(url)
    assert check_links.addresses(f"text {url} text") == []


def test_published_markdown_follows_the_release_list(tmp_path: Path) -> None:
    for name in (
        "README.md",
        "docs/sources.md",
        "slides/outline.md",
        "slides/draft-notes.md",
        "private/notes.md",
        "docs/DRAFT.md",
        "section-9-sample/assignment/solution/answer.md",
        ".cache/brief.md",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Page\n", encoding="utf-8")
    listed = tmp_path / "platform" / "config" / "release.toml"
    listed.parent.mkdir(parents=True)
    listed.write_text(
        'include = ["README.md", "docs/", "slides/", "section-*/"]\n'
        'exclude = ["private/", "slides/draft-notes.md", "section-*/assignment/solution/"]\n'
        'internal_files = ["DRAFT.md"]\n',
        encoding="utf-8",
    )
    found = [p.relative_to(tmp_path).as_posix() for p in check_links.published_markdown(tmp_path)]
    assert found == ["README.md", "docs/sources.md", "slides/outline.md"]


def test_without_a_release_list_every_page_outside_dot_folders_is_read(tmp_path: Path) -> None:
    for name in ("README.md", "docs/a.md", ".venv/lib/b.md"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Page\n", encoding="utf-8")
    found = [p.relative_to(tmp_path).as_posix() for p in check_links.published_markdown(tmp_path)]
    assert found == ["README.md", "docs/a.md"]


@pytest.mark.parametrize(
    ("url", "status", "result"),
    [
        ("https://docs.astral.sh/uv/", 200, "ok"),
        ("https://docs.astral.sh/uv/", 404, "dead"),
        ("https://docs.astral.sh/uv/", 410, "dead"),
        ("https://docs.astral.sh/uv/", 403, "dead"),
        ("https://cheatsheetseries.owasp.org/page.html", 403, "accepted"),
        ("https://genai.owasp.org/llmrisk/", 429, "accepted"),
        ("https://cheatsheetseries.owasp.org/page.html", 404, "dead"),
        ("https://api.openai.com/v1", 404, "accepted"),
        ("https://docs.astral.sh/uv/", 503, "unsure"),
        ("https://docs.astral.sh/uv/", 429, "unsure"),
    ],
)
def test_a_final_status_is_judged_by_its_host(url: str, status: int, result: str) -> None:
    assert check_links.classify(url, status)[0] == result


def test_a_redirect_to_a_live_page_is_ok() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/old":
            return httpx.Response(301, headers={"Location": "https://docs.astral.sh/new"})
        return httpx.Response(200)

    with _client(answer) as client:
        result = check_links.check_one(client, _found("https://docs.astral.sh/old"))
    assert (result.result, result.detail) == ("ok", "200")


def test_a_flaky_site_is_retried_and_then_passes() -> None:
    tries: list[int] = []

    def answer(request: httpx.Request) -> httpx.Response:
        tries.append(1)
        if len(tries) < 3:
            raise httpx.ConnectTimeout("slow", request=request)
        return httpx.Response(200)

    waits: list[float] = []
    with _client(answer) as client:
        result = check_links.check_one(
            client, _found("https://docs.astral.sh/uv/"), sleep=waits.append
        )
    assert result.result == "ok"
    assert len(tries) == 3
    assert waits == list(check_links.BACKOFF_SECONDS)


@pytest.mark.parametrize(
    "error",
    [
        httpx.ReadTimeout("slow"),
        httpx.RemoteProtocolError("dropped"),
        httpx.ConnectError("[Errno 111] Connection refused"),
    ],
)
def test_a_slow_or_flaky_site_is_unsure_never_dead(error: Exception) -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        raise error

    with _client(answer) as client:
        result = check_links.check_one(client, _found("https://docs.astral.sh/uv/"), sleep=_no_wait)
    assert result.result == "unsure"


def test_a_server_error_on_every_try_is_unsure() -> None:
    with _client(lambda request: httpx.Response(502)) as client:
        result = check_links.check_one(client, _found("https://docs.astral.sh/uv/"), sleep=_no_wait)
    assert (result.result, result.detail) == ("unsure", "502 on every try")


def test_a_host_name_that_never_resolves_is_dead() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("[Errno -2] Name or service not known")

    with _client(answer) as client:
        result = check_links.check_one(
            client, _found("https://no-such-host.astral.sh/"), sleep=_no_wait
        )
    assert (result.result, result.detail) == ("dead", "the host name does not resolve")


def test_a_host_name_that_resolves_on_a_later_try_is_not_dead() -> None:
    tries: list[int] = []

    def answer(request: httpx.Request) -> httpx.Response:
        tries.append(1)
        if len(tries) == 1:
            raise httpx.ConnectError("Temporary failure in name resolution")
        return httpx.Response(200)

    with _client(answer) as client:
        result = check_links.check_one(client, _found("https://docs.astral.sh/uv/"), sleep=_no_wait)
    assert result.result == "ok"


@pytest.mark.parametrize("url", ["https://[docs.astral.sh/uv/", "https://docs.astral.sh:abc/"])
def test_an_address_that_is_not_valid_is_found_and_dead(url: str) -> None:
    assert check_links.addresses(f"see {url} here") == [(1, url)]
    with _client(lambda request: httpx.Response(200)) as client:
        result = check_links.check_one(client, _found(url), sleep=_no_wait)
    assert (result.result, result.detail) == ("dead", "not a valid address")


def test_main_fails_on_a_dead_address_and_writes_the_job_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    page = tmp_path / "docs" / "sources.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "Live: https://docs.astral.sh/uv/\n"
        "Gone: https://docs.astral.sh/removed-page\n"
        "Blocked: https://cheatsheetseries.owasp.org/x.html\n"
        "Local: http://localhost:8501\n",
        encoding="utf-8",
    )
    statuses = {"/uv/": 200, "/removed-page": 404, "/x.html": 403}

    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(statuses[request.url.path])

    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    with _client(answer) as client:
        code = check_links.main(["--root", str(tmp_path)], client=client)
    out = capsys.readouterr().out
    assert code == 1
    assert "x dead https://docs.astral.sh/removed-page (docs/sources.md:2): 404" in out
    assert "3 addresses in 1 Markdown files" in out
    assert "dead 1, unsure 0, accepted 1, ok 1" in out
    written = summary.read_text(encoding="utf-8")
    assert "| dead | <https://docs.astral.sh/removed-page> | `docs/sources.md:2` | 404 |" in written
    assert "localhost" not in written


def test_main_passes_when_nothing_is_dead(tmp_path: Path) -> None:
    page = tmp_path / "README.md"
    page.write_text("Slow: https://docs.astral.sh/uv/\n", encoding="utf-8")
    with _client(lambda request: httpx.Response(503)) as client:
        code = check_links.main(
            ["--root", str(tmp_path), "--retries", "1", "--summary", str(tmp_path / "s.md")],
            client=client,
        )
    assert code == 0
