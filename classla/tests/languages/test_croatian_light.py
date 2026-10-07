"""Tests for languages/croatian/light.py. They run the real spaCy model, which
is a dependency (hr_core_news_md), so nothing is faked."""

import pytest
from tlhelper.languages import LANGUAGES
from tlhelper.languages.croatian import accents, light

CROATIAN = LANGUAGES["hr"]
needs_accents = pytest.mark.skipif(
    not accents.ACCENTS_PATH.exists(), reason="no accents.db"
)


def problems(text):
    """{word: its problems} for the words that have one."""
    return {
        word["text"]: word["problems"]
        for sentence in CROATIAN.analyze(text)
        for word in sentence["words"]
        if word["problems"]
    }


def test_words_have_the_keys_and_the_tags_of_classla():
    [sentence] = CROATIAN.analyze("Ona je bila kod kuće.")
    # More than classla, which has no parser: the relation to another word.
    word = sentence["words"][4]
    assert 0 <= word.pop("head") <= 6
    assert word.pop("deprel")
    assert word | {"accent": None} == {
        "id": 5,
        "text": "kuće",
        "lemma": "kuća",
        "upos": "NOUN",
        "xpos": "Ncfsg",
        "feats": {"Case": "Gen", "Gender": "Fem", "Number": "Sing"},
        "accent": None,
        "start_char": 16,
        "end_char": 20,
        "problems": [],
    }
    assert CROATIAN.status() == {"loading": None, "loaded": ["light"]}


@needs_accents
def test_words_have_their_accent():
    [sentence] = CROATIAN.analyze("Ona je bila kod kuće.", check=False)
    assert sentence["words"][4]["accent"] == {"form": "kȕćē", "exact": True}


@pytest.mark.parametrize(
    "text",
    [
        "Ona je bila kod kuće.",
        "Vidim lijepu kuću.",
        "Razgovaram s prijateljem.",
        "Čaša je puna hladne vode.",
        # The model reads "jegulja" as a nominative, and Wiktionary has no
        # case forms of it, so the lexicon cannot say that it is wrong.
        "Moj lebdeći čamac pun je jegulja.",
    ],
)
def test_a_correct_sentence_has_no_problems(text):
    assert problems(text) == {}


def test_the_case_checks_work():
    [reason] = problems("Razgovaram s prijatelj.")["prijatelj"]
    assert reason.startswith("The preposition 's' takes the instrumental")
    assert list(problems("To je lijepa kuću.")) == ["lijepa"]
    assert problems("Ona je je bila kod kuće.")["je"] == ["'je' repeats."]


def test_known_misses():
    """The light model reads the case of a word from its context more than
    classla does, so it makes a wrong word fit. The heavy models flag both of
    these (test_real_models)."""
    assert problems("Vidim lijepa kuću.") == {}
    assert problems("Pijem kava.") == {}


def test_no_spelling_check():
    # The heavy models flag "lebdići" with their lexicon. Here nothing can.
    found = problems("Moj lebdići čamac je velik.")
    assert not any(
        "lexicon" in reason for reasons in found.values() for reason in reasons
    )


@needs_accents
def test_the_lexicon_reads_the_noun_forms_of_wiktionary():
    assert light.LEXICON.noun_can_be("kuće", "Gen")
    assert light.LEXICON.noun_can_be("Kuće", "Nom")
    assert not light.LEXICON.noun_can_be("kuće", "Ins")
    # No case forms of this noun at all, so it passes.
    assert accents.noun_can_be("lebdići", "Gen") is None
    assert light.LEXICON.noun_can_be("lebdići", "Gen")
