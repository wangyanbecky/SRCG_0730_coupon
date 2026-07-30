# AWS Remote Deployment Standards

## Purpose

Use these standards when generating deployment assets for projects built in a local IDE and deployed to remote AWS infrastructure.

## Output Checklist

Generate or update:

- `infra/cloudformation/<env>-remote.yaml`
- `scripts/deploy_cf.sh`
- `scripts/deploy_cli.sh` only when CloudFormation is insufficient
- `scripts/cleanup_cli.sh` whenever `deploy_cli.sh` exists
- `scripts/check_remote_token.sh`
- `scripts/local_client_test.sh`
- `scripts/package_zip.sh`
- `docs/deploy_aws.md`

## Script Requirements

All generated shell scripts must:

- Start with `#!/usr/bin/env bash` and `set -euo pipefail`.
- Print timestamped logs through a shared `log()` helper.
- Check required tools before use.
- Accept configuration through environment variables and documented flags.
- Fail with actionable messages.
- Avoid writing secrets to stdout.

Recommended shell helpers:

```bash
log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { printf '[%s] ERROR: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }
```

## CloudFormation Deployment

`scripts/deploy_cf.sh` should:

- Validate AWS credentials with `aws sts get-caller-identity`.
- Validate the template with `aws cloudformation validate-template`.
- Deploy with `aws cloudformation deploy`.
- Use `--capabilities CAPABILITY_NAMED_IAM` only when IAM resources require it.
- Print stack outputs after deployment.
- Never embed plaintext API tokens in command output.

## AWS CLI Fallback

Use AWS CLI resource creation only when a CloudFormation template cannot reasonably express the required action or the user explicitly asks for a shell-only path.

When creating `scripts/deploy_cli.sh`:

- Create `.aws-remote-deploy/<env>.state` or similar to track resource IDs.
- Append every created resource ID immediately after successful creation.
- Make commands idempotent when practical by checking for existing resources first.

When creating `scripts/cleanup_cli.sh`:

- Require explicit `ENV_NAME` and `AWS_REGION`.
- Require the state file to exist.
- Delete resources in reverse dependency order.
- Continue cleanup on missing resources but log each missing resource.

## ALB API Token Validation

Remote service calls must pass through ALB and use token validation.

Preferred pattern:

- Client sends `X-API-Token: <token>` on each remote API request.
- ALB listener rule gates requests by `http-header` condition on `X-API-Token` when token handling is acceptable for the environment.
- Server validates the same token from Secrets Manager, SSM Parameter Store, or runtime environment.
- Service returns `401` or `403` for absent or invalid token.

If exact ALB token matching would expose secret material in infrastructure configuration, use:

- ALB header-presence or path/host gate as the ALB-supported first gate.
- Server-side token validation as the authoritative enforcement.
- Documentation that states why exact ALB token matching was not used.

## Token Test Matrix

Generate `scripts/check_remote_token.sh` with at least:

- No token: expect `401`, `403`, or ALB fixed-response deny.
- Wrong token: expect `401`, `403`, or ALB fixed-response deny.
- Valid token: expect success from `/health` or a project-specific smoke endpoint.
- Optional server bypass test for private/internal endpoint only when safely available.

The script should accept:

- `BASE_URL`
- `API_TOKEN`
- `TOKEN_HEADER`, default `X-API-Token`
- `HEALTH_PATH`, default `/health`

## Local Client Test Automation

Generate `scripts/local_client_test.sh` to:

- Create `.venv-client-test`.
- Install test dependencies without touching system Python.
- Run only client-side tests, such as request construction, token header inclusion, config parsing, and packaging checks.
- Keep remote smoke tests out of the local test script.

For non-Python projects, the script may still use a Python virtual environment for helper assertions, but should prefer the project's native package manager if client tests already exist.

## Zip Packaging

Generate `scripts/package_zip.sh` to:

- Create `dist/<project>-<timestamp>.zip`.
- Exclude `.git`, virtual environments, caches, logs, local env files, secrets, build output that should be rebuilt, and previous archives.
- Print archive path and size.
- Avoid including `.env`, AWS credentials, token files, or state files.

## Deployment Documentation

`docs/deploy_aws.md` must cover:

- Local prerequisites.
- Required AWS permissions at a practical level.
- Environment variables.
- CloudFormation deployment path.
- AWS CLI fallback path and cleanup path if present.
- Token setup and rotation notes.
- Local client tests.
- Packaging.
- Remote smoke tests.
- Log inspection.
- Rollback and cleanup.
- Expected command outputs at key milestones.

## Acceptance Criteria

The generated assets are complete only when:

- A user can bootstrap the remote environment with CloudFormation-first commands.
- Any CLI-created resources have a matching cleanup script.
- Client and server token validation checks are represented in code or scripts.
- Documentation runs from first setup through final smoke test.
- Local client tests run in a virtual environment.
- Zip packaging excludes secrets and local-only artifacts.
