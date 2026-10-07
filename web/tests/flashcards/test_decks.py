import logging
import sqlite3

from tlhelper.flashcards import decks, store

TOML = """
name = "Basics"
language = "hr"
english_field = "Front"
answer_field = "Back"
"""


def cards():
    conn = sqlite3.connect(store.DB_PATH)
    return conn.execute(
        "SELECT guid, direction, prompt, answers, removed FROM card ORDER BY removed, position"
    ).fetchall()


def test_import(basics):
    assert store.decks("me") == [
        {
            "id": basics,
            "name": "Basics",
            "language": "hr",
            "path": [],
            "counts": {"total": 3, "new": 3, "learning": 0, "due": 0},
        }
    ]
    assert cards()[1] == (
        "guid-hello",
        "to_study",
        "hello / hi",
        '["bok", "zdravo"]',
        0,
    )


def test_reverse_makes_a_second_card(deck_dir, make_apkg):
    make_apkg(deck_dir / "basics.apkg")
    (deck_dir / "basics.toml").write_text(TOML + "reverse = true\n")
    decks.import_decks()
    assert cards()[2:4] == [
        ("guid-hello", "to_study", "hello / hi", '["bok", "zdravo"]', 0),
        ("guid-hello", "to_english", "bok / zdravo", '["hello", "hi"]', 0),
    ]


def test_the_media_of_a_card(deck_dir, make_apkg):
    notes = [
        # A picture is the whole English side: a card, but no reverse card.
        ("guid-house", '<img src="house.jpg">', "kuća[sound:kuća.mp3]", ""),
        ("guid-cat", 'cat<img src="cat.svg">', "mačka", "[sound:mačka.mp3]"),
        ("guid-empty", "", "ništa", "[sound:ništa.mp3]"),
    ]
    make_apkg(deck_dir / "basics.apkg", notes, fields=("Front", "Back", "Audio"))
    (deck_dir / "basics.toml").write_text(
        TOML + 'reverse = true\nmedia_fields = ["Audio"]\n', encoding="utf-8"
    )
    decks.import_decks()
    conn = sqlite3.connect(store.DB_PATH)
    rows = conn.execute(
        "SELECT guid, direction, prompt, prompt_media, answer_media FROM card"
        " ORDER BY position"
    ).fetchall()
    assert rows == [
        ("guid-house", "to_study", "", '["house.jpg"]', '["kuća.mp3"]'),
        ("guid-cat", "to_study", "cat", "[]", '["mačka.mp3"]'),
        ("guid-cat", "to_english", "mačka", "[]", '["mačka.mp3"]'),
    ]
    assert decks.deck_path("basics") == deck_dir / "basics.apkg"
    assert decks.deck_path("absent") is None


def test_a_note_with_its_fields_the_other_way_round(deck_dir, make_apkg):
    notes = [
        ("guid-thanks", "Hvala vam/ti puno[sound:hvala.mp3]", "Thank you very much"),
        ("guid-house", "house", "kuća"),
        # English on both sides, and a Croatian prefix that looks English.
        ("guid-rule", "Which ending is this?", "the ending -a"),
        ("guid-try", "to try", "probati ~ is-"),
    ]
    make_apkg(deck_dir / "basics.apkg", notes)
    (deck_dir / "basics.toml").write_text(TOML, encoding="utf-8")
    decks.import_decks()
    conn = sqlite3.connect(store.DB_PATH)
    rows = conn.execute(
        "SELECT prompt, answers, prompt_media, answer_media FROM card ORDER BY position"
    ).fetchall()
    assert rows == [
        ("Thank you very much", '["Hvala vam/ti puno"]', "[]", '["hvala.mp3"]'),
        ("house", '["kuća"]', "[]", "[]"),
        ("Which ending is this?", '["the ending -a"]', "[]", "[]"),
        ("to try", '["probati ~ is-"]', "[]", "[]"),
    ]


SENTENCES = TOML.replace("Basics", "Sentences") + (
    'subdecks = true\nto_english_notetypes = ["Basic"]\nseparators = ["\\n"]\n'
)
ANKI_DECKS = {
    1: "Default",
    10: "1::Sentences [Part 1]",
    11: "1::Sentences [Part 1]::Read::2",
    12: "1::Sentences [Part 1]::Read::3",
    13: "1::Sentences [Part 1]::Speak::2",
}


def test_each_anki_deck_with_cards_is_a_deck(deck_dir, make_apkg):
    notes = [
        ("guid-a", "I was.", "Bio sam. <br> Bila sam.", 11),
        ("guid-b", "What is it?", "Što je to?", 12),
        ("guid-c", "Yes, yes.", "Da, da.", 13),
        ("guid-d", "And it is.", "I je.", 11),
    ]
    make_apkg(deck_dir / "sentences.apkg", notes, anki_decks=ANKI_DECKS)
    (deck_dir / "sentences.toml").write_text(SENTENCES, encoding="utf-8")
    decks.import_decks()
    # The parts that all the names share are not in the path.
    assert [
        (deck["name"], deck["path"], deck["counts"]["total"])
        for deck in store.decks("me")
    ] == [
        ("Read, 2", ["Sentences", "Read", "2"], 2),
        ("Read, 3", ["Sentences", "Read", "3"], 1),
        ("Speak, 2", ["Sentences", "Speak", "2"], 1),
    ]
    # Only the English is asked, and each line is one text.
    assert cards()[0] == (
        "guid-a",
        "to_english",
        "Bio sam. / Bila sam.",
        '["I was."]',
        0,
    )
    assert store.deck_stamps().keys() == {
        "sentences::1::Sentences [Part 1]::Read::2",
        "sentences::1::Sentences [Part 1]::Read::3",
        "sentences::1::Sentences [Part 1]::Speak::2",
    }
    assert decks.deck_path("sentences::1::Read::2") == deck_dir / "sentences.apkg"


def test_a_subdeck_that_left_the_package(deck_dir, make_apkg, monkeypatch):
    notes = [("guid-a", "I was.", "Bio sam.", 11), ("guid-b", "Yes.", "Da.", 13)]
    make_apkg(deck_dir / "sentences.apkg", notes, anki_decks=ANKI_DECKS)
    (deck_dir / "sentences.toml").write_text(SENTENCES, encoding="utf-8")
    decks.import_decks()
    card = store.next_card("me", store.decks("me")[0]["id"])["card"]
    store.answer("me", card["id"], 3, "I was.", None)
    make_apkg(deck_dir / "sentences.apkg", notes[:1], anki_decks=ANKI_DECKS)
    decks.import_decks()
    # The deck that stays is the same deck, with its progress.
    [deck] = store.decks("me")
    assert (deck["path"], deck["counts"]["learning"]) == (["Sentences", "2"], 1)
    # The second import is the last one for these files.
    monkeypatch.setattr(decks.apkg, "read_notes", None)
    decks.import_decks()


def test_a_package_whose_files_are_gone(basics, deck_dir, make_apkg):
    card = store.next_card("me", basics)["card"]
    store.answer("me", card["id"], 3, "kuća", None)
    (deck_dir / "basics.apkg").unlink()
    (deck_dir / "basics.toml").unlink()
    decks.import_decks()
    assert store.decks("me") == []
    assert {removed for _, _, _, _, removed in cards()} == {1}
    # The files come back: the same deck, with its progress.
    make_apkg(deck_dir / "basics.apkg")
    (deck_dir / "basics.toml").write_text(TOML)
    decks.import_decks()
    [deck] = store.decks("me")
    assert (deck["id"], deck["counts"]["learning"]) == (basics, 1)


def test_an_old_database_gets_the_media_columns(basics, deck_dir):
    conn = sqlite3.connect(store.DB_PATH)
    conn.execute("ALTER TABLE card DROP COLUMN prompt_media")
    conn.execute("ALTER TABLE card DROP COLUMN answer_media")
    conn.execute("ALTER TABLE deck DROP COLUMN path")
    conn.execute("UPDATE deck SET source_stamp = 'of the old import'")
    conn.commit()
    conn.close()
    decks.import_decks()
    card = store.next_card("me", basics)["card"]
    assert (card["prompt_media"], card["answer_media"]) == ([], [])


def test_an_unchanged_deck_is_not_read_again(basics, monkeypatch):
    monkeypatch.setattr(decks.apkg, "read_notes", None)  # a call would raise
    decks.import_decks()


def test_a_new_export_keeps_the_progress(basics, deck_dir, make_apkg, clock):
    card = store.next_card("me", basics)["card"]
    store.answer("me", card["id"], 3, "kuća", None)
    # "house" stays (with a new answer), "hello" goes, and "cat" is new.
    make_apkg(
        deck_dir / "basics.apkg",
        [("guid-cat", "cat", "mačka"), ("guid-house", "house", "kuća / dom")],
    )
    decks.import_decks()
    assert [(guid, removed) for guid, _, _, _, removed in cards()] == [
        ("guid-cat", 0),
        ("guid-house", 0),
        ("guid-hello", 1),
        ("guid-coffee", 1),
    ]
    assert store.get_card(card["id"])["answers"] == ["kuća", "dom"]
    assert store.decks("me")[0]["counts"] == {
        "total": 2,
        "new": 1,
        "learning": 1,
        "due": 0,
    }


def test_a_bad_deck_is_a_log_line(deck_dir, make_apkg, caplog):
    caplog.set_level(logging.WARNING, logger="uvicorn.error")
    (deck_dir / "alone.toml").write_text(TOML)
    make_apkg(deck_dir / "fields.apkg")
    (deck_dir / "fields.toml").write_text(TOML.replace("Front", "English"))
    make_apkg(deck_dir / "language.apkg")
    (deck_dir / "language.toml").write_text(TOML.replace('"hr"', '"xx"'))
    (deck_dir / "syntax.toml").write_text("name = ")
    make_apkg(deck_dir / "good.apkg")
    (deck_dir / "good.toml").write_text(TOML)
    decks.import_decks()
    assert [deck["name"] for deck in store.decks("me")] == ["Basics"]
    text = caplog.text
    assert "alone.toml has no alone.apkg" in text
    assert "no note has the fields 'English' and 'Back'" in text
    assert "no language 'xx'" in text
    assert "deck syntax not imported" in text
