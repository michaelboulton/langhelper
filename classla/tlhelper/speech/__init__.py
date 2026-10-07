"""The "Listen" buttons: a voice service reads a text aloud, and the page
plays the mp3.

The page sends the text and its language code to GET /api/v1/speech/audio
(routes.py), and the browser keeps the answer (README.md, "Listen"). The server sends them to the synthesizer that the variable
TLHELPER_VOICE_BACKEND names (default "openai") and returns the mp3 as it is.
The text of the user goes to that service, so the page makes a request only on
a click. GET /api/v1/speech says whether there is a service, and which of the
languages of the app it reads: the page shows a button only for those.

The speech API of OpenAI (openai.py), the default synthesizer
    GET /v1/models lists the models, and POST /v1/audio/speech returns the
    sound. A model entry with a `languages` list (the omnivoice service in
    this repo) limits the buttons to those languages. An entry with no list
    is taken to read every language.
    1. Set TLHELPER_VOICE_URL to the address of the service, with no path:
       docker-compose.yml sets http://10.89.231.11:8002, the omnivoice
       service of this repo. With no address, the page has no buttons.
    2. TLHELPER_VOICE_MODEL, if set, names the model. Default: the first
       model in the list of the service.
    3. TLHELPER_VOICE_API_KEY, if set, goes in the Authorization header. The
       omnivoice service wants none.
    4. TLHELPER_VOICE_TIMEOUT (default 180) is the most seconds for one
       request. A CPU reads a long text slowly.

To add a synthesizer
    1. Write a module here with a class that fits base.Synthesizer.
    2. Raise base.SpeechError for every failure, with a message that the
       page can show.
    3. Read the address and the credentials from the environment at each
       call, and not at the import of the module.
    4. Add an instance to SYNTHESIZERS below, and the set-up to this
       docstring.
"""

import os

from .base import SpeechError, Synthesizer
from .openai import OpenAISpeech

__all__ = ["SYNTHESIZERS", "SpeechError", "Synthesizer", "current"]

SYNTHESIZERS: dict[str, Synthesizer] = {each.name: each for each in (OpenAISpeech(),)}
DEFAULT = "openai"


def current() -> Synthesizer:
    """The synthesizer that TLHELPER_VOICE_BACKEND names."""
    name = os.environ.get("TLHELPER_VOICE_BACKEND", DEFAULT)
    if name not in SYNTHESIZERS:
        known = ", ".join(sorted(SYNTHESIZERS))
        raise SpeechError(
            f"TLHELPER_VOICE_BACKEND is {name!r}, and must be one of: {known}"
        )
    return SYNTHESIZERS[name]
