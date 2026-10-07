"""What every machine translator has in common."""

from typing import Protocol

from ..messages import CodedError

# For the request of a translator, in seconds. Under the 5 second default time
# limit of the page.
TIMEOUT = 4


class TranslationError(CodedError):
    """The message goes to the page: the English text, and for an error with
    a code, the message "error-{code}" of the catalogs."""


class Translator(Protocol):
    # The value of TRANSLATOR that selects this one, and its key in the cache.
    name: str

    def translate(self, text: str, source: str, target: str) -> str:
        """One request to the service, with no cache: app.translate() has
        the cache. source and target are codes of the app (LanguageInfo.code:
        "hr", "de", "fr", "it", "en"), and the translator maps them to its own
        codes.
        Raises TranslationError on every failure."""
