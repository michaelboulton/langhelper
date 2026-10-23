"""The script of an audio lesson, and the course folder that holds it:

audio/<course>/
  course.toml   # language, name, and the voice of each speaker
  01.txt        # the script of lesson 1
  01/           # the clips of lesson 1, e.g. 1.05-3fa2c1.mp3
  01.mp3        # lesson 1 as one file
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import tomllib
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from ..languages import LANGUAGES

SPEAKERS = ("narrator", "actor 1", "actor 2")
ACTORS = ("actor 1", "actor 2")
HEADERS = ("topic", "summary", "grammar")
# A longer pause is a typo.
MAX_PAUSE = 30
COURSE_FILE = "course.toml"
TITLE = re.compile(r"#\s+(.+)")


class ScriptError(ValueError):
    pass


@dataclass(frozen=True)
class Line:
    speaker: str
    text: str


@dataclass(frozen=True)
class Pause:
    seconds: float


@dataclass(frozen=True)
class Script:
    title: str
    summary: str
    grammar: str
    # The --topic of scripts/audio_lessons.py. Empty in a script by hand.
    topic: str = ""
    lines: list[Line | Pause] = field(default_factory=list)


def one_line(text: str) -> str:
    return " ".join(text.split())


def parse(text: str, source: str = "the script") -> Script:
    """Raises ScriptError with the source and the number of the line."""
    title = None
    headers: dict[str, str] = {}
    lines: list[Line | Pause] = []
    for number, raw in enumerate(text.splitlines(), 1):
        where = f"{source}:{number}"
        if not raw.strip():
            continue
        if title is None:
            match = TITLE.fullmatch(raw.strip())
            if not match:
                raise ScriptError(f"{where}: the first line must be '# <title>'")
            title = one_line(match.group(1))
            continue
        key, colon, value = raw.partition(":")
        key, value = one_line(key).lower(), one_line(value)
        if not colon:
            raise ScriptError(f"{where}: no ':' after the speaker")
        if key in HEADERS:
            if lines:
                raise ScriptError(f"{where}: {key} after the first spoken line")
            if key in headers:
                raise ScriptError(f"{where}: a second {key} line")
            headers[key] = value
        elif key == "pause":
            try:
                seconds = float(value)
            except ValueError:
                seconds = 0
            # Also false for nan.
            if not 0 < seconds <= MAX_PAUSE:
                raise ScriptError(
                    f"{where}: a pause is a number of seconds up to {MAX_PAUSE},"
                    f" not {value!r}"
                )
            lines.append(Pause(seconds))
        elif key in SPEAKERS:
            if not value:
                raise ScriptError(f"{where}: {key} says nothing")
            lines.append(Line(key, value))
        else:
            raise ScriptError(
                f"{where}: {key!r} is not one of {', '.join(SPEAKERS)} or pause"
            )
    if title is None:
        raise ScriptError(f"{source}: no text")
    missing = [key for key in ("summary", "grammar") if not headers.get(key)]
    if missing:
        raise ScriptError(f"{source}: no {' or '.join(missing)} line")
    if not any(isinstance(line, Line) and line.speaker in ACTORS for line in lines):
        raise ScriptError(f"{source}: no line of an actor")
    return Script(
        title, headers["summary"], headers["grammar"], headers.get("topic", ""), lines
    )


def render(script: Script) -> str:
    head = [f"# {script.title}"]
    if script.topic:
        head.append(f"topic: {script.topic}")
    head += [f"summary: {script.summary}", f"grammar: {script.grammar}", ""]
    body = [
        f"pause: {line.seconds:g}"
        if isinstance(line, Pause)
        else f"{line.speaker}: {line.text}"
        for line in script.lines
    ]
    return "\n".join(head + body) + "\n"


def read_script(path: Path) -> Script:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScriptError(f"{path}: {exc}") from exc
    return parse(text, str(path))


def lesson_path(folder: Path, number: int) -> Path:
    return folder / f"{number:02d}.txt"


def clips_path(folder: Path, number: int) -> Path:
    return folder / f"{number:02d}"


def audio_path(folder: Path, number: int) -> Path:
    return folder / f"{number:02d}.mp3"


def stale(path: Path, sources: list[Path]) -> bool:
    """path is not there, or is not newer than each of its sources. A tie
    counts as older: with a coarse clock, a join too many and never one too
    few."""
    if not path.exists():
        return True
    made = path.stat().st_mtime_ns
    return any(source.stat().st_mtime_ns >= made for source in sources)


def lesson_files(folder: Path) -> dict[int, Path]:
    """{number: path} of the scripts in a course folder, in order."""
    found = {
        int(path.stem): path for path in folder.glob("*.txt") if path.stem.isdecimal()
    }
    return dict(sorted(found.items()))


class Course(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str
    name: str
    # {speaker: a named clip of the voice service}, such as {"actor 2": "it-2"}.
    voices: dict[str, str] = {}

    @field_validator("language")
    @classmethod
    def a_language(cls, value: str) -> str:
        if value not in LANGUAGES:
            raise ValueError(f"no language {value!r}: one of {', '.join(LANGUAGES)}")
        return value

    @field_validator("name")
    @classmethod
    def a_name(cls, value: str) -> str:
        value = one_line(value)
        if not value:
            raise ValueError("the name is empty")
        return value

    @field_validator("voices")
    @classmethod
    def speakers(cls, value: dict[str, str]) -> dict[str, str]:
        unknown = sorted(set(value) - set(SPEAKERS))
        if unknown:
            raise ValueError(
                f"no speaker {', '.join(unknown)}: one of {', '.join(SPEAKERS)}"
            )
        return value


def read_course(folder: Path) -> Course:
    path = folder / COURSE_FILE
    try:
        return Course.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as exc:
        raise ScriptError(f"{path}: {exc}") from exc
