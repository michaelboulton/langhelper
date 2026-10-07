"""Each registered language has what app.py and align.py use (base.Language).
Croatian needs the classla models to tag a text, so test_app.py covers its
analyze() with a fake pipeline."""

import pytest
from tlhelper.languages import DEFAULT, ENGLISH, LANGUAGES

WORD_KEYS = {"id", "text", "lemma", "upos", "xpos", "feats", "start_char", "end_char"}
# Only a tagger with a parser gives these, and each spaCy tagger has one.
PARSER_KEYS = {"head", "deprel"}


@pytest.mark.parametrize("language", [*LANGUAGES.values(), ENGLISH])
def test_info_and_status(language):
    info = language.info
    assert info.code == info.code.lower() and info.name and info.tag_name
    assert len(info.code) == 2 and info.placeholder
    assert info.variants[0] == "light"
    assert set(info.variants) <= {"light", "heavy", "nonstandard"}
    for label, address in info.dictionary_links:
        assert label and address.startswith("https://")
    assert set(language.status()) == {"loading", "loaded"}
    assert isinstance(language.extra_glosses, dict)
    assert isinstance(language.glosses("x", "x", "NOUN"), dict)


def test_registry():
    assert DEFAULT == "hr"
    assert all(code == language.info.code for code, language in LANGUAGES.items())
    assert "en" not in LANGUAGES


@pytest.mark.parametrize(
    "language, text",
    [
        (LANGUAGES["de"], "Das ist gut."),
        (LANGUAGES["fr"], "C'est bon."),
        (LANGUAGES["it"], "C'è un problema."),
        (ENGLISH, "This is good."),
    ],
)
def test_spacy_languages_give_the_word_keys(language, text):
    [sentence] = language.analyze(text, check=True)
    assert sentence["text"] == text
    for word in sentence["words"]:
        assert set(word) == WORD_KEYS | PARSER_KEYS | {"problems"}
    [sentence] = language.analyze(text, check=False)
    assert set(sentence["words"][0]) == WORD_KEYS | PARSER_KEYS
    # One root, and each other head is a word of the sentence.
    heads = [word["head"] for word in sentence["words"]]
    assert heads.count(0) == 1
    assert all(0 <= head <= len(heads) for head in heads)
