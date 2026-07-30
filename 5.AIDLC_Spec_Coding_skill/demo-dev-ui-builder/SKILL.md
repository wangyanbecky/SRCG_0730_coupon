---
name: demo-dev-ui-builder
description: Build or adapt a Next.js/React developer-facing demo UI for testing and debugging systems. Use when asked to scaffold, design, or extend a frontend with AWS Identity Center SSO authentication, end-to-end test input and log panes, session connection management, backend/frontend health monitoring, endpoint connection tests, data query tools, large request logs, settings pages, local file-backed configuration, and local or EC2 deployment documentation.
---

# Demo Dev UI Builder

## Workflow

Use this skill to create a pragmatic developer test console, not a marketing site. Prefer a quiet, dense, mainstream SaaS/admin style with clear navigation, fixed-width test panes, readable logs, and operational status surfaces.

1. Inspect the target repository before adding files. Preserve existing Next.js, React, styling, auth, and deployment patterns when present.
2. If the project is new or lacks a usable frontend, copy `assets/next-dev-ui-template/` into the target project and adapt names, endpoints, and package versions.
3. Read `references/ui-requirements.md` when you need detailed requirements, configuration shape, AWS Identity Center notes, or deployment expectations.
4. Read `references/sso-integration.md` before implementing AWS Identity Center SSO. Use the backend SSO broker/device authorization pattern from `Account_SSO_Demo` unless the target project already has a stronger auth standard.
5. Implement local file-backed configuration first, then connect UI controls to API routes.
6. Verify the app locally with the repository's package manager. Start the dev server and provide the URL when appropriate.

## Required Product Shape

Build three primary surfaces:

- **End-to-end testing**: Side-by-side input/control panel and log output panel. Keep a stable max width and fixed panel heights; use scrollbars for overflow. Include session connect/disconnect/reconnect, connection state, request history, and streaming/log append behavior when possible.
- **System status**: Show frontend/backend health, endpoint checks, connection tests, data query actions, recent large-request logs, latency, status codes, timestamps, and failure details.
- **Settings**: Edit main endpoints, feature toggles, polling intervals, timeouts, log limits, API token metadata, and token rotation action when a rotation endpoint exists. Persist all settings to a local config file and load dynamically at page/API runtime.

## Authentication

Use AWS Identity Center SSO through a backend SSO broker when no project auth system exists. The standard pattern is based on `Account_SSO_Demo`: a Flask/backend module registers `/sso/login`, `/sso/poll`, `/sso/logout`, and `/sso/me`; it uses boto3 `sso-oidc` Device Authorization Flow and stores authenticated user data in the server session.

The Next.js UI should not directly store SSO client secrets or access tokens. It should:

- Redirect sign-in to `/sso/login`.
- Read identity from `/api/sso/me`, which proxies to the backend `/sso/me`.
- Redirect sign-out to `/sso/logout`.
- Gate sensitive API routes by verifying the backend session before calling system endpoints.

Keep `SSO_START_URL`, `AWS_REGION`, Flask session secret, and any backend secrets in environment variables. Do not write tokens or client secrets to the local config file.

## Template Contents

The bundled template is intentionally small but complete enough to compile after dependency install:

- `app/page.tsx`: Dashboard with E2E test panel and status monitor.
- `app/settings/page.tsx`: File-backed settings editor and optional token rotation button.
- `app/api/*`: Config, health, query, test-session, token rotation, and SSO session routes.
- `lib/sso.ts`: Backend SSO session verification helper.
- `lib/config.ts`: Safe local JSON config read/write helpers.
- `docs/README.md` and `docs/DEPLOYMENT.md`: Local and EC2 deployment guidance for the generated project.
- `assets/flask-sso-broker/`: Minimal Flask backend SSO broker based on `Account_SSO_Demo`, including `/sso/me` for frontend session checks.

After copying the template, rename product text and replace placeholder endpoints with the user's actual API contract.

## Implementation Standards

- Use React server/client components deliberately. Keep interactive panes as client components.
- Use structured APIs for JSON config and endpoint checks; avoid ad hoc string parsing.
- Make controls explicit: buttons for commands, toggles for booleans, numeric inputs for intervals/timeouts, text inputs for endpoints.
- Keep logs monospace, timestamped, scrollable, and copyable.
- Treat endpoint health checks as server-side API routes to avoid browser CORS surprises.
- Keep deployment docs accurate for both local development and EC2 with a process manager or systemd.
