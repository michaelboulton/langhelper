"""The heavy Croatian models: classla, a fork of Stanza. One pipeline needs
about 2.3 GB, mostly the lemma dictionary, and loads in about 30 seconds."""

import logging
import os

import classla

from ...settings import DATA_ROOT
from ..base import STUDY, ModelsMissing
from . import grammar

# clarin.si is the only public host and its speed varies a lot. Point this at a
# mirror that serves the same paths (<MODEL_URL>/11356/1829/...zip) if needed.
MODEL_URL = os.environ.get("MODEL_URL", "default")
# Set to 0 to never download: classify then returns 503 if the models are not
# already under DATA_ROOT. docker-compose.yml does this for local runs.
DOWNLOAD_MODELS = os.environ.get("DOWNLOAD_MODELS", "1").lower() not in (
    "0",
    "false",
    "no",
)
MODEL_DIR = DATA_ROOT / "classla_resources"

LANG = "hr"
PROCESSORS = "tokenize,pos,lemma"
# The model type of the app: the type of classla.
TYPES = {"heavy": "standard", "nonstandard": "nonstandard"}

logger = logging.getLogger("uvicorn.error")


def get_pipeline(model_type: str) -> classla.Pipeline:
    """model_type: a type of classla. The first use downloads the models from
    clarin.si, which can take minutes."""
    try:
        # Models that are already on disk load with no network access.
        # download() always fetches resources.json from GitHub first.
        return load_pipeline(model_type)
    except Exception as exc:
        if not DOWNLOAD_MODELS:
            raise ModelsMissing(
                f"The {model_type} models did not load from {MODEL_DIR}"
                f" and DOWNLOAD_MODELS is off: {exc!r}"
            ) from exc
        logger.warning(
            "the %s models did not load from %s (%r), downloading",
            model_type,
            MODEL_DIR,
            exc,
        )
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        # download() replaces a file only when its hash is wrong.
        classla.download(
            LANG,
            type=model_type,
            processors=PROCESSORS,
            dir=str(MODEL_DIR),
            model_url=MODEL_URL,
        )
        return load_pipeline(model_type)


def load_pipeline(model_type: str) -> classla.Pipeline:
    return classla.Pipeline(
        LANG,
        type=model_type,
        processors=PROCESSORS,
        dir=str(MODEL_DIR),
        use_gpu=False,
    )


def parse_feats(feats: str | None) -> dict[str, str]:
    """Turn 'Case=Nom|Gender=Fem' into {'Case': 'Nom', 'Gender': 'Fem'}."""
    if not feats or feats == "_":
        return {}
    return dict(pair.split("=", 1) for pair in feats.split("|") if "=" in pair)


def lexicon(pipeline) -> grammar.Lexicon | None:
    """The word forms that the lemma model knows: 1.7 million forms from the
    hrLex lexicon, plain and with their tags. The models already hold them in
    memory. This reads a private attribute of classla, so it can be missing."""
    try:
        trainer = pipeline.processors["lemma"]._trainer
        return grammar.Lexicon(trainer.word_dict, trainer.composite_dict)
    except (AttributeError, KeyError, TypeError):
        return None


def char_span(word) -> tuple[int | None, int | None]:
    token = word.parent
    return (
        getattr(token, "start_char", None),
        getattr(token, "end_char", None),
    )


def words(text: str, variant: str, check: bool) -> list[dict]:
    """variant: "heavy" or "nonstandard"."""
    model_type = TYPES[variant]
    with STUDY.use((LANG, variant), lambda: get_pipeline(model_type)) as pipeline:
        doc = pipeline(text)
        known = lexicon(pipeline) if check else None
    sentences = []
    for sentence in doc.sentences:
        found = []
        for word in sentence.words:
            start, end = char_span(word)
            found.append(
                {
                    "id": word.id,
                    "text": word.text,
                    "lemma": word.lemma or word.text,
                    "upos": word.upos,
                    "xpos": word.xpos,
                    "feats": parse_feats(word.feats),
                    "start_char": start,
                    "end_char": end,
                }
            )
        if check:
            grammar.check(found, known)
        sentences.append({"text": sentence.text, "words": found})
    return sentences
