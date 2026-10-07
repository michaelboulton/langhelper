"""Tests for languages/german. They run the real spaCy models, which are
dependencies (de_core_news_md and de_dep_news_trf), so nothing is faked. The
checks must give the same result with both."""

import pytest

from tlhelper.languages import LANGUAGES
from tlhelper.languages.base import STUDY
from tlhelper.languages.german import checks

GERMAN = LANGUAGES["de"]


# The module scope makes pytest run all tests with one model and then all
# tests with the other, so each model loads one time.
@pytest.fixture(scope="module", params=GERMAN.info.variants)
def problems(request):
    def problems(text):
        """{word: its problems} for the words that have one."""
        return {
            word["text"]: word["problems"]
            for sentence in GERMAN.analyze(text, variant=request.param)
            for word in sentence["words"]
            if word["problems"]
        }

    return problems


@pytest.mark.parametrize("variant", GERMAN.info.variants)
def test_words_have_the_keys_of_the_other_languages(variant):
    [sentence] = GERMAN.analyze("Ich gehe mit dem Hund.", variant=variant)
    assert sentence["text"] == "Ich gehe mit dem Hund."
    assert sentence["words"][4] == {
        "id": 5,
        "text": "Hund",
        "lemma": "Hund",
        "upos": "NOUN",
        "xpos": "NN",
        "feats": {"Case": "Dat", "Gender": "Masc", "Number": "Sing"},
        # The noun of "mit", in the TIGER labels of the German models.
        "head": 3,
        "deprel": "nk",
        "start_char": 17,
        "end_char": 21,
        "problems": [],
    }
    [sentence] = GERMAN.analyze("Ich gehe.", check=False)
    assert "problems" not in sentence["words"][0]


@pytest.mark.parametrize(
    "text",
    [
        "Ich gehe mit dem kleinen Hund in den großen Park.",
        "Sie trinkt kaltes Wasser mit guten Freunden.",
        "Das ist ein kleiner Hund.",
        "Wir wohnen im kleinen Haus.",
        "Wegen dem Regen bleibe ich für meinen Freund hier.",
        # A relative pronoun before an article is not a repeat.
        "Die Frau, die die Katze hat, ist im Haus.",
        "Mein Luftkissenfahrzeug ist voller Aale.",
    ],
)
def test_a_correct_sentence_has_no_problems(problems, text):
    assert problems(text) == {}


def test_preposition_case(problems):
    [reason] = problems("Ich gehe mit den Hund.")["den"]
    assert (
        reason == "The preposition 'mit' takes the dative, but this form is accusative."
    )
    assert list(problems("Für meinem Freund kaufe ich das Haus.")) == ["meinem"]
    # A pronoun shows its case too.
    assert list(problems("Er kommt mit mich.")) == ["mich"]
    # "in" takes both cases, so the check cannot tell.
    assert problems("Ich wohne in die Stadt.") == {}


def test_article_agreement(problems):
    # The light model reads "der" as a feminine dative, and the heavy one as
    # a masculine nominative. Both are a reason to flag it.
    [reason] = problems("Ich gehe mit der Hund.")["der"]
    assert (
        "feminine, but the noun is masculine" in reason
        or "takes the dative, but this form is nominative" in reason
    )


def test_adjective_ending(problems):
    [reason] = problems("Das ist ein kleine Hund.")["kleine"]
    assert reason == (
        "The ending -e does not fit 'Hund' (masculine nominative)."
        " After a word like ein, the ending is -er."
    )


def test_expected_ending():
    assert checks.expected_ending("weak", "Nom", "Masc", "Sing") == "e"
    assert checks.expected_ending("weak", "Acc", "Masc", "Sing") == "en"
    assert checks.expected_ending("mixed", "Nom", "Neut", "Sing") == "es"
    assert checks.expected_ending("mixed", "Dat", "Fem", "Sing") == "en"
    assert checks.expected_ending("strong", "Dat", "Fem", "Sing") == "er"
    assert checks.expected_ending("strong", "Nom", "Masc", "Plur") == "e"
    assert checks.expected_ending("mixed", "Nom", "Masc", "Plur") == "en"
    assert checks.expected_ending("strong", None, "Masc", "Sing") is None


def test_repeat_and_spelling(problems):
    found = problems("Ich habe habe einen Hundd.")
    assert found["habe"] == ["'habe' repeats."]
    assert found["Hundd"][0].startswith("The German word list does not have this word.")


def test_compound_words_pass_the_spelling_check():
    assert checks.is_compound("luftkissenfahrzeug")
    assert checks.is_compound("arbeitszimmer")
    assert not checks.is_compound("hundd")


def test_another_model_drops_the_german_model():
    GERMAN.analyze("Hallo.")
    assert GERMAN.status() == {"loading": None, "loaded": ["light"]}
    with STUDY.use(("hr", "heavy"), lambda: "pipeline"):
        assert GERMAN.status() == {"loading": None, "loaded": []}
    # The next request loads it again.
    GERMAN.analyze("Hallo.")
    assert GERMAN.status()["loaded"] == ["light"]
    STUDY.drop()


def test_glosses_are_empty_without_the_file(tmp_path, monkeypatch):
    from tlhelper.languages.glosses import GlossFile

    monkeypatch.setattr(GERMAN, "gloss_file", GlossFile(tmp_path / "none.db"))
    assert GERMAN.glosses("Hund", "Hund", "NOUN") == {}
