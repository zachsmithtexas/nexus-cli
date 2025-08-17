#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  echo ".env not found"
  exit 0
fi

if command -v dos2unix >/dev/null 2>&1; then
  dos2unix .env || true
else
  sed -i 's/\r$//' .env
fi

echo "Normalized .env line endings."

