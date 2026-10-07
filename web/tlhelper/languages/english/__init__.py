"""English: the other side of each study language. Tagged by spaCy."""

from typing import ClassVar

from ..base import LanguageInfo
from ..spacy_words import SpacyTagger
from . import checks


def english_upos(token) -> str:
    """The Penn Treebank convention tags a participle as a verb (VBG, VBN) even
    before a noun: "my floating boat". The parser marks that use as amod
    (adjective modifier), and a reader expects an adjective there."""
    if token.tag_ in ("VBG", "VBN") and token.dep_ == "amod":
        return "ADJ"
    return token.pos_


class English:
    info = LanguageInfo(
        code="en",
        name="English",
        tag_name="Penn Treebank tag",
        speech="en-US",
        placeholder="My hovercraft is full of eels.",
        ui_locale="en",
        native_name="English",
    )
    extra_glosses: ClassVar[dict[str, list[str]]] = {}

    def __init__(self):
        self.tagger = SpacyTagger("en_core_web_sm", checks.check, english_upos)

    def warm_up(self) -> None:
        self.tagger.warm_up()

    def status(self) -> dict:
        return {
            "loading": "light" if self.tagger.loading else None,
            "loaded": ["light"] if self.tagger.loaded else [],
        }

    def analyze(
        self, text: str, *, variant: str = "light", check: bool = True
    ) -> list[dict]:
        """check: the user entered this text, so each word also gets a
        'problems' list (checks.py). A text from DeepL does not need that."""
        return self.tagger.words(text, check)

    def glosses(self, text: str, lemma: str, upos: str) -> dict[str, int]:
        return {}
