"""The languages of the app. English is always one side of a translation, and
the user selects the other side from LANGUAGES.

To add a language: make a subfolder with a class that implements
base.Language, add it here, and build its gloss file (build_glosses.py). The
machine translator (translators/) must have the language, with a map of its
code if the service has another one, and a tagger must exist for it.
"""

from .base import Language, LanguageInfo, ModelsMissing
from .croatian import Croatian
from .english import English
from .french import French
from .german import German
from .italian import Italian

ENGLISH: Language = English()
# The first one is the default, and the only one that loads at the start.
LANGUAGES: dict[str, Language] = {
    language.info.code: language
    for language in (Croatian(), German(), French(), Italian())
}
DEFAULT = next(iter(LANGUAGES))


def model_type(language: Language, heavy: bool, nonstandard: bool = False) -> str:
    """A language with no such models gives its default, the light ones."""
    variants = language.info.variants
    if nonstandard and "nonstandard" in variants:
        return "nonstandard"
    if heavy and "heavy" in variants:
        return "heavy"
    return variants[0]


__all__ = [
    "DEFAULT",
    "ENGLISH",
    "LANGUAGES",
    "Language",
    "LanguageInfo",
    "ModelsMissing",
    "model_type",
]
