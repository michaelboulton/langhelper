"""Sentence breakdown service for a study language (Croatian, German, French,
Italian) and English. The languages are in languages/.

GET  /                  the single page (static/index.html)
GET  /static/...        the script and the style sheet of the page
GET  /healthz           liveness, does not touch the models
GET  /api/v1/languages  the study languages, for the list on the page
GET  /api/v1/locales    the languages of the page text, and the Fluent file of
                        each one (locales.py)
GET  /api/v1/status     which models are loaded and which one loads now
POST /api/v1/classify   tokenize, tag and lemmatize a text in the study
                        language, check its grammar, and on request translate
                        it to English (DeepL) and tag that too. With source
                        "en", the text is English: check it, translate it to
                        the study language, and break down that text
GET  /api/v1/lemmas     the most-seen lemmas of one language
GET  /api/v1/decks ...  the flashcards (flashcards/routes.py)
POST /api/v1/explain    the "explain with AI" buttons (explain/routes.py)
GET  /api/v1/speech ... the "Listen" buttons: an mp3 of a text from the voice
                        service (speech/routes.py)
GET  /auth/...          the OIDC login (auth.py), only used on a fly.dev hostname

Everything that must survive a restart lives under DATA_ROOT (a Fly volume):
the downloaded models, the SQLite file with the lemma counts and the
cached translations, the decks of the admin, and the SQLite file with the
flashcard progress of each user.
"""

import dataclasses
import logging
import os
import sqlite3
import threading
import time
import unicodedata
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import Field, field_validator
from starlette.middleware.sessions import SessionMiddleware

from . import align, auth, languages, locales, schemas, translators
from .explain import routes as explain_routes
from .flashcards import decks
from .flashcards import routes as flashcard_routes
from .languages import ENGLISH, LANGUAGES, Language, ModelsMissing, model_type
from .messages import CodedHTTPException
from .settings import DATA_ROOT, MAX_TEXT_CHARS
from .speech import routes as speech_routes
from .translators import TranslationError

DB_PATH = DATA_ROOT / "lemmas.db"
# The page, its script and its style sheet. STATIC_DIR is for a layout where
# static/ is not next to the package.
STATIC_DIR = Path(os.environ.get("STATIC_DIR", Path(__file__).parent.parent / "static"))
INDEX_HTML = STATIC_DIR / "index.html"

# Not worth counting: nobody asks for a translation of a comma or a number.
UNTRACKED_UPOS = {"PUNCT", "SYM", "NUM"}

logger = logging.getLogger("uvicorn.error")
# The access line is complete as it is, so it gets a handler with no prefix.
access_logger = logging.getLogger("tlhelper.access")
access_logger.setLevel(logging.INFO)
access_logger.propagate = False
if not access_logger.handlers:
    access_logger.addHandler(logging.StreamHandler())

_db_lock = threading.Lock()

# Before German, the tables had no language: all their rows are Croatian.
# translations is Croatian to English, croatian_translations the other way.
# Before the translators package, the cache had DeepL codes ('HR', 'EN-US')
# and no translator: all its rows are from DeepL.
# New table: {old table: the columns of the new table, from the old one}. The
# order counts: translator_cache copies from translation_cache.
MIGRATIONS = {
    "language_lemma_counts": {
        "lemma_counts": "'hr', lemma, upos, count, last_seen",
    },
    "translation_cache": {
        "translations": "'HR', 'EN-US', text, english, created",
        "croatian_translations": "'EN', 'HR', text, croatian, created",
    },
    "translator_cache": {
        "translation_cache": (
            "'deepl', lower(substr(source, 1, 2)), lower(substr(target, 1, 2)),"
            " text, translated, created"
        ),
    },
}
SCHEMA = {
    "language_lemma_counts": (
        "CREATE TABLE language_lemma_counts ("
        " language TEXT NOT NULL, lemma TEXT NOT NULL, upos TEXT NOT NULL,"
        " count INTEGER NOT NULL, last_seen TEXT NOT NULL,"
        " PRIMARY KEY (language, lemma, upos))"
    ),
    # No longer in use: only a step from the oldest tables to translator_cache.
    "translation_cache": (
        "CREATE TABLE translation_cache ("
        " source TEXT NOT NULL, target TEXT NOT NULL, text TEXT NOT NULL,"
        " translated TEXT NOT NULL, created TEXT NOT NULL,"
        " PRIMARY KEY (source, target, text))"
    ),
    # translator is Translator.name. source and target are codes of the app.
    "translator_cache": (
        "CREATE TABLE translator_cache ("
        " translator TEXT NOT NULL, source TEXT NOT NULL, target TEXT NOT NULL,"
        " text TEXT NOT NULL, translated TEXT NOT NULL, created TEXT NOT NULL,"
        " PRIMARY KEY (translator, source, target, text))"
    ),
}


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}
    for table, create in SCHEMA.items():
        if table in tables:
            continue
        # One transaction: a copy that stops in the middle leaves no table,
        # so the next call does it again. The old tables stay as they are.
        # sqlite3 does not open a transaction for CREATE by itself.
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(create)
            for old, columns in MIGRATIONS[table].items():
                if old in tables:
                    conn.execute(f"INSERT INTO {table} SELECT {columns} FROM {old}")
        tables.add(table)
    return conn


def lemma_key(lemma: str, upos: str) -> str:
    # NFKC: one row for the two ways to write the same letter, for example
    # the half-width and the full-width katakana.
    lemma = unicodedata.normalize("NFKC", lemma)
    return lemma if upos == "PROPN" else lemma.lower()


def count_lemmas(language: str, keys: list[tuple[str, str]], track: bool) -> dict:
    """Bump the counts when track is set, then return the count for each key."""
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with _db_lock, db() as conn:
        if track:
            conn.executemany(
                "INSERT INTO language_lemma_counts VALUES (?, ?, ?, 1, ?)"
                " ON CONFLICT (language, lemma, upos) DO UPDATE"
                " SET count = count + 1, last_seen = excluded.last_seen",
                [(language, lemma, upos, now) for lemma, upos in keys],
            )
        seen = {}
        for key in set(keys):
            row = conn.execute(
                "SELECT count FROM language_lemma_counts"
                " WHERE language = ? AND lemma = ? AND upos = ?",
                (language, *key),
            ).fetchone()
            seen[key] = row[0] if row else 0
    return seen


def translate(text: str, source: Language, target: Language) -> str:
    """One language to another through the machine translator of
    translators/, with a cache in SQLite.

    The page sends the text again after each pause in the typing, and each
    call of a translator uses a quota or costs money, so a text is only ever
    sent once.
    """
    translator = translators.current()
    key = (translator.name, source.info.code, target.info.code, text)
    with _db_lock, db() as conn:
        row = conn.execute(
            "SELECT translated FROM translator_cache"
            " WHERE translator = ? AND source = ? AND target = ? AND text = ?",
            key,
        ).fetchone()
    if row:
        return row[0]
    translated = translator.translate(text, source.info.code, target.info.code)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with _db_lock, db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO translator_cache VALUES (?, ?, ?, ?, ?, ?)",
            (*key, translated, now),
        )
    return translated


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    # Warm the light model of the default language and the English model in
    # the background. Both load in a second or two. A classify request that
    # arrives early waits for the load. Another language, or a heavy model,
    # loads on the first request that asks for it.
    for language in (LANGUAGES[languages.DEFAULT], ENGLISH):
        threading.Thread(target=language.warm_up, daemon=True).start()
    # Only does work after the admin changed a deck file.
    threading.Thread(target=decks.import_decks, daemon=True).start()
    yield


app = FastAPI(
    title="Sentence breakdown",
    summary="Break down a Croatian, German, French or Italian sentence, and learn with flashcards.",
    # The schema is at /openapi.json, and the pages are /docs and /redoc.
    description=(
        "A text in a study language becomes sentences and words, each word"
        " with its lemma, its tags and the problems that the checks found."
        " On request, the result has the English translation and the links"
        " between the words of the two sides."
    ),
    version="1",
    openapi_tags=[
        {"name": "breakdown", "description": "The breakdown of a text."},
        {"name": "flashcards", "description": "The decks and the cards of a user."},
        {"name": "speech", "description": "A text read aloud by the voice service."},
    ],
    lifespan=lifespan,
)
app.include_router(auth.router)
app.include_router(flashcard_routes.router)
app.include_router(explain_routes.router)
app.include_router(speech_routes.router)
# static/js and static/css. The login gate below covers these files too.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# On a fly.dev hostname, every route but /healthz and /auth/* needs a session
# from the OIDC login (auth.py). Defined before access_log, so it runs inside
# it and the refused requests are logged too.
@app.middleware("http")
async def require_login(request: Request, call_next):
    return auth.gate(request) or await call_next(request)


# Apache common log format plus the latency, like Apache's
# '%h %l %u %t "%r" %>s %b %D' but in milliseconds and not microseconds:
#   1.2.3.4 - - [19/Sep/2026:09:30:00 +0000] "POST /api/v1/classify HTTP/1.1" 200 512 41.7ms
# uvicorn's own access log has no latency, so run it with --no-access-log.
# /healthz has no line: the health checks of Fly and of compose call it every
# few seconds.
@app.middleware("http")
async def access_log(request: Request, call_next):
    if request.url.path == "/healthz":
        return await call_next(request)
    start = time.perf_counter()
    status, size = 500, "-"
    try:
        response = await call_next(request)
        status = response.status_code
        size = response.headers.get("content-length", "-")
        return response
    finally:
        # Behind the Fly proxy, the peer address is the proxy.
        host = request.headers.get("fly-client-ip") or (
            request.client.host if request.client else "-"
        )
        target = request.url.path
        if request.url.query:
            target += "?" + request.url.query
        access_logger.info(
            '%s - %s [%s] "%s %s HTTP/%s" %s %s %.1fms',
            host,
            # The logged-in user, from require_login.
            getattr(request.state, "user", "-"),
            datetime.now(UTC).strftime("%d/%b/%Y:%H:%M:%S %z"),
            request.method,
            target,
            request.scope.get("http_version", "1.1"),
            status,
            size,
            (time.perf_counter() - start) * 1000,
        )


# An error with a message in the catalogs of the page: `detail` is the English
# text as before, and `code` and `params` name the message "error-{code}".
@app.exception_handler(CodedHTTPException)
async def coded_error(request: Request, exc: CodedHTTPException) -> JSONResponse:
    return JSONResponse(
        {"detail": exc.detail, "code": exc.code, "params": exc.params},
        status_code=exc.status_code,
        headers=exc.headers,
    )


# The signed session cookie for the OIDC login (auth.py). The last added
# middleware runs first, so this one must come after the decorated ones above:
# request.session then already exists inside require_login.
app.add_middleware(
    SessionMiddleware,
    secret_key=auth.SESSION_SECRET,
    max_age=auth.SESSION_MAX_AGE,
    same_site="lax",
    https_only=True,
)


class ClassifyRequest(schemas.Model):
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    """The text to break down, in the language of `source`."""
    heavy: bool = False
    """Use the heavy models of the study language. They are more exact, and
    the first request waits for their load. English only has a light model."""
    nonstandard: bool = False
    """Use the heavy models for casual text. Only Croatian has them."""
    track: bool = True
    """Count each lemma of the text, for `seen` and for /api/v1/lemmas."""
    translate: bool = False
    """Also translate the text to English, and link the words of the two
    sides."""
    language: str = languages.DEFAULT
    """The study language: a `code` from /api/v1/languages."""
    source: Literal["study", "en"] = "study"
    """Which side the user entered. "en": translate the text to the study
    language first, and break down that text. `translate` and `nonstandard`
    then have no effect, because the translator writes the standard language."""

    @field_validator("language")
    @classmethod
    def known_language(cls, value: str) -> str:
        if value not in LANGUAGES:
            raise ValueError(f"must be one of {', '.join(LANGUAGES)}")
        return value


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


@app.get("/healthz", include_in_schema=False)
def healthz() -> PlainTextResponse:
    return PlainTextResponse("ok")


# A response is the dict of the code: no key that the code did not set.
API: schemas.RouteOptions = {
    "tags": ["breakdown"],
    "response_model_exclude_unset": True,
}


@app.get("/api/v1/languages", response_model=schemas.LanguagesResponse, **API)
def language_list() -> dict:
    """The study languages, English as the other side, and whether the page
    ticks "Large models" by default."""
    return {
        "languages": [dataclasses.asdict(lang.info) for lang in LANGUAGES.values()],
        "english": dataclasses.asdict(ENGLISH.info),
        "large_by_default": os.environ.get("TLHELPER_ALWAYS_LARGE", "") == "1",
    }


@app.get("/api/v1/locales", response_model=schemas.LocalesResponse, **API)
def locale_list() -> dict:
    """The languages that the page has its text in."""
    return {
        "default": locales.DEFAULT,
        "locales": [
            {
                "code": code,
                "name": catalog.language.info.native_name or catalog.language.info.name,
                "direction": catalog.language.info.direction,
            }
            for code, catalog in locales.catalogs().items()
        ],
    }


@app.get(
    "/api/v1/locales/{code}/ui.ftl",
    response_class=PlainTextResponse,
    responses={404: {"description": "No catalog for this code."}},
    **API,
)
def locale_catalog(code: str, request: Request) -> Response:
    """The messages of the page in one language, as a Fluent file."""
    found = locales.read(code)
    if found is None:
        raise HTTPException(status_code=404, detail=f"no locale {code}")
    text, etag = found
    headers = {"etag": etag, "cache-control": "no-cache"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return PlainTextResponse(text, headers=headers)


# The page polls this after it opens, to show that the models still load.
# "loading" is a name for the page ("Croatian heavy") or null.
@app.get("/api/v1/status", response_model=schemas.StatusResponse, **API)
def status() -> dict:
    """Which models are in memory, and which one loads at this moment."""
    loading, loading_model, loaded = None, None, []
    for language in (*LANGUAGES.values(), ENGLISH):
        state = language.status()
        if state["loading"] and not loading:
            loading = f"{language.info.name} {state['loading']}"
            # For a page in another language: it has its own name for each one.
            loading_model = {
                "language": language.info.code,
                "variant": state["loading"],
            }
        loaded += [f"{language.info.name} {name}" for name in state["loaded"]]
    return {"loading": loading, "loading_model": loading_model, "loaded": loaded}


# Plain def, not async: FastAPI runs it in the thread pool, so a slow
# inference does not block /healthz.
@app.post(
    "/api/v1/classify",
    response_model=schemas.ClassifyResponse,
    responses=schemas.MODELS_MISSING,
    **API,
)
def classify(req: ClassifyRequest) -> dict:
    """Break a text into sentences and words, with the lemma, the tags and
    the grammar problems of each word. A translation that fails is an `error`
    in `translation`, and the breakdown is still there."""
    language = LANGUAGES[req.language]
    try:
        if req.source == "en":
            return classify_english(req, language)
        return classify_study(req, language)
    except ModelsMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def classify_study(req: ClassifyRequest, language: Language) -> dict:
    """The user entered a text in the study language."""
    variant = model_type(language, req.heavy, req.nonstandard)
    sentences = study_words(language, req.text, variant, req.track)
    result = {
        "type": variant,
        "language": req.language,
        "source": "study",
        "text": req.text,
        "sentences": sentences,
    }
    if req.translate:
        # A failed translation must not lose the other result.
        try:
            english_text = translate(req.text, language, ENGLISH)
            # A text from DeepL does not need the checks.
            english_sentences = ENGLISH.analyze(english_text, check=False)
            result["translation"] = {
                "text": english_text,
                "sentences": english_sentences,
                # "links" and "guesses": pairs of indexes over the words of
                # all sentences, in order. links come from the dictionary,
                # guesses from the position.
                **align.align(language, sentences, english_sentences),
            }
        except TranslationError as exc:
            logger.warning("no translation: %s", exc)
            result["translation"] = translation_error(exc)
    return result


def translation_error(exc: TranslationError) -> dict:
    """The keys of schemas.Translation for a failed translation."""
    error = {"error": str(exc)}
    if exc.code:
        error |= {"error_code": exc.code, "error_params": exc.params}
    return error


def classify_english(req: ClassifyRequest, language: Language) -> dict:
    """The user entered English. The result has the same shape as for a text
    in the study language: "sentences" is the side of the study language and
    "translation" is the English side, so the links keep their meaning. DeepL
    writes the standard language, so the nonstandard models have no use here."""
    english_sentences = ENGLISH.analyze(req.text, check=True)
    variant = model_type(language, req.heavy)
    result = {
        "type": variant,
        "language": req.language,
        "source": "en",
        "text": "",
        "sentences": [],
    }
    result["translation"] = {"text": req.text, "sentences": english_sentences}
    try:
        study_text = translate(req.text, ENGLISH, language)
    except TranslationError as exc:
        # The checks of the English text are still of use.
        logger.warning("no translation: %s", exc)
        result["translation"] |= translation_error(exc)
        return result
    result["text"] = study_text
    if study_text.strip():
        result["sentences"] = study_words(language, study_text, variant, req.track)
    result["translation"] |= align.align(
        language, result["sentences"], english_sentences
    )
    return result


def study_words(language: Language, text: str, variant: str, track: bool) -> list[dict]:
    """Tag a text in the study language, check its grammar, and count its
    lemmas."""
    sentences = language.analyze(text, variant=variant, check=True)
    words = [word for sentence in sentences for word in sentence["words"]]
    keys = [
        (lemma_key(word["lemma"], word["upos"]), word["upos"])
        for word in words
        if word["upos"] not in UNTRACKED_UPOS
    ]
    seen = count_lemmas(language.info.code, keys, track)
    for word in words:
        key = (lemma_key(word["lemma"], word["upos"]), word["upos"])
        word["seen"] = seen.get(key)
    return sentences


@app.get("/api/v1/lemmas", response_model=schemas.LemmasResponse, **API)
def lemmas(
    limit: int = Query(50, ge=1, le=1000, description="How many lemmas."),
    language: str = Query(
        languages.DEFAULT, description="A `code` from /api/v1/languages."
    ),
) -> dict:
    """The lemmas that were in the most texts, for one language."""
    with _db_lock, db() as conn:
        rows = conn.execute(
            "SELECT lemma, upos, count, last_seen FROM language_lemma_counts"
            " WHERE language = ? ORDER BY count DESC, lemma LIMIT ?",
            (language, limit),
        ).fetchall()
    return {
        "lemmas": [
            {"lemma": lemma, "upos": upos, "count": count, "last_seen": last_seen}
            for lemma, upos, count, last_seen in rows
        ]
    }
