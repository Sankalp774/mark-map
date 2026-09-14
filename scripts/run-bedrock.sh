#!/usr/bin/env bash
# Amazon Bedrock Converse. Only when authorizationStatus is AUTHORIZED.
set -euo pipefail
cd "$(dirname "$0")/.."
export MARKMAP_DESK_MODEL=bedrock
export MARKMAP_DISABLE_BEDROCK=0
export AWS_REGION="${AWS_REGION:-us-west-2}"
export BEDROCK_MODEL_ID="${BEDROCK_MODEL_ID:-us.anthropic.claude-sonnet-4-6}"
echo "Bedrock: region=$AWS_REGION  model=$BEDROCK_MODEL_ID  profile=${AWS_PROFILE:-default}"
exec "${VIRTUAL_ENV:-.venv}/bin/python" -m markmap
