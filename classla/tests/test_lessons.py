"""scripts/lessons.py: flashcards from lessons, with a fake AI service."""

import json

import pytest

from scripts import lessons
from tlhelper import explain
from tlhelper.flashcards import apkg, decks, store

LESSON_1 = """\
# To wander

The verb *lutati* means to wander. Ja lutam, mi lutamo.
"""
ANSWER_1 = {
    "summary": "The verb lutati (to wander) in the present tense.",
    "vocabulary": ["lutati", "grad"],
    "cards": [
        {"english": "I wander through the town.", "answer": "Lutam gradom."},
        {"english": "We wander.", "answer": "Lutamo."},
    ],
}
LESSON_2 = """\
# The past tense

The past tense of a verb: bio sam, bili smo.
"""
ANSWER_2 = {
    "summary": "The past tense of verbs.",
    "vocabulary": ["biti"],
    "cards": [
        {"english": "We wandered.", "answer": "Lutali smo. / Lutale smo."},
        {"english": "They wandered.", "answer": "Lutali su."},
        {"english": "I was.", "answer": "Bio sam. / Bila sam."},
    ],
}


class ScriptedBackend:
    """Gives its answers in order, and keeps what it was asked."""

    name = "scripted"

    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []
        self.systems = []
        self.kwargs = []

    def available(self):
        return True

    def model(self):
        return "scripted-model"

    def complete(self, system, prompt, **kwargs):
        self.systems.append(system)
        self.prompts.append(prompt)
        self.kwargs.append(kwargs)
        assert self.answers, "one request too many"
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, str) else json.dumps(answer)


@pytest.fixture
def scripted(monkeypatch):
    """scripted(*answers): the AI service of the next run."""

    def use(*answers):
        backend = ScriptedBackend(answers)
        monkeypatch.setitem(explain.BACKENDS, "scripted", backend)
        monkeypatch.setenv("TLHELPER_AI_BACKEND", "scripted")
        return backend

    return use


@pytest.fixture
def fake_lemmas(monkeypatch):
    """Each word of the tagged text is a noun: no model load."""

    def lemmas_of(text, language):
        words = sorted({word.strip(".").lower() for word in text.split()})
        return {"NOUN": words} if words else {}

    monkeypatch.setattr(lessons, "lemmas_of", lemmas_of)


@pytest.fixture
def course(deck_dir):
    """The stem of a course in the deck folder, with two lesson files next
    to it."""
    (deck_dir / "01.md").write_text(LESSON_1, encoding="utf-8")
    (deck_dir / "02.md").write_text(LESSON_2, encoding="utf-8")
    return deck_dir / "course"


def run(course, *args):
    lessons.main(["--course", str(course), *args])


def first_run(course, *args):
    run(course, "--language", "hr", "--name", "Croatian course", *args)


def test_the_second_run_builds_on_the_first(course, scripted):
    backend = scripted(ANSWER_1)
    first_run(course, str(course.parent / "01.md"))
    assert backend.kwargs == [
        {"max_tokens": lessons.MAX_TOKENS, "timeout": lessons.TIMEOUT}
    ]
    assert "Earlier lessons" not in backend.prompts[0]
    assert "Lesson 1: To wander" in backend.prompts[0]
    assert backend.systems[0].startswith("You are a teacher of Croatian")
    memory = lessons.load_course(course.with_suffix(".json"))
    [lesson] = memory.lessons
    assert (lesson.key, lesson.number, lesson.title) == ("01", 1, "To wander")
    # The tagger ran on the answers and the vocabulary.
    assert "lutati" in lesson.lemmas["VERB"]
    assert "grad" in lesson.lemmas["NOUN"]
    notes = apkg.read_notes(course.with_suffix(".apkg"))
    assert [note.deck for note in notes] == [("Croatian course", "001 To wander")] * 2

    decks.import_decks()
    [deck] = store.decks("me")
    assert (deck["name"], deck["path"], deck["counts"]["total"]) == (
        "001 To wander",
        ["Croatian course", "001 To wander"],
        2,
    )
    card = store.next_card("me", deck["id"])["card"]
    store.answer("me", card["id"], 3, card["answers"][0], None)

    # The second run: only the new lesson, and no --language or --name.
    backend = scripted(ANSWER_2)
    run(course, str(course.parent / "02.md"))
    [prompt] = backend.prompts
    assert (
        "Earlier lessons:\n1. The verb lutati (to wander) in the present tense."
        in prompt
    )
    assert "- verbs: " in prompt
    assert "lutati" in prompt.split("- verbs: ")[1].split("\n")[0]
    assert "Lesson 2: The past tense" in prompt
    memory = lessons.load_course(course.with_suffix(".json"))
    assert [(lesson.key, lesson.number) for lesson in memory.lessons] == [
        ("01", 1),
        ("02", 2),
    ]
    # "biti" is new, "lutati" is not new in lesson 2.
    assert "lutati" not in memory.lessons[1].lemmas.get("VERB", [])
    after = apkg.read_notes(course.with_suffix(".apkg"))
    assert [note.guid for note in after[:2]] == [note.guid for note in notes]
    assert after[2].deck == ("Croatian course", "002 The past tense")
    assert after[2].fields == {
        "Front": "We wandered.",
        "Back": "Lutali smo. / Lutale smo.",
    }

    decks.import_decks()
    first, second = store.decks("me")
    assert (first["name"], first["counts"]["learning"]) == ("001 To wander", 1)
    assert (second["name"], second["counts"]["total"]) == ("002 The past tense", 3)
    toml = course.with_suffix(".toml").read_text(encoding="utf-8")
    assert 'separators = [" / "]' in toml
    assert "subdecks = true" in toml


def test_a_lesson_in_the_course_is_not_asked_again(
    course, scripted, fake_lemmas, capsys
):
    scripted(ANSWER_1, ANSWER_2)
    first_run(course, str(course.parent / "01.md"), str(course.parent / "02.md"))
    backend = scripted()
    run(course, str(course.parent / "01.md"), str(course.parent / "02.md"))
    assert backend.prompts == []
    assert "01: in the course already" in capsys.readouterr().out
    # --redo asks again, and the lesson keeps its number and its title.
    backend = scripted(ANSWER_1 | {"summary": "Again."})
    run(course, "--redo", "01", "--title", "01=Wandering", str(course.parent / "01.md"))
    [prompt] = backend.prompts
    assert "Earlier lessons" not in prompt
    assert "Lesson 1: Wandering" in prompt
    memory = lessons.load_course(course.with_suffix(".json"))
    assert [(one.number, one.title, one.summary) for one in memory.lessons] == [
        (1, "Wandering", "Again."),
        (2, "The past tense", "The past tense of verbs."),
    ]
    assert apkg.read_notes(course.with_suffix(".apkg"))[0].deck == (
        "Croatian course",
        "001 Wandering",
    )


def test_the_name_and_the_language_come_from_the_memory_file(
    course, scripted, fake_lemmas
):
    scripted(ANSWER_1)
    first_run(course, str(course.parent / "01.md"))
    with pytest.raises(SystemExit, match="--name cannot change it"):
        run(course, "--name", "Other", str(course.parent / "02.md"))
    with pytest.raises(SystemExit, match="--language cannot change it"):
        run(course, "--language", "de", str(course.parent / "02.md"))
    with pytest.raises(SystemExit, match="needs --language and --name"):
        run(course.parent / "other", str(course.parent / "02.md"))


def test_build_only_writes_the_deck_from_the_memory_file(course, scripted, fake_lemmas):
    scripted(ANSWER_1)
    first_run(course, str(course.parent / "01.md"))
    memory = course.with_suffix(".json")
    edited = memory.read_text(encoding="utf-8").replace("Lutamo.", "Mi lutamo.")
    memory.write_text(edited, encoding="utf-8")
    course.with_suffix(".apkg").unlink()
    scripted()
    run(course, "--build-only")
    notes = apkg.read_notes(course.with_suffix(".apkg"))
    assert notes[1].fields["Back"] == "Mi lutamo."
    # A typo in the file is an error.
    memory.write_text(edited.replace('"summary"', '"sumary"'), encoding="utf-8")
    with pytest.raises(SystemExit, match="sumary"):
        run(course, "--build-only")


@pytest.mark.parametrize(
    "answer",
    [
        "I cannot help with that.",
        {"summary": "x", "vocabulary": [], "cards": []},
        {"summary": "x", "cards": [{"english": "Hi.", "answer": "Bok; zdravo"}]},
        {
            "summary": "x",
            "cards": [
                {"english": "Hi.", "answer": "Bok"},
                {"english": "hi.", "answer": "Zdravo"},
            ],
        },
        {"summary": "x", "cards": [{"english": "", "answer": "Bok"}]},
        {"summary": "x", "cards": [{"english": "Hi.", "answer": "Bok"}], "extra": 1},
    ],
    ids=["text", "no cards", "semicolon", "twice", "blank", "extra key"],
)
def test_a_bad_answer_is_asked_again_and_then_stops(
    course, scripted, fake_lemmas, answer
):
    backend = scripted(answer, answer)
    with pytest.raises(SystemExit, match="not valid"):
        first_run(course, str(course.parent / "01.md"))
    assert len(backend.prompts) == 2
    assert backend.prompts[1].endswith("Answer with JSON only.")
    assert not course.with_suffix(".json").exists()
    assert not course.with_suffix(".apkg").exists()


def test_an_answer_in_a_code_fence(course, scripted, fake_lemmas):
    scripted("Here it is:\n```json\n" + json.dumps(ANSWER_1) + "\n```\n")
    first_run(course, str(course.parent / "01.md"))
    assert len(lessons.load_course(course.with_suffix(".json")).lessons[0].cards) == 2


def test_a_busy_service_is_asked_again(course, scripted, fake_lemmas, monkeypatch):
    waits = []
    monkeypatch.setattr(lessons, "sleep", waits.append)
    busy = explain.ExplainError("busy", "ai-busy")
    scripted(busy, ANSWER_1)
    first_run(course, str(course.parent / "01.md"))
    assert waits == [lessons.BUSY_WAIT]
    assert course.with_suffix(".apkg").exists()
    # Another error stops the run, and the memory file stays as it was.
    scripted(explain.ExplainError("no key"))
    with pytest.raises(SystemExit, match="no key"):
        run(course, str(course.parent / "02.md"))
    assert len(lessons.load_course(course.with_suffix(".json")).lessons) == 1


def test_the_backend_option(course, fake_lemmas, fake_claude, monkeypatch):
    """--backend selects a backend of the app in place of the variable."""
    monkeypatch.delenv("TLHELPER_AI_MODEL", raising=False)
    monkeypatch.setenv("TLHELPER_AI_BACKEND", "other")
    with pytest.raises(SystemExit, match="must be one of: claude, openai"):
        first_run(course, str(course.parent / "01.md"))
    folder = fake_claude(json.dumps(ANSWER_1))
    first_run(course, "--backend", "claude", str(course.parent / "01.md"))
    args = (folder / "args").read_text(encoding="utf-8").split("\n")
    assert args[6:8] == [
        "--system-prompt",
        lessons.system_text(lessons.Course(language="hr", name="x")),
    ]
    assert "Lesson 1: To wander" in (folder / "prompt").read_text(encoding="utf-8")
    assert lessons.load_course(course.with_suffix(".json")).lessons[0].model == "claude"
    # An error of the CLI stops the run.
    fake_claude("", code=1, stderr="Not logged in")
    with pytest.raises(SystemExit, match=r"claude failed \(1\): Not logged in"):
        first_run(course, "--backend", "claude", str(course.parent / "02.md"))


def test_a_dry_run_writes_nothing(course, scripted, capsys):
    backend = scripted()
    first_run(course, "--dry-run", str(course.parent / "01.md"))
    out = capsys.readouterr().out
    assert "Lesson 1: To wander" in out
    assert "[about" in out
    assert backend.prompts == []
    assert sorted(path.name for path in course.parent.iterdir()) == ["01.md", "02.md"]


def test_the_key_of_a_lesson():
    assert lessons.lesson_key("lessons/03.md") == "03"
    assert lessons.lesson_key("https://www.easy-croatian.com/2014/11/16.html") == "16"
    assert lessons.lesson_key("https://site.test/lesson-3/") == "lesson-3"
    assert lessons.lesson_key("https://site.test") == "site.test"


def test_a_long_lesson_is_cut_at_a_paragraph():
    text = "\n\n".join(f"Paragraph {n} " + "x" * 50 for n in range(10))
    kept, was_cut = lessons.cut(text, 300)
    assert was_cut
    assert kept.endswith("x") and "\n\nParagraph 5" not in kept
    assert kept.count("Paragraph") == 4
    assert lessons.cut("short", 300) == ("short", False)


def test_the_lemmas_of_the_memory(monkeypatch):
    def lesson(number, lemmas):
        return lessons.Lesson(
            key=str(number),
            number=number,
            source="",
            title="",
            model="",
            summary="",
            lemmas=lemmas,
            cards=[],
        )

    earlier = [
        lesson(
            1,
            {"VERB": [f"v{n}" for n in range(5)], "NOUN": [f"a{n}" for n in range(5)]},
        ),
        lesson(
            2,
            {"VERB": [f"w{n}" for n in range(5)], "NOUN": [f"b{n}" for n in range(5)]},
        ),
        lesson(3, {"NOUN": ["c0", "c1", "c2"]}),
    ]
    assert lessons.memory_lemmas(earlier) == {
        "VERB": [f"v{n}" for n in range(5)] + [f"w{n}" for n in range(5)],
        "NOUN": [f"a{n}" for n in range(5)]
        + [f"b{n}" for n in range(5)]
        + ["c0", "c1", "c2"],
    }
    # With a cap: all of the last lessons, then a sample with the verbs first.
    monkeypatch.setattr(lessons, "MAX_MEMORY_LEMMAS", 10)
    monkeypatch.setattr(lessons, "RECENT_LESSONS", 1)
    capped = lessons.memory_lemmas(earlier)
    assert sum(len(lemmas) for lemmas in capped.values()) == 10
    assert {"c0", "c1", "c2"} <= set(capped["NOUN"])
    assert len(capped["VERB"]) == 4


def test_the_lemmas_of_a_text():
    lemmas = lessons.lemmas_of("Lutali smo gradom.\nPijem kavu.\nlutati\n2024", "hr")
    # The light model: a lemma in lower case, in the group of its part of
    # speech, with no punctuation, no pronoun and no number.
    assert "lutati" in lemmas["VERB"]
    assert "kava" in lemmas["NOUN"]
    assert set(lemmas) <= set(lessons.LEMMA_UPOS)
    assert all(
        lemma.isalpha() and lemma.islower() for v in lemmas.values() for lemma in v
    )
    assert lessons.lemmas_of("  ", "hr") == {}


HTML = """\
<html><head><title>Lesson 3 - The site</title></head><body>
<nav>Home | Next</nav>
<article>
<h2>The cases</h2>
<p>The <b>genitive</b> answers the question <i>whose</i>.</p>
<ul><li>kuća, kuće</li></ul>
<div class="post-comments"><p>Great post!</p></div>
<div id="comments-form">Leave a comment</div>
</article>
<footer>Copyright</footer>
</body></html>
"""


def test_a_web_page_becomes_markdown(monkeypatch):
    pytest.importorskip("markdownify")
    title, markdown = lessons.markdown_of_html(HTML)
    assert title == "Lesson 3 - The site"
    assert "## The cases" in markdown
    assert "**genitive**" in markdown
    assert "*whose*" in markdown
    assert "kuća, kuće" in markdown
    for gone in ("Home", "Great post", "Leave a comment", "Copyright"):
        assert gone not in markdown
    monkeypatch.setattr(lessons, "fetch", lambda url: HTML)
    assert lessons.read_lesson("https://site.test/2014/03.html")[0] == "The cases"
    monkeypatch.setattr(lessons, "fetch", lambda url: "<html><body>text</body></html>")
    assert lessons.read_lesson("https://site.test/2014/03.html")[0] == "03"


def test_a_title_cannot_hold_a_deck_separator(course, scripted, fake_lemmas):
    (course.parent / "01.md").write_text("# A::B\n\ntext\n", encoding="utf-8")
    scripted(ANSWER_1)
    first_run(course, str(course.parent / "01.md"))
    assert apkg.read_notes(course.with_suffix(".apkg"))[0].deck == (
        "Croatian course",
        "001 A B",
    )
