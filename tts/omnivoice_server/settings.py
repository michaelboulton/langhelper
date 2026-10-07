"""The environment variables of the server, read when they are used. README.md
describes each one."""

import os
from pathlib import Path

DEFAULT_MODEL = "Serveurperso/OmniVoice-GGUF"
# Only the fixed items of the model (README.md, "Voice"), with ", " between.
DEFAULT_INSTRUCT = "female, young adult, moderate pitch"
DEFAULT_VOICES = Path(__file__).parent / "voices"


def _list(name: str, default: str) -> list[str]:
    value = os.environ.get(name, "") or default
    return [each.strip() for each in value.split(",") if each.strip()]


def models() -> list[str]:
    """The Hugging Face repos of GGUFs that the server may download and load.
    The first one is the default."""
    return _list("OMNIVOICE_MODELS", DEFAULT_MODEL)


def default_model() -> str:
    return models()[0]


def quant() -> str:
    """The variant of the GGUFs in the repo: Q8_0, Q4_K_M, BF16 or F32."""
    return os.environ.get("OMNIVOICE_QUANT", "Q8_0")


def known_languages() -> set[str]:
    """Every code that the model knows."""
    from .languages import KNOWN

    return set(KNOWN)


def languages() -> list[str]:
    """The codes that the server advertises and accepts. Default: every code
    that the model knows."""
    listed = _list("OMNIVOICE_LANGUAGES", "")
    return listed or sorted(known_languages())


def instruct() -> str:
    """The description of the voice, for a request that has none, in a
    language with no clip."""
    return os.environ.get("OMNIVOICE_INSTRUCT", DEFAULT_INSTRUCT)


def voices_dir() -> Path | None:
    """The folder of the reference clips. Empty: no clips."""
    value = os.environ.get("OMNIVOICE_VOICES", str(DEFAULT_VOICES))
    return Path(value) if value else None


def num_step() -> int:
    return int(os.environ.get("OMNIVOICE_NUM_STEP", "16"))


def cache_size() -> int:
    """How many of the last mp3s stay in memory."""
    return int(os.environ.get("OMNIVOICE_CACHE", "16"))


def preload() -> bool:
    return os.environ.get("OMNIVOICE_PRELOAD", "1") == "1"
