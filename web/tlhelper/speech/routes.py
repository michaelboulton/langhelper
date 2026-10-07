"""The routes of the "Listen" buttons. The package docstring has the design."""

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import Field, field_validator

from .. import languages, schemas, speech
from ..languages import ENGLISH, LANGUAGES
from ..messages import CodedHTTPException, coded_http
from ..settings import MAX_TEXT_CHARS

router = APIRouter(prefix="/api/v1", tags=["speech"])
UNSET = {"response_model_exclude_unset": True}

# The languages of the app that a service can read: the study languages and
# English, which is the other side of each breakdown.
CODES = [*LANGUAGES, ENGLISH.info.code]


class SpeechRequest(schemas.Model):
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    """The text to read aloud."""
    language: str = languages.DEFAULT
    """The language of the text: a `code` from /api/v1/languages, or "en"."""

    @field_validator("language")
    @classmethod
    def known_language(cls, value: str) -> str:
        if value not in CODES:
            raise ValueError(f"must be one of {', '.join(CODES)}")
        return value


def ready() -> tuple[speech.Synthesizer | None, str]:
    """The synthesizer and its model, or None and "" with no service."""
    try:
        synthesizer = speech.current()
        model = synthesizer.model() if synthesizer.available() else ""
    except speech.SpeechError:
        return None, ""
    return (synthesizer, model) if model else (None, "")


@router.get("/speech", response_model=schemas.SpeechInfoResponse, **UNSET)
def speech_info() -> dict:
    """Whether a voice service is set up, its model, and the languages that
    it reads aloud. With no service, the page has no "Listen" buttons."""
    synthesizer, model = ready()
    if synthesizer is None:
        return {"available": False, "model": "", "languages": []}
    served = synthesizer.languages()
    return {
        "available": True,
        "model": model,
        "languages": [code for code in CODES if served is None or code in served],
    }


# A GET, so the browser can keep the mp3 (README.md, "Listen").
@router.get(
    "/speech/audio",
    response_class=Response,
    responses={
        200: {"description": "The sound", "content": {"audio/mpeg": {}}},
        **schemas.SPEECH_ERRORS,
    },
    tags=["speech"],
)
def speak(req: Annotated[SpeechRequest, Query()]) -> Response:
    """Read a text aloud: the mp3 from the voice service. The text goes to
    that service. 422 with the code `voice-language` when the service does not
    read the language."""
    synthesizer, model = ready()
    if synthesizer is None:
        raise CodedHTTPException(
            503, "voice-no-service", "the server has no voice service"
        )
    served = synthesizer.languages()
    if served is not None and req.language not in served:
        raise CodedHTTPException(
            422,
            "voice-language",
            f"the voice service does not read {req.language}",
            language=req.language,
        )
    try:
        data = synthesizer.synthesize(req.text, req.language)
    except speech.SpeechError as exc:
        raise coded_http(502, exc) from exc
    return Response(
        data,
        media_type="audio/mpeg",
        headers={
            "X-Content-Type-Options": "nosniff",
            # The text of a user with a login, so not for a shared cache.
            "Cache-Control": "private, max-age=86400",
            # For the note under the buttons.
            "X-Voice-Model": model,
        },
    )
