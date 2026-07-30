#!/usr/bin/env bash
set -euo pipefail

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { printf '[%s] ERROR: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; exit 1; }

TARGET_DIR="${1:-}"
PROJECT_NAME="${PROJECT_NAME:-app}"
ENV_NAME="${ENV_NAME:-dev}"

[[ -n "$TARGET_DIR" ]] || die "Usage: $0 <target-project-dir>"
mkdir -p "$TARGET_DIR/scripts" "$TARGET_DIR/docs" "$TARGET_DIR/infra/cloudformation" "$TARGET_DIR/dist"

planned_files=(
  "$TARGET_DIR/scripts/local_client_test.sh"
  "$TARGET_DIR/scripts/package_zip.sh"
  "$TARGET_DIR/scripts/check_remote_token.sh"
  "$TARGET_DIR/scripts/deploy_cf.sh"
  "$TARGET_DIR/scripts/deploy_cli.sh"
  "$TARGET_DIR/scripts/cleanup_cli.sh"
  "$TARGET_DIR/infra/cloudformation/${ENV_NAME}-remote.yaml"
  "$TARGET_DIR/docs/deploy_aws.md"
)

if [[ "${FORCE:-0}" != "1" ]]; then
  for path in "${planned_files[@]}"; do
    [[ ! -e "$path" ]] || die "Refusing to overwrite existing file: $path (set FORCE=1 to overwrite)"
  done
fi

log "Scaffolding AWS remote deployment assets in $TARGET_DIR"

cat > "$TARGET_DIR/scripts/local_client_test.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { printf '[%s] ERROR: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

VENV_DIR="${VENV_DIR:-.venv-client-test}"
TEST_PATH="${TEST_PATH:-tests/client}"

need python3
log "Preparing client test virtual environment: $VENV_DIR"
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip >/dev/null

if [[ -f requirements-client-test.txt ]]; then
  log "Installing requirements-client-test.txt"
  python -m pip install -r requirements-client-test.txt
elif [[ -f requirements-dev.txt ]]; then
  log "Installing requirements-dev.txt"
  python -m pip install -r requirements-dev.txt
elif [[ -f pyproject.toml ]]; then
  log "Installing project with test extras when available"
  python -m pip install -e ".[test]" || python -m pip install -e .
else
  log "Installing pytest only"
  python -m pip install pytest
fi

if [[ -d "$TEST_PATH" ]]; then
  log "Running client-only tests from $TEST_PATH"
  python -m pytest "$TEST_PATH"
else
  log "No $TEST_PATH directory found; running lightweight token-header construction check"
  python - <<'PY'
import os
header = os.environ.get("TOKEN_HEADER", "X-API-Token")
token = os.environ.get("API_TOKEN", "dummy-token")
request_headers = {header: token}
assert request_headers.get(header) == token
print("client token header construction ok")
PY
fi
EOF

cat > "$TARGET_DIR/scripts/package_zip.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { printf '[%s] ERROR: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

PROJECT_NAME="${PROJECT_NAME:-$(basename "$PWD")}"
OUT_DIR="${OUT_DIR:-dist}"
STAMP="$(date '+%Y%m%d-%H%M%S')"
ARCHIVE="$OUT_DIR/${PROJECT_NAME}-${STAMP}.zip"

need zip
mkdir -p "$OUT_DIR"
log "Creating package: $ARCHIVE"
zip -r "$ARCHIVE" . \
  -x ".git/*" \
  -x ".venv/*" \
  -x ".venv-*/*" \
  -x "__pycache__/*" \
  -x "node_modules/*" \
  -x "dist/*" \
  -x "build/*" \
  -x "*.log" \
  -x ".env" \
  -x ".env.*" \
  -x "*.pem" \
  -x "*.key" \
  -x ".aws-remote-deploy/*"
log "Package ready: $ARCHIVE"
ls -lh "$ARCHIVE"
EOF

cat > "$TARGET_DIR/scripts/check_remote_token.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { printf '[%s] ERROR: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

BASE_URL="${BASE_URL:-}"
API_TOKEN="${API_TOKEN:-}"
TOKEN_HEADER="${TOKEN_HEADER:-X-API-Token}"
HEALTH_PATH="${HEALTH_PATH:-/health}"

[[ -n "$BASE_URL" ]] || die "Set BASE_URL, for example https://example-alb.amazonaws.com"
[[ -n "$API_TOKEN" ]] || die "Set API_TOKEN"
need curl

url="${BASE_URL%/}${HEALTH_PATH}"
log "Checking no-token request is rejected"
code="$(curl -sS -o /tmp/aws-token-no-token.out -w '%{http_code}' "$url" || true)"
[[ "$code" == "401" || "$code" == "403" ]] || die "Expected no-token request to fail with 401/403, got $code"

log "Checking wrong-token request is rejected"
code="$(curl -sS -o /tmp/aws-token-wrong-token.out -w '%{http_code}' -H "$TOKEN_HEADER: wrong-token" "$url" || true)"
[[ "$code" == "401" || "$code" == "403" ]] || die "Expected wrong-token request to fail with 401/403, got $code"

log "Checking valid-token request succeeds"
code="$(curl -sS -o /tmp/aws-token-valid-token.out -w '%{http_code}' -H "$TOKEN_HEADER: $API_TOKEN" "$url")"
[[ "$code" =~ ^2[0-9][0-9]$ ]] || die "Expected valid-token request to succeed with 2xx, got $code"
log "Remote token validation checks passed"
EOF

cat > "$TARGET_DIR/scripts/deploy_cf.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { printf '[%s] ERROR: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

PROJECT_NAME="${PROJECT_NAME:-app}"
ENV_NAME="${ENV_NAME:-dev}"
AWS_REGION="${AWS_REGION:-}"
STACK_NAME="${STACK_NAME:-$PROJECT_NAME-$ENV_NAME-remote}"
TEMPLATE_FILE="${TEMPLATE_FILE:-infra/cloudformation/${ENV_NAME}-remote.yaml}"

[[ -n "$AWS_REGION" ]] || die "Set AWS_REGION"
[[ -f "$TEMPLATE_FILE" ]] || die "Missing template: $TEMPLATE_FILE"
need aws

log "Checking AWS identity"
aws sts get-caller-identity >/dev/null
log "Validating CloudFormation template: $TEMPLATE_FILE"
aws cloudformation validate-template --region "$AWS_REGION" --template-body "file://$TEMPLATE_FILE" >/dev/null
log "Deploying stack: $STACK_NAME"
aws cloudformation deploy \
  --region "$AWS_REGION" \
  --stack-name "$STACK_NAME" \
  --template-file "$TEMPLATE_FILE" \
  --capabilities CAPABILITY_NAMED_IAM \
  --tags Project="$PROJECT_NAME" Environment="$ENV_NAME" ManagedBy="codex-aws-remote-deploy"
log "Stack outputs"
aws cloudformation describe-stacks \
  --region "$AWS_REGION" \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs' \
  --output table
EOF

cat > "$TARGET_DIR/scripts/deploy_cli.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { printf '[%s] ERROR: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

PROJECT_NAME="${PROJECT_NAME:-app}"
ENV_NAME="${ENV_NAME:-dev}"
AWS_REGION="${AWS_REGION:-}"
STATE_DIR="${STATE_DIR:-.aws-remote-deploy}"
STATE_FILE="$STATE_DIR/${ENV_NAME}.state"

[[ -n "$AWS_REGION" ]] || die "Set AWS_REGION"
need aws
mkdir -p "$STATE_DIR"
touch "$STATE_FILE"

log "Checking AWS identity"
aws sts get-caller-identity >/dev/null
log "AWS CLI fallback scaffold is intentionally minimal"
log "Add project-specific aws create-* commands here and append resource IDs to $STATE_FILE immediately after creation"
EOF

cat > "$TARGET_DIR/scripts/cleanup_cli.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { printf '[%s] ERROR: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

ENV_NAME="${ENV_NAME:-}"
AWS_REGION="${AWS_REGION:-}"
STATE_DIR="${STATE_DIR:-.aws-remote-deploy}"
STATE_FILE="$STATE_DIR/${ENV_NAME}.state"

[[ -n "$ENV_NAME" ]] || die "Set ENV_NAME explicitly before cleanup"
[[ -n "$AWS_REGION" ]] || die "Set AWS_REGION explicitly before cleanup"
[[ -f "$STATE_FILE" ]] || die "Missing state file: $STATE_FILE"
need aws

log "Checking AWS identity"
aws sts get-caller-identity >/dev/null
log "Cleanup scaffold reading $STATE_FILE"
log "Add project-specific aws delete-* commands in reverse dependency order"
EOF

cat > "$TARGET_DIR/infra/cloudformation/${ENV_NAME}-remote.yaml" <<'EOF'
AWSTemplateFormatVersion: "2010-09-09"
Description: Remote AWS environment scaffold for local-IDE development workflow.

Parameters:
  EnvironmentName:
    Type: String
    Default: dev
  ApiTokenSecretArn:
    Type: String
    Description: Secrets Manager or SSM reference used by the service for server-side token validation.
  HealthPath:
    Type: String
    Default: /health

Resources:
  PlaceholderLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub /aws/remote/${EnvironmentName}/app
      RetentionInDays: 14

Outputs:
  LogGroupName:
    Value: !Ref PlaceholderLogGroup
  NextStep:
    Value: Replace this scaffold with ALB, target group, listener rules, service runtime, IAM, and security groups for the project.
EOF

cat > "$TARGET_DIR/docs/deploy_aws.md" <<'EOF'
# AWS Deployment

This project uses a local IDE plus remote AWS infrastructure deployment model.

## Prerequisites

- AWS CLI configured for the target account.
- Required AWS region exported as `AWS_REGION`.
- API token stored outside the repository, preferably in Secrets Manager or SSM Parameter Store.

## Local Client Tests

```bash
./scripts/local_client_test.sh
```

## Package

```bash
./scripts/package_zip.sh
```

## Remote Environment

Prefer CloudFormation:

```bash
PROJECT_NAME=app ENV_NAME=dev AWS_REGION=us-east-1 ./scripts/deploy_cf.sh
```

Use `scripts/deploy_cli.sh` only for project-specific operations that cannot be represented cleanly in CloudFormation. If used, cleanup must be tested with:

```bash
ENV_NAME=dev AWS_REGION=us-east-1 ./scripts/cleanup_cli.sh
```

## Token Smoke Test

```bash
BASE_URL=https://your-alb-dns-name API_TOKEN=redacted ./scripts/check_remote_token.sh
```

Expected checks:

- Missing token is rejected.
- Wrong token is rejected.
- Valid token succeeds.

## Logs

Inspect CloudWatch service logs and ALB access logs for request routing and token rejection evidence.
EOF

chmod +x "$TARGET_DIR"/scripts/*.sh
log "Scaffold complete"
