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
       docker-compose.yml sets http://voice:8002, the omnivoice service of
       this repo. With no address, the page has no buttons.
    2. TLHELPER_VOICE_MODEL, if set, names the model. Default: the first
       model in the list of the service.
    3. TLHELPER_VOICE_API_KEY, if set, goes in the Authorization header. The
       omnivoice service wants none.
    4. TLHELPER_VOICE_TIMEOUT (default 180) is the most seconds for one
       request. A CPU reads a long text slowly.

ElevenLabs (elevenlabs.py), a paid service
    POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id} returns the
    sound. The text of the user goes to ElevenLabs.
    1. Set TLHELPER_VOICE_BACKEND to "elevenlabs".
    2. Set TLHELPER_VOICE_API_KEY to the key, as a secret.
    3. Set TLHELPER_VOICE_ID to the id of a voice of the account. With no
       key or no id, the page has no buttons.
    4. TLHELPER_VOICE_MODEL, if set, names the model. Default:
       eleven_multilingual_v2.

Amazon Polly (polly.py), a paid service
    botocore sends one SynthesizeSpeech call. The text of the user goes to
    AWS. Polly has no Croatian voice, so the page has buttons for German,
    French, Italian and English only.
    1. Set TLHELPER_VOICE_BACKEND to "polly".
    2. Set AWS_REGION. With no region or no credentials, the page has no
       buttons.
    3. Give botocore the credentials: a role, or AWS_ACCESS_KEY_ID and
       AWS_SECRET_ACCESS_KEY as secrets.
    4. TLHELPER_VOICE_MODEL, if set, names the engine. Default: neural.

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
from .elevenlabs import ElevenLabsSpeech
from .openai import OpenAISpeech
from .polly import PollySpeech

__all__ = ["SYNTHESIZERS", "SpeechError", "Synthesizer", "current"]

SYNTHESIZERS: dict[str, Synthesizer] = {
    each.name: each for each in (OpenAISpeech(), ElevenLabsSpeech(), PollySpeech())
}
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
