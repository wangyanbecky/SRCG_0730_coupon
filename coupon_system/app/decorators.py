"""Role-based access control decorators."""
from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*roles):
    """Decorator to restrict access to specific user roles.

    Usage:
        @role_required('admin')
        @role_required('operator', 'admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(401)
            if current_user.role not in roles:
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def operator_required(f):
    """Decorator for operator-only routes."""
    return role_required('operator')(f)


def user_required(f):
    """Decorator for regular user routes."""
    return role_required('user')(f)


def verifier_required(f):
    """Decorator for verifier-only routes."""
    return role_required('verifier')(f)


def admin_required(f):
    """Decorator for admin-only routes."""
    return role_required('admin')(f)
