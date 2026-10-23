"""tlhelper/audio_lessons/script.py, and scripts/audio_lessons.py with a fake
AI service and a fake voice service."""

import hashlib
import json
import os
import re
import shutil
import subprocess

import pytest
import tomllib
from scripts import audio_lessons, lessons
from tlhelper import speech
from tlhelper.audio_lessons import script

LESSON = """\
# Is there meat in this dish?
topic: asking whether a dish has meat in it
summary: Asking a waiter whether a dish has meat in it.
grammar: "there is / there isn't" (c'è, non c'è); yes/no questions.

narrator: You are in a restaurant in Rome. Listen to the conversation.
actor 1: Scusi, c'è carne in questo piatto?
actor 2: No, non c'è carne.
narrator: How do you say "is there"?
pause: 3
actor 1: c'è
narrator: Now ask whether there is meat in this dish.
pause: 5.5
actor 1: C'è carne in questo piatto?
"""
ANSWER_1 = """\
# Is there meat in this dish?
summary: Asking whether a dish has meat in it.
grammar: c'è and non c'è.

narrator: Listen.
actor 1: C'è carne?
actor 2: No, non c'è carne.
narrator: How do you say "is there"?
pause: 3
actor 1: c'è
"""
ANSWER_2 = """\
# The football team
summary: Talking about the local football team.
grammar: The present tense of giocare.

actor 1: La squadra gioca oggi?
actor 2: Sì, gioca alle tre.
narrator: Ask whether the team plays today.
pause: 4
actor 1: La squadra gioca oggi?
"""
HEAD = "# T\nsummary: a\ngrammar: x\n"


def test_a_script_round_trip():
    lesson = script.parse(LESSON)
    assert (lesson.title, lesson.topic) == (
        "Is there meat in this dish?",
        "asking whether a dish has meat in it",
    )
    assert lesson.lines[1:5] == [
        script.Line("actor 1", "Scusi, c'è carne in questo piatto?"),
        script.Line("actor 2", "No, non c'è carne."),
        script.Line("narrator", 'How do you say "is there"?'),
        script.Pause(3),
    ]
    assert script.Pause(5.5) in lesson.lines
    assert script.render(lesson) == LESSON


def test_a_loose_script_is_read():
    lesson = script.parse("\n# Title\nSummary:  A  b.\nGRAMMAR: x\n\nActor  1:  Bok.\n")
    assert (lesson.summary, lesson.topic) == ("A b.", "")
    assert lesson.lines == [script.Line("actor 1", "Bok.")]
    assert script.parse(script.render(lesson)) == lesson


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("", "01.txt: no text"),
        ("summary: a\n", "01.txt:1: the first line must be '# <title>'"),
        ("## T\n", "01.txt:1: the first line"),
        (HEAD + "Bok.\n", "01.txt:4: no ':'"),
        (HEAD + "actor 3: Bok.\n", "01.txt:4: 'actor 3' is not one of"),
        (HEAD + "actor 1:\n", "01.txt:4: actor 1 says nothing"),
        (HEAD + "pause: soon\n", "01.txt:4: a pause is a number"),
        (HEAD + "pause: 0\n", "01.txt:4: a pause"),
        (HEAD + "pause: nan\n", "01.txt:4: a pause"),
        (HEAD + "pause: 300\n", "01.txt:4: a pause"),
        (HEAD + "actor 1: Bok.\nsummary: b\n", "01.txt:5: summary after the first"),
        (HEAD + "summary: b\n", "01.txt:4: a second summary line"),
        ("# T\ngrammar: x\nactor 1: Bok.\n", "01.txt: no summary line"),
        ("# T\nsummary: \nactor 1: Bok.\n", "01.txt: no summary or grammar line"),
        (HEAD + "narrator: Hello.\npause: 2\n", "01.txt: no line of an actor"),
    ],
)
def test_a_script_error_names_the_line(text, error):
    with pytest.raises(script.ScriptError, match=re.escape(error)):
        script.parse(text, "01.txt")


@pytest.mark.parametrize(
    ("toml", "error"),
    [
        ('language = "xx"\nname = "X"\n', "no language 'xx'"),
        ('language = "it"\n', "name"),
        ('language = "it"\nname = "X"\nvoice = 1\n', "voice"),
        ('language = "it"\nname = "X"\n[voices]\n"actor 3" = "it-2"\n', "actor 3"),
        ("language = ", "course.toml"),
    ],
)
def test_a_bad_course_file(tmp_path, toml, error):
    (tmp_path / "course.toml").write_text(toml, encoding="utf-8")
    with pytest.raises(script.ScriptError, match=error):
        script.read_course(tmp_path)


def test_the_voices_of_a_course(tmp_path):
    (tmp_path / "course.toml").write_text(
        'language = "it"\nname = "Italian"\n[voices]\n"actor 2" = "it-2"\n',
        encoding="utf-8",
    )
    assert script.read_course(tmp_path).voices == {"actor 2": "it-2"}


@pytest.fixture
def course(tmp_path):
    return tmp_path / "audio" / "it-course"


def run(course, *args):
    audio_lessons.main(["--course", str(course), *args])


def first_run(course, *args):
    run(course, "--language", "it", "--name", "Italian", *args)


def files(course):
    return sorted(path.name for path in course.iterdir())


def test_each_topic_becomes_the_next_lesson(course, scripted, fake_lemmas):
    backend = scripted(ANSWER_1, ANSWER_2)
    first_run(course, "--topic", "a dish with meat", "--topic", "the football team")
    config = tomllib.loads((course / "course.toml").read_text(encoding="utf-8"))
    assert config == {"language": "it", "name": "Italian"}
    assert files(course) == ["01.txt", "02.txt", "course.toml"]
    assert backend.systems[0].startswith("You are a teacher of Italian")
    assert backend.kwargs[0] == {
        "max_tokens": audio_lessons.MAX_TOKENS,
        "timeout": audio_lessons.TIMEOUT,
    }
    one, two = backend.prompts
    assert "Earlier lessons" not in one
    assert "lesson 1 of a spoken course of Italian" in one
    assert "The topic of the lesson: a dish with meat" in one
    assert audio_lessons.FIRST_STEP in one
    # The memory of lesson 2: the summary and the grammar step of lesson 1,
    # and the words of its actors.
    assert (
        "Earlier lessons:\n1. Asking whether a dish has meat in it."
        " Grammar: c'è and non c'è.\n" in two
    )
    nouns = two.split("- nouns: ")[1].split("\n")[0].split(", ")
    assert "carne" in nouns
    assert "listen" not in nouns
    assert audio_lessons.NEXT_STEP in two
    # The topic is in the file, and the model chose the grammar step.
    first = script.read_script(course / "01.txt")
    assert (first.topic, first.grammar) == ("a dish with meat", "c'è and non c'è.")
    assert first.lines == script.parse(ANSWER_1).lines
    # scripts.lessons reads a script as a lesson, for the flashcards.
    assert lessons.read_lesson(str(course / "02.txt"))[0] == "The football team"
    assert lessons.lesson_key(str(course / "02.txt")) == "02"


def test_a_topic_in_the_course_is_not_asked_again(
    course, scripted, fake_lemmas, capsys
):
    scripted(ANSWER_1, ANSWER_2)
    first_run(course, "--topic", "a dish with meat", "--topic", "the football team")
    backend = scripted()
    run(course, "--topic", " A dish  with meat", "--topic", "the football team")
    assert backend.prompts == []
    assert "in the course already" in capsys.readouterr().out
    # --redo: the same topic and grammar step, and the lessons before it.
    backend = scripted(ANSWER_2)
    run(course, "--redo", "1")
    [prompt] = backend.prompts
    assert "Earlier lessons" not in prompt
    assert "The topic of the lesson: a dish with meat" in prompt
    assert "The grammar step of this lesson: c'è and non c'è." in prompt
    again = script.read_script(course / "01.txt")
    assert (again.title, again.topic, again.grammar) == (
        "The football team",
        "a dish with meat",
        "c'è and non c'è.",
    )
    with pytest.raises(SystemExit, match="no lesson 3"):
        run(course, "--redo", "3")
    # A deleted lesson gets its place back.
    (course / "01.txt").unlink()
    scripted(ANSWER_1)
    run(course, "--topic", "ordering a coffee")
    assert script.read_script(course / "01.txt").topic == "ordering a coffee"
    # A broken script stops the run before a request.
    (course / "03.txt").write_text("hello\n", encoding="utf-8")
    backend = scripted()
    with pytest.raises(SystemExit, match=r"03\.txt:1: the first line"):
        run(course, "--topic", "the weather")


def test_the_grammar_option(course, scripted, fake_lemmas, capsys):
    backend = scripted(ANSWER_1)
    first_run(course, "--topic", "a dish with meat", "--grammar", "the verb essere")
    assert "The grammar step of this lesson: the verb essere" in backend.prompts[0]
    assert script.read_script(course / "01.txt").grammar == "the verb essere"
    with pytest.raises(SystemExit):
        run(course, "--topic", "b", "--topic", "c", "--grammar", "x")
    assert "--grammar needs exactly one --topic" in capsys.readouterr().err


def test_the_name_and_the_language_come_from_the_course_file(
    course, scripted, fake_lemmas
):
    scripted(ANSWER_1)
    first_run(course, "--topic", "a dish with meat")
    with pytest.raises(SystemExit, match="--name cannot change it"):
        run(course, "--name", "Other", "--topic", "b")
    with pytest.raises(SystemExit, match="--language cannot change it"):
        run(course, "--language", "de", "--topic", "b")
    with pytest.raises(SystemExit, match="needs --language and --name"):
        run(course.parent / "other", "--topic", "b")


@pytest.mark.parametrize(
    "answer",
    ["I cannot help with that.", ANSWER_1.replace("actor 2", "actor 3"), HEAD],
    ids=["text", "speaker", "no lines"],
)
def test_a_bad_answer_is_asked_again_and_then_stops(
    course, scripted, fake_lemmas, answer
):
    backend = scripted(answer, answer)
    with pytest.raises(SystemExit, match="the answer is not valid"):
        first_run(course, "--topic", "a dish with meat")
    assert len(backend.prompts) == 2
    assert backend.prompts[1].endswith(audio_lessons.SCRIPT_ONLY)
    assert files(course) == ["course.toml"]


def test_an_answer_in_a_code_fence(course, scripted, fake_lemmas):
    scripted("Here it is:\n```text\n" + ANSWER_1 + "```\n")
    first_run(course, "--topic", "a dish with meat")
    assert script.read_script(course / "01.txt").title == "Is there meat in this dish?"


def test_a_dry_run_writes_nothing(course, scripted, capsys):
    backend = scripted()
    first_run(course, "--dry-run", "--topic", "a dish with meat", "--topic", "b")
    out = capsys.readouterr().out
    assert "The topic of the lesson: a dish with meat" in out
    assert "The topic of the lesson: b" not in out
    assert "[about" in out
    assert backend.prompts == []
    assert not course.exists()


class FakeVoice:
    """The mp3 of a line is its language, its voice and its text."""

    name = "fake"

    def __init__(self):
        self.asked = []

    def available(self):
        return True

    def synthesize(self, text, language, voice=None):
        self.asked.append((text, language, voice))
        return f"{language} {voice} {text}".encode()


@pytest.fixture
def fake_voice(monkeypatch):
    voice = FakeVoice()
    monkeypatch.setattr(speech, "current", lambda: voice)
    return voice


@pytest.fixture
def fake_join(monkeypatch):
    """No ffmpeg: each join is (the name of the mp3, its parts)."""
    joins = []

    def join(ffmpeg, folder, parts, path):
        joins.append((path.name, parts))
        path.write_bytes(b"joined")

    monkeypatch.setattr(audio_lessons, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(audio_lessons, "join", join)
    return joins


def write_course(course, lesson=LESSON):
    course.mkdir(parents=True)
    (course / "course.toml").write_text(
        'language = "it"\nname = "Italian"\n[voices]\n"actor 2" = "it-2"\n',
        encoding="utf-8",
    )
    (course / "01.txt").write_text(lesson, encoding="utf-8")


def clip_names(course):
    return sorted(path.name for path in (course / "01").iterdir())


def digest(language, voice, text):
    text = f"{language}\t{voice}\t{text}"
    return hashlib.sha1(text.encode(), usedforsecurity=False).hexdigest()[:6]


def settle(course):
    """The script and the clips older than the mp3, as after a while."""
    made = (course / "01.mp3").stat().st_mtime_ns
    for path in [course / "01.txt", *(course / "01").iterdir()]:
        os.utime(path, ns=(made - 10**10, made - 10**10))


def test_voice_reads_each_line_into_a_clip(course, fake_voice, fake_join):
    write_course(course, LESSON + "actor 1: c'è\n")
    run(course, "--voice")
    # The narrator in English, actor 1 in the default voice of the language,
    # and actor 2 in the voice of course.toml. A line said twice is asked once.
    assert fake_voice.asked == [
        ("You are in a restaurant in Rome. Listen to the conversation.", "en", None),
        ("Scusi, c'è carne in questo piatto?", "it", None),
        ("No, non c'è carne.", "it", "it-2"),
        ('How do you say "is there"?', "en", None),
        ("c'è", "it", None),
        ("Now ask whether there is meat in this dish.", "en", None),
        ("C'è carne in questo piatto?", "it", None),
    ]
    names = clip_names(course)
    assert [name.split("-")[0] for name in names] == [f"1.0{n}" for n in range(1, 9)]
    no_meat = digest("it", "it-2", "No, non c'è carne.")
    there_is = digest("it", "", "c'è")
    assert (names[2], names[4], names[7]) == (
        f"1.03-{no_meat}.mp3",
        f"1.05-{there_is}.mp3",
        f"1.08-{there_is}.mp3",
    )
    clip = (course / "01" / names[2]).read_bytes().decode()
    assert clip == "it it-2 No, non c'è carne."
    assert (course / "01" / names[7]).read_bytes().decode() == "it None c'è"
    # The clips in the order of the script, each pause, and a gap between two
    # lines.
    [(mp3, parts)] = fake_join
    assert mp3 == "01.mp3"
    gap = audio_lessons.GAP
    expected = [names[0], gap, names[1], gap, names[2], gap, names[3], 3]
    expected += [names[4], gap, names[5], 5.5, names[6], gap, names[7]]
    assert [part if isinstance(part, float) else part.name for part in parts] == (
        expected
    )


def test_a_new_lesson_is_voiced_in_the_same_run(
    course, scripted, fake_lemmas, fake_voice, fake_join, capsys
):
    scripted(ANSWER_1)
    first_run(course, "--topic", "a dish with meat", "--voice")
    assert files(course) == ["01", "01.mp3", "01.txt", "course.toml"]
    assert len(clip_names(course)) == len(fake_voice.asked) == 5
    assert [mp3 for mp3, _ in fake_join] == ["01.mp3"]
    assert "no voice for actor 2" in capsys.readouterr().out


def test_a_rerun_asks_only_for_the_new_lines(course, fake_voice, fake_join):
    write_course(course)
    run(course, "--voice")
    before = [name.split("-")[1] for name in clip_names(course)]
    # Nothing new: no request, and no join.
    settle(course)
    fake_voice.asked.clear()
    fake_join.clear()
    run(course, "--voice")
    assert (fake_voice.asked, fake_join) == ([], [])
    # A new first line and a changed line: the others move, with their clips.
    edited = LESSON.replace(
        "narrator: You", "actor 2: Buongiorno!\nnarrator: You"
    ).replace("No, non c'è carne.", "Sì, c'è carne.")
    (course / "01.txt").write_text(edited, encoding="utf-8")
    (course / "01" / "1.02-abcdef.tmp").write_bytes(b"from a run that died")
    run(course, "--voice")
    assert fake_voice.asked == [
        ("Buongiorno!", "it", "it-2"),
        ("Sì, c'è carne.", "it", "it-2"),
    ]
    assert len(fake_join) == 1
    # Only the clips of the lines are left.
    after = clip_names(course)
    assert [name.split("-")[0] for name in after] == [f"1.0{n}" for n in range(1, 9)]
    hello = digest("it", "it-2", "Buongiorno!")
    yes_meat = digest("it", "it-2", "Sì, c'è carne.")
    assert [name.split("-")[1] for name in after] == [
        f"{hello}.mp3",
        *before[:2],
        f"{yes_meat}.mp3",
        *before[3:],
    ]

    # A failure of the service stops the run, and deletes no clip.
    def broken(text, language, voice=None):
        raise speech.SpeechError("the voice service is down")

    fake_voice.synthesize = broken
    (course / "01.txt").write_text(
        edited.replace("Buongiorno!", "Buonasera!"), encoding="utf-8"
    )
    with pytest.raises(SystemExit, match="'Buonasera!' .*the voice service is down"):
        run(course, "--voice")
    assert clip_names(course) == after


def test_voice_needs_ffmpeg_and_the_voice_service(course, monkeypatch, tmp_path):
    write_course(course)
    monkeypatch.delenv("TLHELPER_VOICE_URL", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "nothing"))
    with pytest.raises(SystemExit, match="--voice needs ffmpeg"):
        run(course, "--voice")
    monkeypatch.setattr(audio_lessons, "find_ffmpeg", lambda: "ffmpeg")
    with pytest.raises(SystemExit, match="set TLHELPER_VOICE_URL"):
        run(course, "--voice")
    # A dry run voices nothing, so it needs neither.
    run(course, "--voice", "--dry-run")
    assert files(course) == ["01.txt", "course.toml"]


def test_the_names_sort_by_line():
    course = script.Course(language="it", name="Italian")
    lesson = script.parse(HEAD + "".join(f"actor 1: Riga {n}.\n" for n in range(100)))
    clips = audio_lessons.clips_of(audio_lessons.parts_of(course, 3, lesson))
    names = [clip.name for clip in clips]
    assert (names[0][:6], names[-1][:6]) == ("3.001-", "3.100-")
    assert sorted(names) == names


def probe(path):
    output = subprocess.run(  # noqa: S603
        [
            shutil.which("ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=channels,sample_rate",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        check=True,
    ).stdout
    found = json.loads(output)
    [stream] = found["streams"]
    return float(found["format"]["duration"]), stream["channels"], stream["sample_rate"]


@pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
    reason="no ffmpeg (apt install ffmpeg)",
)
def test_the_join_with_ffmpeg(tmp_path):
    ffmpeg = audio_lessons.find_ffmpeg()
    folder = tmp_path / "01"
    folder.mkdir()

    def clip(name):
        return audio_lessons.Clip(name, "", "actor 1", "", "it", None)

    # Two clips of silence, of 1 and 0.5 seconds.
    audio_lessons.join(ffmpeg, folder, [1.0], folder / "a.mp3")
    audio_lessons.join(ffmpeg, folder, [0.5], folder / "b.mp3")
    path = tmp_path / "01.mp3"
    parts = [clip("a.mp3"), audio_lessons.GAP, clip("b.mp3"), 2.0, clip("a.mp3")]
    audio_lessons.join(ffmpeg, folder, parts, path)
    duration, channels, rate = probe(path)
    assert duration == pytest.approx(1 + audio_lessons.GAP + 0.5 + 2 + 1, abs=0.2)
    assert (channels, rate) == (1, str(audio_lessons.SAMPLE_RATE))
    # A clip that is not an mp3: no file, and the error of ffmpeg.
    (folder / "b.mp3").write_bytes(b"not an mp3")
    with pytest.raises(lessons.LessonError, match="ffmpeg failed"):
        audio_lessons.join(ffmpeg, folder, parts, tmp_path / "02.mp3")
    assert sorted(path.name for path in tmp_path.iterdir()) == ["01", "01.mp3"]
