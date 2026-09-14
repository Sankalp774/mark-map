#!/usr/bin/env bash
# Demo / tests: Strands tools, no LLM wait.
set -euo pipefail
cd "$(dirname "$0")/.."
export MARKMAP_DESK_MODEL=scripted
export MARKMAP_DISABLE_BEDROCK=1
exec "${VIRTUAL_ENV:-.venv}/bin/python" -m markmap
