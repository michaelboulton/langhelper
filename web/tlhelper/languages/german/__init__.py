"""German: tagged by spaCy, with grammar checks (checks.py). classla has no
German models. The light model is de_core_news_md and the heavy one is
de_dep_news_trf."""

from pathlib import Path
from typing import ClassVar

from ..base import STUDY, Grading, LanguageInfo
from ..glosses import GlossFile
from ..spacy_words import SpacyTagger
from . import checks

# The data of a language is in the folder of the language.
GLOSSES_PATH = Path(__file__).with_name("glosses.db")


class German:
    info = LanguageInfo(
        code="de",
        name="German",
        tag_name="STTS tag",
        placeholder="Mein Luftkissenfahrzeug ist voller Aale.",
        variants=("light", "heavy"),
        speech="de-DE",
        dictionary_links=(
            ("dict.cc: {lemma}", "https://www.dict.cc/?s={lemma}"),
            ("DWDS: {lemma}", "https://www.dwds.de/wb/{lemma}"),
        ),
        ui_locale="de",
        native_name="Deutsch",
        # "ae" for "ä", and also only "a".
        grading=Grading(
            plain_letters=(
                ("ä", ("ae", "a")),
                ("ö", ("oe", "o")),
                ("ü", ("ue", "u")),
                ("ß", ("ss",)),
            )
        ),
    )
    # A contraction has the lemma of its preposition, and Wiktionary has the
    # articles as forms of "der" with a grammar text and no translation.
    extra_glosses: ClassVar[dict[str, list[str]]] = {
        "der": ["the", "that", "who", "which"],
        "ein": ["a", "an", "one"],
        "kein": ["no", "not"],
        "nicht": ["not"],
        "sein": ["be", "his", "its"],
        # spaCy keeps the case form of a pronoun as its lemma, and Wiktionary
        # has those as forms of "ich" and so on, again with no translation.
        "mich": ["me", "myself"],
        "mir": ["me", "myself"],
        "dich": ["you", "yourself"],
        "dir": ["you", "yourself"],
        "ihn": ["him", "it"],
        "ihm": ["him", "it"],
        "uns": ["us", "ourselves"],
        "euch": ["you", "yourselves"],
        "ihnen": ["them", "you"],
        "sich": ["himself", "herself", "itself", "themselves", "yourself"],
    }

    def __init__(self):
        code = self.info.code
        self.taggers = {
            # The md model has about 300 MB of word vectors. The sm model has
            # none, but its tags miss more errors ("mit der Hund").
            "light": SpacyTagger(
                "de_core_news_md", checks.check, slot_key=(code, "light")
            ),
            # A BERT model, 391 MB on disk. It gets 97 of 100 cases and
            # genders, where the md model gets 92. Both have the TIGER labels
            # and the STTS tags, so checks.py is the same.
            "heavy": SpacyTagger(
                "de_dep_news_trf", checks.check, slot_key=(code, "heavy")
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
