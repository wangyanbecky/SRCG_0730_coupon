"""Reusable AWS Identity Center SSO broker for Flask.

This module implements the same Device Authorization Flow used by
Account_SSO_Demo and exposes browser-facing routes that a Next.js UI can
consume through same-site cookies.
"""

import time

import boto3
from flask import jsonify, redirect, session


def init_sso_auth(
    app,
    sso_start_url,
    region="us-east-1",
    login_path="/sso/login",
    poll_path="/sso/poll",
    logout_path="/sso/logout",
    me_path="/sso/me",
    on_login_redirect="/",
    on_logout_redirect="/",
):
    """Register AWS Identity Center SSO routes on a Flask app."""

    @app.route(login_path)
    def sso_login():
        sso_oidc = boto3.client("sso-oidc", region_name=region)

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

        session["_sso"] = {
            "client_id": reg["clientId"],
            "client_secret": reg["clientSecret"],
            "device_code": auth["deviceCode"],
            "auth_url": auth["verificationUriComplete"],
        }

        auth_url = auth["verificationUriComplete"]
        return f"""<!DOCTYPE html><html><head>
<meta http-equiv="refresh" content="5;url={poll_path}">
<style>body{{font-family:system-ui;text-align:center;margin-top:80px}}a{{color:#0073bb}}</style>
</head><body>
<h2>Signing in...</h2>
<p>A new window has been opened for Identity Center login.</p>
<p>If it did not open, <a href="{auth_url}" target="_blank">click here</a>.</p>
<p><em>This page will update automatically after you sign in.</em></p>
<script>window.open("{auth_url}", "_blank");</script>
</body></html>"""

    @app.route(poll_path)
    def sso_poll():
        sso_data = session.get("_sso")
        if not sso_data:
            return redirect(on_login_redirect)

        sso_oidc = boto3.client("sso-oidc", region_name=region)

        try:
            token_resp = sso_oidc.create_token(
                clientId=sso_data["client_id"],
                clientSecret=sso_data["client_secret"],
                grantType="urn:ietf:params:oauth:grant-type:device_code",
                deviceCode=sso_data["device_code"],
            )
        except sso_oidc.exceptions.AuthorizationPendingException:
            return _polling_page(poll_path)
        except sso_oidc.exceptions.SlowDownException:
            time.sleep(5)
            return _polling_page(poll_path)
        except Exception as exc:
            session.pop("_sso", None)
            return f"<h1>Auth Error</h1><p>{exc}</p><a href='{on_login_redirect}'>Back</a>", 400

        access_token = token_resp["accessToken"]
        sso = boto3.client("sso", region_name=region)
        accounts = sso.list_accounts(accessToken=access_token)
        account_list = accounts.get("accountList", [])

        session.pop("_sso", None)
        session["sso_user"] = account_list[0] if account_list else {
            "accountId": "N/A",
            "accountName": "SSO User",
            "emailAddress": "authenticated",
        }
        session["sso_access_token"] = access_token
        return redirect(on_login_redirect)

    @app.route(logout_path)
    def sso_logout():
        session.pop("sso_user", None)
        session.pop("sso_access_token", None)
        session.pop("_sso", None)
        return redirect(on_logout_redirect)

    @app.route(me_path)
    def sso_me():
        user = get_sso_user()
        return jsonify({"authenticated": bool(user), "user": user})


def get_sso_user():
    """Return current authenticated SSO user or None."""
    return session.get("sso_user")


def _polling_page(poll_path):
    return f"""<!DOCTYPE html><html><head>
<meta http-equiv="refresh" content="3;url={poll_path}">
<style>body{{font-family:system-ui;text-align:center;margin-top:100px}}</style>
</head><body><h2>Completing sign-in...</h2><p>Please wait...</p></body></html>"""
