"""Claude Code as the AI service: one `claude -p` process for each request,
with the prompt on its stdin. The set-up is in the docstring of the package.

The login of the CLI is the credential, so the backend needs no key: it is
available where the `claude` command is on the PATH. The image has no CLI,
so in the container the page has no buttons with this backend.
"""

import os
import shutil
import subprocess

from .base import ExplainError

COMMAND = "claude"
# The most characters of the error output of the CLI in an error message.
MAX_STDERR = 500


def model_option() -> str:
    return os.environ.get("TLHELPER_AI_MODEL", "")


class ClaudeCLI:
    name = "claude"

    def available(self) -> bool:
        return shutil.which(COMMAND) is not None

    def model(self) -> str:
        return model_option() or COMMAND

    def complete(
        self,
        system: str,
        prompt: str,
        *,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> str:
        # No tools: the model answers from the prompt alone, and nothing asks
        # for a permission. No session file: the request leaves nothing behind.
        command = [
            COMMAND,
            "-p",
            "--output-format",
            "text",
            "--tools",
            "",
            "--no-session-persistence",
            "--system-prompt",
            system,
        ]
        if model_option():
            command += ["--model", model_option()]
        try:
            run = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ExplainError(
                f"{COMMAND} is not installed, or not on the PATH"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ExplainError(
                f"{COMMAND} did not answer in time", "ai-timeout"
            ) from exc
        if run.returncode:
            detail = " ".join(run.stderr.split())[-MAX_STDERR:] or "no error output"
            raise ExplainError(f"{COMMAND} failed ({run.returncode}): {detail}")
        text = run.stdout.strip()
        if not text:
            raise ExplainError(f"{COMMAND} gave an empty answer", "ai-empty")
        return text
