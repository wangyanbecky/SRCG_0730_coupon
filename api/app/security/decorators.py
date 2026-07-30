"""Role-based access-control decorators."""

from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(*roles):
    def decorator(function):
        @wraps(function)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(401)
            if current_user.role not in roles:
                return abort(403)
            return function(*args, **kwargs)

        return decorated_function

    return decorator


def operator_required(function):
    return role_required("operator")(function)


def user_required(function):
    return role_required("user")(function)


def verifier_required(function):
    return role_required("verifier")(function)


def admin_required(function):
    return role_required("admin")(function)
