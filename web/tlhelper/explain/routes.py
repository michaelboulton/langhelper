"""The routes of the "explain with AI" buttons. The package docstring has the
design."""

import hashlib

from fastapi import APIRouter, HTTPException
from pydantic import Field, field_validator

from .. import explain, languages, locales, schemas
from ..flashcards import grade, store
from ..flashcards.routes import User
from ..languages import LANGUAGES, ModelsMissing
from ..messages import CodedHTTPException, coded_http
from ..settings import MAX_TEXT_CHARS

router = APIRouter(prefix="/api/v1", tags=["explain"])
UNSET: schemas.RouteOptions = {"response_model_exclude_unset": True}

RATING_NAMES = {
    grade.AGAIN: "Again",
    grade.HARD: "Hard",
    grade.GOOD: "Good",
    grade.EASY: "Easy",
}


class ExplainRequest(schemas.Model):
    question: str
    """An `id` from /api/v1/explain/questions."""
    user_context: str = Field(default="", max_length=explain.MAX_CONTEXT_CHARS)
    """What the user wants to add to the question. It goes into the prompt as
    data of the user."""
    locale: str = locales.DEFAULT
    """The language of the answer: a `code` from /api/v1/locales."""

    @field_validator("locale")
    @classmethod
    def known_locale(cls, value: str) -> str:
        if value not in locales.catalogs():
            raise ValueError(f"must be one of {', '.join(locales.catalogs())}")
        return value

    @field_validator("question")
    @classmethod
    def known_question(cls, value: str) -> str:
        if value not in explain.QUESTIONS:
            raise ValueError(f"must be one of {', '.join(explain.QUESTIONS)}")
        return value


class ExplainSentenceRequest(ExplainRequest):
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    """A text in the study language."""
    language: str = languages.DEFAULT
    """The study language: a `code` from /api/v1/languages."""

    @field_validator("language")
    @classmethod
    def known_language(cls, value: str) -> str:
        if value not in LANGUAGES:
            raise ValueError(f"must be one of {', '.join(LANGUAGES)}")
        return value


def tagged(language: languages.Language, text: str) -> list[dict]:
    """The breakdown for the notes of the tagger, with the model of this
    language that is in memory. The server holds one study model
    (base.StudySlot), so a question must not ask for another one: that drops
    the model of the page and loads it again after. Only if no model of the
    language is in memory, the default one loads."""
    if not text.strip():
        return []
    loaded = language.status()["loaded"]
    variant = loaded[0] if loaded else language.info.variants[0]
    return language.analyze(text, variant=variant, check=False)


def ask(user: str, question: explain.Question, values: dict[str, str]) -> dict:
    """The answer to a filled question: from the cache, or from the backend.
    values["learner_language"] is the language of the answer. It is in the
    prompt, so the cache has one answer for each language."""
    try:
        backend = explain.current()
        if not backend.available():
            raise CodedHTTPException(
                503, "ai-no-key", "the server has no key for an AI service"
            )
        prompt = explain.build(question, values)
        model = backend.model()
        key = hashlib.sha256(f"{backend.name}\n{model}\n{prompt}".encode()).hexdigest()
        text = store.explanation(key)
        if text is not None:
            return {"text": text, "model": model, "cached": True}
        if store.explanations_today(user) >= explain.PER_DAY:
            raise CodedHTTPException(
                429,
                "ai-limit",
                f"the limit is {explain.PER_DAY} questions in a day",
                limit=explain.PER_DAY,
            )
        text = backend.complete(explain.system(values["learner_language"]), prompt)
    except explain.ExplainError as exc:
        raise coded_http(502, exc) from exc
    store.save_explanation(key, user, model, text)
    return {"text": text, "model": model, "cached": False}


@router.get("/explain/questions", response_model=schemas.QuestionsResponse, **UNSET)
def questions() -> dict:
    """The questions that a user can select, and if an AI service is set up."""
    try:
        backend = explain.current()
        available, model = backend.available(), backend.model()
    except explain.ExplainError:
        available, model = False, ""
    return {
        "available": available,
        "model": model,
        "max_context_chars": explain.MAX_CONTEXT_CHARS,
        "questions": [
            {"id": each.id, "label": each.label, "where": each.where}
            for each in explain.QUESTIONS.values()
        ],
    }


@router.post(
    "/explain",
    response_model=schemas.ExplainResponse,
    responses=schemas.EXPLAIN_ERRORS,
    **UNSET,
)
def explain_sentence(req: ExplainSentenceRequest, user: User) -> dict:
    """Ask the AI a question about a text in the study language. Only a
    question with `where` "sentence"."""
    question = explain.QUESTIONS[req.question]
    if question.where != "sentence":
        raise CodedHTTPException(
            422,
            "ai-needs-review",
            f"{question.id} needs the review of a flashcard",
            question=question.id,
        )
    language = LANGUAGES[req.language]
    try:
        words = tagged(language, req.text)
    except ModelsMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    values = {
        "language": language.info.name,
        "learner_language": locales.english_name(req.locale),
        "sentence_language": language.info.name,
        "sentence": req.text,
        "tagger_notes": explain.notes(words),
        "user_context": req.user_context,
    }
    return ask(user, question, values)


@router.post(
    "/reviews/{review_id}/explain",
    response_model=schemas.ExplainResponse,
    responses=schemas.NOT_FOUND | schemas.EXPLAIN_ERRORS,
    **UNSET,
)
def explain_review(review_id: int, req: ExplainRequest, user: User) -> dict:
    """Ask the AI a question about an answer of the user to a flashcard. The
    server reads the card and the answer from the review. A question with
    `where` "sentence" is about the side of the card in the study language."""
    question = explain.QUESTIONS[req.question]
    try:
        review = store.get_review(user, review_id)
        card = store.get_card(review["card_id"])
        to_study = card["direction"] == store.TO_STUDY
        language = LANGUAGES[card["language"]]
        rules = (language if to_study else languages.ENGLISH).info.grading
        correct = grade.grade(review["typed"], card["answers"], rules)["answer"]
        if to_study:
            entered = tagged(language, review["typed"])
            right = tagged(language, correct)
            tagger = (
                f"entered: {explain.notes(entered)}; correct: {explain.notes(right)}"
            )
            # A question about the sentence is not about the entered answer.
            if question.where == "sentence":
                tagger = explain.notes(right)
            sentence = correct
        else:
            # The prompt of a "to_english" card is in the study language.
            tagger = explain.notes(tagged(language, card["prompt"]))
            sentence = card["prompt"]
    except store.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelsMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    values = {
        "language": language.info.name,
        "learner_language": locales.english_name(req.locale),
        "sentence_language": language.info.name,
        "sentence": sentence,
        "flashcard_input": card["prompt"] or "(a picture or a sound)",
        "user_input": review["typed"] or "(nothing: the learner did not know)",
        "correct_answer": correct,
        "accepted_answers": " / ".join(card["answers"]),
        "grade": RATING_NAMES[review["auto_rating"]],
        "tagger_notes": tagger,
        "user_context": req.user_context,
    }
    return ask(user, question, values)
