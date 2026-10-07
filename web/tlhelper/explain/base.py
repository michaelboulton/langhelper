"""What every AI backend has in common, and what a question is."""

from dataclasses import dataclass
from typing import Literal, Protocol

from ..messages import CodedError

# For the request of a backend, in seconds. A model needs a few seconds for an
# answer, so this is much more than the time limit of a translator.
TIMEOUT = 30
# The most tokens of one answer. SYSTEM asks for much less.
MAX_TOKENS = 500
# The most characters of what the user adds to a question.
MAX_CONTEXT_CHARS = 300


class ExplainError(CodedError):
    """The message goes to the page: the English text, and for an error with
    a code, the message "error-{code}" of the catalogs."""


@dataclass(frozen=True)
class Question:
    """A question that the user can select. The server writes the prompt: the
    page sends only the id and the context of the user."""

    id: str
    # The text of the button.
    label: str
    # "sentence": about one text, on each tab. "card": about an answer to a
    # flashcard, so it needs a review.
    where: Literal["sentence", "card"]
    # A str.format string. prompt.VARIABLES has the names that it can use.
    template: str
    # The names that the template uses, and thus the values that it needs.
    variables: tuple[str, ...]


class Backend(Protocol):
    # The value of TLHELPER_AI_BACKEND that selects this one.
    name: str

    def available(self) -> bool:
        """The backend has its credentials. If not, the page has no buttons."""

    def model(self) -> str:
        """The model that answers, for the page and for the cache key."""

    def complete(
        self,
        system: str,
        prompt: str,
        *,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> str:
        """One request to the service, with no cache. Raises ExplainError on
        every failure. max_tokens and timeout replace the defaults of the
        service for this one request: a long answer (scripts/lessons.py)
        needs more than the app gives a question."""
