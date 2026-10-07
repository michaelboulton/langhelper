"""Tests for accents.py and build_glosses.py. Run with: uv run pytest

The `db` fixture builds a small accents.db from a kaikki-style sample, so
these tests cover the builder and the lookup together and need no real data.
"""

import json
import sqlite3

import pytest

from tlhelper import build_glosses
from tlhelper.languages.croatian import accents
from tlhelper.languages.glosses import GlossFile


def form(text, *tags):
    return {"form": text, "tags": list(tags)}


SAMPLE = [
    {
        "word": "kuća",
        "pos": "noun",
        "lang_code": "sh",
        "forms": [
            form("kȕća", "canonical", "feminine"),
            form("ку̏ћа", "Cyrillic"),
            form("kȕćica", "diminutive"),
            form("no-table-tags", "table-tags"),
            form("kȕća", "nominative", "singular"),
            form("kȕće", "nominative", "plural"),
            form("kȕćē", "genitive", "singular"),
            form("kȗćā", "genitive", "plural"),
            form("ку̏ће", "nominative", "plural"),
        ],
        "senses": [
            {"glosses": ["house (a building for living in)"]},
            {"glosses": ["home, household"]},
            {
                "glosses": [
                    "A long text that describes the word and is not a translation"
                ]
            },
            {"glosses": ["genitive singular of kuća"], "form_of": [{"word": "kuća"}]},
        ],
    },
    # Two entries for one word: city and hail.
    {
        "word": "grad",
        "pos": "noun",
        "lang_code": "sh",
        "forms": [form("grȃd", "canonical"), form("grȃd", "nominative", "singular")],
        "senses": [{"glosses": ["city, town"]}],
    },
    {
        "word": "grad",
        "pos": "noun",
        "lang_code": "sh",
        "forms": [form("grȁd", "canonical"), form("grȁd", "nominative", "singular")],
        "senses": [{"glosses": ["hail"]}, {"glosses": ["town"]}],
    },
    # The verb tables of Wiktionary have no accents.
    {
        "word": "raditi",
        "pos": "verb",
        "lang_code": "sh",
        "forms": [
            form("ráditi", "canonical", "imperfective"),
            form("ráđēnje", "noun-from-verb"),
            form("radim", "present", "singular"),
        ],
        "senses": [{"glosses": ["to work, to do something"]}, {"glosses": ["to"]}],
    },
    {
        "word": "Zagreb",
        "pos": "name",
        "lang_code": "sh",
        "forms": [form("Zágreb", "canonical"), form("Zágrebu", "locative", "singular")],
    },
    {
        "word": "ti",
        "pos": "pron",
        "lang_code": "sh",
        "forms": [form("tȋ", "canonical"), form("tȋ", "nominative", "singular")],
    },
    {"word": "kuća", "pos": "noun", "lang_code": "sl", "forms": [form("kúča")]},
    {"word": "kuć", "pos": "suffix", "lang_code": "sh", "forms": [form("kȕć")]},
]


@pytest.fixture
def db(tmp_path, monkeypatch):
    source = tmp_path / "sample.jsonl"
    source.write_text("\n".join(json.dumps(entry) for entry in SAMPLE))
    target = tmp_path / "accents.db"
    counts = build_glosses.build(source, target)
    monkeypatch.setattr(accents, "ACCENTS_PATH", target)
    monkeypatch.setattr(accents, "_conn", None)
    monkeypatch.setattr(accents, "_missing", False)
    return target, counts


def test_plain_strips_accents_but_keeps_letters():
    assert accents.plain("kȗćā") == "kuća"
    assert accents.plain("čȅkati") == "čekati"
    assert accents.plain("đȁk") == "đak"
    assert accents.plain("šèćer") == "šećer"
    assert accents.plain("pr̀st") == "prst"
    assert accents.plain("ráđēnje") == "rađenje"


def test_build_keeps_only_latin_accented_forms_of_the_word(db):
    target, counts = db
    conn = sqlite3.connect(target)
    assert conn.execute("SELECT key, form FROM lemmas ORDER BY seq").fetchall() == [
        ("kuća|NOUN", "kȕća"),
        ("grad|NOUN", "grȃd"),
        ("grad|NOUN", "grȁd"),
        ("raditi|VERB", "ráditi"),
        ("raditi|AUX", "ráditi"),
        ("Zagreb|PROPN", "Zágreb"),
        ("ti|PRON", "tȋ"),
        ("ti|DET", "tȋ"),
    ]
    kuca = conn.execute(
        "SELECT surface, form, gcase, number FROM forms WHERE key = 'kuća|NOUN'"
        " ORDER BY seq"
    ).fetchall()
    assert kuca == [
        ("kuća", "kȕća", "nom", "sg"),
        ("kuće", "kȕće", "nom", "pl"),
        ("kuće", "kȕćē", "gen", "sg"),
        ("kuća", "kȗćā", "gen", "pl"),
    ]
    # No Cyrillic, no derived words, no unaccented verb forms, no Slovene.
    assert conn.execute("SELECT count(*) FROM forms").fetchone()[0] == counts[1] == 9
    assert counts[0] == 8


def test_build_glosses(db):
    target, counts = db
    conn = sqlite3.connect(target)
    rows = conn.execute("SELECT key, word, rank FROM glosses ORDER BY key, rank, word")
    assert rows.fetchall() == [
        # The rank is the lower one of the two entries: town is 1 and 1.
        ("grad|NOUN", "city", 0),
        ("grad|NOUN", "hail", 0),
        ("grad|NOUN", "town", 1),
        # No parentheses, no long description, no "genitive singular of".
        ("kuća|NOUN", "house", 0),
        ("kuća|NOUN", "home", 1),
        ("kuća|NOUN", "household", 2),
        # "to work" is work, but "to" alone stays. "something" is a stopword.
        ("raditi|AUX", "work", 0),
        ("raditi|AUX", "do", 1),
        ("raditi|AUX", "to", 2),
        ("raditi|VERB", "work", 0),
        ("raditi|VERB", "do", 1),
        ("raditi|VERB", "to", 2),
    ]
    assert counts[2] == 12


def test_glosses_for(db, monkeypatch):
    assert accents.glosses_for("kuće", "kuća", "NOUN") == {
        "house": 0,
        "home": 1,
        "household": 2,
    }
    # The entry of the word itself counts too, not only the lemma.
    assert accents.glosses_for("grad", "other", "NOUN")["city"] == 0
    assert accents.glosses_for("nema", "nema", "NOUN") == {}
    # A missing file gives no glosses.
    monkeypatch.setattr(accents, "_conn", None)
    monkeypatch.setattr(accents, "ACCENTS_PATH", db[0].parent / "no.db")
    assert accents.glosses_for("kuće", "kuća", "NOUN") == {}


def test_accent_picks_the_form_by_case_and_number(db):
    gen_sg = {"Case": "Gen", "Number": "Sing"}
    nom_pl = {"Case": "Nom", "Number": "Plur"}
    gen_pl = {"Case": "Gen", "Number": "Plur"}
    assert accents.accent_for("kuće", "kuća", "NOUN", gen_sg) == {
        "form": "kȕćē",
        "exact": True,
    }
    assert accents.accent_for("kuće", "kuća", "NOUN", nom_pl)["form"] == "kȕće"
    assert accents.accent_for("kuća", "kuća", "NOUN", gen_pl)["form"] == "kȗćā"


def test_accent_is_ambiguous_without_a_matching_case(db):
    for feats in ({}, {"Case": "Loc", "Number": "Sing"}):
        assert accents.accent_for("kuće", "kuća", "NOUN", feats) == {
            "form": "kȕće / kȕćē",
            "exact": True,
            "ambiguous": True,
        }


def test_accent_falls_back_to_the_dictionary_form(db):
    assert accents.accent_for("radim", "raditi", "VERB", {}) == {
        "form": "ráditi",
        "exact": False,
    }
    # The capital of "Radim" does not go onto another word.
    assert accents.accent_for("Radim", "raditi", "VERB", {})["form"] == "ráditi"
    assert accents.accent_for("raditi", "raditi", "VERB", {}) == {
        "form": "ráditi",
        "exact": True,
    }


def test_accent_gives_each_reading_of_a_homograph(db):
    feats = {"Case": "Nom", "Number": "Sing"}
    assert accents.accent_for("grad", "grad", "NOUN", feats) == {
        "form": "grȃd / grȁd",
        "exact": True,
        "ambiguous": True,
    }


def test_accent_keeps_the_capital(db):
    feats = {"Case": "Nom", "Number": "Sing"}
    assert accents.accent_for("Kuća", "kuća", "NOUN", feats)["form"] == "Kȕća"
    loc = {"Case": "Loc", "Number": "Sing"}
    assert accents.accent_for("Zagrebu", "Zagreb", "PROPN", loc)["form"] == "Zágrebu"


def test_accent_unknown_word_and_punctuation(db):
    assert accents.accent_for("stol", "stol", "NOUN", {}) is None
    assert accents.accent_for(".", ".", "PUNCT", {}) is None
    assert accents.accent_for("5", "5", "NUM", {}) is None


def test_clitics_have_no_accent(db):
    clitic = {"form": "je", "exact": True, "clitic": True}
    assert accents.accent_for("je", "biti", "AUX", {}) == clitic
    assert accents.accent_for("se", "sebe", "PRON", {"Case": "Acc"})["clitic"]
    assert accents.accent_for("li", "li", "PART", {})["clitic"]
    # "ti" is a clitic in the dative, and the stressed tȋ in the nominative.
    assert accents.accent_for("ti", "ti", "PRON", {"Case": "Dat"})["clitic"]
    nom = {"Case": "Nom", "Number": "Sing"}
    assert accents.accent_for("ti", "ti", "PRON", nom) == {"form": "tȋ", "exact": True}


def test_missing_file_gives_no_accents(tmp_path, monkeypatch):
    monkeypatch.setattr(accents, "ACCENTS_PATH", tmp_path / "none.db")
    monkeypatch.setattr(accents, "_conn", None)
    monkeypatch.setattr(accents, "_missing", False)
    assert accents.accent_for("kuća", "kuća", "NOUN", {}) is None
    assert accents._missing


def test_a_german_build_has_only_the_glosses(tmp_path):
    entries = [
        {
            "word": "Haus",
            "pos": "noun",
            "lang_code": "de",
            "senses": [{"glosses": ["house, home"]}],
            "forms": [form("Häuser", "nominative", "plural")],
        },
        # Another language in the same file.
        {"word": "kuća", "pos": "noun", "lang_code": "sh", "senses": []},
    ]
    source = tmp_path / "sample.jsonl"
    source.write_text("\n".join(json.dumps(entry) for entry in entries))
    target = tmp_path / "glosses.db"
    assert build_glosses.build(source, target, "de") == (0, 0, 2)
    tables = sqlite3.connect(target).execute("SELECT name FROM sqlite_master")
    assert [name for (name,) in tables] == ["glosses"]
    glosses = GlossFile(target)
    assert glosses.glosses_for("Häuser", "Haus", "NOUN") == {"house": 0, "home": 1}
    assert glosses.glosses_for("kuća", "kuća", "NOUN") == {}


@pytest.mark.skipif(not accents.ACCENTS_PATH.exists(), reason="no accents.db")
def test_real_accents_file(monkeypatch):
    monkeypatch.setattr(accents, "_conn", None)
    gen_pl = {"Case": "Gen", "Number": "Plur"}
    assert accents.accent_for("kuća", "kuća", "NOUN", gen_pl)["form"] == "kȗćā"
    assert accents.accent_for("večeras", "večeras", "ADV", {})["form"] == "večèras"
