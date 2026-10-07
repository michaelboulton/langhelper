"""Tests for languages/french. They run the real spaCy model, which is a
dependency (fr_core_news_md), so nothing is faked."""

import pytest
from tlhelper.languages import LANGUAGES
from tlhelper.languages.base import STUDY

FRENCH = LANGUAGES["fr"]


def problems(text):
    """{word: its problems} for the words that have one."""
    return {
        word["text"]: word["problems"]
        for sentence in FRENCH.analyze(text)
        for word in sentence["words"]
        if word["problems"]
    }


def test_words_have_the_keys_of_the_other_languages():
    [sentence] = FRENCH.analyze("Les chats noirs dorment.")
    assert sentence["words"][2] == {
        "id": 3,
        "text": "noirs",
        "lemma": "noir",
        "upos": "ADJ",
        # The model has no tag set, and its tag is only the UPOS.
        "xpos": "",
        "feats": {"Gender": "Masc", "Number": "Plur"},
        "head": 2,
        "deprel": "amod",
        "start_char": 10,
        "end_char": 15,
        "problems": [],
    }


@pytest.mark.parametrize(
    "text",
    [
        "Mon aéroglisseur est plein d'anguilles.",
        "C'est peut-être la belle maison de l'homme.",
        "Je ne mange pas du pain au marché avec mon amie.",
        "Les enfants mangent des pommes vertes.",
        # A subject and its reflexive pronoun are not a repeat.
        "Nous nous levons tôt.",
    ],
)
def test_a_correct_sentence_has_no_problems(text):
    assert problems(text) == {}


def test_agreement():
    [reason] = problems("J'ai une petit chat.")["une"]
    assert reason == (
        "Does not agree with 'chat': this form is feminine, but the noun is"
        " masculine (gender)."
    )
    # An adjective before the noun, and one after it.
    assert list(problems("Il voit la grand maison.")) == ["grand"]
    [reason] = problems("Une voiture rouges passe.")["rouges"]
    assert reason.endswith("this form is plural, but the noun is singular (number).")


def test_repeat_and_spelling():
    found = problems("Je je mange la maizon.")
    assert found["je"] == ["'je' repeats."]
    assert found["maizon"] == [
        "The French word list does not have this word. Did you mean 'maison'?"
    ]


def test_glosses():
    assert FRENCH.glosses("anguilles", "anguille", "NOUN") == {"eel": 0}
    # à and a are one key, and the part of speech keeps them apart.
    assert "to" in FRENCH.glosses("à", "à", "ADP")
    assert "to" not in FRENCH.glosses("a", "avoir", "AUX")


def test_another_model_drops_the_french_model():
    FRENCH.analyze("Bonjour.")
    assert FRENCH.status() == {"loading": None, "loaded": ["light"]}
    with STUDY.use(("hr", "heavy"), lambda: "pipeline"):
        assert FRENCH.status() == {"loading": None, "loaded": []}
    STUDY.drop()
