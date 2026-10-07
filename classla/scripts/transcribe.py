#!/usr/bin/env python3

"""The transcript of a voice clip, from a model that hears audio: the llamacpp
service of docker-compose.yml (Gemma with its --mmproj), or any service with
the chat completions API of OpenAI and `input_audio`. A quick check that a
clip is speech, such as the mp3 of the voice service or a reference clip of
omnivoice. The set-up is in scripts/README.md.

With no TLHELPER_AI_* variables set, it asks the llamacpp service at
http://localhost:9931/v1. Each variable that is set replaces its default.

    # One clip, with the llamacpp service up
    uv run python -m scripts.transcribe hr.wav

    # Several clips, each heard 3 times, with the language named in the prompt
    uv run python -m scripts.transcribe --language Croatian --tries 3 out/*.mp3

A clip is a .wav or an .mp3. Run it from the folder of the project, as a
module.
"""

import argparse
import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# The llamacpp service of docker-compose.yml, from the host. Before the import:
# the module reads TLHELPER_AI_MODEL when it loads.
os.environ.setdefault("TLHELPER_AI_API_BASE", "http://localhost:9931/v1")
os.environ.setdefault("TLHELPER_AI_API_KEY", "local")
os.environ.setdefault("TLHELPER_AI_MODEL", "gemma-4-12b")

from tlhelper.explain import openai as service

FORMATS = ("wav", "mp3")
SYSTEM = (
    "You are a speech recognizer. You write down what is said, in the language"
    " it is said in."
)
PROMPT = "Transcribe the speech in this audio. Output only the transcript."
LANGUAGE_PROMPT = (
    "Transcribe the speech in this audio. It is in {language}. Output only the"
    " transcript."
)
# A little randomness and a repeat penalty: at 0 and with no penalty, Gemma
# can repeat one token of its template until max_tokens (see scripts/README.md).
TEMPERATURE = 0.3
REPEAT_PENALTY = 1.3
MAX_TOKENS = 300
TIMEOUT = 120


def audio_part(path: Path) -> dict:
    kind = path.suffix.lower().lstrip(".")
    if kind not in FORMATS:
        raise SystemExit(
            f"{path}: only .wav and .mp3 (ffmpeg -i {path.name} {path.stem}.wav)"
        )
    data = base64.b64encode(path.read_bytes()).decode()
    return {"type": "input_audio", "input_audio": {"data": data, "format": kind}}


def transcribe(client, model: str, path: Path, language: str) -> str:
    prompt = LANGUAGE_PROMPT.format(language=language) if language else PROMPT
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": [audio_part(path), {"type": "text", "text": prompt}],
            },
        ],
        temperature=TEMPERATURE,
        max_completion_tokens=MAX_TOKENS,
        # llama-server reads it; the API of OpenAI has no such parameter.
        extra_body={"repeat_penalty": REPEAT_PENALTY},
        timeout=TIMEOUT,
    )
    return (response.choices[0].message.content or "").strip()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.transcribe",
        description="The transcript of each voice clip, from a model that hears audio.",
    )
    parser.add_argument("clips", nargs="+", type=Path, help=".wav or .mp3 files")
    parser.add_argument(
        "--language",
        default="",
        help="the name of the language in English, for the prompt (default: none, "
        "so the model is not led to hear that language)",
    )
    parser.add_argument(
        "--tries", type=int, default=1, help="how many times to ask for each clip"
    )
    args = parser.parse_args(argv)

    missing = [str(clip) for clip in args.clips if not clip.is_file()]
    if missing:
        raise SystemExit(f"no such file: {', '.join(missing)}")

    client = service.OpenAICompatible().client()
    for clip in args.clips:
        for attempt in range(1, args.tries + 1):
            label = f"{clip} #{attempt}" if args.tries > 1 else str(clip)
            text = transcribe(client, service.MODEL, clip, args.language)
            print(f"== {label}\n{text or '(empty answer)'}\n", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
