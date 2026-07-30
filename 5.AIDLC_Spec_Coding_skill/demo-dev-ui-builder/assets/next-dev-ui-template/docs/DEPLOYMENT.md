# Deployment

## Local

Use local development for feature work and endpoint contract testing:

```bash
npm install
npm run dev
```

Run the SSO backend locally, for example the Flask broker from `Account_SSO_Demo`, and set:

```bash
SSO_BACKEND_BASE_URL=http://localhost:5002
NEXT_PUBLIC_SSO_LOGIN_PATH=http://localhost:5002/sso/login
NEXT_PUBLIC_SSO_LOGOUT_PATH=http://localhost:5002/sso/logout
```

## EC2

1. Install Node.js LTS.
2. Copy the project to the instance.
3. Create `.env.production` with `SSO_BACKEND_BASE_URL` and any app settings.
4. Place local config at a stable path, for example `/opt/demo-dev-ui/local.config.json`.
5. Build and start:

```bash
npm ci
npm run build
DEMO_UI_CONFIG_PATH=/opt/demo-dev-ui/local.config.json npm run start
```

## systemd Example

```ini
[Unit]
Description=Demo Dev UI
After=network.target

[Service]
WorkingDirectory=/opt/demo-dev-ui/app
Environment=NODE_ENV=production
Environment=SSO_BACKEND_BASE_URL=http://127.0.0.1:5002
Environment=DEMO_UI_CONFIG_PATH=/opt/demo-dev-ui/local.config.json
EnvironmentFile=/opt/demo-dev-ui/.env.production
ExecStart=/usr/bin/npm run start
Restart=always
User=ec2-user

[Install]
WantedBy=multi-user.target
```

## Reverse Proxy

Terminate TLS with Nginx or an AWS load balancer. Forward `/` to the Next.js port, usually `3000`, and forward `/sso/` to the backend SSO broker.

```nginx
location / {
  proxy_pass http://127.0.0.1:3000;
}

location /sso/ {
  proxy_pass http://127.0.0.1:5002/sso/;
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```
