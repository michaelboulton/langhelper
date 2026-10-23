"""A check by ear of the named voices of the voice service: the same sentence
in each voice that --voice names, one mp3 for each. The set-up is in
scripts/README.md.

    TLHELPER_VOICE_URL=http://localhost:8002 uv run python -m scripts.check_voices \\
        --language it --voice it --voice it-2

Run it from the folder of the project, as a module.
"""

import argparse
from pathlib import Path

from tlhelper import speech
from tlhelper.speech.openai import OpenAISpeech

# About three seconds each: a shorter text can fail (../tts/README.md, "Voice").
SAMPLES = {
    "de": "Guten Tag. Ist in diesem Gericht Fleisch?",
    "en": "Good afternoon. Is there any meat in this dish?",
    "fr": "Bonjour. Est-ce qu'il y a de la viande dans ce plat ?",
    "hr": "Dobar dan. Ima li mesa u ovom jelu?",
    "it": "Buongiorno. C'è carne in questo piatto?",
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n", 1)[1],
    )
    parser.add_argument(
        "--voice",
        action="append",
        required=True,
        metavar="NAME",
        help="a voice of the service, such as it-2. Can repeat",
    )
    parser.add_argument(
        "--language", required=True, help="the code of the language, such as it"
    )
    parser.add_argument(
        "--text", help="the text to read. Default: a sample sentence of the language"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("voice-check"),
        help="the folder of the mp3s. Default: voice-check",
    )
    args = parser.parse_args(argv)
    text = args.text or SAMPLES.get(args.language)
    if not text:
        parser.error(f"no sample sentence for {args.language!r}: give --text")
    service = OpenAISpeech()
    if not service.available():
        raise SystemExit("set TLHELPER_VOICE_URL, such as http://localhost:8002")
    entry = service.entry()
    if entry is None:
        raise SystemExit("the voice service gave no model list: is it up?")
    known = entry.get("voices") or []
    missing = [voice for voice in args.voice if voice not in known]
    if missing:
        raise SystemExit(
            f"the service has no voice {', '.join(missing)}, only:"
            f" {', '.join(known) or 'none'}. A voice is <name>.wav or <name>.mp3,"
            " and <name>.txt, in tts/omnivoice_server/voices/"
            ' (../tts/README.md, "Voice")'
        )
    args.out.mkdir(parents=True, exist_ok=True)
    for voice in args.voice:
        try:
            data = service.synthesize(text, args.language, voice)
        except speech.SpeechError as exc:
            raise SystemExit(f"{voice}: {exc}") from exc
        path = args.out / f"{args.language}-{voice}.mp3"
        path.write_bytes(data)
        print(path)
    print(f"Each file says {text!r}, and each in another voice.")


if __name__ == "__main__":
    main()
