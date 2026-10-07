"""The routes. README.md has each one with an example.

GET  /healthz          liveness, and which models are in memory
GET  /v1/models        the models, each with the languages that it reads
POST /v1/audio/speech  the mp3 of a text
"""

import logging
import threading
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from . import settings
from .synth import Synth

logger = logging.getLogger("omnivoice_server")

# The most characters of one request. A CPU reads a text of this size in
# minutes, and a caller that wants more sends more requests.
MAX_CHARS = 4000

# The Cache-Status header of RFC 9211: whether the mp3 came from the cache of
# Synth.
CACHE_HIT = "omnivoice; hit"
CACHE_MISS = "omnivoice; fwd=miss"

synth = Synth()


class CodedHTTPException(HTTPException):
    """An HTTPException with a `code` next to `detail` in its JSON."""

    def __init__(self, status_code: int, code: str, detail: str):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class NoHealthLines(logging.Filter):
    """Drops the access lines of /healthz: the health check of compose calls
    it every few seconds."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/healthz " not in record.getMessage()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger("uvicorn.access").addFilter(NoHealthLines())
    unknown = sorted(set(settings.languages()) - settings.known_languages())
    # uvicorn logs the error and exits on a failed start.
    if unknown:
        raise RuntimeError(
            f"OMNIVOICE_LANGUAGES has codes that the model does not know: {unknown}"
        )
    # A clip that is not a 24 kHz mono WAV, or has no transcript, stops the
    # start too.
    logger.info("voice clips: %s", sorted(synth.voices()) or "none")
    if settings.preload():
        # The lock is held during the load, so an early request waits.
        logger.info("loading %s", settings.default_model())
        threading.Thread(
            target=synth.load, args=(settings.default_model(),), daemon=True
        ).start()
    yield


app = FastAPI(
    title="OmniVoice",
    summary="Text to speech with OmniVoice, behind an OpenAI-shaped API.",
    version="1",
    lifespan=lifespan,
)


@app.exception_handler(CodedHTTPException)
async def coded_error(request: Request, exc: CodedHTTPException) -> JSONResponse:
    return JSONResponse(
        {"detail": exc.detail, "code": exc.code}, status_code=exc.status_code
    )


class SpeechRequest(BaseModel):
    model: str | None = None
    """An id from /v1/models. Default: the first one."""
    input: str = Field(min_length=1, max_length=MAX_CHARS)
    """The text to read."""
    language: str
    """A code from the `languages` of the model in /v1/models."""
    instruct: str | None = None
    """A description of the voice, such as "female, low pitch, british
    accent". Default: the reference clip of the language, else
    OMNIVOICE_INSTRUCT."""
    response_format: Literal["mp3"] = "mp3"


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "loaded": synth.loaded()}


@app.get("/v1/models")
def models() -> dict:
    languages = settings.languages()
    return {
        "object": "list",
        "data": [
            {
                "id": model_id,
                "object": "model",
                "owned_by": model_id.split("/")[0] if "/" in model_id else "",
                "languages": languages,
            }
            for model_id in settings.models()
        ],
    }


# Plain def: FastAPI runs it in the thread pool, so /healthz answers during
# a generation.
@app.post("/v1/audio/speech", response_class=Response)
def speech(req: SpeechRequest) -> Response:
    model_id = req.model or settings.default_model()
    if model_id not in settings.models():
        raise CodedHTTPException(
            404, "unknown-model", f"no model {model_id!r}: see /v1/models"
        )
    if req.language not in settings.languages():
        raise CodedHTTPException(
            422,
            "unknown-language",
            f"no language {req.language!r}: see the languages in /v1/models",
        )
    text = req.input.strip()
    if not text:
        raise CodedHTTPException(422, "empty-text", "the input is only spaces")
    try:
        data, cached = synth.speak(text, req.language, req.instruct, model_id)
    except ValueError as exc:
        # The model refuses an instruct item outside its list, and says which.
        raise CodedHTTPException(422, "bad-instruct", str(exc)) from exc
    return Response(
        data,
        media_type="audio/mpeg",
        headers={"Cache-Status": CACHE_HIT if cached else CACHE_MISS},
    )
