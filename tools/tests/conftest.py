"""The folders of the app data, and a fake AI service for the scripts."""

import json
import os
import shlex

import pytest
from tlhelper import explain
from tlhelper.flashcards import decks, store

from scripts import lessons

# shortcut: the package writer of the web tests, through the pythonpath of
# pyproject.toml. Move it to a shared module if more web fixtures are needed.
from flashcards.conftest import write_apkg


@pytest.fixture
def deck_dir(tmp_path, monkeypatch):
    """An empty deck folder and an empty database."""
    folder = tmp_path / "decks"
    folder.mkdir()
    monkeypatch.setattr(decks, "DECK_DIRS", [folder])
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "flashcards.db")
    return folder


@pytest.fixture
def make_apkg():
    return write_apkg


class ScriptedBackend:
    """Gives its answers in order, and keeps what it was asked."""

    name = "scripted"

    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []
        self.systems = []
        self.kwargs = []

    def available(self):
        return True

    def model(self):
        return "scripted-model"

    def complete(self, system, prompt, **kwargs):
        self.systems.append(system)
        self.prompts.append(prompt)
        self.kwargs.append(kwargs)
        assert self.answers, "one request too many"
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, str) else json.dumps(answer)


@pytest.fixture
def scripted(monkeypatch):
    """scripted(*answers): the AI service of the next run of a script."""

    def use(*answers):
        backend = ScriptedBackend(answers)
        monkeypatch.setitem(explain.BACKENDS, "scripted", backend)
        monkeypatch.setenv("TLHELPER_AI_BACKEND", "scripted")
        return backend

    return use


@pytest.fixture
def fake_lemmas(monkeypatch):
    """Each word of the tagged text is a noun: no model load."""

    def lemmas_of(text, language):
        words = sorted({word.strip(".").lower() for word in text.split()})
        return {"NOUN": words} if words else {}

    monkeypatch.setattr(lessons, "lemmas_of", lemmas_of)


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    """fake_claude(stdout, code=0, stderr="", sleep=0): a `claude` command
    on the PATH, for the Claude Code backend (tlhelper/explain/claude_cli.py).
    It keeps its arguments and its stdin in the folder it returns."""
    folder = tmp_path / "claude-cli"
    folder.mkdir()
    monkeypatch.setenv("PATH", f"{folder}:{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_CLAUDE_DIR", str(folder))

    def use(stdout, code=0, stderr="", sleep=0):
        script = folder / "claude"
        script.write_text(
            "#!/bin/sh\n"
            'printf "%s\\n" "$@" > "$FAKE_CLAUDE_DIR/args"\n'
            'cat > "$FAKE_CLAUDE_DIR/prompt"\n'
            f"sleep {sleep}\n"
            f"printf '%s' {shlex.quote(stderr)} >&2\n"
            f"printf '%s' {shlex.quote(stdout)}\n"
            f"exit {code}\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        return folder

    return use
