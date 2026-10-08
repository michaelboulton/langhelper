"""The shapes of the API, for the OpenAPI schema (/openapi.json, /docs).

The code builds plain dicts, and a route gives its shape as response_model.
The docstring under an attribute is its description in the schema. A key that
is not always there is optional here, and a route leaves out the unset keys
(response_model_exclude_unset), so a response is the dict as the code made it.
"""

from enum import Enum
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, model_validator

from .messages import Problem


class Model(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)


class RouteOptions(TypedDict, total=False):
    """Keyword arguments that several routes share, as `**options`."""

    tags: list[str | Enum]
    response_model_exclude_unset: bool


# The type of the `responses` argument of a route.
Responses = dict[int | str, dict[str, Any]]


# The breakdown of a text


class Accent(Model):
    form: str
    """The word with its accent marks. " / " is between two possible forms."""
    exact: bool
    """False: the accent is that of the dictionary form, and not of this form."""
    ambiguous: bool = False
    """The data has more than one accented form for this word."""
    clitic: bool = False
    """The word has no accent of its own."""


class ProblemMessage(Model):
    key: str
    """The id of a message in /api/v1/locales/{code}/ui.ftl."""
    params: dict[str, str | int | list[str]]
    """The parameters of the message. A value is a raw tag ("Loc"), and the
    catalog has the word for it."""


class Word(Model):
    @model_validator(mode="before")
    @classmethod
    def messages_of_problems(cls, data):
        """The checks give a messages.Problem: a str with the message in it."""
        if not isinstance(data, dict) or not data.get("problems"):
            return data
        if "problem_messages" in data:
            return data
        return {
            **data,
            "problem_messages": [
                {"key": problem.key, "params": problem.params}
                if isinstance(problem, Problem)
                else None
                for problem in data["problems"]
            ],
        }

    id: int
    """The position in the sentence, from 1."""
    text: str
    lemma: str
    """The dictionary form."""
    upos: str
    """The Universal POS tag, for example "NOUN"."""
    xpos: str
    """The tag of the tag set of the language (LanguageInfo.tag_name)."""
    feats: dict[str, str]
    """The Universal features, for example {"Case": "Nom", "Number": "Sing"}."""
    head: int = 0
    """The `id` of the word that this word depends on. 0 for the root of the
    sentence, and for a tagger with no parser (classla)."""
    deprel: str = ""
    """The relation to the head, in the labels of the model: "obj" for
    Croatian (Universal Dependencies), "oa" for German (TIGER). Empty for a
    tagger with no parser."""
    start_char: int
    """The position of the first letter in the text."""
    end_char: int
    """The position after the last letter in the text."""
    problems: list[str] = []
    """What the grammar and spelling checks found, in English. Only with the
    checks."""
    problem_messages: list[ProblemMessage | None] = []
    """The message of each entry of `problems`, in the same order, for a page
    in another language. Null for a problem with no message. Absent if the
    word has no problem."""
    accent: Accent | None = None
    """The pitch accent. Only for Croatian, and null for a word with no data."""
    reading: str = ""
    """How to say the word, for a script that does not show it. No language
    of today gives it."""
    seen: int | None = None
    """How often the lemma was in a text before. Null for a lemma with no
    count, for example punctuation. Only in /api/v1/classify."""


class Sentence(Model):
    text: str
    words: list[Word]


class Links(Model):
    links: list[tuple[int, int]] = []
    """Pairs [word of the study language, English word] from the dictionary.
    An index counts the words of all the sentences of a side, from 0."""
    guesses: list[tuple[int, int]] = []
    """Pairs like links, but only from the position of the two words."""


class Translation(Links):
    text: str = ""
    """The English side."""
    sentences: list[Sentence] = []
    error: str = ""
    """Why there is no translation, in English. The other keys can then be
    absent."""
    error_code: str = ""
    """The message "error-{error_code}" of /api/v1/locales/{code}/ui.ftl has
    the same text for a page in another language. Not for each error."""
    error_params: dict[str, str | int] = {}
    """The parameters of that message."""


class ClassifyResponse(Model):
    type: str
    """The model type that made the breakdown: "light", "heavy" or
    "nonstandard"."""
    language: str
    source: Literal["study", "en"]
    text: str
    """The text in the study language: from the user, or from the translator.
    Empty after a translation that failed."""
    sentences: list[Sentence]
    """The side of the study language."""
    translation: Translation | None = None
    """The English side. Only with `translate`, or with the source "en"."""


class LanguageInfo(Model):
    code: str
    """ISO 639-1. This is the `language` of a request."""
    name: str
    tag_name: str
    """The name of the xpos tag set."""
    placeholder: str
    """An example text for the input field."""
    variants: list[str]
    """The model types. The first one is the default."""
    light_note: str
    """What the light model cannot do, if the heavy one can."""
    has_accents: bool
    direction: Literal["ltr", "rtl"]
    """The direction of the script: the `dir` of a text in this language."""
    speech: str
    """The BCP 47 tag for the speech synthesis of the browser."""
    dictionary_links: list[tuple[str, str]]
    """(label, address). "{lemma}" in either one becomes the lemma of a word."""
    ui_locale: str = ""
    """The `code` of the page text in this language (/api/v1/locales). Empty:
    the page has no text in this language."""
    native_name: str = ""
    """The name of the language in the language."""


class Locale(Model):
    code: str
    """BCP 47. The catalog is /api/v1/locales/{code}/ui.ftl."""
    name: str
    """The name of the language in the language, for example "Hrvatski"."""
    direction: Literal["ltr", "rtl"]
    """The direction of the script: the `dir` of the page."""


class LocalesResponse(Model):
    default: str
    """The complete catalog. A message that another catalog does not have
    comes from this one."""
    locales: list[Locale]
    """The default one first."""


class LanguagesResponse(Model):
    languages: list[LanguageInfo]
    """The study languages."""
    english: LanguageInfo
    """The other side of each study language."""
    large_by_default: bool
    """True: TLHELPER_ALWAYS_LARGE is 1, as in the compose file. The page then
    ticks "Large models" until the user makes a choice."""


class LoadingModel(Model):
    language: str
    """A `code` from /api/v1/languages."""
    variant: str
    """The model type, for example "heavy"."""


class StatusResponse(Model):
    loading: str | None
    """The model that loads at this moment, for example "Croatian heavy"."""
    loading_model: LoadingModel | None = None
    """The same model, as values."""
    loaded: list[str]
    """The models in memory."""


class LemmaCount(Model):
    lemma: str
    upos: str
    count: int
    last_seen: str
    """ISO 8601, UTC."""


class LemmasResponse(Model):
    lemmas: list[LemmaCount]
    """The most frequent lemma first."""


# The flashcards


class Counts(Model):
    total: int
    """The cards of the deck."""
    new: int
    """The cards that the user never answered."""
    learning: int
    """The cards in the short learning steps."""
    due: int
    """The cards in review whose next review time is now or in the past."""


class Deck(Model):
    id: int
    name: str
    language: str
    path: list[str]
    """The place in the deck tree, for a deck of a package with subdecks:
    ["Croatian sentences", "Read", "2"]. Empty for a deck on its own."""
    counts: Counts


class DecksResponse(Model):
    decks: list[Deck]


class Media(Model):
    kind: Literal["image", "audio"]
    url: str


Direction = Literal["to_study", "to_english"]


class NextCard(Model):
    card_id: int
    direction: Direction
    """ "to_study": the prompt is English, and the user enters the study
    language. "to_english" is the other way round."""
    language: str
    prompt: str
    media: list[Media]
    """The images and the sound clips of the prompt."""
    prompt_sentences: list[Sentence]
    """The breakdown of the prompt."""
    counts: Counts


class NoCard(Model):
    done: Literal[True]
    next_due: str | None
    """When the next card comes, ISO 8601. Null: the deck has no more cards."""
    counts: Counts


class LinkedAnswer(Links):
    sentences: list[Sentence]


class AnswerResponse(Model):
    review_id: int
    """The key for a change of the rating."""
    rating: int
    """The automatic rating: 1 Again, 2 Hard, 3 Good, 4 Easy."""
    next_due: str
    """When the card comes again, ISO 8601."""
    diff: list[tuple[Literal["equal", "delete", "insert"], str]]
    """The typed answer against the closest accepted answer. "delete" is a
    typed part that is wrong, and "insert" is a part that is missing."""
    answers: list[str]
    """All the accepted answers."""
    media: list[Media]
    """The images and the sound clips of the answer."""
    typed: LinkedAnswer
    """The typed answer, with the checks and the links to the prompt."""
    correct: LinkedAnswer
    """The closest accepted answer, with the links to the prompt."""


class RatingResponse(Model):
    rating: int
    next_due: str


class FlashcardUser(Model):
    id: str
    """The `sub` claim of the login."""
    name: str


class UsersResponse(Model):
    me: str
    admin: bool
    users: list[FlashcardUser]
    """The own entry first. The other users are only there for an admin."""


class StatsDay(Model):
    date: str
    reviews: int
    passed: int
    """The reviews with a rating other than "Again"."""


class StatsResponse(Model):
    counts: Counts | dict[str, int]
    """The sum over the decks. Empty if there is no deck."""
    reviews: int
    success_rate: float | None
    """The share of the reviews that were not "Again". Null with no reviews."""
    lapses: int
    """How often a card in review got "Again"."""
    streak_days: int
    days: list[StatsDay]
    """One entry for each of the last days, the oldest first. A day starts at
    00:00 UTC."""


# The "explain with AI" buttons


class ExplainQuestion(Model):
    id: str
    """The `question` of a request."""
    label: str
    """The text of the button."""
    where: Literal["sentence", "card"]
    """ "sentence": about a text, for each of the two routes. "card": about an
    answer to a flashcard, only for the route of a review."""


class QuestionsResponse(Model):
    available: bool
    """False: the server has no key for an AI service, so each request fails."""
    model: str
    """The model that answers. Empty if none is set."""
    max_context_chars: int
    """The most characters of `user_context`."""
    questions: list[ExplainQuestion]
    """In the order of the buttons."""


class ExplainResponse(Model):
    text: str
    """The answer of the model, as plain text. It can be wrong."""
    model: str
    """The model that wrote the answer."""
    cached: bool
    """The answer is from an earlier, equal request."""


class SpeechInfoResponse(Model):
    available: bool
    """A voice service is set up. If not, the page has no "Listen" buttons."""
    model: str
    """The model that reads aloud. Empty if none is set."""
    languages: list[str]
    """The codes of the languages that the service reads aloud: study
    languages, and "en"."""


class ErrorResponse(Model):
    detail: str


NOT_FOUND: Responses = {
    404: {"model": ErrorResponse, "description": "No such deck or card"}
}
MODELS_MISSING: Responses = {
    503: {"model": ErrorResponse, "description": "The models are not on the disk"}
}
EXPLAIN_ERRORS: Responses = {
    429: {"model": ErrorResponse, "description": "The limit of the user for a day"},
    502: {"model": ErrorResponse, "description": "The AI service failed"},
    503: {
        "model": ErrorResponse,
        "description": "No key for an AI service, or the models are not on the disk",
    },
}
SPEECH_ERRORS: Responses = {
    502: {"model": ErrorResponse, "description": "The voice service failed"},
    503: {"model": ErrorResponse, "description": "No voice service is set up"},
}
