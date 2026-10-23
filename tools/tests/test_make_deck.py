from tlhelper.flashcards import apkg

from scripts import make_deck


def test_make_deck_writes_a_package_that_the_reader_reads(tmp_path):
    source = tmp_path / "mine.tsv"
    source.write_text(
        "# a comment\nhouse\tkuća\n\nhello\tbok / zdravo\n", encoding="utf-8"
    )
    first = apkg.read_notes(make_deck.make_deck(source))
    assert [note.fields for note in first] == [
        {"Front": "house", "Back": "kuća"},
        {"Front": "hello", "Back": "bok / zdravo"},
    ]
    # The guid comes from the English text: a new answer is the same note.
    source.write_text("hello\tbok\n", encoding="utf-8")
    [second] = apkg.read_notes(make_deck.make_deck(source))
    assert second.guid == first[1].guid


def test_write_package_gives_each_note_its_anki_deck(tmp_path):
    notes = [
        make_deck.PackageNote("g1", "house", "kuća", "Course::001 Nouns"),
        make_deck.PackageNote("g2", "I am.", "Ja sam.", "Course::002 To be"),
        make_deck.PackageNote("g3", "cat", "mačka", "Course::001 Nouns"),
    ]
    package = make_deck.write_package(tmp_path / "course.apkg", notes)
    assert [(note.guid, note.deck) for note in apkg.read_notes(package)] == [
        ("g1", ("Course", "001 Nouns")),
        ("g2", ("Course", "002 To be")),
        ("g3", ("Course", "001 Nouns")),
    ]


def test_write_package_with_a_clip(tmp_path):
    notes = [make_deck.PackageNote("g1", "house", "kuća [sound:a1.mp3]", "Course")]
    package = make_deck.write_package(
        tmp_path / "course.apkg", notes, {"a1.mp3": b"a clip"}
    )
    [note] = apkg.read_notes(package)
    assert (note.fields["Back"], note.media) == ("kuća", {"Back": ["a1.mp3"]})
    assert apkg.read_media(package, "a1.mp3") == b"a clip"
