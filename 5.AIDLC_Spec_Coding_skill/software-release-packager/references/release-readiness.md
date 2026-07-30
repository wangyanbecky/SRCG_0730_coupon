# Release Readiness Checklist

Use this reference before creating a software release package.

## Best Timing

Prefer packaging when:

- The release scope is frozen and mapped to requirements or task records.
- Implementation, tests, deployment notes, and README updates are complete.
- CI or local equivalent tests pass.
- The target version has a clear semantic version, tag, release notes, and rollback/deployment path.
- No unrelated experimental work is mixed into the release tree.

Delay packaging when:

- Requirements or design still disagree with implemented behavior.
- Deployment instructions refer to old service names, ports, regions, images, variables, or scripts.
- Test fixtures require local secrets or developer-only files.
- The package would include `.env`, credentials, private keys, local caches, logs, virtual environments, or editor/system metadata.

## Consistency Matrix

Check each artifact category against the others:

- Requirements: user-visible behavior, API contracts, supported environments, non-goals.
- Design: architecture, data flow, dependency assumptions, security posture, operational behavior.
- Tasks: completed scope, deferred work, known limitations, acceptance criteria.
- Code: implemented behavior, version number, config defaults, feature flags, API names.
- Tests: unit/integration/e2e coverage for release scope, fixtures without secrets, deterministic setup.
- Deployment: build commands, environment variables, health checks, rollback, infrastructure names.
- README.md: install, configuration, run, test, deploy, troubleshooting, version compatibility.

Flag inconsistencies as release blockers when they change user behavior, security, deployment success, or artifact contents.

## Sensitive Information And Environment Variables

Exclude or replace:

- `.env`, `.env.*`, local config files, shell history, editor settings, generated credentials.
- AWS access keys, GitHub tokens, OAuth client secrets, API tokens, JWT signing secrets, database passwords, private keys.
- Developer-specific paths, local hostnames, personal account IDs, temporary buckets, local registry endpoints.
- Test scripts that source local secrets without a documented safe sample alternative.

Use `.env.example` or documented placeholder names instead of real values. Keep sample values obviously fake, such as `YOUR_API_TOKEN_HERE`.

## Development Script And Test Audit

Before packaging:

- Identify package-manager scripts, shell scripts, Makefile targets, CI workflows, and deployment helpers.
- Run the tests that validate the release scope, or record why a test cannot run locally.
- Inspect scripts for destructive actions, hard-coded credentials, absolute local paths, unpinned remote downloads, and environment mutation.
- Confirm generated artifacts are either rebuilt during release or intentionally excluded.

## GitHub Release Rules

- The user must create the target GitHub repository before publication.
- Use the user's existing GitHub authentication, normally `gh auth status`.
- Do not write tokens to files, logs, release notes, or config.
- Publish only when the user explicitly requests GitHub mode.
- Upload the local `tar.gz` artifact and include release notes or a generated report when appropriate.
