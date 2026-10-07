"""The light Croatian model: spaCy hr_core_news_md, 64 MB. It loads in a
second. It comes from the same corpus as the classla models (hr500k), so it
has the same tags, but it is less exact: spaCy reports about 92 of 100 correct
lemmas and cases. It reads "Pijem" as a noun, for example."""

from ..spacy_words import SpacyTagger
from . import accents, grammar

LANG = "hr"


class WiktionaryLexicon(grammar.Lexicon):
    """The noun forms of accents.db, in place of the hrLex lexicon that only
    the classla models hold. Only some nouns have their case forms there, and
    that is too few for a spelling check. A noun with no forms there passes:
    the light model is the default, and a miss is better than a wrong flag on
    a correct sentence ("pun je jegulja")."""

    spelling = False

    def __init__(self):
        super().__init__({}, {})

    def noun_can_be(self, text: str, case: str) -> bool:
        return accents.noun_can_be(text, case) is not False


LEXICON = WiktionaryLexicon()


def check(tokens: list, words: list[dict]) -> None:
    grammar.check(words, LEXICON)


TAGGER = SpacyTagger("hr_core_news_md", check, slot_key=(LANG, "light"))
