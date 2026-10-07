"""The breakdown tab in a real browser, with the real light models and a fake
translator. The browser fixtures are in conftest.py."""

import re

import pytest
from playwright.sync_api import expect

from tlhelper import speech, translators


class FakeTranslator:
    name = "fake"

    def translate(self, text, source, target):
        return {
            "I am going to the islands.": "Idem na otoke.",
            "Idem na otoke.": "I am going to the islands.",
        }[text]


# A silent MPEG-1 layer III frame (128 kbit/s, 44.1 kHz, 417 bytes), a few
# times: the browser plays it with no error.
SILENT_MP3 = (b"\xff\xfb\x90\x00" + b"\x00" * 413) * 8


class FakeSynthesizer:
    name = "fake"

    def __init__(self):
        self.calls = []

    def available(self):
        return True

    def model(self):
        return "fake-voice"

    def languages(self):
        return ["hr", "en"]

    def synthesize(self, text, language):
        self.calls.append((text, language))
        return SILENT_MP3


@pytest.fixture(autouse=True)
def translator(monkeypatch):
    monkeypatch.setitem(translators.TRANSLATORS, "fake", FakeTranslator())
    monkeypatch.setenv("TRANSLATOR", "fake")


def breakdown(page, text, source="study"):
    """Enter a text and wait for the breakdown. The light models take a moment
    on the first text."""
    page.goto("/")
    page.locator(f"input[name=source][value={source}]").check()
    page.locator("#text").fill(text)
    page.locator("#go").click()
    expect(page.locator("#status")).to_contain_text("light", timeout=60_000)


def line(page, number):
    """Each word of a line of the breakdown, with its tag and its note."""
    chips = page.locator("#result .sentence").nth(number).locator(".chip")
    words = chips.locator(".w").all_inner_texts()
    tags = chips.locator(".p").all_inner_texts()
    return list(zip(words, tags, strict=True))


def test_a_croatian_sentence(page):
    breakdown(page, "Idem na otoke.")
    expect(page.locator("#heavy")).not_to_be_checked()
    assert line(page, 0) == [
        ("Idem", "VERB (F/1/S)"),
        ("na", "ADP"),
        ("otoke", "NOUN (A/M/P)"),
        (".", "PUNCT"),
    ]
    otoke = page.locator("#result .chip").nth(2)
    expect(otoke.locator(".p")).to_have_attribute(
        "title", "Case: accusative, Gender: masculine, Number: plural"
    )
    otoke.click()
    expect(page.locator("#detail h2")).to_have_text("otoke")
    expect(page.locator("#detail")).to_contain_text("otok")


def test_a_croatian_determiner_and_pronoun(page):
    breakdown(page, "Vidim moju kuću. Vidim nju.")
    assert line(page, 0)[1] == ("moju", "DET (A/F/S)")
    assert line(page, 1)[1] == ("nju", "PRON (A/F/S)")


def test_an_english_sentence(page):
    breakdown(page, "I am going to the islands.", source="en")
    # The English text is on top, and the Croatian translation is under it.
    assert line(page, 0) == [
        ("I", "PRON (N/–/S)"),
        ("am", "AUX (F/1/S)"),
        ("going", "VERB (P/–/–)"),
        ("to", "ADP"),
        ("the", "DET"),
        ("islands", "NOUN (–/–/P)"),
        (".", "PUNCT"),
    ]
    assert line(page, 1) == [
        ("Idem", "VERB (F/1/S)"),
        ("na", "ADP"),
        ("otoke", "NOUN (A/M/P)"),
        (".", "PUNCT"),
    ]
    expect(page.locator("#result .note")).to_have_text("Croatian: Idem na otoke.")
    expect(page.locator("#result svg.links path").first).to_be_attached()


def test_no_listen_buttons_without_a_voice_service(page):
    breakdown(page, "Idem na otoke.")
    expect(page.locator("#result .chip").first).to_be_attached()
    expect(page.locator("#listen")).to_be_hidden()


def test_the_listen_buttons(page, monkeypatch):
    fake = FakeSynthesizer()
    monkeypatch.setitem(speech.SYNTHESIZERS, "fake", fake)
    monkeypatch.setenv("TLHELPER_VOICE_BACKEND", "fake")
    page.goto("/")
    page.locator("#translate").check()
    page.locator("#text").fill("Idem na otoke.")
    page.locator("#go").click()
    expect(page.locator("#status")).to_contain_text("light", timeout=60_000)
    buttons = page.locator("#listen button")
    expect(buttons).to_have_text(["Croatian", "English"])
    expect(page.locator("#listen audio")).to_be_hidden()
    buttons.first.click()
    expect(page.locator("#listen audio")).to_have_attribute(
        "src", re.compile(r"^blob:")
    )
    expect(page.locator("#listen audio")).to_be_visible()
    expect(page.locator("#listen p")).to_have_text("fake-voice read this.")
    buttons.nth(1).click()
    expect(page.locator("#listen p")).to_have_text("fake-voice read this.")
    assert fake.calls == [
        ("Idem na otoke.", "hr"),
        ("I am going to the islands.", "en"),
    ]


def test_large_models_by_default(page, monkeypatch):
    monkeypatch.setenv("TLHELPER_ALWAYS_LARGE", "1")
    page.goto("/")
    expect(page.locator("#heavy")).to_be_checked()
    expect(page.locator("#cards-heavy")).to_be_checked()
    # The choice of the user wins over the default of the server.
    page.locator("#heavy").uncheck()
    page.reload()
    expect(page.locator("#language option").first).to_be_attached()
    expect(page.locator("#heavy")).not_to_be_checked()
    expect(page.locator("#cards-heavy")).not_to_be_checked()
