"""Each service with the speech API of OpenAI: GET /v1/models for the list of
models, and POST /v1/audio/speech for the mp3. The set-up is in the docstring
of the package.

Each variable has the prefix TLHELPER_VOICE_, so the address of this app is
not the OPENAI_BASE_URL that another tool on the machine reads.
"""

import os
import time

import requests

from .base import MODELS_TIMEOUT, SpeechError, timeout

# How long the list of models stays, in seconds. The page asks for it on each
# load, and the omnivoice service has a fixed list.
MODELS_MAX_AGE = 60


def url() -> str:
    """The address of the service, with no slash at the end. Empty: no
    service, and the page has no buttons."""
    return os.environ.get("TLHELPER_VOICE_URL", "").rstrip("/")


def api_key() -> str:
    return os.environ.get("TLHELPER_VOICE_API_KEY", "")


def headers() -> dict[str, str]:
    key = api_key()
    return {"Authorization": f"Bearer {key}"} if key else {}


class OpenAISpeech:
    name = "openai"

    def __init__(self):
        # The list of models, or None while the service gave none, and when
        # it came.
        self._models: list[dict] | None = None
        self._fetched = 0.0

    def available(self) -> bool:
        return bool(url())

    def models(self) -> list[dict] | None:
        """The `data` of /v1/models, or None when the service does not
        answer. Either answer stays for MODELS_MAX_AGE seconds."""
        if time.monotonic() - self._fetched < MODELS_MAX_AGE:
            return self._models
        self._fetched = time.monotonic()
        try:
            response = requests.get(
                f"{url()}/v1/models", headers=headers(), timeout=MODELS_TIMEOUT
            )
            data = response.json()["data"] if response.status_code == 200 else None
        except (requests.RequestException, ValueError, KeyError, TypeError):
            data = None
        self._models = data if isinstance(data, list) else None
        return self._models

    def model(self) -> str:
        """TLHELPER_VOICE_MODEL, or the first model of the service."""
        named = os.environ.get("TLHELPER_VOICE_MODEL", "")
        if named or not self.available():
            return named
        models = self.models() or []
        return str(models[0].get("id", "")) if models else ""

    def entry(self) -> dict | None:
        """The entry of the model in the list of the service."""
        model = self.model()
        for each in self.models() or []:
            if each.get("id") == model:
                return each
        return None

    def languages(self) -> list[str] | None:
        entry = self.entry()
        # No entry, or an entry with no list (a real OpenAI service): the
        # service does not say.
        if entry is None or not isinstance(entry.get("languages"), list):
            return None
        return [str(code) for code in entry["languages"]]

    def synthesize(self, text: str, language: str) -> bytes:
        if not self.available():
            raise SpeechError("TLHELPER_VOICE_URL is not set", "voice-no-service")
        body = {"input": text, "language": language, "response_format": "mp3"}
        if self.model():
            body["model"] = self.model()
        try:
            response = requests.post(
                f"{url()}/v1/audio/speech",
                headers=headers(),
                json=body,
                timeout=timeout(),
            )
        except requests.Timeout as exc:
            raise SpeechError(
                "the voice service did not answer in time", "voice-timeout"
            ) from exc
        except requests.RequestException as exc:
            raise SpeechError(
                f"the voice service is not reachable: {exc!r}", "voice-no-service"
            ) from exc
        if response.status_code != 200:
            raise SpeechError(
                f"the voice service returned HTTP {response.status_code}",
                "voice-http",
                status=response.status_code,
            )
        if not response.content:
            raise SpeechError(
                "the voice service gave no sound", "voice-http", status=200
            )
        return response.content
