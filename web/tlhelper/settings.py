"""The configuration that more than one module reads."""

import os
from pathlib import Path

# Everything that must survive a restart lives here (a Fly volume).
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data"))
# Set to 0 to never download the heavy models (classla, Stanza): a request
# then returns 503 if they are not already under DATA_ROOT.
DOWNLOAD_MODELS = os.environ.get("DOWNLOAD_MODELS", "1").lower() not in (
    "0",
    "false",
    "no",
)
# The most characters of a text that a user sends for a breakdown.
MAX_TEXT_CHARS = int(os.environ.get("MAX_TEXT_CHARS", "1000"))
