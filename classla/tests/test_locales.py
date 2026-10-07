"""The catalogs of the page text (tlhelper/languages/*/ui.ftl), and the code
that names their messages."""

import re
import warnings
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fluent.syntax import FluentParser, ast
from fluent.syntax.visitor import Visitor

from tlhelper import app as service
from tlhelper import locales

ROOT = Path(__file__).parents[1]
CODES = list(locales.catalogs())
OTHERS = [code for code in CODES if code != locales.DEFAULT]


class Variables(Visitor):
    def __init__(self):
        self.names = set()

    def visit_VariableReference(self, node):
        self.names.add(node.id.name)


def messages(code: str) -> dict[str, set[str]]:
    """Each message of a catalog, with the variables that it uses."""
    text, _ = locales.read(code)
    resource = FluentParser().parse(text)
    junk = [each.content for each in resource.body if isinstance(each, ast.Junk)]
    assert junk == [], f"{code}: the parser does not understand this"
    found = {}
    for entry in resource.body:
        if isinstance(entry, ast.Message):
            # The small formatter of i18n.js has no attributes.
            assert entry.attributes == [], entry.id.name
            assert entry.id.name not in found, f"{code}: {entry.id.name} is there twice"
            variables = Variables()
            variables.visit(entry)
            found[entry.id.name] = variables.names
    return found


def test_the_locales():
    assert locales.DEFAULT == "en"
    assert CODES == ["en", "hr", "de", "fr", "it"]


@pytest.mark.parametrize("code", CODES)
def test_a_catalog_parses(code):
    assert messages(code)


@pytest.mark.parametrize("code", OTHERS)
def test_a_translation_follows_the_english_catalog(code):
    english, translated = messages("en"), messages(code)
    assert set(translated) - set(english) == set()
    for name, variables in translated.items():
        # "$gotName" is the word for the raw value "$got", and a translation
        # can select on the raw value.
        allowed = english[name] | {each.removesuffix("Name") for each in english[name]}
        assert variables <= allowed, name
    missing = sorted(set(english) - set(translated))
    if missing:
        warnings.warn(f"{code} shows these in English: {', '.join(missing)}")


def test_the_code_names_messages_that_exist():
    english = set(messages("en"))
    python = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "tlhelper").rglob("*.py")
    )
    page = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [*(ROOT / "static/js").glob("*.js"), ROOT / "static/index.html"]
    )
    named = set(re.findall(r'Problem\(\s*"([a-z-]+)"', python))
    assert len(named) >= 10
    # The code of an error: a text like "ai-limit" is nothing else in the code.
    named |= {
        "error-" + code
        for code in re.findall(r'"((?:ai|translator|voice)-[a-z-]+|not-admin)"', python)
    }
    # A complete id. An id that the page builds ends in "-": "upos-" + tag.
    named |= set(re.findall(r'\bt(?:Or)?\(\s*"([A-Za-z0-9_-]+[A-Za-z0-9_])"', page))
    named |= set(re.findall(r'data-l10n-[a-z]+="([A-Za-z0-9_-]+)"', page))
    assert named - english == set()


def test_the_api_of_the_locales():
    client = TestClient(service.app)
    listed = client.get("/api/v1/locales").json()
    assert listed["default"] == "en"
    assert [(each["code"], each["name"]) for each in listed["locales"]] == [
        ("en", "English"),
        ("hr", "Hrvatski"),
        ("de", "Deutsch"),
        ("fr", "Français"),
        ("it", "Italiano"),
    ]
    catalog = client.get("/api/v1/locales/hr/ui.ftl")
    assert catalog.status_code == 200
    assert catalog.headers["content-type"] == "text/plain; charset=utf-8"
    assert "tab-cards = Kartice" in catalog.text
    again = client.get(
        "/api/v1/locales/hr/ui.ftl", headers={"if-none-match": catalog.headers["etag"]}
    )
    assert again.status_code == 304
    assert client.get("/api/v1/locales/xx/ui.ftl").status_code == 404
