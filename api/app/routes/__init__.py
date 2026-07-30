"""Blueprint exports."""

from api.app.routes.admin import admin_bp
from api.app.routes.api_v1 import api_v1_bp
from api.app.routes.auth import auth_bp
from api.app.routes.operator import operator_bp
from api.app.routes.user import user_bp
from api.app.routes.verifier import verifier_bp

__all__ = [
    "auth_bp",
    "api_v1_bp",
    "operator_bp",
    "user_bp",
    "verifier_bp",
    "admin_bp",
]
