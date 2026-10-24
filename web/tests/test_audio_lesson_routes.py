"""tlhelper/audio_lessons/routes.py. test_browser_audio.py has the tab in a
real browser."""

import os

import pytest
from fastapi.testclient import TestClient
from tlhelper import app as service
from tlhelper.audio_lessons import routes
from tlhelper.flashcards import store
from tlhelper.flashcards.routes import current_user

LESSON = """\
# Is there meat in this dish?
summary: Asking a waiter whether a dish has meat in it.
grammar: "there is / there isn't" (c'è, non c'è).

narrator: How do you say "is there"?
pause: 3
actor 1: c'è
actor 2: No, non c'è carne.
"""
COURSE = 'language = "it"\nname = "Italian"\n'
# A silent MPEG-1 layer III frame, a few times: the browser plays it.
SILENT_MP3 = (b"\xff\xfb\x90\x00" + b"\x00" * 413) * 8


@pytest.fixture
def audio_root(tmp_path, monkeypatch):
    """DATA_ROOT/audio/ with the course it-course: lesson 1 with its mp3,
    lesson 2 with an mp3 older than its script, lesson 3 with no mp3, and
    lesson 4 that does not parse."""
    root = tmp_path / "audio"
    course = root / "it-course"
    course.mkdir(parents=True)
    (course / "course.toml").write_text(COURSE, encoding="utf-8")
    for number in (1, 2, 3):
        (course / f"0{number}.txt").write_text(LESSON, encoding="utf-8")
    (course / "04.txt").write_text("no title\n", encoding="utf-8")
    for number in (1, 2):
        (course / f"0{number}.mp3").write_bytes(SILENT_MP3)
    os.utime(course / "01.txt", ns=(1, 1))
    os.utime(course / "02.mp3", ns=(1, 1))
    # Not courses: a folder with no course.toml, and a bad course.toml.
    (root / "empty").mkdir()
    (root / "bad").mkdir()
    (root / "bad" / "course.toml").write_text('language = "xx"\n', encoding="utf-8")
    monkeypatch.setattr(routes, "AUDIO_ROOT", root)
    return root


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client, with an empty flashcards.db for the progress."""
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "flashcards.db")
    return TestClient(service.app)


@pytest.fixture
def as_user():
    """as_user("user-2") makes the requests after it those of user-2."""

    def switch(user):
        service.app.dependency_overrides[current_user] = lambda: user

    yield switch
    service.app.dependency_overrides.pop(current_user, None)


def lessons_of(client):
    [course] = client.get("/api/v1/audio-lessons").json()["courses"]
    return {lesson["number"]: lesson for lesson in course["lessons"]}


def put_progress(client, path, position, duration=120.0):
    return client.put(
        f"/api/v1/audio-lessons/{path}/progress",
        json={"position": position, "duration": duration},
    )


def test_the_courses(audio_root, client):
    assert client.get("/api/v1/audio-lessons").json() == {
        "courses": [
            {
                "id": "it-course",
                "name": "Italian",
                "language": "it",
                "lessons": [
                    {
                        "number": number,
                        "title": "Is there meat in this dish?",
                        "audio": audio,
                        "position": 0.0,
                        "duration": 0.0,
                        "finished": False,
                    }
                    for number, audio in ((1, "ready"), (2, "stale"), (3, "none"))
                ],
            }
        ]
    }


def test_no_audio_folder(tmp_path, monkeypatch, client):
    monkeypatch.setattr(routes, "AUDIO_ROOT", tmp_path / "audio")
    assert client.get("/api/v1/audio-lessons").json() == {"courses": []}


def test_the_script_of_a_lesson(audio_root, client):
    lesson = client.get("/api/v1/audio-lessons/it-course/1").json()
    assert lesson["title"] == "Is there meat in this dish?"
    assert lesson["grammar"] == "\"there is / there isn't\" (c'è, non c'è)."
    assert lesson["lines"] == [
        {"speaker": "narrator", "text": 'How do you say "is there"?', "seconds": 0},
        {"speaker": "pause", "text": "", "seconds": 3},
        {"speaker": "actor 1", "text": "c'è", "seconds": 0},
        {"speaker": "actor 2", "text": "No, non c'è carne.", "seconds": 0},
    ]
    assert client.get("/api/v1/audio-lessons/it-course/01").json() == lesson
    for path in ("it-course/9", "it-course/4", "nothing/1", "empty/1"):
        assert client.get(f"/api/v1/audio-lessons/{path}").status_code == 404, path


def test_the_mp3_of_a_lesson(audio_root, client):
    response = client.get("/api/v1/audio-lessons/it-course/1.mp3")
    assert response.status_code == 200
    assert response.content == SILENT_MP3
    assert response.headers["content-type"] == "audio/mpeg"
    part = client.get(
        "/api/v1/audio-lessons/it-course/1.mp3", headers={"range": "bytes=0-3"}
    )
    assert (part.status_code, part.content) == (206, SILENT_MP3[:4])
    assert client.get("/api/v1/audio-lessons/it-course/3.mp3").status_code == 404


def test_no_path_out_of_the_audio_folder(audio_root, client):
    # A course.toml and an mp3 next to audio/, where ".." leads.
    (audio_root.parent / "course.toml").write_text(COURSE, encoding="utf-8")
    (audio_root.parent / "01.mp3").write_bytes(b"secret")
    (audio_root.parent / "01.txt").write_text(LESSON, encoding="utf-8")
    for course in ("%2E%2E", "..%2F..", "%2E%2E%2F%2E%2E", "."):
        for path in (f"{course}/1.mp3", f"{course}/1"):
            response = client.get(f"/api/v1/audio-lessons/{path}")
            assert response.status_code == 404, path
            assert b"secret" not in response.content
    for course in ("..", "../audio/..", "/", "."):
        with pytest.raises(routes.HTTPException):
            routes.course_folder(course)


def test_save_and_read_the_progress(audio_root, client):
    response = put_progress(client, "it-course/1", 30.5)
    assert response.status_code == 200
    assert response.json() == {"position": 30.5, "duration": 120.0, "finished": False}
    lessons = lessons_of(client)
    assert lessons[1] | {"title": ""} == {
        "number": 1,
        "title": "",
        "audio": "ready",
        "position": 30.5,
        "duration": 120.0,
        "finished": False,
    }
    assert (lessons[2]["position"], lessons[2]["duration"]) == (0, 0)
    # A later save replaces the position, and "01" is lesson 1.
    put_progress(client, "it-course/01", 42)
    assert lessons_of(client)[1]["position"] == 42


def test_a_finished_lesson_stays_finished(audio_root, client):
    within = 120 - store.FINISHED_WITHIN
    assert not put_progress(client, "it-course/1", within - 1).json()["finished"]
    assert put_progress(client, "it-course/1", within).json()["finished"]
    # The user listens again from the start.
    again = put_progress(client, "it-course/1", 3).json()
    assert again == {"position": 3, "duration": 120, "finished": True}
    assert lessons_of(client)[1]["finished"]
    # A position after the end is the end.
    assert put_progress(client, "it-course/2", 500).json() == {
        "position": 120,
        "duration": 120,
        "finished": True,
    }


def test_the_progress_of_two_users(audio_root, client, as_user):
    as_user("user-1")
    put_progress(client, "it-course/1", 10)
    as_user("user-2")
    assert lessons_of(client)[1]["position"] == 0
    put_progress(client, "it-course/1", 20)
    assert lessons_of(client)[1]["position"] == 20
    as_user("user-1")
    assert lessons_of(client)[1]["position"] == 10


def test_bad_progress(audio_root, client):
    for path in ("nothing/1", "empty/1", "%2E%2E/1", ".../1", "it-course/9"):
        assert put_progress(client, path, 1).status_code == 404, path
    assert put_progress(client, "it-course/x", 1).status_code == 422
    for position, duration in ((-1, 120), (1, 0)):
        response = put_progress(client, "it-course/1", position, duration)
        assert response.status_code == 422, (position, duration)
    assert store.audio_progress("local") == {}
