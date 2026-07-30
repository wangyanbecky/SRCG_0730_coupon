# Demo Developer UI Requirements

## Scope

Create a Next.js/React UI for developers who need to test, debug, and monitor a demo system. The UI should be operational and information-dense, with restrained colors, clear state, and predictable controls.

## Pages

### Dashboard

- Require authentication.
- Show a compact top bar with signed-in user identity and session status.
- Provide an end-to-end testing area with two adjacent panes:
  - Left pane: input payload, target endpoint selector, session controls, send/clear buttons, request options.
  - Right pane: streaming or appended logs with timestamps, severity, request id, latency, and response summary.
- Use a fixed max width such as `1280px`; panes should have stable heights such as `520px`; overflow must scroll.
- Include session connection management: connect, disconnect, reconnect, heartbeat timestamp, and status indicator.

### System Status

- Show frontend status, backend status, configured endpoint health, latency, and last checked time.
- Include explicit connection test actions for each configured endpoint.
- Provide data query controls for simple diagnostics.
- Surface large request logs: request id, route, payload size, status, duration, and timestamp.

### Settings

- Load from and save to a local JSON file at runtime.
- Configure main endpoints: API base URL, health URL, query URL, test session URL, optional token rotation URL.
- Configure parameters: polling interval, timeout, log retention, debug logging, mock mode, request size threshold.
- Include an API token rotation button only when `tokenRotationUrl` exists in config.
- Do not store API token secrets in this local config; store only token metadata and endpoint references.

## Local Config Shape

Use a JSON file similar to:

```json
{
  "endpoints": {
    "apiBaseUrl": "http://localhost:8080",
    "healthUrl": "http://localhost:8080/health",
    "queryUrl": "http://localhost:8080/query",
    "testSessionUrl": "http://localhost:8080/test/session",
    "tokenRotationUrl": ""
  },
  "runtime": {
    "pollingIntervalMs": 10000,
    "requestTimeoutMs": 15000,
    "maxLogEntries": 500,
    "largeRequestThresholdKb": 512
  },
  "features": {
    "debugLogging": true,
    "mockMode": false,
    "autoReconnect": true
  }
}
```

## AWS Identity Center SSO

Use the backend SSO broker pattern from `Account_SSO_Demo`, not a frontend-held token model. The backend performs AWS Identity Center Device Authorization Flow with boto3:

1. `register_client(clientType="public", scopes=["sso:account:access"])`
2. `start_device_authorization(startUrl=SSO_START_URL)`
3. Store `clientId`, `clientSecret`, and `deviceCode` temporarily in the backend session.
4. Open `verificationUriComplete` for the user.
5. Poll `create_token(grantType="urn:ietf:params:oauth:grant-type:device_code")`.
6. On success, call `sso.list_accounts(accessToken=access_token)` and store normalized user info in session.

Standard backend routes:

```text
/sso/login   starts login and opens Identity Center verification
/sso/poll    polls device authorization result
/sso/logout  clears session
/sso/me      returns { authenticated, user } as JSON
```

Expected environment variables:

```bash
SSO_START_URL=https://d-XXXXX.awsapps.com/start
AWS_REGION=us-east-1
FLASK_SECRET_KEY=replace-with-random-secret
SSO_BACKEND_BASE_URL=http://localhost:5002
```

Deploy Next.js and the backend behind the same site whenever possible. Use Nginx or an ALB path rule so `/sso/*` reaches the backend and `/` reaches Next.js. This keeps cookies same-site and prevents CORS-driven auth problems.

## Deployment Expectations

Local development should use `npm run dev` or the repository package manager equivalent. EC2 deployment should document:

- Node.js LTS installation.
- Environment variables.
- Build command.
- Process manager via `systemd` or PM2.
- Reverse proxy with Nginx when using TLS/custom domains.
- `/sso/*` reverse proxy path to the backend SSO broker.
- Local config file path and permissions.
