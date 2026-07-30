#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  package_release.sh --project PATH --name NAME --version VERSION [--mode local|github] [--repo owner/repo] [--out-dir DIR] [--tag-prefix v]

Creates an isolated release staging directory, scans it for sensitive/development-only content,
builds a tar.gz artifact, and optionally publishes it as a GitHub release asset.

GitHub mode requires:
  - The repository already exists.
  - gh is installed.
  - gh auth status succeeds with the user's token/login.
USAGE
}

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

PROJECT=""
NAME=""
VERSION=""
MODE="local"
REPO=""
OUT_DIR=""
TAG_PREFIX="v"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project) PROJECT="${2:-}"; shift 2 ;;
    --name) NAME="${2:-}"; shift 2 ;;
    --version) VERSION="${2:-}"; shift 2 ;;
    --mode) MODE="${2:-}"; shift 2 ;;
    --repo) REPO="${2:-}"; shift 2 ;;
    --out-dir) OUT_DIR="${2:-}"; shift 2 ;;
    --tag-prefix) TAG_PREFIX="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Unknown argument: $1" ;;
  esac
done

[ -n "$PROJECT" ] || fail "--project is required"
[ -n "$NAME" ] || fail "--name is required"
[ -n "$VERSION" ] || fail "--version is required"
[ "$MODE" = "local" ] || [ "$MODE" = "github" ] || fail "--mode must be local or github"
[ -d "$PROJECT" ] || fail "Project directory does not exist: $PROJECT"

if [ "$MODE" = "github" ]; then
  [ -n "$REPO" ] || fail "--repo owner/repo is required for github mode"
  command -v gh >/dev/null 2>&1 || fail "gh CLI is required for github mode"
  gh auth status >/dev/null 2>&1 || fail "gh auth status failed; authenticate with GitHub before publishing"
  gh repo view "$REPO" >/dev/null 2>&1 || fail "GitHub repository not found or inaccessible: $REPO"
fi

PROJECT_ABS="$(cd "$PROJECT" && pwd)"
TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
SAFE_NAME="$(printf '%s' "$NAME" | tr -c 'A-Za-z0-9._-' '-')"
SAFE_VERSION="$(printf '%s' "$VERSION" | tr -c 'A-Za-z0-9._-' '-')"

if [ -z "$OUT_DIR" ]; then
  OUT_DIR="$PROJECT_ABS/.release-work"
fi

RELEASE_ROOT="$OUT_DIR/${SAFE_NAME}-${SAFE_VERSION}-${TIMESTAMP}"
STAGE_DIR="$RELEASE_ROOT/stage/${SAFE_NAME}"
ARTIFACT_DIR="$RELEASE_ROOT/artifacts"
REPORT="$RELEASE_ROOT/release-report.md"
EXCLUDES="$RELEASE_ROOT/excludes.txt"

mkdir -p "$STAGE_DIR" "$ARTIFACT_DIR"

cat > "$EXCLUDES" <<'EOF'
.git
.git/
.svn
.hg
.DS_Store
.env
.env.*
*.pem
*.key
*.p12
*.pfx
id_rsa
id_ed25519
node_modules
node_modules/
dist
build
target
.next
.turbo
.venv
venv
env
__pycache__
.pytest_cache
.mypy_cache
.ruff_cache
*.log
logs
coverage
.coverage
.release-work
EOF

log "Staging release in $RELEASE_ROOT"

if command -v rsync >/dev/null 2>&1; then
  RSYNC_ARGS=(-a)
  while IFS= read -r pattern; do
    [ -n "$pattern" ] && RSYNC_ARGS+=(--exclude "$pattern")
  done < "$EXCLUDES"
  rsync "${RSYNC_ARGS[@]}" "$PROJECT_ABS/" "$STAGE_DIR/"
else
  log "rsync not found; using tar fallback"
  tar -C "$PROJECT_ABS" \
    --exclude='.git' --exclude='.env' --exclude='.env.*' --exclude='node_modules' \
    --exclude='.venv' --exclude='venv' --exclude='env' --exclude='.release-work' \
    -cf - . | tar -C "$STAGE_DIR" -xf -
fi

log "Writing release report"
{
  printf '# Release Report\n\n'
  printf '%s\n' "- Project: \`$PROJECT_ABS\`"
  printf '%s\n' "- Name: \`$NAME\`"
  printf '%s\n' "- Version: \`$VERSION\`"
  printf '%s\n' "- Mode: \`$MODE\`"
  printf '%s\n' "- Release workspace: \`$RELEASE_ROOT\`"
  printf '%s\n\n' "- Staged source: \`$STAGE_DIR\`"
  printf '## Expected Review Before Publishing\n\n'
  printf '%s\n' '- Requirements, design, tasks, code, deployment docs, and README are consistent.'
  printf '%s\n' '- Release-relevant tests and scripts were reviewed and run or explicitly skipped.'
  printf '%s\n\n' '- Development environment variables and sensitive information are excluded or replaced.'
  printf '## Detected Documentation\n\n'
  find "$STAGE_DIR" -maxdepth 4 -type f \( \
    -iname 'readme.md' -o -iname '*requirement*' -o -iname '*design*' -o \
    -iname '*task*' -o -iname '*deploy*' -o -iname '*release*' \
  \) | sed "s#^$STAGE_DIR/#- #"
  printf '\n## Exclusion Patterns\n\n'
  sed 's/^/- `/' "$EXCLUDES" | sed 's/$/`/'
} > "$REPORT"

log "Scanning staged source for blocked files"
BLOCKED_FILES="$RELEASE_ROOT/blocked-files.txt"
find "$STAGE_DIR" -type f \( \
  -name '.env' -o -name '.env.*' -o -name '*.pem' -o -name '*.key' -o \
  -name '*.p12' -o -name '*.pfx' -o -name 'id_rsa' -o -name 'id_ed25519' \
\) > "$BLOCKED_FILES"

if [ -s "$BLOCKED_FILES" ]; then
  cat "$BLOCKED_FILES" >&2
  fail "Blocked sensitive/development files found in staged source"
fi

log "Scanning staged source for secret-like content"
SECRET_HITS="$RELEASE_ROOT/secret-hits.txt"
if command -v rg >/dev/null 2>&1; then
  rg -n --hidden --glob '!*.lock' --glob '!package-lock.json' --glob '!yarn.lock' \
    '(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]+|-----BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----|(?i)(aws_secret_access_key|secret_access_key|client_secret|api[_-]?token|auth[_-]?token|password|token|secret)\s*[:=]\s*["'\'']?[A-Za-z0-9_./+=@-]{12,})' \
    "$STAGE_DIR" > "$SECRET_HITS" || true
else
  grep -RInE 'AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]+|PRIVATE KEY|(aws_secret_access_key|secret_access_key|client_secret|api[_-]?token|auth[_-]?token|password|token|secret)[[:space:]]*[:=][[:space:]]*["'\'']?[A-Za-z0-9_./+=@-]{12,}' "$STAGE_DIR" > "$SECRET_HITS" || true
fi

if [ -s "$SECRET_HITS" ]; then
  cat "$SECRET_HITS" >&2
  fail "Secret-like content found in staged source; replace with safe placeholders before packaging"
fi

ENV_WARNINGS="$RELEASE_ROOT/environment-warnings.txt"
if command -v rg >/dev/null 2>&1; then
  rg -n --hidden --glob '!*.lock' --glob '!package-lock.json' --glob '!yarn.lock' \
    '(AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN|GH_TOKEN|CLIENT_SECRET|API[_-]?TOKEN|AUTH[_-]?TOKEN|DATABASE_URL|DB_PASSWORD|PASSWORD|SECRET)' \
    "$STAGE_DIR" > "$ENV_WARNINGS" || true
else
  grep -RInE 'AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN|GH_TOKEN|CLIENT_SECRET|API[_-]?TOKEN|AUTH[_-]?TOKEN|DATABASE_URL|DB_PASSWORD|PASSWORD|SECRET' "$STAGE_DIR" > "$ENV_WARNINGS" || true
fi

if [ -s "$ENV_WARNINGS" ]; then
  {
    printf '\n## Environment Variable Review Warnings\n\n'
    printf 'These references may be safe placeholders or documentation, but must be reviewed before publication:\n\n'
    sed 's/^/- `/' "$ENV_WARNINGS" | sed 's/$/`/'
  } >> "$REPORT"
  log "Environment variable review warnings written to $ENV_WARNINGS"
fi

ARTIFACT="$ARTIFACT_DIR/${SAFE_NAME}-${SAFE_VERSION}.tar.gz"
log "Creating artifact $ARTIFACT"
tar -C "$RELEASE_ROOT/stage" -czf "$ARTIFACT" "$SAFE_NAME"

{
  printf '\n## Artifact\n\n'
  printf '%s\n' "- Local tar.gz: \`$ARTIFACT\`"
} >> "$REPORT"

if [ "$MODE" = "github" ]; then
  TAG="${TAG_PREFIX}${VERSION}"
  log "Publishing GitHub release $TAG to $REPO"
  if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
    gh release upload "$TAG" "$ARTIFACT" --repo "$REPO" --clobber
  else
    gh release create "$TAG" "$ARTIFACT" --repo "$REPO" --title "$NAME $VERSION" --notes-file "$REPORT"
  fi
  RELEASE_URL="$(gh release view "$TAG" --repo "$REPO" --json url --jq .url)"
  printf '\n## GitHub Release\n\n- URL: `%s`\n' "$RELEASE_URL" >> "$REPORT"
  log "GitHub release: $RELEASE_URL"
fi

log "Release artifact: $ARTIFACT"
log "Release report: $REPORT"
