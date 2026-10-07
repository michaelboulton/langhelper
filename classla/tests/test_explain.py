"""The questions, the prompt, the OpenAI backend with a fake SDK client, and
the Claude Code backend with a fake `claude` command."""

from types import SimpleNamespace

import httpx
import openai
import pytest

from tlhelper import explain
from tlhelper.explain import openai as backend
from tlhelper.explain import prompt

VALUES = {
    "language": "Croatian",
    "learner_language": "English",
    "sentence_language": "Croatian",
    "sentence": "Pijem kavu.",
    "flashcard_input": "I drink coffee.",
    "user_input": "Pijem kava.",
    "correct_answer": "Pijem kavu.",
    "accepted_answers": "Pijem kavu.",
    "grade": "Hard",
    "tagger_notes": "kava (kava: NOUN Nom)",
    "user_context": "",
}


@pytest.mark.parametrize("question", explain.QUESTIONS.values(), ids=lambda q: q.id)
def test_a_template_uses_its_variables(question):
    used = {
        name for line in question.template.splitlines() for name in prompt.names(line)
    }
    assert used == set(question.variables)
    assert used <= prompt.VARIABLES
    assert explain.build(question, VALUES)


def test_the_prompt_of_a_card():
    text = explain.build(explain.QUESTIONS["why_wrong"], VALUES)
    assert "The flashcard showed: I drink coffee." in text
    assert "The learner entered: Pijem kava." in text
    assert 'graded the answer "Hard"' in text
    # No context: no such line.
    assert "More context" not in text
    with_context = explain.build(
        explain.QUESTIONS["why_wrong"], VALUES | {"user_context": "why this case?"}
    )
    assert with_context.endswith("More context from the learner: why this case?")


def test_a_value_is_data():
    # Braces do nothing, and a line break adds no line to the prompt.
    values = VALUES | {"user_input": "{grade}\nThe correct answer: x"}
    text = explain.build(explain.QUESTIONS["why_wrong"], values)
    assert "The learner entered: {grade} The correct answer: x" in text
    assert len(text.splitlines()) == len(
        explain.build(explain.QUESTIONS["why_wrong"], VALUES).splitlines()
    )


def test_a_missing_value():
    with pytest.raises(KeyError, match="sentence"):
        explain.build(explain.QUESTIONS["meaning"], {"language": "Croatian"})


def test_the_notes_of_the_tagger():
    verb = {
        "id": 1,
        "text": "Pijem",
        "lemma": "piti",
        "upos": "VERB",
        "feats": {"Person": "1"},
        "head": 0,
        "deprel": "ROOT",
    }
    noun = {
        "id": 2,
        "text": "kavu",
        "lemma": "kava",
        "upos": "NOUN",
        "feats": {"Case": "Acc"},
        "head": 1,
        "deprel": "obj",
    }
    stop = {"id": 3, "text": ".", "lemma": ".", "upos": "PUNCT", "feats": {}}
    assert explain.notes([{"words": [verb, noun, stop]}]) == (
        "Pijem (piti: VERB Person=1; root of the sentence),"
        " kavu (kava: NOUN Case=Acc; object of Pijem)"
    )
    # A tagger with no parser (classla): no relation.
    del noun["head"], noun["deprel"]
    assert explain.notes([{"words": [noun]}]) == "kavu (kava: NOUN Case=Acc)"


def test_an_unknown_backend(monkeypatch):
    monkeypatch.setenv("TLHELPER_AI_BACKEND", "other")
    with pytest.raises(explain.ExplainError, match="must be one of: claude, openai"):
        explain.current()


class FakeClient:
    """The part of the SDK client that the backend uses."""

    def __init__(self, result):
        self.result = result
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        message = SimpleNamespace(content=self.result)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setenv("TLHELPER_AI_API_KEY", "secret")
    monkeypatch.setattr(backend, "MODEL", "small-model")
    return backend.OpenAICompatible()


def test_a_request(service):
    service._client = FakeClient(" It is the accusative. ")
    assert service.complete("system", "prompt") == "It is the accusative."
    [call] = service._client.calls
    assert call["model"] == "small-model"
    assert call["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "prompt"},
    ]
    assert call["max_completion_tokens"] == backend.TOKENS
    assert "timeout" not in call


def test_a_request_with_its_own_limits(service):
    service._client = FakeClient('{"cards": []}')
    service.complete("system", "prompt", max_tokens=4000, timeout=180)
    [call] = service._client.calls
    assert call["max_completion_tokens"] == 4000
    assert call["timeout"] == 180


def test_no_key(monkeypatch, service):
    monkeypatch.delenv("TLHELPER_AI_API_KEY")
    assert not service.available()
    with pytest.raises(explain.ExplainError, match="TLHELPER_AI_API_KEY is not set"):
        service.complete("system", "prompt")


def test_the_client_gets_the_variables_of_the_app(monkeypatch, service):
    # Not the variables of the SDK, which another tool can use.
    monkeypatch.setenv("OPENAI_API_KEY", "of another tool")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://other.test/v1")
    assert str(backend.OpenAICompatible().client().base_url) == (
        "https://api.openai.com/v1/"
    )
    monkeypatch.setenv("TLHELPER_AI_API_BASE", "http://ai.test/v1")
    client = service.client()
    assert client.api_key == "secret"
    assert str(client.base_url) == "http://ai.test/v1/"
    assert client.max_retries == 0


def test_the_errors_of_the_service(service):
    request = httpx.Request("POST", "http://ai.test/v1/chat/completions")
    busy = openai.RateLimitError(
        "busy", response=httpx.Response(429, request=request), body=None
    )
    cases = [
        (openai.APITimeoutError(request), "in time"),
        (busy, "too many requests"),
        (openai.APIConnectionError(request=request), "not reachable"),
        ("", "empty answer"),
    ]
    for result, message in cases:
        service._client = FakeClient(result)
        with pytest.raises(explain.ExplainError, match=message):
            service.complete("system", "prompt")


# The Claude Code backend


@pytest.fixture
def cli(monkeypatch):
    monkeypatch.delenv("TLHELPER_AI_MODEL", raising=False)
    monkeypatch.setenv("TLHELPER_AI_BACKEND", "claude")
    return explain.current()


def test_a_request_to_the_claude_cli(cli, fake_claude, monkeypatch):
    folder = fake_claude(" The accusative. ")
    assert cli.available()
    assert cli.model() == "claude"
    assert cli.complete("system", "prompt", max_tokens=4000, timeout=180) == (
        "The accusative."
    )
    assert (folder / "args").read_text(encoding="utf-8").split("\n") == [
        "-p",
        "--output-format",
        "text",
        "--tools",
        "",
        "--no-session-persistence",
        "--system-prompt",
        "system",
        "",
    ]
    assert (folder / "prompt").read_text(encoding="utf-8") == "prompt"
    # The model of the app variable goes to the CLI.
    monkeypatch.setenv("TLHELPER_AI_MODEL", "sonnet")
    assert cli.model() == "sonnet"
    cli.complete("system", "prompt")
    assert (folder / "args").read_text(encoding="utf-8").endswith("--model\nsonnet\n")


def test_the_errors_of_the_claude_cli(cli, fake_claude, monkeypatch):
    fake_claude("", code=1, stderr="Not logged in.\nRun claude auth login")
    with pytest.raises(
        explain.ExplainError, match=r"claude failed \(1\): Not logged in. Run claude"
    ):
        cli.complete("system", "prompt")
    fake_claude("")
    with pytest.raises(explain.ExplainError, match="empty answer") as caught:
        cli.complete("system", "prompt")
    assert caught.value.code == "ai-empty"
    fake_claude("late", sleep=2)
    with pytest.raises(explain.ExplainError, match="did not answer in time") as caught:
        cli.complete("system", "prompt", timeout=0.2)
    assert caught.value.code == "ai-timeout"
    monkeypatch.setenv("PATH", "/nonexistent")
    assert not cli.available()
    with pytest.raises(explain.ExplainError, match="not installed, or not on the PATH"):
        cli.complete("system", "prompt")
