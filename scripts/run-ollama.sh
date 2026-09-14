#!/usr/bin/env bash
# Ollama (Homebrew build uses MLX on Apple silicon). ollama serve + ollama pull llama3.2 first.
set -euo pipefail
cd "$(dirname "$0")/.."
export MARKMAP_DESK_MODEL=ollama
export MARKMAP_DISABLE_BEDROCK=1
export OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
export MARKMAP_OLLAMA_MODEL="${MARKMAP_OLLAMA_MODEL:-llama3.2}"
echo "Ollama: $OLLAMA_HOST  model=$MARKMAP_OLLAMA_MODEL"
exec "${VIRTUAL_ENV:-.venv}/bin/python" -m markmap
