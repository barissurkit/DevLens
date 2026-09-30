#!/usr/bin/env bash
# Compares the commit served by the production frontend with the head of main.
# A mismatch several minutes after a merge means Render served a stale build:
# use Manual Deploy -> "Clear build cache & deploy" on the frontend service.
set -euo pipefail
FRONTEND_URL="${FRONTEND_URL:-https://devlens.barissurkit.com}"
expected="$(git rev-parse "${1:-origin/main}")"
served="$(curl -fsS "$FRONTEND_URL/version" | python -c 'import json,sys; print(json.load(sys.stdin)["commit"])')"
echo "expected: $expected"
echo "served:   $served"
if [ "$expected" = "$served" ]; then echo "OK: production serves the expected commit."; else echo "MISMATCH: production is not on the expected commit." >&2; exit 1; fi
