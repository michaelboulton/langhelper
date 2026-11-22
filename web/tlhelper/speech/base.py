"""What every voice synthesizer has in common."""

import os
from typing import Protocol

import requests

from ..messages import CodedError

# For the list of models on a page load, in seconds: the page waits for it.
MODELS_TIMEOUT = 2
# For one synthesis, in seconds. A CPU needs a while for a long text.
DEFAULT_TIMEOUT = 180


def timeout() -> float:
    return float(os.environ.get("TLHELPER_VOICE_TIMEOUT", str(DEFAULT_TIMEOUT)))


class SpeechError(CodedError):
    """The message goes to the page: the English text, and for an error with
    a code, the message "error-{code}" of the catalogs."""


def post(url: str, headers: dict[str, str], body: dict) -> bytes:
    """One POST to a voice service: the sound of its answer. Raises
    SpeechError on every failure."""
    try:
        response = requests.post(url, headers=headers, json=body, timeout=timeout())
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
        raise SpeechError("the voice service gave no sound", "voice-http", status=200)
    return response.content


class Synthesizer(Protocol):
    # The value of TLHELPER_VOICE_BACKEND that selects this one.
    name: str

    def available(self) -> bool:
        """The synthesizer has an address. If not, the page has no buttons."""

    def model(self) -> str:
        """The model that reads aloud, for the page. Empty if none is known."""

    def languages(self) -> list[str] | None:
        """The codes of the app ("hr", "en") that the model reads aloud. None
        when the service does not say, or does not answer: every language
        then counts, and synthesize() reports the failure."""

    def synthesize(self, text: str, language: str, voice: str | None = None) -> bytes:
        """One request to the service: an mp3 of the text, in the language
        with this code of the app. voice names a voice of the service, and
        None is its default. Raises SpeechError on every failure."""
