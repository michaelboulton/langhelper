"""check_voices with the OpenAI-shaped synthesizer of the app and a fake
requests."""

from types import SimpleNamespace

import pytest
from tlhelper.speech import openai as backend

from scripts import check_voices

MP3 = b"\xff\xfb\x90\x00" + b"\x00" * 100
OMNIVOICE = {"id": "k2-fsa/OmniVoice", "object": "model", "languages": ["hr", "en"]}


def fake_service(monkeypatch, models=None, sound=MP3):
    """requests.get and requests.post of a service: the calls go to the list
    it returns, as (method, url, kwargs)."""
    calls = []
    listed = {"object": "list", "data": models or []}

    def get(url, **kwargs):
        calls.append(("get", url, kwargs))
        return SimpleNamespace(status_code=200, json=lambda: listed)

    def post(url, **kwargs):
        calls.append(("post", url, kwargs))
        return SimpleNamespace(status_code=200, content=sound)

    monkeypatch.setattr(backend.requests, "get", get)
    monkeypatch.setattr(backend.requests, "post", post)
    return calls


@pytest.fixture(autouse=True)
def address(monkeypatch):
    monkeypatch.setenv("TLHELPER_VOICE_URL", "http://voice:8002/")
    monkeypatch.delenv("TLHELPER_VOICE_MODEL", raising=False)
    monkeypatch.delenv("TLHELPER_VOICE_API_KEY", raising=False)
    monkeypatch.delenv("TLHELPER_VOICE_BACKEND", raising=False)


def test_check_voices(monkeypatch, tmp_path, capsys):
    calls = fake_service(monkeypatch, models=[{**OMNIVOICE, "voices": ["it", "it-2"]}])
    out = tmp_path / "out"
    check_voices.main(
        ["--language", "it", "--voice", "it", "--voice", "it-2", "--out", str(out)],
        standalone_mode=False,
    )
    assert (out / "it-it.mp3").read_bytes() == MP3
    assert (out / "it-it-2.mp3").read_bytes() == MP3
    posts = [kwargs["json"] for method, _, kwargs in calls if method == "post"]
    assert [(post["input"], post["voice"]) for post in posts] == [
        (check_voices.SAMPLES["it"], "it"),
        (check_voices.SAMPLES["it"], "it-2"),
    ]
    assert "it-it-2.mp3" in capsys.readouterr().out


@pytest.mark.parametrize(
    "models, args, error",
    [
        (
            [{**OMNIVOICE, "voices": ["it"]}],
            ["--voice", "it-2"],
            "no voice it-2, only: it",
        ),
        ([OMNIVOICE], ["--voice", "it"], "no voice it, only: none"),
        ([], ["--voice", "it"], "no model list"),
    ],
)
def test_check_voices_stops_before_a_request(monkeypatch, tmp_path, models, args, error):
    calls = fake_service(monkeypatch, models=models)
    with pytest.raises(SystemExit, match=error):
        check_voices.main(["--language", "it", "--out", str(tmp_path), *args])
    assert [method for method, _, _ in calls] == ["get"]


def test_check_voices_without_an_address(monkeypatch):
    monkeypatch.delenv("TLHELPER_VOICE_URL", raising=False)
    with pytest.raises(SystemExit, match="TLHELPER_VOICE_URL"):
        check_voices.main(["--language", "it", "--voice", "it"])
