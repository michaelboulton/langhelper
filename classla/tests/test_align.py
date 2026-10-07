"""Tests for the links between the words of the study language and the
English words. The examples are Croatian."""

from types import SimpleNamespace

import pytest

from tlhelper import align
from tlhelper.languages import LANGUAGES
from tlhelper.languages.croatian import accents
from tlhelper.languages.french import GLOSSES_PATH as FRENCH_GLOSSES_PATH
from tlhelper.languages.german import GLOSSES_PATH
from tlhelper.languages.italian import GLOSSES_PATH as ITALIAN_GLOSSES_PATH

GLOSSES = {
    "ona": {"she": 0},
    "biti": {"be": 0, "exist": 1},
    "kuća": {"house": 0, "home": 1},
    "ići": {"go": 0, "walk": 1, "do": 8},
    "htjeti": {"want": 0, "will": 6},
    "u": {"in": 0, "to": 3},
    "biti-to": {"to": 0},
    "dugo": {"for": 0, "long": 1},
    "za": {"for": 0},
    "morati": {"have": 0, "must": 2},
    "imati": {"have": 0},
}


def language(glosses=lambda text, lemma, upos: GLOSSES.get(lemma, {})):
    """A language with fixed glosses, and the extra glosses of Croatian."""
    return SimpleNamespace(glosses=glosses, extra_glosses=LANGUAGES["hr"].extra_glosses)


FAKE = language()


def hr(text, lemma, upos):
    return {"text": text, "lemma": lemma, "upos": upos}


def en(text, lemma, upos):
    return {"text": text, "lemma": lemma, "upos": upos}


def pairs(croatian, english, language=FAKE):
    return [
        (croatian[i]["text"], english[j]["text"])
        for i, j in align.links(language, croatian, english)
    ]


def test_links_by_the_english_lemma():
    croatian = [
        hr("Ona", "ona", "PRON"),
        hr("je", "biti", "AUX"),
        hr("kod", "kod", "ADP"),
    ]
    croatian += [hr("kuće", "kuća", "NOUN"), hr(".", ".", "PUNCT")]
    english = [en("She", "she", "PRON"), en("was", "be", "AUX"), en("at", "at", "ADP")]
    english += [en("home", "home", "NOUN"), en(".", ".", "PUNCT")]
    # "kod" has no gloss here, and punctuation never links.
    assert pairs(croatian, english) == [("Ona", "She"), ("je", "was"), ("kuće", "home")]
    assert align.links(FAKE, croatian, english) == [[0, 0], [1, 1], [3, 3]]


def test_a_name_links_by_its_text():
    croatian = [hr("Zagrebu", "Zagreb", "PROPN"), hr("2024", "2024", "NUM")]
    english = [en("2024", "2024", "NUM"), en("Zagreb", "Zagreb", "PROPN")]
    assert pairs(croatian, english) == [("Zagrebu", "Zagreb"), ("2024", "2024")]


def test_a_word_is_in_one_link_and_the_closest_position_wins():
    je = hr("je", "biti", "AUX")
    croatian = [je, hr("x", "x", "X"), hr("x", "x", "X"), dict(je)]
    english = [en("is", "be", "AUX"), en("y", "y", "X"), en("y", "y", "X")]
    english += [en("is", "be", "AUX")]
    assert align.links(FAKE, croatian, english) == [[0, 0], [3, 3]]
    # One "is" for two "je": only the closer one links.
    assert align.links(FAKE, croatian, english[:1]) == [[0, 0]]


def test_the_main_meaning_wins_over_a_closer_side_meaning():
    filler = [hr("x", "x", "X")] * 6
    croatian = [hr("x", "x", "X"), hr("Idem", "ići", "VERB"), *filler]
    english = [en("y", "y", "X"), en("do", "do", "VERB"), en("y", "y", "X")]
    english += [en("go", "go", "VERB")] + [en("y", "y", "X")] * 6
    # "do" is at the same place in the text, but it is a side meaning of ići.
    assert pairs(croatian, english) == [("Idem", "go")]


def test_do_and_the_to_of_an_infinitive_never_link():
    english = [en("I", "I", "PRON"), en("do", "do", "AUX"), en("not", "not", "PART")]
    english += [
        en("want", "want", "VERB"),
        en("to", "to", "PART"),
        en("go", "go", "VERB"),
    ]
    croatian = [hr("ići", "ići", "VERB"), hr("u", "u", "ADP")]
    assert pairs(croatian, english) == [("ići", "go")]
    # Also not to a Croatian helper verb: "biste" has "to" in its glosses.
    assert pairs([hr("biste", "biti-to", "AUX")], english) == []
    # A helper verb with a meaning links: "ću" and "will".
    croatian = [hr("ću", "htjeti", "AUX")]
    english = [en("I", "I", "PRON"), en("will", "will", "AUX")]
    assert pairs(croatian, english) == [("ću", "will")]


def test_an_english_preposition_only_links_to_a_croatian_one():
    english = [en("for", "for", "ADP"), en("a", "a", "DET"), en("long", "long", "ADJ")]
    assert pairs([hr("dugo", "dugo", "ADV")], english) == [("dugo", "long")]
    assert pairs([hr("za", "za", "ADP")], english) == [("za", "for")]


def test_a_word_gives_up_its_first_choice_if_another_word_needs_it():
    # "have" is the main meaning of both words. A best-first choice gives it
    # to "morate" and leaves "imati" with nothing.
    croatian = [hr("morate", "morati", "VERB"), hr("imati", "imati", "VERB")]
    english = [en("you", "you", "PRON"), en("must", "must", "AUX")]
    english += [en("have", "have", "VERB")]
    assert pairs(croatian, english) == [("morate", "must"), ("imati", "have")]


def test_extra_glosses_fill_the_gaps_of_wiktionary():
    english = [en("my", "my", "PRON"), en("and", "and", "CCONJ")]
    croatian = [hr("svoju", "svoj", "DET"), hr("i", "i", "CCONJ")]
    assert pairs(croatian, english) == [("svoju", "my"), ("i", "and")]


def test_an_english_determiner_only_links_to_a_croatian_one():
    fake = language(lambda text, lemma, upos: {"this": 0, "morning": 1})
    english = [en("This", "this", "DET"), en("morning", "morning", "NOUN")]
    jutros = [hr("Jutros", "jutros", "ADV")]
    assert pairs(jutros, english, fake) == [("Jutros", "morning")]
    assert pairs([hr("Ovo", "ovaj", "DET")], english, fake) == [("Ovo", "This")]


def sentence(*words):
    return {"words": list(words)}


def test_align_links_inside_the_sentence_pairs():
    je = hr("je", "biti", "AUX")
    croatian = [
        sentence(hr("Ona", "ona", "PRON")),
        sentence(je, hr("kuća", "kuća", "NOUN")),
    ]
    english = [sentence(en("She", "she", "PRON"), en("is", "be", "AUX"))]
    english += [sentence(en("The", "the", "DET"), en("house", "house", "NOUN"))]
    # "je" does not link to the "is" of the first sentence. The indexes count
    # over all sentences: "kuća" is word 2 and "house" is word 3.
    assert align.align(FAKE, croatian, english) == {
        "links": [[0, 0], [2, 3]],
        "guesses": [],
    }


def test_align_without_sentence_pairs_keeps_links_close():
    filler = [hr("x", "x", "X")] * 8
    croatian = [sentence(je := hr("je", "biti", "AUX"), *filler), sentence(dict(je))]
    english = [sentence(en("is", "be", "AUX"), *[en("y", "y", "X")] * 9)]
    # One English sentence for two Croatian ones. The last "je" is too far
    # from the only "is", and the first "je" has it.
    assert align.align(FAKE, croatian, english) == {"links": [[0, 0]], "guesses": []}
    english = [sentence(*[en("y", "y", "X")] * 9, en("is", "be", "AUX"))]
    assert align.align(FAKE, croatian, english) == {"links": [[9, 9]], "guesses": []}
    assert align.align(FAKE, [], []) == {"links": [], "guesses": []}


def test_no_words():
    assert align.links(FAKE, [], []) == []
    assert align.guesses([], [], []) == []


def test_guess_fills_a_gap_between_two_links():
    croatian = [hr("moj", "moj", "DET"), hr("plutajući", "plutajući", "ADJ")]
    croatian += [hr("čamac", "čamac", "NOUN")]
    english = [en("My", "my", "PRON"), en("floating", "float", "ADJ")]
    english += [en("boat", "boat", "NOUN")]
    assert align.guesses(croatian, english, [[0, 0], [2, 2]]) == [[1, 1]]
    # The start and the end of the text hold a gap too.
    assert align.guesses(croatian, english, [[0, 0], [1, 1]]) == [[2, 2]]
    assert align.guesses(croatian, english, [[1, 1], [2, 2]]) == []  # DET and PRON


def test_guess_takes_two_free_words_in_a_row():
    # "ispravno vidjeli" and "correctly view": no dictionary entry for both.
    croatian = [hr("Da", "da", "SCONJ"), hr("ispravno", "ispravno", "ADV")]
    croatian += [hr("vidjeli", "vidjeti", "VERB"), hr("ovu", "ovaj", "DET")]
    english = [en("To", "to", "PART"), en("correctly", "correctly", "ADV")]
    english += [en("view", "view", "VERB"), en("this", "this", "DET")]
    assert align.guesses(croatian, english, [[3, 3]]) == [[1, 1], [2, 2]]


def test_guess_needs_the_same_part_of_speech_near_its_place():
    x, y = hr("x", "x", "X"), en("y", "y", "X")
    noun = hr("a", "a", "NOUN")
    # Another part of speech.
    english = [y, en("b", "b", "VERB"), y]
    assert align.guesses([x, noun, x], english, [[0, 0], [2, 2]]) == []
    # "the" and "se" are not words with a meaning of their own, and English
    # adds "the": the noun is one place later.
    croatian = [x, hr("se", "sebe", "PRON"), noun, x]
    english = [y, en("the", "the", "DET"), y, en("b", "b", "NOUN"), y]
    assert align.guesses(croatian, english, [[0, 0], [3, 4]]) == [[2, 3]]
    # Too far from its place: more than MAX_SHIFT words.
    english = [y, y, y, y, y, y, en("b", "b", "NOUN"), y, y, y, y, y, y]
    assert align.guesses([x, noun, x], english, [[0, 0], [2, 12]]) == []
    # Two Croatian nouns for one English noun: the closer one has it.
    croatian = [x, noun, dict(noun), x]
    english = [y, y, en("b", "b", "NOUN"), y]
    assert align.guesses(croatian, english, [[0, 0], [3, 3]]) == [[2, 2]]


@pytest.mark.skipif(not GLOSSES_PATH.exists(), reason="no glosses.db")
def test_real_german_glosses():
    german = [hr("Mein", "mein", "DET"), hr("Hund", "Hund", "NOUN")]
    german += [hr("ist", "sein", "AUX"), hr("klein", "klein", "ADJ")]
    english = [en("My", "my", "PRON"), en("dog", "dog", "NOUN")]
    english += [en("is", "be", "AUX"), en("small", "small", "ADJ")]
    assert pairs(german, english, LANGUAGES["de"]) == [
        ("Mein", "My"),
        ("Hund", "dog"),
        ("ist", "is"),
        ("klein", "small"),
    ]


@pytest.mark.skipif(not FRENCH_GLOSSES_PATH.exists(), reason="no glosses.db")
def test_real_french_glosses():
    # The articles and "ne ... pas" have only the extra glosses.
    french = [hr("Le", "le", "DET"), hr("chat", "chat", "NOUN")]
    french += [hr("ne", "ne", "ADV"), hr("mange", "manger", "VERB")]
    french += [hr("pas", "pas", "ADV"), hr("de", "de", "ADP")]
    french += [hr("poisson", "poisson", "NOUN")]
    english = [en("The", "the", "DET"), en("cat", "cat", "NOUN")]
    english += [en("does", "do", "AUX"), en("not", "not", "PART")]
    english += [en("eat", "eat", "VERB"), en("fish", "fish", "NOUN")]
    found = pairs(french, english, LANGUAGES["fr"])
    for pair in [("Le", "The"), ("chat", "cat"), ("mange", "eat"), ("poisson", "fish")]:
        assert pair in found
    assert ("ne", "not") in found or ("pas", "not") in found


@pytest.mark.skipif(not ITALIAN_GLOSSES_PATH.exists(), reason="no glosses.db")
def test_real_italian_glosses():
    # The article and the preposition with an article have only the extra
    # glosses: spaCy gives "sul" the lemma "su il".
    italian = [hr("Il", "il", "DET"), hr("gatto", "gatto", "NOUN")]
    italian += [hr("dorme", "dormire", "VERB"), hr("sul", "su il", "ADP")]
    italian += [hr("divano", "divano", "NOUN")]
    english = [en("The", "the", "DET"), en("cat", "cat", "NOUN")]
    english += [en("sleeps", "sleep", "VERB"), en("on", "on", "ADP")]
    english += [en("the", "the", "DET"), en("sofa", "sofa", "NOUN")]
    found = pairs(italian, english, LANGUAGES["it"])
    for pair in [
        ("Il", "The"),
        ("gatto", "cat"),
        ("dorme", "sleeps"),
        ("divano", "sofa"),
    ]:
        assert pair in found
    assert ("sul", "on") in found


def test_german_pronoun_in_a_case_form():
    # spaCy gives "mich" the lemma "mich", and English gives "me" the lemma "I".
    german = [hr("Bring", "Bring", "VERB"), hr("mich", "mich", "PRON")]
    german += [hr("zum", "zu", "ADP"), hr("Bus", "Bus", "NOUN")]
    english = [en("take", "take", "VERB"), en("me", "I", "PRON")]
    english += [en("to", "to", "ADP"), en("the", "the", "DET")]
    english += [en("bus", "bus", "NOUN")]
    assert ("mich", "me") in pairs(german, english, LANGUAGES["de"])


@pytest.mark.skipif(not accents.ACCENTS_PATH.exists(), reason="no accents.db")
def test_real_glosses():
    croatian = [hr("Moj", "moj", "DET"), hr("čamac", "čamac", "NOUN")]
    croatian += [hr("pun", "pun", "ADJ"), hr("je", "biti", "AUX")]
    croatian += [hr("jegulja", "jegulja", "NOUN"), hr(".", ".", "PUNCT")]
    english = [
        en("My", "my", "PRON"),
        en("boat", "boat", "NOUN"),
        en("is", "be", "AUX"),
    ]
    english += [en("full", "full", "ADJ"), en("of", "of", "ADP")]
    english += [en("eels", "eel", "NOUN"), en(".", ".", "PUNCT")]
    assert pairs(croatian, english, LANGUAGES["hr"]) == [
        ("Moj", "My"),
        ("čamac", "boat"),
        ("pun", "full"),
        ("je", "is"),
        ("jegulja", "eels"),
    ]
