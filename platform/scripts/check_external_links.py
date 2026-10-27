"""Check every external address in the published Markdown: the weekly link check.

Usage:
    python platform/scripts/check_external_links.py [--root PATH] [--summary PATH] [--list]
        [FILE ...]

Reads every Markdown file the release ships (the `include`, `exclude` and `internal_files` of
platform/config/release.toml; with no release list, as in a learner's copy, every Markdown file
outside dot folders), which takes in the course pages, the slide outline (slides/outline.md) and the
sources page (docs/sources.md). Named FILEs are read instead, relative to the root.

Each distinct address (its fragment removed) is fetched once with a GET that follows redirects and
reads no body, with a timeout and retries spaced out (RETRIES, BACKOFF_SECONDS). Hosts are visited
in parallel, the addresses of one host one at a time. Each address ends in one of four results:

- ok: a success or redirect status in the end;
- accepted: a host on ACCEPTED_BLOCKS answered 401, 403 or 429, as it does for any client that is
  not a browser, or a host on API_HOSTS (an API's base address, written as a setting's value)
  answered at all (each entry gives its reason); the address is not proven, and is listed as such;
- unsure: a slow or flaky site, after every retry: a timeout, a dropped connection, a server error
  (5xx), or a rate limit (429) from any host. Listed, never a failure: a site that is down this
  week is not a dead link;
- dead: a client error the host means (404, 410, any other 4xx not accepted), or a host name that
  does not resolve on any try. A dead address fails the check.

Local and placeholder addresses (localhost, private networks, example domains, any address with
a placeholder such as <port> or {name}) are not fetched. The report prints one line per address
that is not ok, then the count of each result; with --summary (or the GITHUB_STEP_SUMMARY variable
that GitHub Actions sets) it also writes a Markdown summary there, which GitHub shows as the job
summary. Nothing else is written; no issue is opened. Exits 1 on any dead address, else 0.
"""

from __future__ import annotations

import argparse
import fnmatch
import ipaddress
import os
import re
import sys
import time
import tomllib
from collections import defaultdict
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx

REPO = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
RELEASE_LIST = "platform/config/release.toml"

TIMEOUT_SECONDS = 20.0
RETRIES = 3  # tries per address, for a timeout, a dropped connection, a 5xx or a 429
BACKOFF_SECONDS = (2.0, 8.0)  # the wait before the second and the third try
PARALLEL_HOSTS = 8
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) loop-engineering-link-check/1 "
    "(weekly check of a course's published links)"
)

# Hosts that answer an automated client with 401, 403 or 429 however often it asks: the page is
# there for a reader with a browser. Each entry names the host (and its subdomains) and why.
ACCEPTED_BLOCKS: dict[str, str] = {
    "owasp.org": "the OWASP pages show a browser check to any client without a browser",
}
# Hosts named as a setting's value (an API's base address), not as a page to read: any HTTP
# answer, whatever its status, shows the host is there; only a name that does not resolve fails.
API_HOSTS: dict[str, str] = {
    "api.openai.com": "the OpenAI API's base address, a setting value",
    "api.smith.langchain.com": "the LangSmith API's base address, a setting value",
    "eu.api.smith.langchain.com": "the LangSmith API's European base address, a setting value",
}
# Statuses an accepted host may answer with (999 is LinkedIn's own refusal).
BLOCK_STATUSES = frozenset({401, 403, 429, 999})

OK, ACCEPTED, UNSURE, DEAD = "ok", "accepted", "unsure", "dead"
RESULTS = (DEAD, UNSURE, ACCEPTED, OK)

_URL = re.compile(r"https?://[^\s<>\"'`\]|\\]+")
_TRAILING = ".,;:!?*_~"
_PLACEHOLDER = re.compile(r"[<>{}$]|%7B|%3C", re.IGNORECASE)
_LOCAL_SUFFIXES = (".local", ".internal", ".localhost", ".test", ".example", ".invalid")
_EXAMPLE_DOMAINS = ("example.com", "example.org", "example.net")


@dataclass(frozen=True)
class Found:
    url: str  # without its fragment
    where: str  # path:line of the first mention


@dataclass(frozen=True)
class Result:
    url: str
    where: str
    result: str  # ok, accepted, unsure, dead
    detail: str


# -- which files ----------------------------------------------------------------------------------


def _matches(path: str, entry: str) -> bool:
    """A release-list entry: a folder (ending in /, everything under it) or a file pattern."""
    if entry.endswith("/"):
        return fnmatch.fnmatchcase(path, entry + "*")
    return fnmatch.fnmatchcase(path, entry)


def published_markdown(root: Path) -> list[Path]:
    """Every Markdown file the release ships from this tree, sorted."""
    candidates = [
        p
        for p in root.rglob("*.md")
        if not any(
            part.startswith(".") and part != ".github" for part in p.relative_to(root).parts[:-1]
        )
    ]
    release_list = root / RELEASE_LIST
    if not release_list.is_file():
        return sorted(candidates, key=lambda p: p.relative_to(root).as_posix())
    listed = tomllib.loads(release_list.read_text(encoding="utf-8"))
    include = listed.get("include", [])
    exclude = listed.get("exclude", [])
    internal = set(listed.get("internal_files", []))
    kept = []
    for path in candidates:
        rel = path.relative_to(root).as_posix()
        if path.name in internal:
            continue
        if any(_matches(rel, e) for e in include) and not any(_matches(rel, e) for e in exclude):
            kept.append(path)
    return sorted(kept, key=lambda p: p.relative_to(root).as_posix())


# -- which addresses ------------------------------------------------------------------------------


def _trim(url: str) -> str:
    """An address as written in Markdown: trailing punctuation and an unbalanced closing
    parenthesis (the end of a Markdown link) are not part of it."""
    while url and (url[-1] in _TRAILING or (url[-1] == ")" and url.count(")") > url.count("("))):
        url = url[:-1]
    return url


def host_of(url: str) -> str | None:
    """The address's host name in lower case ("" without one), or None when the address is
    malformed (a stray bracket, a port that is not a number): the check reports it as dead."""
    try:
        parts = urlsplit(url)
        _ = parts.port
    except ValueError:
        return None
    return (parts.hostname or "").lower()


def is_local_or_placeholder(url: str) -> bool:
    """True for an address a link check must not fetch: a placeholder, a local host, a private
    network, or an example domain."""
    if _PLACEHOLDER.search(url):
        return True
    host = host_of(url)
    if host is None:
        return False  # malformed: checked, and reported as dead
    if not host or "." not in host and host != "localhost":
        return True
    if host == "localhost" or host.endswith(_LOCAL_SUFFIXES):
        return True
    if host in _EXAMPLE_DOMAINS or host.endswith(tuple(f".{d}" for d in _EXAMPLE_DOMAINS)):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_unspecified


def addresses(text: str) -> list[tuple[int, str]]:
    """(line, address without its fragment) for every external address in the text."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in _URL.finditer(line):
            url = _trim(match.group(0))
            # An address that runs into a placeholder, such as /o/<organisation>, is a pattern.
            placeholder = line[match.end() : match.end() + 1] == "<"
            if placeholder or is_local_or_placeholder(url):
                continue
            if host_of(url) is None:
                found.append((number, url.split("#", 1)[0]))
            else:
                found.append((number, urlunsplit(urlsplit(url)._replace(fragment=""))))
    return found


def collect(root: Path, files: Iterable[Path]) -> list[Found]:
    """Each distinct address, with the first place it is written."""
    first: dict[str, str] = {}
    for path in files:
        rel = path.relative_to(root).as_posix()
        for number, url in addresses(path.read_text(encoding="utf-8", errors="replace")):
            first.setdefault(url, f"{rel}:{number}")
    return [Found(url, where) for url, where in sorted(first.items())]


# -- one address ----------------------------------------------------------------------------------


def _listed_reason(url: str, hosts: dict[str, str]) -> str | None:
    host = host_of(url) or ""
    for name, reason in hosts.items():
        if host == name or host.endswith(f".{name}"):
            return reason
    return None


def _resolves_not(error: Exception) -> bool:
    text = str(error).lower()
    return any(
        words in text
        for words in (
            "name or service not known",
            "nodename nor servname",
            "getaddrinfo failed",
            "no address associated",
            "temporary failure in name resolution",
        )
    )


def classify(url: str, status: int) -> tuple[str, str]:
    """The result of a final status, after redirects."""
    if status < 400:
        return OK, str(status)
    api = _listed_reason(url, API_HOSTS)
    if api is not None:
        return ACCEPTED, f"{status}: {api}"
    reason = _listed_reason(url, ACCEPTED_BLOCKS)
    if status in BLOCK_STATUSES and reason is not None:
        return ACCEPTED, f"{status}: {reason}"
    if status == 429 or status >= 500 or status in (408, 425):
        return UNSURE, f"{status} on every try"
    return DEAD, str(status)


def check_one(
    client: httpx.Client,
    found: Found,
    *,
    retries: int = RETRIES,
    sleep: Callable[[float], None] = time.sleep,
) -> Result:
    """Fetch one address, retrying a timeout, a dropped connection, a 5xx or a 429."""
    if host_of(found.url) is None:
        return Result(found.url, found.where, DEAD, "not a valid address")
    detail = ""
    unresolved = 0
    for attempt in range(retries):
        if attempt:
            sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])
        try:
            with client.stream("GET", found.url) as response:
                status = response.status_code
        except httpx.InvalidURL as error:
            return Result(found.url, found.where, DEAD, f"not a valid address: {error}")
        except httpx.TimeoutException:
            detail = f"no answer within {TIMEOUT_SECONDS:.0f} seconds on every try"
            continue
        except httpx.TransportError as error:
            if _resolves_not(error):
                unresolved += 1
                detail = "the host name does not resolve"
            else:
                detail = f"connection failed on every try: {type(error).__name__}"
            continue
        result, detail = classify(found.url, status)
        if result != UNSURE:
            return Result(found.url, found.where, result, detail)
    if unresolved == retries:
        return Result(found.url, found.where, DEAD, detail)
    return Result(found.url, found.where, UNSURE, detail)


def check_all(found: list[Found], client: httpx.Client, retries: int = RETRIES) -> list[Result]:
    """Every address, the hosts in parallel and each host's addresses one at a time."""
    by_host: dict[str, list[Found]] = defaultdict(list)
    for item in found:
        by_host[host_of(item.url) or ""].append(item)

    def one_host(items: list[Found]) -> list[Result]:
        return [check_one(client, item, retries=retries) for item in items]

    with ThreadPoolExecutor(max_workers=PARALLEL_HOSTS) as pool:
        groups = list(pool.map(one_host, by_host.values()))
    return sorted((r for group in groups for r in group), key=lambda r: r.url)


# -- the report -----------------------------------------------------------------------------------


def summary_markdown(results: list[Result], files: int) -> str:
    counts = {name: sum(r.result == name for r in results) for name in RESULTS}
    lines = [
        "## Weekly link check",
        "",
        f"{len(results)} external addresses in {files} published Markdown files: "
        + ", ".join(f"{counts[name]} {name}" for name in RESULTS)
        + ".",
        "",
    ]
    listed = [r for r in results if r.result != OK]
    if listed:
        lines += ["| Result | Address | First written at | Detail |", "|---|---|---|---|"]
        for r in sorted(listed, key=lambda r: (RESULTS.index(r.result), r.url)):
            lines.append(f"| {r.result} | <{r.url}> | `{r.where}` | {r.detail} |")
        lines.append("")
    lines.append(
        "Only a dead address fails the check; an unsure one (a slow or flaky site) and an "
        "accepted one (a site that blocks automated clients, or an API's base address) are "
        "listed for a reader to open."
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str], client: httpx.Client | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO, help="the tree to read")
    parser.add_argument("--summary", type=Path, help="write a Markdown summary here")
    parser.add_argument("--retries", type=int, default=RETRIES, help="tries per address")
    parser.add_argument("--list", action="store_true", help="print the addresses; fetch nothing")
    parser.add_argument("files", nargs="*", help="these Markdown files only, under the root")
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    if arguments.files:
        files = [(root / name).resolve() for name in arguments.files]
    else:
        files = published_markdown(root)
    found = collect(root, files)
    if arguments.list:
        for item in found:
            print(f"{item.url} ({item.where})")
        print(f"{len(found)} addresses in {len(files)} Markdown files")
        return 0
    started = time.monotonic()
    own_client = client is None
    client = client or httpx.Client(
        follow_redirects=True,
        timeout=TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"},
    )
    try:
        results = check_all(found, client, retries=max(1, arguments.retries))
    finally:
        if own_client:
            client.close()
    for r in sorted(results, key=lambda r: (RESULTS.index(r.result), r.url)):
        if r.result != OK:
            mark = "x" if r.result == DEAD else "-"
            print(f"{mark} {r.result} {r.url} ({r.where}): {r.detail}")
    counts = ", ".join(f"{name} {sum(r.result == name for r in results)}" for name in RESULTS)
    seconds = time.monotonic() - started
    print(
        f"{len(results)} addresses in {len(files)} Markdown files, {seconds:.0f} seconds: {counts}"
    )
    target = arguments.summary or (
        Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.environ.get("GITHUB_STEP_SUMMARY") else None
    )
    if target is not None:
        with target.open("a", encoding="utf-8") as summary:
            summary.write(summary_markdown(results, len(files)))
    return 1 if any(r.result == DEAD for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
