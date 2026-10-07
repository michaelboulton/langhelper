# Build from the repository root, which holds the uv workspace:
#   podman build -f web/Dockerfile -t langhelper-web .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first, so a change to tlhelper/ or static/ does not reinstall
# torch. The root pyproject.toml pins torch to the CPU-only wheel index. uv
# reads the pyproject.toml of each workspace member, so tts/ needs its file too.
COPY pyproject.toml uv.lock /app/
COPY web/pyproject.toml /app/web/
COPY tts/pyproject.toml /app/tts/
RUN UV_COMPILE_BYTECODE=1 uv sync --frozen --no-dev --package langhelper-web --no-install-workspace --no-cache

# The flashcard decks of the image. More decks can go in /data/decks.
COPY web/decks/ /app/decks/
COPY web/entrypoint.sh /app/
# With the data files of the languages (accents.db, glosses.db).
COPY web/tlhelper/ /app/tlhelper/
COPY web/static/ /app/static/
RUN chmod +x /app/entrypoint.sh

# Non-root. Fly mounts the volume with the uid/gid of USER, so /data is writable.
RUN useradd --create-home --uid 1000 web \
    && mkdir -p /data && chown web:web /data
USER web

ENV HOME=/home/web \
    PATH=/app/.venv/bin:$PATH \
    DATA_ROOT=/data \
    STATIC_DIR=/app/static \
    PORT=8000

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
