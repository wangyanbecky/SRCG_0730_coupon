---
name: aws-remote-deploy
description: Create AWS deployment workflows for software projects that are developed in a local IDE and deployed to remote AWS infrastructure. Use when Codex needs to generate CloudFormation-first infrastructure templates, AWS CLI shell fallbacks with matching cleanup scripts, ALB-fronted remote service calls with API token validation, deployment documentation from environment bootstrap through smoke tests, local client-only test automation with virtual environments, and zip packaging scripts.
---

# AWS Remote Deploy

## Overview

Use this skill to produce project-specific AWS deployment assets under the assumption that developers work locally in an IDE while all runtime infrastructure lives in AWS. Treat every generated deployment script, test script, and document as part of that operating model.

## Required Assumptions

- Local machine: source editing, client-only tests, packaging, and deployment command execution.
- Remote AWS: compute, networking, load balancing, secrets, logs, and service runtime.
- Deployment priority: CloudFormation template first; AWS CLI shell only when CloudFormation is impractical or explicitly requested.
- Remote service ingress: all public service calls enter through an ALB and require API token validation.
- Local tests: run client-side tests only, inside a virtual environment; do not start local copies of remote services unless the user explicitly asks.

## Workflow

1. Inspect the project before generating assets:
   - Identify language, build command, client entry point, server entry point, health endpoint, container requirements, and existing infra conventions.
   - Prefer existing package managers and test runners.
   - If the remote service cannot be inferred, generate explicit TODO markers only where project-specific values are genuinely unknown.

2. Generate the remote environment bootstrap:
   - Prefer `infra/cloudformation/*.yaml`.
   - Include parameters for environment name, AWS region, service image/artifact, health path, listener port, and API token secret source.
   - Include ALB, target group, listener/listener rule, security groups, logs, IAM roles, and service runtime resources appropriate to the project.
   - Use AWS CLI shell only as a fallback; when generating an AWS CLI deployment shell script, also generate a matching cleanup shell script that removes every resource it creates.

3. Enforce remote API token checks:
   - Use an ALB-supported HTTP-header gate for the API token, normally `X-API-Token`.
   - Add server-side token validation as the authoritative check. ALB header rules are a first gate, not a substitute for application validation.
   - Generate client code/config that sends the token for remote calls.
   - Generate functional checks for no token, wrong token, and valid token.

4. Generate local automation:
   - `scripts/local_client_test.sh`: create/reuse a virtual environment and run only client tests.
   - `scripts/package_zip.sh`: produce a deployable zip from source while excluding local caches, virtual environments, build artifacts, logs, secrets, and VCS internals.
   - Keep scripts idempotent where possible and print clear timestamped progress logs.

5. Generate deployment documentation:
   - Start with prerequisites and AWS identity/region checks.
   - Cover environment bootstrap, build/package, deploy, token configuration, smoke tests, logs, rollback/cleanup, and expected outputs.
   - Minimize manual user intervention; provide copy-paste commands and make scripts log each major step.
   - Include final basic tests from deployment success through ALB health and token-protected API calls.

## Required Outputs

Generate these files unless the target project already has equivalent assets:

- `infra/cloudformation/<env>-remote.yaml`: CloudFormation template for remote AWS infrastructure.
- `scripts/deploy_cf.sh`: CloudFormation validate/package/deploy flow with clear logs.
- `scripts/deploy_cli.sh`: AWS CLI fallback only when needed.
- `scripts/cleanup_cli.sh`: required whenever `deploy_cli.sh` exists.
- `scripts/check_remote_token.sh`: ALB/client/server token validation smoke checks.
- `scripts/local_client_test.sh`: local virtualenv-based client-only test runner.
- `scripts/package_zip.sh`: zip packaging script.
- `docs/deploy_aws.md`: end-to-end deployment and basic test guide.

Use `scripts/scaffold_aws_remote_deploy.sh <target-project>` from this skill to create a baseline script/doc layout when starting from a project with no deployment assets.

## CloudFormation Rules

- Prefer CloudFormation for repeatable remote environment creation.
- Use parameters instead of hard-coded account, region, image, domain, and token values.
- Put secrets in Secrets Manager or SSM Parameter Store; do not write plaintext tokens into generated docs, committed files, or zip bundles.
- Output ALB DNS name, service endpoint, log group names, and smoke-test command hints.
- Add stack tags for project, environment, owner, and managed-by.

## AWS CLI Fallback Rules

Generate AWS CLI shell deployment only when CloudFormation is not enough for the specific project or user asks for it. The shell flow must:

- Use `set -euo pipefail`.
- Print timestamped logs for every major step.
- Check AWS identity and region before creating resources.
- Track created resource IDs in a local state file.
- Generate a paired cleanup script that reads the state file and deletes resources in reverse dependency order.
- Avoid destructive cleanup unless the environment name, region, and state file are explicit.

## Token Validation Rules

Remote API token validation must be verified from both sides:

- Client check: prove the generated client includes the token header for remote calls.
- ALB check: `curl` without token and with wrong token must be rejected before normal success.
- Server check: valid token succeeds, and server-side middleware/handler rejects a wrong token even if a request reaches the service.
- Logs: document where to inspect ALB access logs, service logs, or application logs for token rejection evidence.

Use exact header matching at ALB only as a first gate. If a secure design cannot safely put token material in an ALB listener rule, use an ALB header-presence gate plus server-side validation, and state that tradeoff clearly in `docs/deploy_aws.md`.

## Local Test Rules

- Run local tests only for client behavior, packaging, and request construction.
- Always create/use a virtual environment for Python test tooling when Python is involved.
- Do not require AWS credentials for local client tests unless testing signed AWS SDK client behavior.
- Keep networked remote smoke tests in `scripts/check_remote_token.sh`, separate from local tests.

## References

- Read `references/deployment-standards.md` for the full output checklist, security requirements, and acceptance criteria.
- Read `references/cloudformation-patterns.md` when generating CloudFormation resources or deciding whether AWS CLI fallback is justified.
