#!/usr/bin/env bash
# Built-in Strands desk model (no external LLM).
set -euo pipefail
cd "$(dirname "$0")/.."
export MARKMAP_DESK_MODEL=desk
export MARKMAP_DISABLE_BEDROCK=1
exec "${VIRTUAL_ENV:-.venv}/bin/python" -m markmap
