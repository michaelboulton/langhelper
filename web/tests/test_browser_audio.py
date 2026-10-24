"""The Audio lessons tab of the Flutter app in a real browser. The browser
fixtures are in conftest.py."""

import os
import re

import pytest
from playwright.sync_api import expect
from tlhelper.audio_lessons import routes

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
    (course / "02.txt").write_text(LESSON.replace("meat", "fish"), encoding="utf-8")
    monkeypatch.setattr(routes, "AUDIO_ROOT", tmp_path / "audio")
    return course


def open_tab(new_page, width):
    page = new_page(width=width, height=1000)
    page.goto("/#/audio")
    page.get_by_role("heading", name="Italian").wait_for()
    return page


def player_button(page, name):
    return page.get_by_role("button", name=name, exact=True)


@pytest.mark.parametrize("width", [390, 1280])
def test_the_courses_and_a_lesson(new_page, note, screenshot, width):
    page = open_tab(new_page, width)
    expect(page.get_by_role("tab", name="Audio lessons")).to_be_visible()
    page.get_by_role("button", name="Is there fish in this dish?").wait_for()
    screenshot(page, f"audio-courses-{width}")

    with page.expect_response(re.compile(r"/audio-lessons/it-course/1\.mp3$")):
        page.get_by_role("button", name="Is there meat in this dish?").click()
    assert page.url.endswith("/#/audio/it-course/1")
    page.get_by_role("heading", name="Is there meat in this dish?").wait_for()
    # The lines of the script in order, each with its speaker. The script is
    # HTML, so the browser finds a text in it, as with Ctrl+F.
    lines = [r"Narrator:\s+How do you say", r"\(pause, 3 s\)", r"You:\s+c'è", "Other"]
    script = page.locator(".lesson-script p")
    tops = [script.filter(has_text=re.compile("^" + each)) for each in lines]
    for each in tops:
        each.wait_for()
    boxes = [each.bounding_box()["y"] for each in tops]
    assert boxes == sorted(boxes)
    assert page.evaluate("text => window.find(text)", "non c'è carne")
    expect(script.last.locator("span")).to_have_attribute("lang", "it")
    # Space plays, also after a click in the script.
    tops[0].click()
    page.keyboard.press("Space")
    player_button(page, "Pause").wait_for()
    page.keyboard.press("Space")
    player_button(page, "Play").wait_for()
    # Each button of the player has its name, also while its tooltip shows.
    for name in ("Back 10 s", "Play", "Forward 10 s"):
        player_button(page, name).hover()
        expect(player_button(page, name)).to_be_visible()
    player_button(page, "Play").click()
    player_button(page, "Pause").wait_for()
    page.get_by_role("button", name="1.25×").click()
    player_button(page, "Back 10 s").click()
    page.mouse.move(0, 0)
    screenshot(page, f"audio-lesson-{width}")

    page.get_by_role("button", name="All lessons").click()
    page.get_by_role("button", name="Is there fish in this dish?").click()
    note(page, "This lesson has no sound yet.").wait_for()
    expect(player_button(page, "Play")).to_have_count(0)


def test_a_lesson_with_an_old_sound(new_page, audio_root, note):
    # The mp3 is older than its script.
    stale = LESSON.replace("meat", "milk")
    (audio_root / "03.txt").write_text(stale, encoding="utf-8")
    (audio_root / "03.mp3").write_bytes(SILENT_MP3)
    os.utime(audio_root / "03.mp3", ns=(1, 1))
    page = open_tab(new_page, 1280)
    page.get_by_role("button", name="Is there milk in this dish?").click()
    note(page, re.compile("^The script changed after the sound was made")).wait_for()
    expect(player_button(page, "Play")).to_be_visible()


def test_the_browser_scrolls_a_long_script(new_page, audio_root):
    long = LESSON.replace("meat", "rice") + "actor 1: c'è\n" * 200
    (audio_root / "03.txt").write_text(long, encoding="utf-8")
    page = open_tab(new_page, 1280)
    page.get_by_role("button", name="Is there rice in this dish?").click()
    script = page.locator(".lesson-script")
    script.locator("p").first.hover()
    page.mouse.wheel(0, 1000)
    # The wheel scrolls the HTML of the script, not Flutter.
    page.wait_for_function(
        "() => document.querySelector('.lesson-script').scrollTop > 0"
    )
    assert script.evaluate("element => element.scrollHeight > element.clientHeight")


def is_save(request):
    return request.method == "PUT" and request.url.endswith("/it-course/1/progress")


@pytest.mark.parametrize("width", [390, 1280])
def test_the_progress_of_the_lessons(
    browser, server, new_page, note, screenshot, width
):
    # Lesson 1 at 12 s of 30 s, and lesson 2 finished.
    request = browser.new_context(base_url=server).request
    for lesson, position in ((1, 12.0), (2, 30.0)):
        response = request.put(
            f"/api/v1/audio-lessons/it-course/{lesson}/progress",
            data={"position": position, "duration": 30.0},
        )
        assert response.ok
    request.dispose()

    page = open_tab(new_page, width)
    note(page, "40%").wait_for()
    note(page, "Finished").wait_for()
    screenshot(page, f"audio-progress-{width}")

    # Continue opens the first lesson that is not finished.
    with page.expect_response(re.compile(r"/audio-lessons/it-course/1\.mp3$")):
        page.get_by_role("button", name="Continue").click()
    assert page.url.endswith("/#/audio/it-course/1")
    player_button(page, "Play").click()
    page.wait_for_timeout(1500)
    with page.expect_request(is_save) as saved:
        player_button(page, "Pause").click()
    # The player started at the saved position.
    body = saved.value.post_data_json
    assert 12 < body["position"] < 20
