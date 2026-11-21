"""Tests for languages/italian. They run the real models, so nothing is
faked: spaCy (it_core_news_md, a dependency) and Stanza (in
.data/stanza_resources at the repository root). The checks must give the same
result with both."""

from pathlib import Path

import pytest
from tlhelper.languages import LANGUAGES
from tlhelper.languages.base import STUDY, ModelsMissing
from tlhelper.languages.italian import heavy

ITALIAN = LANGUAGES["it"]
STANZA_MODELS = Path(__file__).parents[3] / ".data" / "stanza_resources"

VARIANTS = [
    pytest.param(
        variant,
        marks=pytest.mark.skipif(
            variant == "heavy" and not (STANZA_MODELS / "it").exists(),
            reason="the Stanza models are not in .data/ at the repository root",
        ),
    )
    for variant in ITALIAN.info.variants
]


@pytest.fixture(scope="module", autouse=True)
def stanza_models():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(heavy, "MODEL_DIR", STANZA_MODELS)
        yield


# The module scope makes pytest run all tests with one model and then all
# tests with the other, so each model loads one time.
@pytest.fixture(scope="module", params=VARIANTS)
def problems(request):
    def problems(text):
        """{word: its problems} for the words that have one."""
        return {
            word["text"]: word["problems"]
            for sentence in ITALIAN.analyze(text, variant=request.param)
            for word in sentence["words"]
            if word["problems"]
        }

    return problems


@pytest.mark.parametrize("variant", VARIANTS)
def test_words_have_the_keys_of_the_other_languages(variant):
    [sentence] = ITALIAN.analyze("I gatti neri dormono.", variant=variant)
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


def test_the_light_model_keeps_a_preposition_with_an_article_as_one_word():
    [sentence] = ITALIAN.analyze("Il gatto dorme sul divano.")
    sul = sentence["words"][3]
    assert (sul["text"], sul["lemma"], sul["upos"], sul["xpos"]) == (
        "sul",
        "su il",
        "ADP",
        "E_RD",
    )


@pytest.mark.parametrize("variant", VARIANTS[1:])
def test_the_heavy_model_splits_a_preposition_with_an_article(variant):
    [sentence] = ITALIAN.analyze("Il gatto dorme sul divano.", variant=variant)
    su, il = sentence["words"][3:5]
    assert [(w["text"], w["upos"], w["xpos"]) for w in (su, il)] == [
        ("su", "ADP", "E"),
        ("il", "DET", "RD"),
    ]
    # Both words have the span of "sul".
    assert {(w["start_char"], w["end_char"]) for w in (su, il)} == {(15, 18)}


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
def test_a_correct_sentence_has_no_problems(problems, text):
    assert problems(text) == {}


def test_agreement(problems):
    [reason] = problems("Ho una piccolo gatto.")["una"]
    assert reason == (
        "Does not agree with 'gatto': this form is feminine, but the noun is"
        " masculine (gender)."
    )
    # An adjective before the noun, and one after it.
    assert list(problems("Vedo la piccolo casa.")) == ["piccolo"]
    [reason] = problems("Ha una macchina rosse.")["rosse"]
    assert reason.endswith("this form is plural, but the noun is singular (number).")


@pytest.mark.parametrize("variant", VARIANTS[1:])
@pytest.mark.parametrize(
    "text, flagged",
    [
        # The article inside a preposition.
        ("Vedo della ragazzo.", ["la"]),
        # Stanza reads the gender and the number from the noun, not from its
        # article, so these do not pass as with the light model.
        ("Vedo il casa.", ["il"]),
        ("Vedo il gatti.", ["il"]),
        ("Sto mangiando una mela.", []),
    ],
)
def test_what_only_the_heavy_model_finds(variant, text, flagged):
    [sentence] = ITALIAN.analyze(text, variant=variant)
    assert [w["text"] for w in sentence["words"] if w["problems"]] == flagged


def test_repeat_and_spelling(problems):
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


def test_download_off_raises_models_missing(tmp_path, monkeypatch):
    STUDY.drop()
    monkeypatch.setattr(heavy, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(heavy, "DOWNLOAD_MODELS", False)
    monkeypatch.setattr(
        heavy.stanza, "download", lambda *a, **kw: pytest.fail("downloaded")
    )
    with pytest.raises(ModelsMissing, match="DOWNLOAD_MODELS is off"):
        ITALIAN.analyze("Ciao.", variant="heavy")
    # A failed load leaves the slot empty and not locked.
    assert (STUDY.key, STUDY.loading) == (None, None)
