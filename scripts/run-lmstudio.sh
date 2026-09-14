#!/usr/bin/env bash
# LM Studio (or any OpenAI-compatible /v1 server). Start the server first.
set -euo pipefail
cd "$(dirname "$0")/.."
export MARKMAP_DESK_MODEL=mlx
export MARKMAP_DISABLE_BEDROCK=1
export MARKMAP_MLX_BASE_URL="${MARKMAP_MLX_BASE_URL:-http://127.0.0.1:1234/v1}"
export MARKMAP_MLX_MODEL="${MARKMAP_MLX_MODEL:-llama-3.2-3b-instruct}"
echo "LM Studio: $MARKMAP_MLX_BASE_URL  model=$MARKMAP_MLX_MODEL"
exec "${VIRTUAL_ENV:-.venv}/bin/python" -m markmap
