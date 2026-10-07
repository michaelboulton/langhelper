"""The text of the page in each language: one Fluent file (ui.ftl) in the
folder of a language that has LanguageInfo.ui_locale. The page gets the file
as it is and formats the messages (static/js/i18n.js), so Python only names a
message: a Message has the id and the parameters, and the English text for a
client that has no catalog.
"""

import hashlib
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .languages import ENGLISH, LANGUAGES, Language

CATALOG_NAME = "ui.ftl"
# The complete catalog. A message that is not in another one comes from here.
DEFAULT = ENGLISH.info.ui_locale


@dataclass(frozen=True)
class Catalog:
    language: Language
    path: Path


def _folder(language: Language) -> Path:
    """The folder of the package of the language."""
    return Path(sys.modules[type(language).__module__].__file__).parent


@lru_cache(maxsize=1)
def catalogs() -> dict[str, Catalog]:
    """The locales by code, English first. A language with ui_locale and no
    file is not here."""
    found = {}
    for language in (ENGLISH, *LANGUAGES.values()):
        path = _folder(language) / CATALOG_NAME
        if language.info.ui_locale and path.is_file():
            found[language.info.ui_locale] = Catalog(language, path)
    return found


def read(code: str) -> tuple[str, str] | None:
    """(the text of the catalog, its ETag), or None for an unknown code."""
    catalog = catalogs().get(code)
    if catalog is None:
        return None
    data = catalog.path.read_bytes()
    return data.decode("utf-8"), '"' + hashlib.sha256(data).hexdigest()[:32] + '"'


def english_name(code: str) -> str:
    """The English name of the language of a locale: "German" for "de"."""
    catalog = catalogs().get(code) or catalogs()[DEFAULT]
    return catalog.language.info.name
