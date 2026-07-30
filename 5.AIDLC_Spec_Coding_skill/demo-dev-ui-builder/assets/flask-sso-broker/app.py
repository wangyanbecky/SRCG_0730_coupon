"""Minimal Flask SSO broker app for local development."""

import os

from dotenv import load_dotenv
from flask import Flask

from sso_auth import get_sso_user, init_sso_auth

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

init_sso_auth(
    app,
    sso_start_url=os.environ["SSO_START_URL"],
    region=os.environ.get("AWS_REGION", "us-east-1"),
    on_login_redirect=os.environ.get("SSO_LOGIN_REDIRECT", "http://localhost:3000"),
    on_logout_redirect=os.environ.get("SSO_LOGOUT_REDIRECT", "http://localhost:3000"),
)


@app.route("/")
def index():
    user = get_sso_user()
    if user:
        return f"Signed in as {user.get('emailAddress') or user.get('accountName')}"
    return '<a href="/sso/login">Login with Identity Center</a>'


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", "5002")))
