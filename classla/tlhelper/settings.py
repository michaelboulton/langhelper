"""The configuration that more than one module reads."""

import os
from pathlib import Path

# Everything that must survive a restart lives here (a Fly volume).
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data"))
# The most characters of a text that a user sends for a breakdown.
MAX_TEXT_CHARS = int(os.environ.get("MAX_TEXT_CHARS", "1000"))
