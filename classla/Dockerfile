FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first, so a change to tlhelper/ or static/ does not reinstall
# torch. pyproject.toml pins torch to the CPU-only wheel index.
COPY pyproject.toml uv.lock /app/
RUN UV_COMPILE_BYTECODE=1 uv sync --frozen --no-dev --no-install-project --no-cache

# The flashcard decks of the image. More decks can go in /data/decks.
COPY decks/ /app/decks/
COPY entrypoint.sh /app/
# With the data files of the languages (accents.db, glosses.db).
COPY tlhelper/ /app/tlhelper/
COPY static/ /app/static/
RUN chmod +x /app/entrypoint.sh

# Non-root. Fly mounts the volume with the uid/gid of USER, so /data is writable.
RUN useradd --create-home --uid 1000 classla \
    && mkdir -p /data && chown classla:classla /data
USER classla

ENV HOME=/home/classla \
    PATH=/app/.venv/bin:$PATH \
    DATA_ROOT=/data \
    STATIC_DIR=/app/static \
    PORT=8000

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
