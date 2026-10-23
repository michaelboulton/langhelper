# Build from the repository root, which holds the uv workspace:
#   docker build -f web/Dockerfile -t langhelper-web .
#
# Stage 1: the pinned dependencies of web/ only, out of the uv.lock of the
# workspace (README.md, "The image").
FROM python:3.12-slim AS lock

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

WORKDIR /src
# uv reads the pyproject.toml of each workspace member.
COPY pyproject.toml uv.lock ./
COPY web/pyproject.toml web/
COPY tts/pyproject.toml tts/
COPY tools/pyproject.toml tools/
RUN uv export --quiet --frozen --no-dev --package langhelper-web --no-emit-workspace \
    --format pylock.toml -o /pylock.toml

# Stage 2: the server.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first, so a change to tlhelper/ or static/ does not reinstall
# torch. The layer changes only when pylock.toml changes.
COPY --from=lock /pylock.toml /app/
RUN uv venv --quiet /app/.venv \
    && UV_COMPILE_BYTECODE=1 uv pip sync --quiet --python /app/.venv --no-cache /app/pylock.toml

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
