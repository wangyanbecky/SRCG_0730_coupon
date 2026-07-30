# Demo Dev UI

Next.js developer console for end-to-end testing, system health checks, backend connection tests, diagnostic queries, large request logs, local file-backed settings, and AWS Identity Center SSO through a backend SSO broker.

## Local Development

1. Install dependencies:

```bash
npm install
```

2. Create environment file:

```bash
cp .env.example .env.local
```

3. Start or configure a backend SSO broker that exposes `/sso/login`, `/sso/logout`, and `/sso/me`. The broker should follow the `Account_SSO_Demo` Device Authorization Flow pattern.

4. Configure `.env.local`:

```bash
SSO_BACKEND_BASE_URL=http://localhost:5002
NEXT_PUBLIC_SSO_LOGIN_PATH=http://localhost:5002/sso/login
NEXT_PUBLIC_SSO_LOGOUT_PATH=http://localhost:5002/sso/logout
```

5. Start the app:

```bash
npm run dev
```

6. Open `http://localhost:3000`.

## Configuration

Runtime settings are loaded from `config/local.config.json` by default. Override the path with:

```bash
DEMO_UI_CONFIG_PATH=/opt/demo-dev-ui/local.config.json
```

Do not store API token secrets in this file. Use environment variables or your secret manager for sensitive values.

## SSO Contract

The frontend expects same-site SSO routes:

- `/sso/login`: starts AWS Identity Center login.
- `/sso/logout`: clears backend session.
- `/sso/me`: returns `{"authenticated": true, "user": {...}}`.

In production, proxy `/sso/*` to the backend SSO broker so browser cookies stay same-site, then use `/sso/login` and `/sso/logout` as the public paths.
