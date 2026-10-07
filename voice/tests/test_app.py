"""The routes with a fake model, and the mp3 encoder with a real signal."""

import logging
import wave

import numpy as np
import pytest
from fastapi.testclient import TestClient

from omnivoice_server import app as service
from omnivoice_server import native, settings, synth

RATE = 24000
MODEL = settings.DEFAULT_MODEL
# The Cache-Status header (RFC 9211).
HIT = "omnivoice; hit"
MISS = "omnivoice; fwd=miss"


def sine(seconds: float = 0.1) -> np.ndarray:
    steps = np.arange(int(RATE * seconds))
    return (0.5 * np.sin(2 * np.pi * 440 * steps / RATE)).astype(np.float32)


class FakeModel:
    sampling_rate = RATE

    def __init__(self, model_id):
        self.model_id = model_id
        self.calls = []

    def reference(self, samples, text):
        return ("codes", len(samples), text)

    def generate(self, **kwargs):
        # The real model has a fixed list of instruct items.
        if kwargs["instruct"] and "clear" in kwargs["instruct"]:
            raise ValueError("Unsupported instruct items found in clear: 'clear'")
        self.calls.append(kwargs)
        return sine()


@pytest.fixture
def fake(monkeypatch):
    """The synth with a fake loader and no clips, and the server with no
    preload."""
    loaded = {}

    def loader(model_id):
        loaded[model_id] = FakeModel(model_id)
        return loaded[model_id]

    monkeypatch.setenv("OMNIVOICE_PRELOAD", "0")
    monkeypatch.setenv("OMNIVOICE_VOICES", "")
    monkeypatch.delenv("OMNIVOICE_MODELS", raising=False)
    monkeypatch.delenv("OMNIVOICE_LANGUAGES", raising=False)
    monkeypatch.delenv("OMNIVOICE_INSTRUCT", raising=False)
    monkeypatch.setattr(service, "synth", synth.Synth(loader))
    return loaded


def write_clip(path, seconds=0.5, rate=RATE, text="Dobar dan."):
    """A WAV of a sine, and its transcript next to it when text is set."""
    pcm = (sine(seconds) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as clip:
        clip.setnchannels(1)
        clip.setsampwidth(2)
        clip.setframerate(rate)
        clip.writeframes(pcm.tobytes())
    if text:
        path.with_suffix(".txt").write_text(text + "\n")


@pytest.fixture
def voices(fake, monkeypatch, tmp_path):
    """A clip for hr and a default clip."""
    write_clip(tmp_path / "hr.wav", 0.5, text="Dobar dan.")
    write_clip(tmp_path / "default.wav", 0.25, text="Good morning.")
    monkeypatch.setenv("OMNIVOICE_VOICES", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(fake):
    with TestClient(service.app) as client:
        yield client


def is_mp3(data: bytes) -> bool:
    # An mp3 frame starts with 11 bits of sync, or the file has an ID3 tag.
    return data[:3] == b"ID3" or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0)


def test_mp3_of_a_sine():
    data = synth.mp3(sine(0.5), RATE)
    assert is_mp3(data)
    # 64 kbit/s for half a second is about 4 kB.
    assert 3000 < len(data) < 6000


def test_the_models(client, monkeypatch):
    listed = client.get("/v1/models").json()
    assert listed["object"] == "list"
    [model] = listed["data"]
    assert model["id"] == MODEL
    assert model["object"] == "model"
    assert model["owned_by"] == "Serveurperso"
    assert {"hr", "de", "fr", "it", "en"} <= set(model["languages"])
    assert len(model["languages"]) > 600

    monkeypatch.setenv("OMNIVOICE_LANGUAGES", "hr, en")
    monkeypatch.setenv("OMNIVOICE_MODELS", f"{MODEL},someone/OmniVoice-fork")
    listed = client.get("/v1/models").json()
    assert [each["id"] for each in listed["data"]] == [MODEL, "someone/OmniVoice-fork"]
    assert listed["data"][1]["owned_by"] == "someone"
    assert listed["data"][1]["languages"] == ["hr", "en"]


def test_speech(client, fake):
    response = client.post(
        "/v1/audio/speech", json={"input": " Dobar dan. ", "language": "hr"}
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "audio/mpeg"
    assert is_mp3(response.content)
    model = fake[MODEL]
    assert model.calls == [
        {
            "text": "Dobar dan.",
            "language": "hr",
            "instruct": settings.DEFAULT_INSTRUCT,
            "num_step": 16,
            "reference": None,
        }
    ]
    assert client.get("/healthz").json() == {"status": "ok", "loaded": [MODEL]}


def test_the_clip_of_the_language_then_the_default_clip(voices):
    with TestClient(service.app) as client:
        for language, instruct in [("hr", None), ("de", None), ("hr", "male")]:
            body = {"input": "Dobar dan.", "language": language}
            if instruct:
                body["instruct"] = instruct
            response = client.post("/v1/audio/speech", json=body)
            assert response.status_code == 200, response.text
    calls = service.synth.models[MODEL].calls
    assert [(call["instruct"], call["reference"]) for call in calls] == [
        (None, ("codes", RATE // 2, "Dobar dan.")),
        (None, ("codes", RATE // 4, "Good morning.")),
        # An instruct is voice design, with no clip.
        ("male", None),
    ]


def test_no_default_clip_is_the_instruct_of_the_environment(voices):
    (voices / "default.wav").unlink()
    with TestClient(service.app) as client:
        client.post("/v1/audio/speech", json={"input": "Hallo", "language": "de"})
    [call] = service.synth.models[MODEL].calls
    assert call["instruct"] == settings.DEFAULT_INSTRUCT
    assert call["reference"] is None


def test_a_cloned_voice_is_cached(voices):
    with TestClient(service.app) as client:
        headers = [
            client.post(
                "/v1/audio/speech", json={"input": "Dobar dan.", "language": "hr"}
            ).headers["cache-status"]
            for _ in range(2)
        ]
    assert headers == [MISS, HIT]
    assert len(service.synth.models[MODEL].calls) == 1


def lfs_pointer(folder):
    """What a clone without git lfs has in place of the WAV."""
    (folder / "hr.wav").write_text("version https://git-lfs.github.com/spec/v1\n")
    (folder / "hr.txt").write_text("Dobar dan.\n")


@pytest.mark.parametrize(
    "make, error",
    [
        (lambda folder: write_clip(folder / "hr.wav", rate=44100), "44100 Hz"),
        (lambda folder: write_clip(folder / "hr.wav", text=""), "hr.txt"),
        (lfs_pointer, "not a WAV"),
    ],
)
def test_a_bad_clip_stops_the_start(fake, monkeypatch, tmp_path, make, error):
    make(tmp_path)
    monkeypatch.setenv("OMNIVOICE_VOICES", str(tmp_path))
    with pytest.raises(ValueError, match=error), TestClient(service.app):
        pass


def test_the_clips_of_the_repo():
    clips = synth.read_voices(settings.DEFAULT_VOICES)
    assert "hr" in clips
    for samples, text in clips.values():
        # README.md, "Voice": 3 to 10 seconds or so, and it.wav is 17.
        assert 3 <= len(samples) / synth.CLIP_RATE <= 18
        assert text


def test_the_cache_of_the_last_mp3s(client, fake, monkeypatch):
    monkeypatch.setenv("OMNIVOICE_CACHE", "2")

    def speak(text, **more):
        response = client.post(
            "/v1/audio/speech", json={"input": text, "language": "en", **more}
        )
        assert response.status_code == 200, response.text
        return response.headers["cache-status"]

    assert speak("One") == MISS
    assert speak("One") == HIT
    assert speak(" One ") == HIT
    assert speak("One", language="hr") == MISS
    assert speak("One", instruct="male") == MISS
    # The cache holds two, so "One" in English is gone.
    assert speak("One") == MISS
    # A hit keeps its entry when it is the oldest one.
    assert speak("One", instruct="male") == HIT
    assert speak("Two") == MISS
    assert speak("One", instruct="male") == HIT
    # No voice: the model picks one each time, so nothing is cached.
    assert speak("One", instruct="") == MISS
    assert speak("One", instruct="") == MISS
    calls = fake[MODEL].calls
    assert len(calls) == 7


def test_the_instruct_of_the_request_and_of_the_environment(client, fake, monkeypatch):
    client.post(
        "/v1/audio/speech",
        json={"input": "Hello", "language": "en", "instruct": "male, whispering"},
    )
    monkeypatch.setenv("OMNIVOICE_INSTRUCT", "female, fast")
    client.post("/v1/audio/speech", json={"input": "Hello", "language": "en"})
    # An empty instruct is no instruct: the model picks a voice.
    client.post(
        "/v1/audio/speech", json={"input": "Hello", "language": "en", "instruct": ""}
    )
    model = fake[MODEL]
    assert [call["instruct"] for call in model.calls] == [
        "male, whispering",
        "female, fast",
        None,
    ]


def test_an_instruct_that_the_model_refuses(client, fake):
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Hi", "language": "en", "instruct": "clear, female"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "bad-instruct"
    assert "'clear'" in response.json()["detail"]
    assert fake[MODEL].calls == []


def test_an_unknown_language(client, fake, monkeypatch):
    response = client.post("/v1/audio/speech", json={"input": "Hi", "language": "xx"})
    assert response.status_code == 422
    assert response.json()["code"] == "unknown-language"
    monkeypatch.setenv("OMNIVOICE_LANGUAGES", "hr")
    response = client.post("/v1/audio/speech", json={"input": "Hi", "language": "en"})
    assert response.status_code == 422
    assert response.json()["code"] == "unknown-language"
    assert fake == {}


def test_an_unknown_model(client, fake):
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Hi", "language": "en", "model": "someone/else"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "unknown-model"
    assert fake == {}


def test_an_empty_text(client, fake):
    response = client.post("/v1/audio/speech", json={"input": "   ", "language": "en"})
    assert response.status_code == 422
    assert response.json()["code"] == "empty-text"
    response = client.post("/v1/audio/speech", json={"input": "", "language": "en"})
    assert response.status_code == 422
    assert fake == {}


def test_a_language_that_the_model_does_not_know_stops_the_start(fake, monkeypatch):
    monkeypatch.setenv("OMNIVOICE_LANGUAGES", "hr,klingon")
    with pytest.raises(RuntimeError, match="klingon"), TestClient(service.app):
        pass


def test_the_preload(fake, monkeypatch):
    monkeypatch.setenv("OMNIVOICE_PRELOAD", "1")
    with TestClient(service.app) as client:
        # The thread holds the lock until the model is there, so a request
        # waits for it.
        response = client.post(
            "/v1/audio/speech", json={"input": "Hi", "language": "en"}
        )
        assert response.status_code == 200
        assert client.get("/healthz").json()["loaded"] == [MODEL]
    assert list(fake) == [MODEL]


def test_no_access_line_for_healthz(client):
    access = logging.getLogger("uvicorn.access")
    assert any(isinstance(each, service.NoHealthLines) for each in access.filters)

    def line(path):
        # The record of uvicorn: the format and the args of its access line.
        return logging.LogRecord(
            "uvicorn.access",
            logging.INFO,
            "",
            0,
            '%s - "%s %s HTTP/%s" %d',
            ("127.0.0.1:1", "GET", path, "1.1", 200),
            None,
        )

    assert not access.filter(line("/healthz"))
    assert access.filter(line("/v1/models"))
    assert access.filter(line("/healthz2"))


def test_the_language_list_needs_no_library(monkeypatch):
    monkeypatch.setenv("OMNIVOICE_LIB", "/nowhere/libomnivoice.so")
    known = settings.known_languages()
    assert {"hr", "de", "fr", "it", "en", "zh", "fa"} <= known
    assert len(known) > 600


def test_a_missing_library_names_the_variable(monkeypatch):
    monkeypatch.setenv("OMNIVOICE_LIB", "/nowhere/libomnivoice.so")
    monkeypatch.setattr(native, "_library", None)
    with pytest.raises(RuntimeError, match="OMNIVOICE_LIB.*README"):
        native.Model("base.gguf", "codec.gguf")
    with pytest.raises(RuntimeError, match="/nowhere/libomnivoice.so"):
        native.library()
