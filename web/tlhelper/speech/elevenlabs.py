"""The text-to-speech API of ElevenLabs: POST /v1/text-to-speech/{voice_id}
for the mp3. The set-up is in the docstring of the package.
"""

import os
from urllib.parse import quote

from .base import SpeechError, post
from .openai import api_key

URL = "https://api.elevenlabs.io/v1/text-to-speech"
# The default of the API.
DEFAULT_MODEL = "eleven_multilingual_v2"


def voice_id() -> str:
    return os.environ.get("TLHELPER_VOICE_ID", "")


class ElevenLabsSpeech:
    name = "elevenlabs"

    def available(self) -> bool:
        return bool(api_key() and voice_id())

    def model(self) -> str:
        return os.environ.get("TLHELPER_VOICE_MODEL", "") or DEFAULT_MODEL

    def languages(self) -> list[str] | None:
        # Each multilingual model reads every language of the app.
        return None

    def synthesize(self, text: str, language: str, voice: str | None = None) -> bytes:
        if not self.available():
            raise SpeechError(
                "TLHELPER_VOICE_API_KEY or TLHELPER_VOICE_ID is not set",
                "voice-no-service",
            )
        model = self.model()
        body = {"text": text, "model_id": model}
        # The API does not support language_code for the multilingual_v2 models.
        if not model.startswith("eleven_multilingual"):
            body["language_code"] = language
        return post(
            f"{URL}/{quote(voice or voice_id(), safe='')}",
            {"xi-api-key": api_key()},
            body,
        )
