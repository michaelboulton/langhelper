"""The routes of the audio lessons tab. The courses are the folders of
DATA_ROOT/audio/, in the layout of script.py.

GET /api/v1/audio-lessons                        the courses and their lessons,
                                                 with the progress of the user
GET /api/v1/audio-lessons/{course}/{lesson}      the script of a lesson
GET /api/v1/audio-lessons/{course}/{lesson}.mp3  the sound of a lesson
PUT /api/v1/audio-lessons/{course}/{lesson}/progress  save the position of
                                                 the user in a lesson
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import Field

from .. import schemas
from ..flashcards import store
from ..flashcards.routes import User
from ..settings import DATA_ROOT
from . import script

AUDIO_ROOT = DATA_ROOT / "audio"

router = APIRouter(prefix="/api/v1", tags=["audio lessons"])
logger = logging.getLogger("uvicorn.error")


def course_folder(course: str) -> Path:
    """The folder of a course, or 404. The name must not lead out of
    audio/: "..", for example."""
    root = AUDIO_ROOT.resolve()
    folder = (root / course).resolve()
    if folder.parent != root or not (folder / script.COURSE_FILE).is_file():
        raise HTTPException(status_code=404, detail=f"no course {course!r}")
    return folder


class AudioProgressRequest(schemas.Model):
    position: float = Field(ge=0)
    """Where the player is, in seconds."""
    duration: float = Field(gt=0)
    """The length of the mp3 in seconds, as the player sees it."""


NOT_STARTED = {"position": 0.0, "duration": 0.0, "finished": False}


def audio_state(folder: Path, number: int, path: Path) -> str:
    audio = script.audio_path(folder, number)
    if not audio.is_file():
        return "none"
    return "stale" if script.stale(audio, [path]) else "ready"


@router.get("/audio-lessons", response_model=schemas.AudioCoursesResponse)
def courses(user: User) -> dict:
    """The courses, by folder name, and their lessons in order, each with the
    progress of the user. A course or a lesson that does not parse is left
    out, and the log has the error."""
    progress = store.audio_progress(user)
    found = []
    folders = sorted(AUDIO_ROOT.iterdir()) if AUDIO_ROOT.is_dir() else []
    for folder in folders:
        if not (folder / script.COURSE_FILE).is_file():
            continue
        try:
            course = script.read_course(folder)
        except script.ScriptError as exc:
            logger.warning("%s", exc)
            continue
        lessons = []
        for number, path in script.lesson_files(folder).items():
            try:
                title = script.read_script(path).title
            except script.ScriptError as exc:
                logger.warning("%s", exc)
                continue
            lessons.append(
                {
                    "number": number,
                    "title": title,
                    "audio": audio_state(folder, number, path),
                    **progress.get((folder.name, number), NOT_STARTED),
                }
            )
        found.append(
            {
                "id": folder.name,
                "name": course.name,
                "language": course.language,
                "lessons": lessons,
            }
        )
    return {"courses": found}


# Before the route of the script, which would read "01.mp3" as a lesson.
@router.get(
    "/audio-lessons/{course}/{lesson}.mp3",
    response_class=FileResponse,
    responses={
        200: {"description": "The sound", "content": {"audio/mpeg": {}}},
        **schemas.NOT_FOUND,
    },
)
def lesson_audio(course: str, lesson: int) -> FileResponse:
    """The mp3 of a lesson. FileResponse answers a Range request, so the
    player can jump."""
    audio = script.audio_path(course_folder(course), lesson)
    if not audio.is_file():
        raise HTTPException(status_code=404, detail=f"lesson {lesson} has no sound")
    return FileResponse(
        audio,
        media_type="audio/mpeg",
        # A new run of the script can change the file: ask with the ETag.
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-cache",
        },
    )


@router.get(
    "/audio-lessons/{course}/{lesson}",
    response_model=schemas.AudioLessonResponse,
    responses=schemas.NOT_FOUND,
)
def lesson_script(course: str, lesson: int) -> dict:
    """The parsed script of a lesson."""
    path = script.lesson_path(course_folder(course), lesson)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"no lesson {lesson}")
    try:
        parsed = script.read_script(path)
    except script.ScriptError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "title": parsed.title,
        "summary": parsed.summary,
        "grammar": parsed.grammar,
        "lines": [
            {"speaker": "pause", "text": "", "seconds": line.seconds}
            if isinstance(line, script.Pause)
            else {"speaker": line.speaker, "text": line.text, "seconds": 0}
            for line in parsed.lines
        ],
    }


@router.put(
    "/audio-lessons/{course}/{lesson}/progress",
    response_model=schemas.AudioProgressResponse,
    responses=schemas.NOT_FOUND,
)
def save_progress(
    course: str, lesson: int, req: AudioProgressRequest, user: User
) -> dict:
    """Save where the user is in a lesson. The lesson is finished the first
    time that the position is within a few seconds of the end, and stays
    finished."""
    folder = course_folder(course)
    if not script.lesson_path(folder, lesson).is_file():
        raise HTTPException(status_code=404, detail=f"no lesson {lesson}")
    return store.save_audio_progress(
        user, folder.name, lesson, req.position, req.duration
    )
