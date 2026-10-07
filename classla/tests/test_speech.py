"""The "Listen" routes with a fake synthesizer, and the OpenAI-shaped
synthesizer with a fake requests."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from tlhelper import app as service
from tlhelper import speech
from tlhelper.speech import openai as backend

MP3 = b"\xff\xfb\x90\x00" + b"\x00" * 100
AUDIO = "/api/v1/speech/audio"


class FakeSynthesizer:
    name = "fake"

    def __init__(self):
        self.url = "http://voice"
        self.served = ["hr", "en"]
        self.calls = []
        self.error = None

    def available(self):
        return bool(self.url)

    def model(self):
        return "fake-voice" if self.url else ""

    def languages(self):
        return self.served

    def synthesize(self, text, language):
        if self.error:
            raise speech.SpeechError(self.error, "voice-timeout")
        self.calls.append((text, language))
        return MP3


@pytest.fixture
def fake(monkeypatch):
    fake = FakeSynthesizer()
    monkeypatch.setitem(speech.SYNTHESIZERS, "fake", fake)
    monkeypatch.setenv("TLHELPER_VOICE_BACKEND", "fake")
    return fake


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("TLHELPER_VOICE_URL", raising=False)
    monkeypatch.delenv("TLHELPER_VOICE_MODEL", raising=False)
    monkeypatch.delenv("TLHELPER_VOICE_BACKEND", raising=False)
    return TestClient(service.app)


# The routes


def test_no_service_by_default(client, monkeypatch):
    monkeypatch.setattr(
        backend.requests, "get", lambda *a, **kw: pytest.fail("called the network")
    )
    assert client.get("/api/v1/speech").json() == {
        "available": False,
        "model": "",
        "languages": [],
    }
    response = client.get(AUDIO, params={"text": "Bok", "language": "hr"})
    assert response.status_code == 503
    assert response.json()["code"] == "voice-no-service"


def test_the_info(client, fake):
    assert client.get("/api/v1/speech").json() == {
        "available": True,
        "model": "fake-voice",
        "languages": ["hr", "en"],
    }
    # A service that does not say: every language of the app.
    fake.served = None
    assert client.get("/api/v1/speech").json()["languages"] == [
        "hr",
        "de",
        "fr",
        "it",
        "en",
    ]
    # A service with an address but no model is no service.
    fake.url = ""
    assert client.get("/api/v1/speech").json()["available"] is False


def test_an_unknown_backend(client, monkeypatch):
    monkeypatch.setenv("TLHELPER_VOICE_BACKEND", "parrot")
    assert client.get("/api/v1/speech").json()["available"] is False
    assert client.get(AUDIO, params={"text": "Bok"}).status_code == 503


def test_speak(client, fake):
    response = client.get(AUDIO, params={"text": "Šećer i čaj.", "language": "hr"})
    assert response.status_code == 200, response.text
    assert response.content == MP3
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.headers["cache-control"] == "private, max-age=86400"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-voice-model"] == "fake-voice"
    response = client.get(AUDIO, params={"text": "Good day.", "language": "en"})
    assert response.status_code == 200
    assert fake.calls == [("Šećer i čaj.", "hr"), ("Good day.", "en")]
    # The mp3 is a GET: a POST is no route.
    response = client.post(AUDIO, json={"text": "Bok", "language": "hr"})
    assert response.status_code == 405


def test_a_language_that_the_service_does_not_read(client, fake):
    response = client.get(AUDIO, params={"text": "Hallo", "language": "de"})
    assert response.status_code == 422
    assert response.json()["code"] == "voice-language"
    assert response.json()["params"] == {"language": "de"}
    # Not a language of the app at all.
    response = client.get(AUDIO, params={"text": "Hola", "language": "es"})
    assert response.status_code == 422
    assert "must be one of hr, de, fr, it, en" in response.text
    assert fake.calls == []


def test_a_failure_of_the_service(client, fake):
    fake.error = "the voice service did not answer in time"
    response = client.get(AUDIO, params={"text": "Bok", "language": "hr"})
    assert response.status_code == 502
    assert response.json() == {
        "detail": "the voice service did not answer in time",
        "code": "voice-timeout",
        "params": {},
    }


def test_the_text_limit(client, fake):
    response = client.get(AUDIO, params={"text": "", "language": "hr"})
    assert response.status_code == 422
    response = client.get(AUDIO, params={"text": "x" * 1001, "language": "hr"})
    assert response.status_code == 422


# The OpenAI-shaped synthesizer


def fake_service(monkeypatch, models=None, status=200, sound=MP3, calls=None):
    """requests.get and requests.post of a service: the calls go to `calls`
    as (method, url, kwargs)."""
    calls = [] if calls is None else calls
    listed = {"object": "list", "data": models or []}

    def get(url, **kwargs):
        calls.append(("get", url, kwargs))
        return SimpleNamespace(status_code=status, json=lambda: listed)

    def post(url, **kwargs):
        calls.append(("post", url, kwargs))
        return SimpleNamespace(status_code=status, content=sound)

    monkeypatch.setattr(backend.requests, "get", get)
    monkeypatch.setattr(backend.requests, "post", post)
    return calls


@pytest.fixture
def openai(monkeypatch):
    """A fresh synthesizer with an address, and a cache with nothing in it."""
    monkeypatch.setenv("TLHELPER_VOICE_URL", "http://voice:8002/")
    monkeypatch.delenv("TLHELPER_VOICE_MODEL", raising=False)
    monkeypatch.delenv("TLHELPER_VOICE_API_KEY", raising=False)
    return backend.OpenAISpeech()


OMNIVOICE = {"id": "k2-fsa/OmniVoice", "object": "model", "languages": ["hr", "en"]}


def test_the_models_and_the_languages(openai, monkeypatch):
    calls = fake_service(monkeypatch, models=[OMNIVOICE])
    assert openai.available()
    assert openai.model() == "k2-fsa/OmniVoice"
    assert openai.languages() == ["hr", "en"]
    # The list stays for a minute: one request.
    assert [each[1] for each in calls] == ["http://voice:8002/v1/models"]
    assert calls[0][2] == {"headers": {}, "timeout": backend.MODELS_TIMEOUT}
    # A named model that the list does not have: the service does not say.
    monkeypatch.setenv("TLHELPER_VOICE_MODEL", "tts-1")
    assert openai.model() == "tts-1"
    assert openai.languages() is None


def test_a_model_with_no_languages(openai, monkeypatch):
    fake_service(monkeypatch, models=[{"id": "tts-1", "object": "model"}])
    assert openai.model() == "tts-1"
    assert openai.languages() is None


def test_a_service_that_does_not_answer(openai, monkeypatch):
    def get(url, **kwargs):
        raise backend.requests.ConnectionError()

    monkeypatch.setattr(backend.requests, "get", get)
    assert openai.available()
    assert openai.models() is None
    assert openai.model() == ""
    assert openai.languages() is None
    # With a named model, the page has the buttons, and a click reports the
    # failure.
    monkeypatch.setenv("TLHELPER_VOICE_MODEL", "k2-fsa/OmniVoice")
    assert openai.model() == "k2-fsa/OmniVoice"
    monkeypatch.setattr(backend.requests, "post", get)
    with pytest.raises(speech.SpeechError, match="not reachable") as failed:
        openai.synthesize("Bok", "hr")
    assert failed.value.code == "voice-no-service"


def test_the_list_stays_for_a_minute(openai, monkeypatch):
    calls = fake_service(monkeypatch, models=[OMNIVOICE])
    now = [1000.0]
    monkeypatch.setattr(backend.time, "monotonic", lambda: now[0])
    openai.models()
    now[0] += 30
    openai.models()
    assert len(calls) == 1
    now[0] += 31
    openai.models()
    assert len(calls) == 2


def test_synthesize(openai, monkeypatch):
    calls = fake_service(monkeypatch, models=[OMNIVOICE])
    monkeypatch.setenv("TLHELPER_VOICE_API_KEY", "secret")
    monkeypatch.setenv("TLHELPER_VOICE_TIMEOUT", "7")
    assert openai.synthesize("Dobar dan.", "hr") == MP3
    method, url, kwargs = calls[-1]
    assert (method, url) == ("post", "http://voice:8002/v1/audio/speech")
    assert kwargs == {
        "headers": {"Authorization": "Bearer secret"},
        "json": {
            "input": "Dobar dan.",
            "language": "hr",
            "response_format": "mp3",
            "model": "k2-fsa/OmniVoice",
        },
        "timeout": 7.0,
    }


def test_synthesize_without_an_address(monkeypatch):
    monkeypatch.delenv("TLHELPER_VOICE_URL", raising=False)
    monkeypatch.setattr(
        backend.requests, "post", lambda *a, **kw: pytest.fail("called the service")
    )
    with pytest.raises(speech.SpeechError, match="TLHELPER_VOICE_URL"):
        backend.OpenAISpeech().synthesize("Bok", "hr")


def test_synthesize_timeout(openai, monkeypatch):
    def post(url, **kwargs):
        raise backend.requests.Timeout()

    fake_service(monkeypatch, models=[OMNIVOICE])
    monkeypatch.setattr(backend.requests, "post", post)
    with pytest.raises(speech.SpeechError, match="in time") as failed:
        openai.synthesize("Bok", "hr")
    assert failed.value.code == "voice-timeout"


@pytest.mark.parametrize("status", [404, 422, 500])
def test_synthesize_http_errors(openai, monkeypatch, status):
    fake_service(monkeypatch, models=[OMNIVOICE])
    monkeypatch.setattr(
        backend.requests,
        "post",
        lambda url, **kw: SimpleNamespace(status_code=status, content=b"{}"),
    )
    with pytest.raises(speech.SpeechError, match=f"HTTP {status}") as failed:
        openai.synthesize("Bok", "hr")
    assert failed.value.code == "voice-http"
    assert failed.value.params == {"status": status}


def test_an_empty_sound(openai, monkeypatch):
    fake_service(monkeypatch, models=[OMNIVOICE], sound=b"")
    with pytest.raises(speech.SpeechError, match="no sound"):
        openai.synthesize("Bok", "hr")


def test_the_environment_selects_the_synthesizer(monkeypatch):
    monkeypatch.delenv("TLHELPER_VOICE_BACKEND", raising=False)
    assert speech.current().name == "openai"
    monkeypatch.setenv("TLHELPER_VOICE_BACKEND", "parrot")
    with pytest.raises(speech.SpeechError, match="'parrot'.*openai"):
        speech.current()
