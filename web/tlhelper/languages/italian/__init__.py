"""Italian: tagged by spaCy (it_core_news_md), with grammar checks (checks.py).
It has only the light model."""

from pathlib import Path
from typing import ClassVar

from ..base import STUDY, LanguageInfo
from ..glosses import GlossFile
from ..spacy_words import SpacyTagger
from . import checks

GLOSSES_PATH = Path(__file__).with_name("glosses.db")


class Italian:
    info = LanguageInfo(
        code="it",
        name="Italian",
        # The Tanl tags of the Italian Stanford Dependency Treebank: S noun,
        # A adjective, RD definite article, E_RD preposition with an article.
        tag_name="ISDT tag",
        placeholder="Il gatto nero dorme sul divano.",
        variants=("light",),
        speech="it-IT",
        dictionary_links=(
            ("WordReference: {lemma}", "https://www.wordreference.com/iten/{lemma}"),
            ("Treccani: {lemma}", "https://www.treccani.it/vocabolario/{lemma}/"),
        ),
        ui_locale="it",
        native_name="Italiano",
    )
    # Wiktionary glosses the articles with "the" and "a", which the gloss
    # build drops as stopwords, and "a" and "essere" with prose. spaCy gives
    # a preposition with an article (sul, della) a lemma of two words.
    extra_glosses: ClassVar[dict[str, list[str]]] = {
        "il": ["the"],
        "uno": ["a", "an", "one"],
        "a il": ["to", "at", "the"],
        "di il": ["of", "some", "the"],
        "da il": ["from", "the"],
        "in il": ["in", "the"],
        "su il": ["on", "the"],
        "con il": ["with", "the"],
        "a": ["to", "at", "in"],
        "essere": ["be"],
        "non": ["not"],
        "ne": ["of it", "of them", "some"],
        "ci": ["there", "us", "ourselves"],
    }

    def __init__(self):
        self.taggers = {
            "light": SpacyTagger(
                "it_core_news_md", checks.check, slot_key=(self.info.code, "light")
            ),
        }
        self.gloss_file = GlossFile(GLOSSES_PATH)

    def warm_up(self) -> None:
        self.taggers["light"].warm_up()

    def status(self) -> dict:
        return STUDY.status(self.info.code)

    def analyze(
        self, text: str, *, variant: str = "light", check: bool = True
    ) -> list[dict]:
        return self.taggers[variant].words(text, check)

    def glosses(self, text: str, lemma: str, upos: str) -> dict[str, int]:
        return self.gloss_file.glosses_for(text, lemma, upos)
