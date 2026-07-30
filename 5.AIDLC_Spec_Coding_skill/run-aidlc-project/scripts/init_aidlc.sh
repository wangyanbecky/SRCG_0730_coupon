#!/usr/bin/env bash
set -euo pipefail

target="${1:-.}"

if [[ ! -d "$target" ]]; then
  printf 'Target directory does not exist: %s\n' "$target" >&2
  exit 1
fi

mkdir -p \
  "$target/.aidlc/plan" \
  "$target/.aidlc/requirements" \
  "$target/.aidlc/design" \
  "$target/src"

printf 'AIDLC project structure is ready at %s\n' "$(cd "$target" && pwd)"
