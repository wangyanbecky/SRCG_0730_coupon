---
name: software-release-packager
description: Prepare clean software release packages and GitHub releases. Use when Codex needs to decide whether a version is ready to package, verify requirements/design/tasks/code/deployment/README consistency, isolate release work in a new subdirectory, remove development environment variables and sensitive information, audit development test scripts and cases, create local tar.gz artifacts, or publish an existing user-approved release to a pre-created GitHub repository using authenticated GitHub token/gh login.
---

# Software Release Packager

## Overview

Use this skill to perform user-triggered software version packaging without disturbing the active development environment. Release work must happen in a fresh staging subdirectory, pass consistency and sensitive-data checks, produce a local `tar.gz`, and only publish to GitHub when the user explicitly asks for remote publication.

## Release Decision

Package only when the release point is defensible:

- Requirements, design, task records, code, deployment docs, and `README.md` describe the same behavior and version scope.
- The codebase has no unresolved release-blocking TODO/FIXME markers in release-critical files.
- Development-only environment variables, local credentials, sample secrets, `.env` files, virtual environments, caches, logs, and build outputs are excluded.
- Tests and scripts relevant to release quality are identified and run, or skipped only with a documented reason.
- The user has explicitly requested packaging now. Do not package merely because checks passed.

Read `references/release-readiness.md` before deciding whether to package or when a consistency check needs detail.

## Workflow

1. Inspect the project:
   - Identify language, package manager, version source, build command, test command, deployment files, `README.md`, requirements, design docs, and task records.
   - Check current git status. Never revert unrelated changes.
   - Confirm whether the user wants local-only packaging or GitHub publication.

2. Validate release readiness:
   - Compare requirements, design, tasks, code behavior, deployment docs, and `README.md`.
   - Run relevant tests and lint/build commands from the project. If unavailable, document the gap.
   - Inspect development scripts and test cases for local-only paths, hostnames, tokens, hard-coded accounts, generated files, and environment-variable leakage.

3. Stage in a new subdirectory:
   - Use `scripts/package_release.sh` or create an equivalent process under a fresh release workspace such as `.release-work/<project>-<version>-<timestamp>/`.
   - Copy only releaseable source and docs. Exclude `.git`, `.env*`, virtual environments, dependency caches, logs, local config, editor metadata, and generated outputs unless the project explicitly requires them.

4. Scan before packaging:
   - Fail on secret-like patterns, private keys, token assignments, AWS keys, GitHub tokens, `.env` files, and development-only config in the staged tree.
   - Produce a release report with artifact path, excluded patterns, detected docs, test commands, and any warnings.

5. Create local artifact:
   - Generate `tar.gz` from the staged subdirectory, not from the live development tree.
   - Keep the artifact under the release workspace or an explicit output directory.

6. Publish to GitHub only on explicit request:
   - Require the user to have created the GitHub repository before publication.
   - Require `gh auth status` to pass using the user's token/login. Do not ask the user to paste tokens into files.
   - Create a GitHub release for the requested tag and upload the generated `tar.gz`.
   - Do not create repositories, rotate credentials, or change GitHub authentication state unless the user explicitly asks.

## Script Usage

Use the bundled script when the target project is a normal filesystem project:

```bash
software-release-packager/scripts/package_release.sh \
  --project /path/to/project \
  --name my-project \
  --version 1.2.3 \
  --mode local
```

For GitHub publication, run only after the user confirms remote release:

```bash
software-release-packager/scripts/package_release.sh \
  --project /path/to/project \
  --name my-project \
  --version 1.2.3 \
  --mode github \
  --repo owner/repo
```

The script stages the project, scans the staged tree, writes a report, creates `tar.gz`, and optionally calls `gh release create`.

## Required Outputs

- A release readiness summary covering timing, consistency, tests, sensitive data, and packaging exclusions.
- A local `tar.gz` artifact path when packaging succeeds.
- A release report path.
- For GitHub mode, the GitHub release URL or the exact authentication/repository blocker.

## Resources

- `scripts/package_release.sh`: deterministic staging, scanning, local archive creation, and optional GitHub release upload.
- `references/release-readiness.md`: detailed release timing, consistency, sensitive information, and test/script audit checklist.
