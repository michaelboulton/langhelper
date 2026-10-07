#!/bin/sh
# Make sure that $DATA_ROOT (a persistent volume) is writable, then exec the
# web server as the single foreground process.
#
# The volume holds the classla models and the lemma-count database. The app
# downloads any missing models at startup, so the first boot on an empty volume
# is slow and later boots only load the models from disk.
set -eu

: "${DATA_ROOT:=/data}"
: "${PORT:=8000}"
export DATA_ROOT

mkdir -p "$DATA_ROOT"
if [ ! -w "$DATA_ROOT" ]; then
    echo "ERROR: $DATA_ROOT is not writable by $(id -un); models and lemma counts could not be persisted." >&2
    exit 1
fi

# A podman or docker secret arrives as a file, not as a variable. A variable
# that is already set (a Fly secret) wins.
: "${DEEPL_API_KEY_FILE:=/run/secrets/deepl_api_key}"
if [ -z "${DEEPL_API_KEY:-}" ] && [ -r "$DEEPL_API_KEY_FILE" ]; then
    DEEPL_API_KEY=$(cat "$DEEPL_API_KEY_FILE")
    export DEEPL_API_KEY
fi
: "${TLHELPER_AI_API_KEY_FILE:=/run/secrets/tlhelper_ai_api_key}"
if [ -z "${TLHELPER_AI_API_KEY:-}" ] && [ -r "$TLHELPER_AI_API_KEY_FILE" ]; then
    TLHELPER_AI_API_KEY=$(cat "$TLHELPER_AI_API_KEY_FILE")
    export TLHELPER_AI_API_KEY
fi

cd /app
# --no-access-log: tlhelper/app.py writes its own access line, which has the
# latency.
exec uvicorn tlhelper.app:app --host 0.0.0.0 --port "$PORT" --no-access-log
