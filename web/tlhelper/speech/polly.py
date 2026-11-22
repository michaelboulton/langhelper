"""Amazon Polly, through botocore: one SynthesizeSpeech call for the mp3. The
set-up is in the docstring of the package.

botocore finds the credentials itself: the AWS_ variables, a credentials file,
or a role (README.md, "Limit a leaked voice credential").
"""

import os
from functools import cache

from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    ReadTimeoutError,
)
from botocore.session import Session, get_session

from .base import SpeechError, timeout

# One voice for each language that Polly reads, each with the neural and the
# generative engine. Polly has no Croatian voice.
VOICES = {"de": "Vicki", "fr": "Lea", "it": "Bianca", "en": "Joanna"}
DEFAULT_ENGINE = "neural"


def region() -> str:
    # botocore itself reads only AWS_DEFAULT_REGION.
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION", "")


# One session for the process: it renews the credentials of a role.
@cache
def session() -> Session:
    return get_session()


@cache
def client():
    return session().create_client(
        "polly", region_name=region(), config=Config(read_timeout=timeout())
    )


class PollySpeech:
    name = "polly"

    def available(self) -> bool:
        return bool(region()) and session().get_credentials() is not None

    def engine(self) -> str:
        return os.environ.get("TLHELPER_VOICE_MODEL", "") or DEFAULT_ENGINE

    def model(self) -> str:
        return f"polly-{self.engine()}"

    def languages(self) -> list[str] | None:
        return list(VOICES)

    def synthesize(self, text: str, language: str, voice: str | None = None) -> bytes:
        if not region():
            raise SpeechError("AWS_REGION is not set", "voice-no-service")
        try:
            sound = (
                client()
                .synthesize_speech(
                    Text=text,
                    OutputFormat="mp3",
                    VoiceId=voice or VOICES[language],
                    Engine=self.engine(),
                )["AudioStream"]
                .read()
            )
        except ClientError as exc:
            status = exc.response["ResponseMetadata"]["HTTPStatusCode"]
            raise SpeechError(
                f"the voice service returned HTTP {status}", "voice-http", status=status
            ) from exc
        except (ConnectTimeoutError, ReadTimeoutError) as exc:
            raise SpeechError(
                "the voice service did not answer in time", "voice-timeout"
            ) from exc
        except BotoCoreError as exc:
            raise SpeechError(
                f"the voice service is not reachable: {exc!r}", "voice-no-service"
            ) from exc
        if not sound:
            raise SpeechError(
                "the voice service gave no sound", "voice-http", status=200
            )
        return sound
