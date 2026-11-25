#!/usr/bin/env sh
# Sobe o experimento localmente num container Linux: http://localhost:8000
cd "$(dirname "$0")/.."
RAIZ="$(pwd -W 2>/dev/null || pwd)"
MSYS_NO_PATHCONV=1 docker run --rm -it -p 8000:8000 -v "$RAIZ:/app:ro" -w /app python:3.12-slim \
  python scripts/servidor_local.py
