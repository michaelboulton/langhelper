from tlhelper.flashcards import inspect_deck

TOML = """
name = "Basics"
language = "hr"
english_field = "Front"
answer_field = "Back"
reverse = true
"""


def run(*args):
    inspect_deck.main([*map(str, args)], standalone_mode=False)


def test_notes_counts_the_filled_fields(deck_dir, make_apkg, capsys):
    notes = [("guid-a", "kuća", "house", ""), ("guid-b", "žedan", "", "")]
    package = make_apkg(
        deck_dir / "basics.apkg", notes, fields=("Word", "Meaning", "Audio")
    )
    run("notes", package)
    out = capsys.readouterr().out
    assert "'Basic': 2 notes" in out
    assert "       2 Word\n       1 Meaning\n       0 Audio\n" in out

    run("notes", package, "--grep", "^ku")
    assert capsys.readouterr().out.startswith("1 notes")


def test_cards_filters_by_direction_and_text(deck_dir, make_apkg, capsys):
    package = make_apkg(deck_dir / "basics.apkg")
    (deck_dir / "basics.toml").write_text(TOML, encoding="utf-8")
    run("cards", package, "--direction", "to_english", "--grep", "kavu")
    out = capsys.readouterr().out
    assert "6 cards: {'to_study': 3, 'to_english': 3}" in out
    assert "1 cards match" in out
    assert "to_english: 'Pijem kavu.' [] -> ['I drink coffee.'] []" in out
