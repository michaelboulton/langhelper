import zipfile

import pytest
from tlhelper.flashcards import apkg, make_deck


@pytest.mark.parametrize("new_format", [False, True])
def test_reads_the_fields_by_name_in_both_formats(tmp_path, make_apkg, new_format):
    path = make_apkg(tmp_path / "deck.apkg", new_format=new_format)
    notes = apkg.read_notes(path)
    assert [note.guid for note in notes] == ["guid-house", "guid-hello", "guid-coffee"]
    assert notes[0] == apkg.Note(
        "guid-house", "Basic", {"Front": "house", "Back": "kuća"}
    )


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


def test_a_field_loses_its_html_and_its_sound():
    field = '<div>Dobar&nbsp;dan</div><div><b>gospodine</b></div>[sound:dan.mp3]<img src="a.png">'
    # A line of the card stays a line: it can be one of several answers.
    assert apkg.clean(field) == "Dobar dan\ngospodine"
    assert apkg.clean("kuća <br> <br>house") == "kuća\nhouse"
    assert apkg.clean("a &lt; b") == "a < b"


@pytest.mark.parametrize("new_format", [False, True])
def test_the_anki_deck_of_a_note(tmp_path, make_apkg, new_format):
    path = make_apkg(
        tmp_path / "deck.apkg",
        [("guid-a", "house", "kuća", 11), ("guid-b", "cat", "mačka", 12)],
        new_format=new_format,
        anki_decks={1: "Default", 11: "Croatian::Read::2", 12: "Croatian::Speak"},
    )
    assert [note.deck for note in apkg.read_notes(path)] == [
        ("Croatian", "Read", "2"),
        ("Croatian", "Speak"),
    ]


def test_the_media_files_of_a_field():
    field = (
        "[sound:dobar dan.mp3]<img src=\"my%20house.jpg\"><IMG class=x src='b&amp;b.PNG' />"
        "<img src=bare.gif>[sound:dobar dan.mp3]"
    )
    assert apkg.media_of(field) == [
        "dobar dan.mp3",
        "my house.jpg",
        "b&b.PNG",
        "bare.gif",
    ]
    # Not a file type for a card: a script, a font, a drawing with a script.
    assert apkg.media_of('<img src="x.svg">[sound:_font.ttf]<img src="">') == []


@pytest.mark.parametrize("new_format", [False, True])
def test_reads_a_media_file_in_both_formats(tmp_path, make_apkg, new_format):
    notes = [("guid-house", '<img src="house.jpg">', "kuća[sound:kuća.mp3]")]
    media = {"house.jpg": b"a picture", "kuća.mp3": b"a clip", "gone.jpg": b""}
    path = make_apkg(tmp_path / "deck.apkg", notes, new_format=new_format, media=media)
    [note] = apkg.read_notes(path)
    assert note.fields == {"Front": "", "Back": "kuća"}
    assert note.media == {"Front": ["house.jpg"], "Back": ["kuća.mp3"]}
    assert apkg.read_media(path, "house.jpg") == b"a picture"
    assert apkg.read_media(path, "kuća.mp3") == b"a clip"
    # A name is a key of the list, never a path into the zip or the disk.
    for name in ("absent.jpg", "0", "media", "../deck.apkg", "collection.anki21"):
        with pytest.raises(KeyError):
            apkg.read_media(path, name)


def test_a_new_export_has_a_new_media_list(tmp_path, make_apkg):
    path = make_apkg(tmp_path / "deck.apkg", media={"a.jpg": b"first"})
    assert apkg.read_media(path, "a.jpg") == b"first"
    path.unlink()
    make_apkg(path, media={"b.jpg": b"other", "a.jpg": b"second"})
    assert apkg.read_media(path, "a.jpg") == b"second"


def test_a_bad_file_gives_BadDeck(tmp_path):
    text = tmp_path / "text.apkg"
    text.write_text("not a zip")
    with pytest.raises(apkg.BadDeck, match="not a deck package"):
        apkg.read_notes(text)
    empty = tmp_path / "empty.apkg"
    with zipfile.ZipFile(empty, "w") as package:
        package.writestr("media", "{}")
    with pytest.raises(apkg.BadDeck, match="no collection"):
        apkg.read_notes(empty)
    broken = tmp_path / "broken.apkg"
    with zipfile.ZipFile(broken, "w") as package:
        package.writestr("collection.anki21", b"not sqlite")
    with pytest.raises(apkg.BadDeck):
        apkg.read_notes(broken)
    with pytest.raises(apkg.BadDeck):
        apkg.read_notes(tmp_path / "absent.apkg")
    with pytest.raises(apkg.BadDeck):
        apkg.read_media(tmp_path / "absent.apkg", "a.jpg")
    with zipfile.ZipFile(broken, "w") as package:
        package.writestr("media", b"not json and not zstd")
    with pytest.raises(apkg.BadDeck, match="no list of the media files"):
        apkg.read_media(broken, "a.jpg")
