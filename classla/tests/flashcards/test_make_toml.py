import sys
import tomllib

import pytest

from tlhelper.flashcards import decks, make_toml, store
from tlhelper.flashcards.apkg import Note

NOTES = [
    ("guid-house", "kuća", "house", ""),
    ("guid-thirsty", "žedan", "thirsty", ""),
    ("guid-coffee", "Pijem kavu.", "I drink coffee.", "[sound:kava.mp3]"),
]


def run(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["make_toml", *map(str, args)])
    make_toml.main()


def test_the_result_imports(deck_dir, make_apkg, monkeypatch):
    package = make_apkg(
        deck_dir / "my-deck.apkg", NOTES, fields=("Word", "Meaning", "Audio")
    )
    run(monkeypatch, package, "--language", "hr")

    config = tomllib.loads((deck_dir / "my-deck.toml").read_text(encoding="utf-8"))
    assert config == {
        "name": "my deck",
        "language": "hr",
        "english_field": "Meaning",
        "answer_field": "Word",
        "notetype": ["Basic"],
        "reverse": False,
        "new_per_day": 10,
        "reviews_per_day": 100,
    }
    decks.import_decks()
    [deck] = store.decks("anyone")
    assert (deck["name"], deck["counts"]["total"]) == ("my deck", 3)


def test_options_win_and_a_file_stays(deck_dir, make_apkg, monkeypatch):
    package = make_apkg(deck_dir / "basics.apkg")
    run(monkeypatch, package, "--language", "hr", "--english-field", "Back")
    with pytest.raises(SystemExit, match="--force"):
        run(monkeypatch, package, "--language", "hr")
    run(monkeypatch, package, "--language", "hr", "--reverse", "--force")

    config = tomllib.loads((deck_dir / "basics.toml").read_text(encoding="utf-8"))
    assert (config["english_field"], config["reverse"]) == ("Front", True)


def test_the_options_for_subdecks(deck_dir, make_apkg, monkeypatch, capsys):
    notes = [
        ("guid-a", "I was.", "Bio sam.<br>Bila sam.", 11),
        ("guid-b", "Yes.", "Da.", 12),
    ]
    package = make_apkg(
        deck_dir / "basics.apkg", notes, anki_decks={11: "All::Read", 12: "All::Speak"}
    )
    options = ("--subdecks", "--to-english-notetype", "Basic", "--lines")
    run(monkeypatch, package, "--language", "hr", "--english-field", "Front", *options)
    assert "1 All :: Read" in capsys.readouterr().out
    decks.import_decks()
    assert [deck["name"] for deck in store.decks("anyone")] == ["Read", "Speak"]
    card = store.next_card("anyone", store.decks("anyone")[0]["id"])["card"]
    assert (card["direction"], card["answers"]) == ("to_english", ["I was."])


def test_guess_leaves_out_the_small_and_the_different_note_types():
    notes = [
        Note(f"w{n}", "Words", {"Front": "kuća", "Back": "house"}) for n in range(150)
    ]
    notes += [
        Note(f"m{n}", "More", {"Front": "žedan", "Back": "thirsty"}) for n in range(50)
    ]
    notes += [Note(f"c{n}", "Cloze", {"Text": "Ja {{c1::sam}}"}) for n in range(20)]
    notes += [Note("q", "Basic", {"Front": "a question", "Back": "its answer"})]
    assert make_toml.guess(notes) == {
        "english_field": "Back",
        "answer_field": "Front",
        "notetype": ["Words", "More"],
    }


def test_notetype_can_be_a_list():
    notes = [
        Note("a", "Words", {"Front": "house", "Back": "kuća"}),
        Note("b", "More", {"Front": "thirsty", "Back": "žedan"}),
        Note("c", "Basic", {"Front": "a question", "Back": "its answer"}),
    ]
    config = decks.DEFAULTS | {"english_field": "Front", "answer_field": "Back"}

    def guids(notetype):
        cards = decks.cards_of(notes, config | {"notetype": notetype})
        return [card["guid"] for card in cards]

    assert guids(["Words", "More"]) == ["a", "b"]
    assert guids("More") == ["b"]
    assert guids(None) == ["a", "b", "c"]
