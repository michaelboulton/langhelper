"""Each service with the chat completions API of OpenAI, through the OpenAI
SDK. The set-up is in the docstring of the package.

Each variable of the app has the prefix TLHELPER_AI_, so the key of this app
is not the OPENAI_API_KEY that another tool on the machine reads.
"""

import os

from .base import MAX_TOKENS, TIMEOUT, ExplainError

# Without a model or a key, the page has no buttons, and a request gets an
# error.
MODEL = os.environ.get("TLHELPER_AI_MODEL", "")
# A model that thinks before it answers uses tokens for that, so it needs more.
TOKENS = int(os.environ.get("TLHELPER_AI_MAX_TOKENS", str(MAX_TOKENS)))


def api_key() -> str:
    return os.environ.get("TLHELPER_AI_API_KEY", "")


def api_base() -> str:
    """Never empty: with no address, the SDK reads OPENAI_BASE_URL."""
    return os.environ.get("TLHELPER_AI_API_BASE", "") or "https://api.openai.com/v1"


class OpenAICompatible:
    name = "openai"

    def __init__(self):
        self._client = None

    def available(self) -> bool:
        return bool(api_key() and MODEL)

    def model(self) -> str:
        return MODEL

    def client(self):
        # Not at the import of the module: the app must start with no key.
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=api_key(),
                base_url=api_base(),
                timeout=TIMEOUT,
                max_retries=0,
            )
        return self._client

    def complete(
        self,
        system: str,
        prompt: str,
        *,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> str:
        if not api_key():
            raise ExplainError("TLHELPER_AI_API_KEY is not set")
        if not MODEL:
            raise ExplainError("TLHELPER_AI_MODEL is not set")
        import openai

        # The SDK takes a timeout for one request, so the client stays.
        options = {"timeout": timeout} if timeout is not None else {}
        try:
            response = self.client().chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=max_tokens or TOKENS,
                **options,
            )
        except openai.APITimeoutError as exc:
            raise ExplainError(
                "the AI service did not answer in time", "ai-timeout"
            ) from exc
        except openai.RateLimitError as exc:
            raise ExplainError(
                "the AI service has too many requests, or no credit", "ai-busy"
            ) from exc
        except openai.AuthenticationError as exc:
            raise ExplainError("the AI service did not accept the key") from exc
        except openai.APIStatusError as exc:
            raise ExplainError(
                f"the AI service returned HTTP {exc.status_code}",
                "ai-http",
                status=exc.status_code,
            ) from exc
        except openai.OpenAIError as exc:
            raise ExplainError(f"the AI service is not reachable: {exc!r}") from exc
        text = (response.choices[0].message.content or "").strip()
        if not text:
            raise ExplainError(
                "the AI service gave an empty answer (more tokens?)", "ai-empty"
            )
        return text
