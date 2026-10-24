"""The Audio lessons tab of the Flutter build in app/, in Chromium. It skips
unless STATIC_DIR is that build (README.md, "The Flutter app"):

STATIC_DIR=app/build/web uv run pytest tests/test_browser_audio_app.py
"""

import re
from pathlib import Path

import pytest
from playwright.sync_api import expect
from tlhelper import app as service
from tlhelper.audio_lessons import routes

pytestmark = pytest.mark.skipif(
    not (service.STATIC_DIR / "flutter_bootstrap.js").is_file(),
    reason="STATIC_DIR is not a Flutter build",
)

LESSON = """\
# Is there meat in this dish?
summary: Asking a waiter whether a dish has meat in it.
grammar: "there is / there isn't" (c'è, non c'è).

narrator: How do you say "is there"?
pause: 3
actor 1: c'è
actor 2: No, non c'è carne.
"""
# A silent MPEG-1 layer III frame of 26 ms, for 30 s: the browser plays it
# with no error, and the seek bar has a length.
SILENT_MP3 = (b"\xff\xfb\x90\x00" + b"\x00" * 413) * 1150


@pytest.fixture(autouse=True)
def audio_root(tmp_path, monkeypatch):
    """The course it-course: lesson 1 with its mp3, lesson 2 with no mp3."""
    course = tmp_path / "audio" / "it-course"
    course.mkdir(parents=True)
    (course / "course.toml").write_text(
        'language = "it"\nname = "Italian"\n', encoding="utf-8"
    )
    (course / "01.txt").write_text(LESSON, encoding="utf-8")
    (course / "01.mp3").write_bytes(SILENT_MP3)
    (course / "02.txt").write_text(
        LESSON.replace("meat", "fish"), encoding="utf-8"
    )
    monkeypatch.setattr(routes, "AUDIO_ROOT", tmp_path / "audio")


def open_tab(browser, server, width):
    # Tall, so that --screenshots shows the whole tab.
    context = browser.new_context(
        base_url=server, viewport={"width": width, "height": 1000}
    )
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto("/#/audio")
    page.get_by_role("heading", name="Italian").wait_for()
    return context, page, errors


def note(page, text):
    """A text of the semantics tree: a node of its own, or the aria-label of
    the group that Flutter merges it into."""
    return (
        page.get_by_label(text)
        .or_(page.locator("flt-semantics").get_by_text(text))
        .first
    )


def screenshot(request, page, name):
    if folder := request.config.getoption("--screenshots"):
        # The canvas paints a moment after the semantics tree changes.
        page.wait_for_timeout(1000)
        page.screenshot(path=Path(folder) / f"{name}.png")


@pytest.mark.parametrize("width", [390, 1280])
def test_the_courses_and_a_lesson(browser, server, request, width):
    context, page, errors = open_tab(browser, server, width)
    expect(page.get_by_role("tab", name="Audio lessons")).to_be_visible()
    page.get_by_role("button", name="Is there fish in this dish?").wait_for()
    screenshot(request, page, f"audio-courses-{width}")

    with page.expect_response(re.compile(r"/audio-lessons/it-course/1\.mp3$")):
        page.get_by_role("button", name="Is there meat in this dish?").click()
    assert page.url.endswith("/#/audio/it-course/1")
    page.get_by_role("heading", name="Is there meat in this dish?").wait_for()
    # The lines of the script in order, each with its speaker.
    lines = [r"Narrator:\s+How do you say", r"\(pause, 3 s\)", r"You:\s+c'è", "Other"]
    tops = [note(page, re.compile("^" + each)) for each in lines]
    for each in tops:
        each.wait_for()
    boxes = [each.bounding_box()["y"] for each in tops]
    assert boxes == sorted(boxes)
    # The tooltip of a hovered button adds its text to the label.
    page.mouse.move(0, 0)
    for name in ("Back 10 s", "Play", "Forward 10 s"):
        expect(page.get_by_role("button", name=name, exact=True)).to_be_visible()
    page.get_by_role("button", name="Play", exact=True).click()
    page.get_by_role("button", name="1.25×").click()
    page.get_by_role("button", name="Back 10 s").click()
    page.mouse.move(0, 0)
    screenshot(request, page, f"audio-lesson-{width}")

    page.get_by_role("button", name="All lessons").click()
    page.get_by_role("button", name="Is there fish in this dish?").click()
    note(page, "This lesson has no sound yet.").wait_for()
    expect(page.get_by_role("button", name="Play", exact=True)).to_have_count(0)
    assert errors == []
    context.close()
