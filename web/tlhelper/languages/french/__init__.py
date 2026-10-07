"""French: tagged by spaCy (fr_core_news_md), with grammar checks (checks.py).
It has only the light model."""

from pathlib import Path
from typing import ClassVar

from ..base import STUDY, Grading, LanguageInfo
from ..glosses import GlossFile
from ..spacy_words import SpacyTagger
from . import checks

GLOSSES_PATH = Path(__file__).with_name("glosses.db")


class French:
    info = LanguageInfo(
        code="fr",
        name="French",
        # The model gives no tags of its own, so the page shows none.
        tag_name="UD tag",
        placeholder="Mon aéroglisseur est plein d'anguilles.",
        variants=("light",),
        speech="fr-FR",
        dictionary_links=(
            ("WordReference: {lemma}", "https://www.wordreference.com/fren/{lemma}"),
            ("CNRTL: {lemma}", "https://www.cnrtl.fr/definition/{lemma}"),
        ),
        ui_locale="fr",
        native_name="Français",
        grading=Grading(plain_letters=(("œ", ("oe",)), ("æ", ("ae",)))),
    )
    # The articles are the lemmas of la, les, une, du and d'. Wiktionary gives
    # them only their pronoun senses, or grammar text.
    extra_glosses: ClassVar[dict[str, list[str]]] = {
        "le": ["the"],
        "un": ["a", "an"],
        "de": ["of", "some", "any"],
        "au": ["to", "at", "in", "the"],
        "ne": ["not"],
        "pas": ["not"],
        # spaCy gives "belle" the lemma "bel", and Wiktionary has it as "beau".
        "bel": ["beautiful", "handsome", "fine", "nice"],
    }

    def __init__(self):
        self.taggers = {
            "light": SpacyTagger(
                "fr_core_news_md", checks.check, slot_key=(self.info.code, "light")
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
