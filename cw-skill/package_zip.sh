#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_NAME="${1:-cw-skill.zip}"
OUTPUT_PATH="$ROOT_DIR/$PACKAGE_NAME"

if [ -f "$OUTPUT_PATH" ]; then
  rm -f "$OUTPUT_PATH"
fi

cd "$ROOT_DIR"
zip -r "$OUTPUT_PATH" . \
  -x "*.git*" \
  -x "*/__pycache__/*" \
  -x "*/__pycache__/" \
  -x "*.pyc" \
  -x "*.pyo" \
  -x "*.DS_Store" \
  -x "set_env.private.sh"

echo "Created: $OUTPUT_PATH"
