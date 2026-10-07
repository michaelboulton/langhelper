"""Tests for languages/italian. They run the real spaCy model, which is a
dependency (it_core_news_md), so nothing is faked."""

import pytest
from tlhelper.languages import LANGUAGES
from tlhelper.languages.base import STUDY

ITALIAN = LANGUAGES["it"]


def problems(text):
    """{word: its problems} for the words that have one."""
    return {
        word["text"]: word["problems"]
        for sentence in ITALIAN.analyze(text)
        for word in sentence["words"]
        if word["problems"]
    }


def test_words_have_the_keys_of_the_other_languages():
    [sentence] = ITALIAN.analyze("I gatti neri dormono.")
    assert sentence["words"][2] == {
        "id": 3,
        "text": "neri",
        "lemma": "nero",
        "upos": "ADJ",
        # The ISDT tag set: A is an adjective.
        "xpos": "A",
        "feats": {"Gender": "Masc", "Number": "Plur"},
        "head": 2,
        "deprel": "amod",
        "start_char": 8,
        "end_char": 12,
        "problems": [],
    }


def test_a_preposition_with_an_article_is_one_word():
    [sentence] = ITALIAN.analyze("Il gatto dorme sul divano.")
    sul = sentence["words"][3]
    assert (sul["text"], sul["lemma"], sul["upos"], sul["xpos"]) == (
        "sul",
        "su il",
        "ADP",
        "E_RD",
    )


@pytest.mark.parametrize(
    "text",
    [
        "Il gatto nero dorme sul divano.",
        "Vado al mercato con la mia amica.",
        "L'amico di mia sorella è arrivato dalla stazione.",
        "Ho una piccola casa nella città.",
        "Non ho mai visto un'opera così bella.",
        "Ci sono molti libri interessanti.",
        "Io sto mangiando una mela.",
        "Me lo ha detto ieri.",
        "Noi ci laviamo le mani.",
        "C'è un problema.",
    ],
)
def test_a_correct_sentence_has_no_problems(text):
    assert problems(text) == {}


def test_agreement():
    [reason] = problems("Ho una piccolo gatto.")["una"]
    assert reason == (
        "Does not agree with 'gatto': this form is feminine, but the noun is"
        " masculine (gender)."
    )
    # An adjective before the noun, and one after it.
    assert list(problems("Vedo la piccolo casa.")) == ["piccolo"]
    [reason] = problems("Ha una macchina rosse.")["rosse"]
    assert reason.endswith("this form is plural, but the noun is singular (number).")


def test_repeat_and_spelling():
    found = problems("Io io mangio la maccina.")
    assert found["io"] == ["'io' repeats."]
    assert found["maccina"] == [
        "The Italian word list does not have this word. Did you mean 'macchina'?"
    ]


def test_glosses():
    assert ITALIAN.glosses("anguille", "anguilla", "NOUN") == {"eel": 0}
    assert "cat" in ITALIAN.glosses("gatto", "gatto", "NOUN")
    # Wiktionary glosses the article with "the", which the build drops as a
    # stopword, so the article has only its extra gloss.
    assert ITALIAN.glosses("il", "il", "DET") == {}
    assert ITALIAN.extra_glosses["il"] == ["the"]


def test_another_model_drops_the_italian_model():
    ITALIAN.analyze("Ciao.")
    assert ITALIAN.status() == {"loading": None, "loaded": ["light"]}
    with STUDY.use(("hr", "heavy"), lambda: "pipeline"):
        assert ITALIAN.status() == {"loading": None, "loaded": []}
    STUDY.drop()
