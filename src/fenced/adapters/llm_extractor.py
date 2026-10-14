"""The extractor that asks a model, and the only file in `src` that names a provider.

The provider is Anthropic, reached over its Messages API with the standard library. The key
comes from the environment variable `FENCED_LLM_API_KEY` and from nowhere else. When it is
absent the extractor is never built. The constructor raises `MissingKey` with a message that
says what is missing and what runs without it, and the command line prints that and stops
before the first message is read.

The model is asked for three fields and nothing else, a name, an address and one of the
five levels of awareness. It is not shown the catalog, the sellers or a price, and the
prompt is one constant so the fourth fence can read it. What comes back is a mapping that
still has to cross `Lead.from_fields`, which refuses rather than coerces.

The model can be changed with `FENCED_LLM_MODEL`. Changing the provider is changing this file.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping

from fenced.domain.lead import Awareness

PROVIDER = "anthropic"
ENDPOINT = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
# A refusal by the model is answered by the provider with another model of its choosing.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
KEY_VARIABLE = "FENCED_LLM_API_KEY"
MODEL_VARIABLE = "FENCED_LLM_MODEL"
DEFAULT_MODEL = "claude-opus-5-5"
# Room for the thinking the model does before it answers, and the three fields after it.
MAX_TOKENS = 4096
TIMEOUT_SECONDS = 60
SYSTEM_PROMPT = (
    "You read one message a person wrote to a business and return three fields as JSON. "
    "name is the name the person signs with. "
    "email is the address the person can be written back at, exactly as written. "
    "awareness is how far along the person is, as one of these five. "
    "unaware when they describe a situation and do not call it a problem. "
    "problem_aware when they name a problem and no way to solve it. "
    "solution_aware when they know the kind of solution and are weighing options. "
    "product_aware when they ask about one particular offer. "
    "ready_to_buy when they say they want to buy now. "
    "Return only what the message says. When a field is not in the message return an "
    "empty string for it. Do not guess and do not add anything."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string"},
        "awareness": {"type": "string", "enum": [level.value for level in Awareness]},
    },
    "required": ["name", "email", "awareness"],
    "additionalProperties": False,
}
EXPLANATION = (
    f"The model extractor needs a key in the environment variable {KEY_VARIABLE}, and it is "
    "not set. Nothing was read and nothing was written. Set it in the environment of this "
    "shell, never in a file under version control, or run without --extractor model to use "
    "the fake extractor, which needs no key and no network."
)

# What sends a request. It takes the address, the headers and the body, and returns the body
# of the answer. A test passes its own, so no test reaches the network.
Send = Callable[[str, Mapping[str, str], bytes], bytes]


class LlmError(RuntimeError):
    """Anything that kept the model from returning the fields."""


class MissingKey(LlmError):
    """No key in the environment, so no request is made at all."""


class ExtractionFailed(LlmError):
    """A request that was made and did not come back as three fields."""


def _send(url: str, headers: Mapping[str, str], body: bytes) -> bytes:
    """Post the body and return the answer, or a refusal that carries no key."""
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as answer:
            return answer.read()
    except urllib.error.HTTPError as failed:
        raise ExtractionFailed(f"the provider answered {failed.code} {failed.reason}") from None
    except urllib.error.URLError as failed:
        raise ExtractionFailed(f"the provider could not be reached, {failed.reason}") from None


class LlmExtractor:
    """A model behind the shape of an extractor."""

    def __init__(self, environ: Mapping[str, str], send: Send = _send) -> None:
        key = environ.get(KEY_VARIABLE, "").strip()
        if not key:
            raise MissingKey(EXPLANATION)
        self._key = key
        self.model = environ.get(MODEL_VARIABLE, "").strip() or DEFAULT_MODEL
        self._send = send

    def request(self, text: str) -> dict[str, object]:
        """The body of the request for one message, which a test can read without sending it."""
        return {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": text}],
            "output_config": {
                "effort": "low",
                "format": {"type": "json_schema", "schema": SCHEMA},
            },
            "fallbacks": "default",
        }

    def extract(self, text: str) -> dict[str, object]:
        """The three fields the model found, as a mapping the boundary still has to accept."""
        headers = {
            "content-type": "application/json",
            "x-api-key": self._key,
            "anthropic-version": API_VERSION,
            "anthropic-beta": FALLBACK_BETA,
        }
        body = json.dumps(self.request(text)).encode("utf-8")
        try:
            answer = json.loads(self._send(ENDPOINT, headers, body))
        except json.JSONDecodeError:
            raise ExtractionFailed("the provider answered with something that is not JSON") from None
        if not isinstance(answer, dict):
            raise ExtractionFailed("the provider answered with something that is not an object")
        if answer.get("stop_reason") != "end_turn":
            raise ExtractionFailed(f"the model stopped with {answer.get('stop_reason')!r}")
        texts = [
            block.get("text")
            for block in answer.get("content") or []
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if not texts or not isinstance(texts[-1], str):
            raise ExtractionFailed("the model returned no text")
        try:
            fields = json.loads(texts[-1])
        except json.JSONDecodeError:
            raise ExtractionFailed("the model returned text that is not JSON") from None
        if not isinstance(fields, dict):
            raise ExtractionFailed("the model returned JSON that is not an object")
        return fields
