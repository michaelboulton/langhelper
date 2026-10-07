"""The "explain with AI" buttons: a language model answers a question about a
sentence, or about an answer to a flashcard.

The user selects one of questions.QUESTIONS and can add some context. The
server fills the template of the question (prompt.build) with its own data and
sends it to the backend that the variable TLHELPER_AI_BACKEND names
(default "openai"). The page never sends a prompt, so the route is not a free
door to a paid service. The prompt also has the notes of the tagger
(prompt.notes): the lemma, the part of speech, the features, and the relation
of each word. routes.tagged() makes them with the model that is in memory, so
a question loads no other model. The text of the user goes to that service, so
the page makes a request only on a click.

The OpenAI SDK (openai.py), the default backend
    It calls each service with the chat completions API of OpenAI. A Claude
    or a Gemini subscription gives no API access: the key must be an API key.
    Each variable has the prefix TLHELPER_AI_, and the backend gives the key
    and the address to the SDK.
    1. Set TLHELPER_AI_API_KEY. In the container, entrypoint.sh can read the
       key from the secret /run/secrets/tlhelper_ai_api_key (see
       docker-compose.yml). On Fly: fly secrets set TLHELPER_AI_API_KEY=...
    2. Set TLHELPER_AI_MODEL to a model of the service. A small model is
       enough.
    3. For a service that is not OpenAI, set TLHELPER_AI_API_BASE:
           Anthropic    https://api.anthropic.com/v1/
           Gemini       https://generativelanguage.googleapis.com/v1beta/openai/
           OpenRouter   https://openrouter.ai/api/v1
           Ollama       http://localhost:11434/v1 (the key can be any text)
           llama.cpp    http://localhost:8080/v1 (the key can be any text;
                        docker-compose.yml has such a service, on port
                        9931)
    4. TLHELPER_AI_MAX_TOKENS (default 500) limits one answer.
       TLHELPER_AI_PER_DAY (default 50)
       limits the requests of one user in a day. The cache does not count.

Claude Code (claude_cli.py), TLHELPER_AI_BACKEND=claude
    Each request is one `claude -p` process, with no tools and no session
    file, so a machine with the CLI and its login needs no key. For a local
    run and for the scripts (scripts/README.md); the image has no CLI.
    TLHELPER_AI_MODEL, if set, goes to `claude --model`: an alias such as
    "sonnet", or a full model name. TLHELPER_AI_MAX_TOKENS does nothing here.

To add a backend
    1. Write a module here with a class that fits base.Backend.
    2. Raise base.ExplainError for every failure, with a message that the
       page can show.
    3. Read the credentials from the environment. Import the SDK and make
       its client on the first call, and not at the import of the module.
    4. Add an instance to BACKENDS below, and the set-up to this docstring.

To add a question
    Add a Question to questions.QUESTIONS. Its template can use the names of
    prompt.VARIABLES. The page reads the list from /api/v1/explain/questions.
"""

import os

from .base import MAX_CONTEXT_CHARS, Backend, ExplainError, Question
from .claude_cli import ClaudeCLI
from .openai import OpenAICompatible
from .prompt import build, notes
from .questions import QUESTIONS, SYSTEM, system

__all__ = [
    "BACKENDS",
    "MAX_CONTEXT_CHARS",
    "PER_DAY",
    "QUESTIONS",
    "SYSTEM",
    "Backend",
    "ExplainError",
    "Question",
    "build",
    "current",
    "notes",
    "system",
]

BACKENDS: dict[str, Backend] = {
    each.name: each for each in (OpenAICompatible(), ClaudeCLI())
}
DEFAULT = "openai"
# The requests of one user in a day (UTC) that go to the service.
PER_DAY = int(os.environ.get("TLHELPER_AI_PER_DAY", "50"))


def current() -> Backend:
    """The backend that TLHELPER_AI_BACKEND names."""
    name = os.environ.get("TLHELPER_AI_BACKEND", DEFAULT)
    if name not in BACKENDS:
        known = ", ".join(sorted(BACKENDS))
        raise ExplainError(
            f"TLHELPER_AI_BACKEND is {name!r}, and must be one of: {known}"
        )
    return BACKENDS[name]
