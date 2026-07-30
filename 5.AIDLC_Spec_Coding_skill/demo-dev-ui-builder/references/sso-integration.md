# SSO Integration Standard

Use this reference when adding AWS Identity Center SSO to a generated developer UI.

## Canonical Pattern

Follow the `Account_SSO_Demo` backend broker model:

- A backend module owns Identity Center interaction through boto3.
- The browser never stores AWS SSO access tokens.
- The backend stores short-lived device authorization state in session under `_sso`.
- The backend stores authenticated user info in session under `sso_user`.
- The backend may store `sso_access_token` only server-side if downstream AWS account APIs need it.
- The frontend consumes only coarse identity state through JSON: `{ authenticated, user }`.

For a new project, copy `assets/flask-sso-broker/` as the backend starting point, or copy only `sso_auth.py` into an existing Flask service.

## Backend Routes

Register these routes on the backend:

```text
GET /sso/login   register OIDC client, start device authorization, open verification URL
GET /sso/poll    poll create_token until success/pending/slowdown/error
GET /sso/logout  clear sso_user, sso_access_token, and _sso from session
GET /sso/me      return authenticated user JSON
```

`/sso/me` is the small addition most frontends need:

```python
from flask import jsonify
from sso_auth import get_sso_user

@app.route("/sso/me")
def sso_me():
    user = get_sso_user()
    return jsonify({"authenticated": bool(user), "user": user})
```

## boto3 Flow

Use `boto3.client("sso-oidc", region_name=region)`:

```python
reg = sso_oidc.register_client(
    clientName=app.name,
    clientType="public",
    scopes=["sso:account:access"],
)
auth = sso_oidc.start_device_authorization(
    clientId=reg["clientId"],
    clientSecret=reg["clientSecret"],
    startUrl=sso_start_url,
)
```

Poll with:

```python
token_resp = sso_oidc.create_token(
    clientId=sso_data["client_id"],
    clientSecret=sso_data["client_secret"],
    grantType="urn:ietf:params:oauth:grant-type:device_code",
    deviceCode=sso_data["device_code"],
)
```

Handle `AuthorizationPendingException` by returning a polling page, handle `SlowDownException` by waiting before polling again, and clear `_sso` on unrecoverable errors.

After success, call:

```python
sso = boto3.client("sso", region_name=region)
accounts = sso.list_accounts(accessToken=token_resp["accessToken"])
```

Normalize `accountList[0]` into the session user shape:

```json
{
  "accountId": "123456789012",
  "accountName": "DemoAccount",
  "emailAddress": "user@example.com"
}
```

## Next.js Frontend Contract

Use same-site routing:

- Sign in link: `/sso/login`
- Sign out link: `/sso/logout`
- Session status: `/api/sso/me`

Implement `/api/sso/me` in Next.js as a server-side proxy to the backend `/sso/me`, forwarding the incoming `cookie` header. Protect Next.js API routes by calling the same helper before performing endpoint checks, test-session requests, config edits, or token rotation.

Environment variables:

```bash
SSO_BACKEND_BASE_URL=http://localhost:5002
NEXT_PUBLIC_SSO_LOGIN_PATH=http://localhost:5002/sso/login
NEXT_PUBLIC_SSO_LOGOUT_PATH=http://localhost:5002/sso/logout
```

For production, prefer same-site paths:

```bash
NEXT_PUBLIC_SSO_LOGIN_PATH=/sso/login
NEXT_PUBLIC_SSO_LOGOUT_PATH=/sso/logout
```

Proxy `/sso/*` to the backend SSO service and keep Next.js under the same domain.

## Local Setup

Identity Center setup should create or discover an account-level instance, create a test user if needed, and write:

```bash
SSO_START_URL=https://<identity-store-id>.awsapps.com/start
FLASK_SECRET_KEY=<random>
AWS_REGION=us-east-1
```

The user still needs to set/reset the test user's password in AWS Console before first login.
