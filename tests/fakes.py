"""Test doubles for the two vendor clients, built in one place.

Eight test modules used to carry their own `SimpleNamespace(create=...)` stub, all
Anthropic-shaped, all subtly different. That was survivable while there was one
vendor. It is not now: a role decides which SDK surface its client must expose, and
a per-module stub is a per-module chance to fake the wrong one and prove nothing.

So the doubles live here and are built **from the registry**, the same way the real
clients are. Ask for a client by role and you get the shape that role's provider
actually uses:

    agent, reference  ->  client.chat.completions.create(...)   (OpenAI)
    judge             ->  client.messages.create(...)           (Anthropic)

Every double records the requests it was handed, because a test that asserts on the
request body is the only way to check things like "the static prefix did not move
into the per-item turn" — which is the property prompt caching depends on and which
nothing else can observe.

**The usage shapes are the vendors' real ones, including the trap.** OpenAI reports
`prompt_tokens` INCLUDING cached tokens with `cached_tokens` as a subset breakdown;
Anthropic reports `input_tokens` EXCLUDING them. `loopeng.providers` exists to
reconcile that, and a double that flattened the difference would let the bug it
guards against pass every test.
"""

from types import SimpleNamespace

from loopeng.registry import OPENAI, spec_for

# What a call reports when a test does not care about tokens. Small and non-round so
# an accidental hard-coded expectation stands out.
DEFAULT_TOKENS = {"input_tokens": 100, "output_tokens": 50, "cached_tokens": 0}


def openai_response(text: str, *, model: str, tokens: dict) -> SimpleNamespace:
    """An OpenAI chat completion, in the shape `providers._openai_usage` reads.

    `prompt_tokens` is the TOTAL input and `cached_tokens` is a subset of it — the
    real convention, so a double cannot hide a double-count.
    """
    cached = tokens.get("cached_tokens", 0)
    return SimpleNamespace(
        model=model,
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(
            prompt_tokens=tokens["input_tokens"] + cached,
            completion_tokens=tokens["output_tokens"],
            prompt_tokens_details=SimpleNamespace(
                cached_tokens=cached,
                cache_write_tokens=tokens.get("cache_write_tokens", 0),
            ),
        ),
    )


def anthropic_response(text: str, *, model: str, tokens: dict) -> SimpleNamespace:
    """An Anthropic message, in the shape `providers._anthropic_usage` reads."""
    return SimpleNamespace(
        model=model,
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(
            input_tokens=tokens["input_tokens"],
            output_tokens=tokens["output_tokens"],
            cache_creation_input_tokens=tokens.get("cache_write_tokens", 0),
            cache_read_input_tokens=tokens.get("cached_tokens", 0),
        ),
    )


class FakeClient:
    """A vendor client that answers from a script and remembers what it was asked.

    `replies` are returned in order; the last one repeats, so a test that only cares
    about the first call does not have to pad. `raises` is a callable or an
    exception instance returned instead of a reply — a failing call, which still
    billed and still has to be recorded.
    """

    def __init__(self, role, replies=("SELECT 1",), *, tokens=None, raises=None,
                 served_model=None):
        self.spec = spec_for(role)
        # Three shapes, because the call sites genuinely have three needs: one SQL
        # string for a single-shot test, a list to script a retry sequence, and a
        # callable keyed on the question so a whole grid can be driven offline.
        # Accepting all three here is what let eight bespoke stubs collapse into one.
        if callable(replies):
            self._answer = replies
        else:
            scripted = [replies] if isinstance(replies, str) else list(replies)
            self._answer = lambda _question: scripted[
                min(self.calls - 1, len(scripted) - 1)
            ]
        self._tokens = dict(DEFAULT_TOKENS if tokens is None else tokens)
        self._raises = raises
        # Lets a test drive `registry.assert_served_by` — the check that catches a
        # silent model swap. Defaults to honest.
        self._served_model = served_model or self.spec.model_id
        self.calls = 0
        self.requests: list[dict] = []

        if self.spec.provider == OPENAI:
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self._create)
            )
        else:
            self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        self.requests.append(kwargs)

        if self._raises is not None:
            raise self._raises() if callable(self._raises) else self._raises

        text = self._answer(self._question_of(kwargs))
        build = (
            openai_response if self.spec.provider == OPENAI else anthropic_response
        )
        return build(text, model=self._served_model, tokens=self._tokens)

    def _question_of(self, request) -> str:
        """The question this request is about, whichever vendor's shape it is in.

        The loops put the question in the first user turn as `Question: <text>`. A
        callable script keys on it, so a grid of items can be driven offline with one
        client rather than one per item.
        """
        turns = (
            request["messages"][1:]
            if self.spec.provider == OPENAI
            else request["messages"]
        )
        first = turns[0]["content"] if turns else ""
        return first.split("Question: ")[-1]

    # ---- what the request carried, for the tests that assert on it ----------

    def system_of(self, index: int = 0) -> str:
        """The static prefix as this vendor received it.

        Both vendors are asked for the same thing and put it in different places;
        a test about prefix stability should not have to know which.
        """
        request = self.requests[index]
        if self.spec.provider == OPENAI:
            return request["messages"][0]["content"]
        return request["system"]

    def turns_of(self, index: int = 0) -> list[dict]:
        """The per-item conversation, with the system block stripped off."""
        request = self.requests[index]
        if self.spec.provider == OPENAI:
            return list(request["messages"][1:])
        return list(request["messages"])


def rate_limited(provider_role: str = "agent"):
    """A 429 from the right vendor's SDK, for exercising the backoff path."""
    spec = spec_for(provider_role)
    if spec.provider == OPENAI:
        import httpx2 as httpx
        import openai as sdk

        url = "https://api.openai.com/"
    else:
        import anthropic as sdk
        import httpx

        url = "https://api.anthropic.com/"

    return sdk.RateLimitError(
        "Error code: 429",
        response=httpx.Response(429, request=httpx.Request("POST", url)),
        body=None,
    )


def refusal(kind: str, role: str = "agent"):
    """A fatal, non-retryable failure from the right vendor's SDK.

    `kind` is one of the names `providers.triage_call_failure` returns:
    "credential", "bad_request", "model_unavailable".
    """
    spec = spec_for(role)
    if spec.provider == OPENAI:
        import httpx2 as httpx
        import openai as sdk

        url = "https://api.openai.com/"
    else:
        import anthropic as sdk
        import httpx

        url = "https://api.anthropic.com/"

    status, cls = {
        "credential": (401, sdk.AuthenticationError),
        "bad_request": (400, sdk.BadRequestError),
        "model_unavailable": (404, sdk.NotFoundError),
    }[kind]

    return cls(
        f"Error code: {status}",
        response=httpx.Response(status, request=httpx.Request("POST", url)),
        body=None,
    )
