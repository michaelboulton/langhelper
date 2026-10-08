"""Tests for app.py and for the classla pipeline of languages/croatian. Run
with: uv run pytest

The unit tests replace the classla pipeline with a fake, so they need no
models. test_real_models loads the real ones and is skipped when they are not
in .data/ at the repository root (start the app once with DATA_ROOT=../.data to
download them).
"""

import re
import resource
import sqlite3
import time
from importlib.util import find_spec
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from tlhelper import app as service
from tlhelper import translators
from tlhelper.languages import ENGLISH, LANGUAGES
from tlhelper.languages.base import STUDY
from tlhelper.languages.croatian import accents, heavy, light
from tlhelper.translators import deepl

CROATIAN, GERMAN = LANGUAGES["hr"], LANGUAGES["de"]

REAL_MODELS = Path(__file__).parents[2] / ".data" / "classla_resources"


def word(id, text, lemma, upos, xpos, feats, start):
    token = SimpleNamespace(start_char=start, end_char=start + len(text))
    return SimpleNamespace(
        id=id, text=text, lemma=lemma, upos=upos, xpos=xpos, feats=feats, parent=token
    )


def fake_doc(text):
    words = [
        word(1, "Ona", "on", "PRON", "Pp3fsn", "Case=Nom|Gender=Fem", 0),
        word(2, "je", "biti", "AUX", "Var3s", "Mood=Ind", 4),
        word(3, "bila", "biti", "AUX", "Vap-sf", "Tense=Past", 7),
        word(4, "Zagreb", "Zagreb", "PROPN", "Npmsn", None, 12),
        word(5, ".", ".", "PUNCT", "Z", "_", 18),
    ]
    return SimpleNamespace(sentences=[SimpleNamespace(text=text, words=words)])


@pytest.fixture
def client(tmp_path, monkeypatch):
    requested = []

    def get_pipeline(model_type):
        requested.append(model_type)
        return fake_doc

    monkeypatch.setattr(service, "DB_PATH", tmp_path / "lemmas.db")
    monkeypatch.setattr(heavy, "get_pipeline", get_pipeline)
    # The slot can hold the fake pipeline of the test before this one.
    STUDY.drop()
    # The tests of translate() itself set a key and a fake requests.post.
    monkeypatch.setattr(deepl, "API_KEY", "")
    monkeypatch.delenv("TRANSLATOR", raising=False)
    # test_croatian_accents.py covers the lookup. Here only the wiring matters.
    monkeypatch.setattr(
        accents,
        "accent_for",
        lambda text, lemma, upos, feats: {
            "form": f"{text}|{lemma}|{upos}|{feats}",
            "exact": True,
        },
    )
    # No `with`: the lifespan (and so the model warm-up) does not run.
    client = TestClient(service.app)
    client.requested = requested
    return client


def classify(client, **body):
    """With the heavy models, because those are the fake ones. The tests of
    the light models say heavy=False."""
    body.setdefault("text", "Ona je bila Zagreb.")
    body.setdefault("heavy", True)
    response = client.post("/api/v1/classify", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def seen(result):
    return [w["seen"] for w in result["sentences"][0]["words"]]


def test_parse_feats():
    assert heavy.parse_feats("Case=Nom|Gender=Fem") == {
        "Case": "Nom",
        "Gender": "Fem",
    }
    assert heavy.parse_feats(None) == {}
    assert heavy.parse_feats("_") == {}


def test_lemma_key_keeps_case_only_for_proper_nouns():
    assert service.lemma_key("Zagreb", "PROPN") == "Zagreb"
    assert service.lemma_key("Kuća", "NOUN") == "kuća"
    # One key for the half-width and the full-width form.
    assert service.lemma_key("ｶﾒﾗ", "NOUN") == service.lemma_key("カメラ", "NOUN")


def test_healthz_and_index(client):
    assert client.get("/healthz").text == "ok"
    page = client.get("/")
    assert page.status_code == 200
    # The page loads its script, its style sheet, and its manifest and icon
    # for the install on Android from /static.
    for path, content in [
        ("/static/js/breakdown.js", "/api/v1/classify"),
        ("/static/css/breakdown.css", ".chip"),
        ("/static/manifest.json", '"src": "/static/icon.svg"'),
        ("/static/icon.svg", "<svg"),
    ]:
        assert path in page.text
        file = client.get(path)
        assert file.status_code == 200
        assert content in file.text
    manifest = client.get("/static/manifest.json").json()
    for icon in manifest["icons"]:
        file = client.get(icon["src"])
        assert file.headers["content-type"] == icon["type"]
        if icon["type"] == "image/png":
            assert file.content.startswith(b"\x89PNG")
            assert icon["sizes"] in ("192x192", "512x512")
    purposes = [(icon["type"], icon["purpose"]) for icon in manifest["icons"]]
    assert ("image/png", "maskable") in purposes


def test_classify_shape(client):
    result = classify(client)
    assert (result["type"], result["language"]) == ("heavy", "hr")
    assert (result["source"], result["text"]) == ("study", "Ona je bila Zagreb.")
    sentence = result["sentences"][0]
    assert sentence["text"] == "Ona je bila Zagreb."
    assert sentence["words"][0] == {
        "id": 1,
        "text": "Ona",
        "lemma": "on",
        "upos": "PRON",
        "xpos": "Pp3fsn",
        "feats": {"Case": "Nom", "Gender": "Fem"},
        "accent": {
            "form": "Ona|on|PRON|{'Case': 'Nom', 'Gender': 'Fem'}",
            "exact": True,
        },
        "start_char": 0,
        "end_char": 3,
        "problems": [],
        "seen": 1,
    }


def test_counts_go_up_and_punctuation_is_not_counted(client):
    # "biti" occurs twice in the text, so one request counts it twice.
    assert seen(classify(client)) == [1, 2, 2, 1, None]
    assert seen(classify(client)) == [2, 4, 4, 2, None]


def test_track_false_reads_but_does_not_count(client):
    assert seen(classify(client, track=False)) == [0, 0, 0, 0, None]
    classify(client)
    assert seen(classify(client, track=False)) == [1, 2, 2, 1, None]


def test_nonstandard_selects_the_other_models(client):
    # nonstandard is heavy with or without the heavy field.
    assert classify(client, nonstandard=True, heavy=False)["type"] == "nonstandard"
    classify(client)
    # The same models again: no second load.
    classify(client)
    assert client.requested == ["nonstandard", "standard"]


def test_the_default_is_the_light_model(client):
    """The real hr_core_news_md model."""
    result = classify(client, text="Ona je bila kod kuće.", heavy=False)
    assert result["type"] == "light"
    assert client.requested == []
    words = result["sentences"][0]["words"]
    assert [(w["lemma"], w["upos"]) for w in words][3:5] == [
        ("kod", "ADP"),
        ("kuća", "NOUN"),
    ]
    assert words[4]["xpos"] == "Ncfsg"
    assert words[4]["accent"] == {
        "form": "kuće|kuća|NOUN|{'Case': 'Gen', 'Gender': 'Fem', 'Number': 'Sing'}",
        "exact": True,
    }
    assert [w["problems"] for w in words] == [[], [], [], [], [], []]
    assert STUDY.key == ("hr", "light")
    body = {"text": "Bok"}
    assert client.post("/api/v1/classify", json=body).json()["type"] == "light"


def test_a_switch_drops_the_other_model(client):
    def names():
        return client.get("/api/v1/status").json()["loaded"]

    classify(client, heavy=False)
    assert "Croatian light" in names()
    classify(client)
    assert "Croatian heavy" in names() and "Croatian light" not in names()
    classify(client, text="Ich gehe.", language="de", heavy=False)
    assert [n for n in names() if not n.startswith("English")] == ["German light"]


def test_start_only_warms_the_light_models(client, tmp_path, monkeypatch):
    warmed = []
    monkeypatch.setattr(service, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(light.TAGGER, "warm_up", lambda: warmed.append("hr light"))
    monkeypatch.setattr(ENGLISH, "warm_up", lambda: warmed.append("en"))
    monkeypatch.setattr(service.decks, "import_decks", lambda: warmed.append("decks"))
    with client:
        # The warm up runs in threads.
        deadline = time.monotonic() + 5
        while len(warmed) < 3 and time.monotonic() < deadline:
            time.sleep(0.01)
    assert sorted(warmed) == ["decks", "en", "hr light"]
    assert client.requested == []


def test_lemmas_endpoint(client):
    classify(client)
    rows = client.get("/api/v1/lemmas", params={"limit": 2}).json()["lemmas"]
    assert [(r["lemma"], r["upos"], r["count"]) for r in rows] == [
        ("biti", "AUX", 2),
        ("Zagreb", "PROPN", 1),
    ]
    assert client.get("/api/v1/lemmas", params={"limit": 0}).status_code == 422
    # Each language has its own counts.
    assert client.get("/api/v1/lemmas", params={"language": "de"}).json() == {
        "lemmas": []
    }


def test_languages_endpoint(client, monkeypatch):
    monkeypatch.delenv("TLHELPER_ALWAYS_LARGE", raising=False)
    body = client.get("/api/v1/languages").json()
    assert [(lang["code"], lang["name"]) for lang in body["languages"]] == [
        ("hr", "Croatian"),
        ("de", "German"),
        ("fr", "French"),
        ("it", "Italian"),
    ]
    croatian_info, german_info, french_info, italian_info = body["languages"]
    assert croatian_info["variants"] == ["light", "heavy", "nonstandard"]
    assert german_info["variants"] == ["light", "heavy"]
    assert french_info["variants"] == ["light"]
    assert italian_info["variants"] == ["light"]
    assert body["english"]["variants"] == ["light"]
    assert (croatian_info["has_accents"], german_info["has_accents"]) == (True, False)
    assert german_info["dictionary_links"][0] == [
        "dict.cc: {lemma}",
        "https://www.dict.cc/?s={lemma}",
    ]
    assert body["english"]["tag_name"] == "Penn Treebank tag"
    assert body["large_by_default"] is False
    monkeypatch.setenv("TLHELPER_ALWAYS_LARGE", "1")
    assert client.get("/api/v1/languages").json()["large_by_default"] is True


def test_text_limits(client):
    assert client.post("/api/v1/classify", json={"text": ""}).status_code == 422
    too_long = "a" * (service.MAX_TEXT_CHARS + 1)
    assert client.post("/api/v1/classify", json={"text": too_long}).status_code == 422
    assert client.requested == []


ENGLISH_SENTENCES = [
    {
        "text": "She was in Zagreb.",
        "words": [
            {
                "id": 1,
                "text": "She",
                "lemma": "she",
                "upos": "PRON",
                "xpos": "PRP",
                "feats": {"Case": "Nom"},
                "start_char": 0,
                "end_char": 3,
            }
        ],
    }
]


def fake_translation(monkeypatch, translate):
    monkeypatch.setattr(service, "translate", translate)
    monkeypatch.setattr(
        ENGLISH, "analyze", lambda text, check=True: ENGLISH_SENTENCES, raising=False
    )
    # test_align.py has the tests for the links. This shows what align gets:
    # the language, and the sentences of both sides.
    monkeypatch.setattr(
        service.align,
        "align",
        lambda language, study, english: {
            "links": [[len(study[0]["words"]), len(english[0]["words"])]],
            # The API only lets pairs of numbers through.
            "guesses": [[0, 0]] if language.info.code == "hr" else [],
        },
    )


def test_translate_off_by_default(client, monkeypatch):
    fake_translation(monkeypatch, lambda *args: pytest.fail("translated"))
    assert "translation" not in classify(client)


def test_translate_adds_english_words(client, monkeypatch):
    calls = []

    def translate(text, source, target):
        calls.append((text, source, target))
        return "She was in Zagreb."

    fake_translation(monkeypatch, translate)
    result = classify(client, translate=True)
    assert calls == [("Ona je bila Zagreb.", CROATIAN, ENGLISH)]
    assert result["translation"] == {
        "text": "She was in Zagreb.",
        "sentences": ENGLISH_SENTENCES,
        "links": [[5, 1]],
        "guesses": [[0, 0]],
    }
    assert seen(result) == [1, 2, 2, 1, None]


def test_translation_error_keeps_the_croatian_result(client, monkeypatch):
    def translate(text, source, target):
        raise service.TranslationError("the DeepL quota for this month is used up")

    fake_translation(monkeypatch, translate)
    result = classify(client, translate=True)
    assert result["translation"] == {
        "error": "the DeepL quota for this month is used up"
    }
    assert len(result["sentences"][0]["words"]) == 5


def test_english_source_gives_the_croatian_breakdown(client, monkeypatch):
    calls = []

    def translate(text, source, target):
        calls.append((text, source, target))
        return "Ona je bila Zagreb."

    fake_translation(monkeypatch, translate)
    # nonstandard and translate have no effect on an English text.
    result = classify(client, text="She was in Zagreb.", source="en", nonstandard=True)
    assert calls == [("She was in Zagreb.", ENGLISH, CROATIAN)]
    assert client.requested == ["standard"]
    assert (result["type"], result["source"]) == ("heavy", "en")
    assert result["text"] == "Ona je bila Zagreb."
    assert seen(result) == [1, 2, 2, 1, None]
    assert result["translation"] == {
        "text": "She was in Zagreb.",
        "sentences": ENGLISH_SENTENCES,
        "links": [[5, 1]],
        "guesses": [[0, 0]],
    }


def test_english_source_keeps_the_english_checks_on_an_error(client, monkeypatch):
    def translate(text, source, target):
        raise service.TranslationError("DEEPL_API_KEY is not set")

    fake_translation(monkeypatch, translate)
    result = classify(client, text="She was in Zagreb.", source="en")
    assert result["sentences"] == []
    assert result["translation"] == {
        "text": "She was in Zagreb.",
        "sentences": ENGLISH_SENTENCES,
        "error": "DEEPL_API_KEY is not set",
    }
    assert client.requested == []


def test_unknown_language_and_source(client):
    for body in ({"language": "xx"}, {"source": "de"}, {"source": "hr"}):
        bad = client.post("/api/v1/classify", json={"text": "Bok", **body})
        assert bad.status_code == 422, body
    assert client.requested == []


def test_german_both_directions(client, monkeypatch):
    """The real German and English spaCy models, and a fake DeepL."""
    posts = fake_deepl(monkeypatch, text="I walk with the dog.")
    result = classify(
        client,
        text="Ich gehe mit den Hund.",
        language="de",
        translate=True,
        heavy=False,
        # German has no nonstandard models.
        nonstandard=True,
    )
    assert (result["type"], result["language"]) == ("light", "de")
    assert client.requested == []
    words = result["sentences"][0]["words"]
    assert [w["text"] for w in words if w["problems"]] == ["den"]
    # For a page in another language: the message of each problem.
    [den] = [w for w in words if w["problems"]]
    assert len(den["problem_messages"]) == len(den["problems"])
    assert all(m["key"].startswith("problem-") for m in den["problem_messages"])
    assert "problem_messages" not in words[0]
    assert "accent" not in words[0]
    assert [w["seen"] for w in words] == [1, 1, 1, 1, 1, None]
    english = result["translation"]["sentences"][0]["words"]
    assert [w["text"] for w in english][:2] == ["I", "walk"]
    assert posts[0][1]["json"]["source_lang"] == "DE"

    fake_deepl(monkeypatch, text="Ich gehe mit dem Hund.", posts=posts)
    result = classify(
        client, text="I walk with the dog.", language="de", source="en", heavy=False
    )
    assert result["text"] == "Ich gehe mit dem Hund."
    assert [w["seen"] for w in result["sentences"][0]["words"]][:2] == [2, 2]
    assert posts[1][1]["json"] == {
        "text": ["I walk with the dog."],
        "source_lang": "EN",
        "target_lang": "DE",
    }
    # The counts of German are not the counts of Croatian.
    rows = client.get("/api/v1/lemmas").json()["lemmas"]
    assert rows == []


def test_english_words_checks_only_the_text_of_the_user():
    [sentence] = ENGLISH.analyze("i is not hapy", check=True)
    assert [w["text"] for w in sentence["words"] if w["problems"]] == ["is", "hapy"]
    [sentence] = ENGLISH.analyze("i is not hapy", check=False)
    assert "problems" not in sentence["words"][0]


def fake_deepl(monkeypatch, status=200, text="She was at home.", posts=None):
    posts = [] if posts is None else posts

    def post(url, **kwargs):
        posts.append((url, kwargs))
        body = {"translations": [{"text": text}]}
        return SimpleNamespace(status_code=status, json=lambda: body)

    monkeypatch.setattr(deepl, "API_KEY", "secret")
    monkeypatch.setattr(deepl.requests, "post", post)
    return posts


def test_translate_caches(client, monkeypatch):
    posts = fake_deepl(monkeypatch)
    for _ in range(2):
        translated = service.translate("Ona je bila kod kuće.", CROATIAN, ENGLISH)
        assert translated == "She was at home."
    [(url, kwargs)] = posts
    assert url == deepl.URL
    assert kwargs["headers"] == {"Authorization": "DeepL-Auth-Key secret"}
    assert kwargs["json"] == {
        "text": ["Ona je bila kod kuće."],
        "source_lang": "HR",
        "target_lang": "EN-US",
    }


def test_each_language_pair_has_its_own_cache(client, monkeypatch):
    posts = fake_deepl(monkeypatch)
    # The fake DeepL always answers with the same text.
    assert service.translate("Home.", ENGLISH, CROATIAN) == "She was at home."
    assert service.translate("Home.", ENGLISH, CROATIAN) == "She was at home."
    # The same text in the other direction, or in another language, is
    # another request.
    service.translate("Home.", CROATIAN, ENGLISH)
    service.translate("Home.", ENGLISH, GERMAN)
    assert [kwargs["json"] for _, kwargs in posts] == [
        {"text": ["Home."], "source_lang": "EN", "target_lang": "HR"},
        {"text": ["Home."], "source_lang": "HR", "target_lang": "EN-US"},
        {"text": ["Home."], "source_lang": "EN", "target_lang": "DE"},
    ]


def test_old_tables_move_to_the_tables_with_a_language(client, monkeypatch):
    """A lemmas.db from before German: its rows are all Croatian."""
    conn = sqlite3.connect(service.DB_PATH)
    conn.executescript(
        """
        CREATE TABLE lemma_counts (lemma TEXT NOT NULL, upos TEXT NOT NULL,
            count INTEGER NOT NULL, last_seen TEXT NOT NULL,
            PRIMARY KEY (lemma, upos));
        CREATE TABLE translations (text TEXT PRIMARY KEY,
            english TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE croatian_translations (text TEXT PRIMARY KEY,
            croatian TEXT NOT NULL, created TEXT NOT NULL);
        INSERT INTO lemma_counts VALUES ('biti', 'AUX', 40, '2026-01-01');
        INSERT INTO translations VALUES ('Bok', 'Hi', '2026-01-01');
        INSERT INTO croatian_translations VALUES ('Hi', 'Bok', '2026-01-01');
        """
    )
    conn.close()
    posts = fake_deepl(monkeypatch)
    assert service.translate("Bok", CROATIAN, ENGLISH) == "Hi"
    assert service.translate("Hi", ENGLISH, CROATIAN) == "Bok"
    assert posts == []
    assert seen(classify(client)) == [1, 42, 42, 1, None]
    # A second start does not copy the rows again.
    assert seen(classify(client, track=False)) == [1, 42, 42, 1, None]


def test_the_cache_with_deepl_codes_moves_to_the_cache_with_a_translator(
    client, monkeypatch
):
    """A lemmas.db from before translators/: its rows are all from DeepL."""
    conn = sqlite3.connect(service.DB_PATH)
    conn.executescript(
        """
        CREATE TABLE translation_cache (source TEXT NOT NULL,
            target TEXT NOT NULL, text TEXT NOT NULL, translated TEXT NOT NULL,
            created TEXT NOT NULL, PRIMARY KEY (source, target, text));
        INSERT INTO translation_cache VALUES ('HR', 'EN-US', 'Bok', 'Hi', '2026-01-01');
        INSERT INTO translation_cache VALUES ('EN', 'DE', 'Hi', 'Hallo', '2026-01-01');
        """
    )
    conn.close()
    posts = fake_deepl(monkeypatch)
    assert service.translate("Bok", CROATIAN, ENGLISH) == "Hi"
    assert service.translate("Hi", ENGLISH, GERMAN) == "Hallo"
    assert posts == []


class FakeTranslator:
    name = "fake"

    def __init__(self):
        self.calls = []

    def translate(self, text, source, target):
        self.calls.append((text, source, target))
        return "from the fake"


def test_the_environment_selects_the_translator(client, monkeypatch):
    posts = fake_deepl(monkeypatch)
    fake = FakeTranslator()
    monkeypatch.setitem(translators.TRANSLATORS, "fake", fake)
    assert service.translate("Bok", CROATIAN, ENGLISH) == "She was at home."
    monkeypatch.setenv("TRANSLATOR", "fake")
    # The codes of the app, and not the text of DeepL from the cache.
    for _ in range(2):
        assert service.translate("Bok", CROATIAN, ENGLISH) == "from the fake"
    assert fake.calls == [("Bok", "hr", "en")]
    assert len(posts) == 1


def test_an_unknown_translator(client, monkeypatch):
    monkeypatch.setenv("TRANSLATOR", "babel")
    with pytest.raises(service.TranslationError, match="'babel'.*deepl"):
        service.translate("Bok", CROATIAN, ENGLISH)


def test_translate_without_a_key(client, monkeypatch):
    monkeypatch.setattr(
        deepl.requests, "post", lambda *a, **kw: pytest.fail("called DeepL")
    )
    with pytest.raises(service.TranslationError, match="DEEPL_API_KEY is not set"):
        service.translate("Bok", CROATIAN, ENGLISH)


@pytest.mark.parametrize(
    "status, reason", [(456, "quota"), (429, "too many"), (403, "HTTP 403")]
)
def test_translate_deepl_errors(client, monkeypatch, status, reason):
    fake_deepl(monkeypatch, status)
    with pytest.raises(service.TranslationError, match=reason):
        service.translate("Bok", CROATIAN, ENGLISH)
    # A failure is not cached.
    fake_deepl(monkeypatch)
    assert service.translate("Bok", CROATIAN, ENGLISH) == "She was at home."


def test_translate_timeout(client, monkeypatch):
    def post(url, **kwargs):
        raise deepl.requests.Timeout()

    monkeypatch.setattr(deepl, "API_KEY", "secret")
    monkeypatch.setattr(deepl.requests, "post", post)
    with pytest.raises(service.TranslationError, match="in time"):
        service.translate("Bok", CROATIAN, ENGLISH)


def test_english_words_real_spacy():
    [first, second] = ENGLISH.analyze("She was at home. It rained.", check=False)
    assert first["text"] == "She was at home."
    assert [(w["lemma"], w["upos"]) for w in first["words"]] == [
        ("she", "PRON"),
        ("be", "AUX"),
        ("at", "ADP"),
        ("home", "NOUN"),
        (".", "PUNCT"),
    ]
    assert first["words"][1] == {
        "id": 2,
        "text": "was",
        "lemma": "be",
        "upos": "AUX",
        "xpos": "VBD",
        "feats": {
            "Mood": "Ind",
            "Number": "Sing",
            "Person": "3",
            "Tense": "Past",
            "VerbForm": "Fin",
        },
        "head": 0,
        "deprel": "ROOT",
        "start_char": 4,
        "end_char": 7,
    }
    # The spans are offsets in the whole text, and the ids restart.
    rained = second["words"][1]
    assert (rained["id"], rained["start_char"], rained["end_char"]) == (2, 20, 26)

    # A participle before a noun shows as an adjective, but keeps its VBG tag.
    [boat, lake] = ENGLISH.analyze(
        "My floating boat is full of eels. The boat is floating on the lake.",
        check=False,
    )
    floating = boat["words"][1]
    assert (floating["upos"], floating["xpos"]) == ("ADJ", "VBG")
    floating = lake["words"][3]
    assert (floating["upos"], floating["xpos"]) == ("VERB", "VBG")


def test_access_log_line_has_the_latency(client, monkeypatch):
    lines = []
    monkeypatch.setattr(
        service.access_logger, "info", lambda fmt, *args: lines.append(fmt % args)
    )
    # The health checks call /healthz every few seconds: no line for it.
    assert client.get("/healthz").text == "ok"
    client.get("/", headers={"fly-client-ip": "203.0.113.7"})
    client.get("/api/v1/lemmas?limit=0")
    assert re.fullmatch(
        r"203\.0\.113\.7 - - \[\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2} \+0000\]"
        r' "GET / HTTP/1\.1" 200 \d+ \d+\.\dms',
        lines[0],
    ), lines[0]
    assert '"GET /api/v1/lemmas?limit=0 HTTP/1.1" 422 ' in lines[1]
    assert len(lines) == 2


def test_models_on_disk_load_without_a_download(monkeypatch):
    monkeypatch.setattr(heavy, "load_pipeline", lambda model_type: fake_doc)
    monkeypatch.setattr(
        heavy.classla, "download", lambda *a, **kw: pytest.fail("downloaded")
    )
    assert heavy.get_pipeline("standard") is fake_doc


def test_status_names_the_models_that_load(tmp_path, monkeypatch):
    client = TestClient(service.app)
    during = []

    def load_pipeline(model_type):
        during.append(client.get("/api/v1/status").json())
        return fake_doc

    monkeypatch.setattr(service, "DB_PATH", tmp_path / "lemmas.db")
    monkeypatch.setattr(heavy, "load_pipeline", load_pipeline)
    STUDY.drop()

    # The English model of the other tests can be in the list too.
    def status():
        state = client.get("/api/v1/status").json()
        state["loaded"] = [n for n in state["loaded"] if n.startswith("Croatian")]
        return state

    idle = {"loading": None, "loading_model": None}
    assert status() == {**idle, "loaded": []}
    classify(client)
    assert [state["loading"] for state in during] == ["Croatian heavy"]
    # The same model as values, for a page in another language.
    assert [state["loading_model"] for state in during] == [
        {"language": "hr", "variant": "heavy"}
    ]
    assert status() == {**idle, "loaded": ["Croatian heavy"]}


def test_missing_models_download_then_load(tmp_path, monkeypatch):
    calls = []

    def load_pipeline(model_type):
        calls.append("load")
        if "download" not in calls:
            raise FileNotFoundError("no models yet")
        return fake_doc

    monkeypatch.setattr(heavy, "MODEL_DIR", tmp_path / "models")
    monkeypatch.setattr(heavy, "load_pipeline", load_pipeline)
    monkeypatch.setattr(
        heavy.classla, "download", lambda *a, **kw: calls.append("download")
    )
    assert heavy.get_pipeline("standard") is fake_doc
    assert calls == ["load", "download", "load"]


def test_download_off_gives_503_and_no_download(tmp_path, monkeypatch):
    STUDY.drop()
    monkeypatch.setattr(heavy, "MODEL_DIR", tmp_path / "models")
    monkeypatch.setattr(heavy, "DOWNLOAD_MODELS", False)
    monkeypatch.setattr(
        heavy.classla, "download", lambda *a, **kw: pytest.fail("downloaded")
    )
    body = {"text": "Bok", "heavy": True}
    response = TestClient(service.app).post("/api/v1/classify", json=body)
    assert response.status_code == 503
    assert "DOWNLOAD_MODELS is off" in response.json()["detail"]
    # A failed load leaves the slot empty and not locked.
    assert (STUDY.key, STUDY.loading) == (None, None)


@pytest.mark.skipif(
    not (REAL_MODELS / "hr" / "lemma" / "nonstandard.pt").exists(),
    reason="the real models are not in .data/ at the repository root",
)
@pytest.mark.skipif(
    find_spec("de_dep_news_trf") is None, reason="de_dep_news_trf is not installed"
)
def test_real_models(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "DB_PATH", tmp_path / "lemmas.db")
    monkeypatch.setattr(heavy, "MODEL_DIR", REAL_MODELS)
    STUDY.drop()
    client = TestClient(service.app)

    words = classify(client, text="Ona je bila kod kuće.")["sentences"][0]["words"]
    assert [(w["lemma"], w["upos"]) for w in words] == [
        ("on", "PRON"),
        ("biti", "AUX"),
        ("biti", "AUX"),
        ("kod", "ADP"),
        ("kuća", "NOUN"),
        (".", "PUNCT"),
    ]
    assert words[4]["feats"] == {"Case": "Gen", "Gender": "Fem", "Number": "Sing"}
    assert (words[4]["start_char"], words[4]["end_char"]) == (16, 20)
    # "kuće" is also the nominative plural kȕće. The case from classla selects
    # the genitive singular, with its long last vowel.
    assert words[4]["accent"] == {"form": "kȕćē", "exact": True}
    assert words[1]["accent"] == {"form": "je", "exact": True, "clitic": True}
    assert words[5]["accent"] is None
    assert [w["problems"] for w in words] == [[], [], [], [], [], []]

    # classla tags a wrong word by its form, so the grammar checks see it.
    wrong = {
        "Pijem kava.": "kava",
        "Vidim lijepa kuću.": "lijepa",
        "Razgovaram s prijatelj.": "prijatelj",
    }
    for text, flagged in wrong.items():
        words = classify(client, text=text)["sentences"][0]["words"]
        assert [w["text"] for w in words if w["problems"]] == [flagged], text
    # The lexicon inside the lemma model finds the unknown word. "kava" stays,
    # because it is also a genitive plural: full of coffees.
    words = classify(client, text="moj lebdići čamac pun je je je je kava")
    words = words["sentences"][0]["words"]
    assert [w["text"] for w in words if w["problems"]] == ["lebdići", "je", "je", "je"]
    # A phrase that repeats. "pun je jegulje" (full of eel) is correct.
    words = classify(client, text="moj plutajući čamac pun je pun je pun je jegulje")
    words = words["sentences"][0]["words"]
    assert [w["id"] for w in words if w["problems"]] == [6, 7, 8, 9]
    for text in [
        "Pijem kavu.",
        "Vidim lijepu kuću.",
        "Razgovaram s prijateljem.",
        "Moj lebdeći čamac pun je jegulja.",
        "Čaša je puna hladne vode.",
    ]:
        words = classify(client, text=text)["sentences"][0]["words"]
        assert not any(w["problems"] for w in words), text

    # The nonstandard models put the diacritics back.
    casual = classify(client, text="sta radis veceras", nonstandard=True)
    lemmas = [w["lemma"] for w in casual["sentences"][0]["words"]]
    assert lemmas == ["što", "raditi", "večeras"]

    # The other heavy model, then back to a heavy and to a light one.
    german = classify(client, text="Ich gehe mit den Hund.", language="de")
    assert german["type"] == "heavy"
    words = german["sentences"][0]["words"]
    assert [w["text"] for w in words if w["problems"]] == ["den"]
    # French has only the light model, and a request for the heavy one gets it.
    french = classify(client, text="J'ai une petit chat.", language="fr")
    assert french["type"] == "light"
    words = french["sentences"][0]["words"]
    assert [w["text"] for w in words if w["problems"]] == ["une"]
    italian = classify(client, text="Ho una piccolo gatto.", language="it")
    assert italian["type"] == "light"
    words = italian["sentences"][0]["words"]
    assert [w["text"] for w in words if w["problems"]] == ["una"]
    classify(client, text="Pijem kavu.")
    assert classify(client, text="Pijem kavu.", heavy=False)["type"] == "light"

    # Only one model stays loaded, so the peak stays under the 4 GB machine.
    assert STUDY.key == ("hr", "light")
    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
    assert peak_mb < 3500, f"peak memory was {peak_mb} MB"
