"""Application logging and lightweight system health checks."""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import sys
import time
import uuid
import weakref
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import g, got_request_exception, request
from flask_login import current_user
from sqlalchemy import text

from api.app.extensions import db


_ALLOWED_LOG_FIELDS = (
    "timestamp",
    "level",
    "logger",
    "event",
    "request_id",
    "method",
    "endpoint",
    "status",
    "duration_ms",
    "user_id",
    "role",
    "message",
)
_TEXT_LOG_FIELDS = {
    "timestamp",
    "logger",
    "event",
    "request_id",
    "method",
    "endpoint",
    "role",
    "message",
}
_NUMERIC_LOG_FIELDS = {"status", "duration_ms", "user_id"}
_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_SENSITIVE_PATTERNS = (
    (
        re.compile(
            r"(?i)\b(password|secret|token|authorization|cookie|session|api[_-]?key)"
            r"\b\s*[:=]\s*[^\s,;]+"
        ),
        r"\1=[REDACTED]",
    ),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "[REDACTED_AWS_KEY]"),
    (
        re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|sqlite|mongodb)(?:\+\w+)?://\S+"),
        "[REDACTED_DATABASE_URI]",
    ),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "1**********"),
)


def sanitize_text(value, max_length=500):
    """Redact common secret/PII patterns and bound display size."""
    result = str(value or "")
    for pattern, replacement in _SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    if len(result) > max_length:
        return result[: max_length - 1] + "…"
    return result


class JsonLineFormatter(logging.Formatter):
    """Serialize only explicitly allowed event metadata as JSON Lines."""

    def format(self, record):
        event_data = getattr(record, "event_data", {}) or {}
        if not isinstance(event_data, dict):
            event_data = {}
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname if record.levelname in _LEVELS else "INFO",
            "logger": sanitize_text(record.name, 120),
            "event": sanitize_text(event_data.get("event", record.getMessage()), 120),
            "message": sanitize_text(event_data.get("message", record.getMessage())),
        }
        for field in _ALLOWED_LOG_FIELDS:
            if field in {"timestamp", "level", "logger", "event", "message"}:
                continue
            if field in event_data and event_data[field] is not None:
                value = event_data[field]
                payload[field] = (
                    sanitize_text(value, 200) if isinstance(value, str) else value
                )
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class ResilientRotatingFileHandler(RotatingFileHandler):
    """Mark the health state when logging or rollover fails."""

    def __init__(self, *args, error_callback=None, **kwargs):
        self.error_callback = error_callback
        super().__init__(*args, **kwargs)

    def handleError(self, record):
        error = sys.exc_info()[1]
        if self.error_callback is not None:
            try:
                self.error_callback(type(error).__name__ if error else "LoggingError")
            except Exception:
                pass
        # Do not delegate to logging's stderr handler because records may be sensitive.


def _configured_path(app, key):
    root_dir = Path(app.config.get("APP_ROOT_DIR", app.root_path)).resolve()
    value = Path(str(app.config[key])).expanduser()
    return (root_dir / value).resolve() if not value.is_absolute() else value.resolve()


def _resolve_log_path(app):
    allowed_root = _configured_path(app, "APP_LOG_ROOT")
    candidate = _configured_path(app, "APP_LOG_FILE")
    candidate.relative_to(allowed_root)
    return candidate


def _close_logger(logger):
    for handler in list(logger.handlers):
        try:
            handler.flush()
            handler.close()
        finally:
            logger.removeHandler(handler)
    logging.Logger.manager.loggerDict.pop(logger.name, None)


def configure_observability(app):
    """Attach request logging without making application startup depend on it."""
    app.extensions["started_at"] = datetime.now(timezone.utc)
    app.extensions["system_log_configured"] = False
    app.extensions["system_log_error"] = None
    app.extensions["system_log_fallback"] = False

    try:
        log_path = _resolve_log_path(app)
    except (KeyError, OSError, RuntimeError, ValueError):
        log_path = (Path(app.instance_path) / "logs" / "app.log").resolve()
        app.extensions["system_log_error"] = "InvalidConfiguredPath"
        app.extensions["system_log_fallback"] = True
    app.extensions["system_log_path"] = log_path

    logger = logging.getLogger(f"couponflow.{id(app)}")
    configured_level = str(app.config.get("APP_LOG_LEVEL", "INFO")).upper()
    logger.setLevel(getattr(logging, configured_level, logging.INFO))
    logger.propagate = False
    app.extensions["system_logger"] = logger
    app_ref = weakref.ref(app)

    def mark_log_error(error_type):
        target = app_ref()
        if target is not None:
            target.extensions["system_log_configured"] = False
            target.extensions["system_log_error"] = error_type

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8"):
            pass
        handler = ResilientRotatingFileHandler(
            log_path,
            maxBytes=int(app.config.get("APP_LOG_MAX_BYTES", 5 * 1024 * 1024)),
            backupCount=int(app.config.get("APP_LOG_BACKUP_COUNT", 5)),
            encoding="utf-8",
            delay=True,
            error_callback=mark_log_error,
        )
        handler.setFormatter(JsonLineFormatter())
        logger.addHandler(handler)
        app.extensions["system_log_configured"] = True
    except (OSError, TypeError, ValueError) as error:
        app.extensions["system_log_error"] = type(error).__name__
        logger.addHandler(logging.NullHandler())

    weakref.finalize(app, _close_logger, logger)

    @app.before_request
    def begin_request_observation():
        g.request_started_at = time.perf_counter()
        g.request_id = uuid.uuid4().hex

    @app.after_request
    def complete_request_observation(response):
        request_id = getattr(g, "request_id", uuid.uuid4().hex)
        response.headers["X-Request-ID"] = request_id
        if request.endpoint == "static":
            return response

        started_at = getattr(g, "request_started_at", None)
        duration_ms = (
            round((time.perf_counter() - started_at) * 1000, 2)
            if started_at is not None
            else None
        )
        authenticated = bool(getattr(current_user, "is_authenticated", False))
        status = response.status_code
        level = (
            logging.ERROR
            if status >= 500
            else logging.WARNING
            if status >= 400
            else logging.INFO
        )
        try:
            logger.log(
                level,
                "request_completed",
                extra={
                    "event_data": {
                        "event": "request_completed",
                        "request_id": request_id,
                        "method": request.method,
                        "endpoint": request.endpoint or "unknown",
                        "status": status,
                        "duration_ms": duration_ms,
                        "user_id": current_user.id if authenticated else None,
                        "role": current_user.role if authenticated else "anonymous",
                        "message": "HTTP request completed",
                    }
                },
            )
        except Exception:
            mark_log_error("LoggingError")
        return response

    def log_unhandled_exception(_sender, exception, **_extra):
        try:
            logger.error(
                "unhandled_exception",
                extra={
                    "event_data": {
                        "event": "unhandled_exception",
                        "request_id": getattr(g, "request_id", None),
                        "method": request.method,
                        "endpoint": request.endpoint or "unknown",
                        "message": f"Unhandled {type(exception).__name__}",
                    }
                },
            )
        except Exception:
            mark_log_error("LoggingError")

    got_request_exception.connect(log_unhandled_exception, app, weak=False)


def _safe_log_entry(raw):
    if not isinstance(raw, dict):
        return None
    entry = {}
    raw_level = raw.get("level")
    entry["level"] = (
        raw_level.upper()
        if isinstance(raw_level, str) and raw_level.upper() in _LEVELS
        else "INFO"
    )
    for field in _TEXT_LOG_FIELDS:
        if field in raw and raw[field] is not None:
            entry[field] = sanitize_text(raw[field], 500 if field == "message" else 200)
    for field in _NUMERIC_LOG_FIELDS:
        if field not in raw or raw[field] is None:
            continue
        value = raw[field]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            entry[field] = value
        else:
            entry[field] = sanitize_text(value, 80)
    return entry


def _tail_lines(path, max_lines, max_bytes):
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        file_size = stream.tell()
        read_size = min(file_size, max_bytes)
        stream.seek(-read_size, os.SEEK_END)
        data = stream.read(read_size)
    return data.decode("utf-8", errors="replace").splitlines()[-max_lines:]


def read_system_logs(app, level="", query="", limit=50):
    """Read a bounded tail of the active log, skipping malformed records."""
    level_value = str(level or "").upper()
    normalized_level = level_value if level_value in _LEVELS else ""
    normalized_query = sanitize_text(query, 100).casefold()
    try:
        requested_limit = int(limit)
    except (TypeError, ValueError):
        requested_limit = 50
    max_limit = max(1, int(app.config.get("APP_LOG_VIEW_MAX_LIMIT", 100)))
    bounded_limit = max(1, min(requested_limit, max_limit))
    log_path = app.extensions.get("system_log_path")
    if not isinstance(log_path, Path):
        return [], "日志路径不可用。"
    if not log_path.exists():
        return [], None

    try:
        scan_lines = max(100, int(app.config.get("APP_LOG_SCAN_LINES", 2000)))
        max_bytes = min(
            max(65536, scan_lines * 1024),
            max(65536, int(app.config.get("APP_LOG_MAX_BYTES", 5 * 1024 * 1024))),
        )
        lines = _tail_lines(log_path, scan_lines, max_bytes)
    except (OSError, TypeError, ValueError) as error:
        return [], f"日志读取失败（{type(error).__name__}）"

    entries = []
    for line in reversed(lines):
        try:
            entry = _safe_log_entry(json.loads(line))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        if entry is None:
            continue
        if normalized_level and entry.get("level") != normalized_level:
            continue
        if normalized_query:
            searchable = " ".join(str(value) for value in entry.values()).casefold()
            if normalized_query not in searchable:
                continue
        entries.append(entry)
        if len(entries) >= bounded_limit:
            break
    return entries, None


def _flask_version():
    try:
        return version("flask")
    except (PackageNotFoundError, ValueError):
        return "unknown"


def _duration_label(total_seconds):
    total_seconds = max(0, int(total_seconds))
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days:
        return f"{days}天 {hours}小时 {minutes}分钟"
    if hours:
        return f"{hours}小时 {minutes}分钟"
    if minutes:
        return f"{minutes}分钟 {seconds}秒"
    return f"{seconds}秒"


def _status_value(status, key, default=None):
    if isinstance(status, dict):
        return status.get(key, default)
    return getattr(status, key, default)


def collect_system_health(app):
    """Collect isolated local checks; no external network probes are performed."""
    checked_at = datetime.now(timezone.utc)
    checks = [
        {
            "name": "应用进程",
            "status": "healthy",
            "latency_ms": 0,
            "detail": "Flask 应用正在响应请求。",
        }
    ]

    db_started = time.perf_counter()
    try:
        db.session.execute(text("SELECT 1")).scalar_one()
        db_status = "healthy"
        db_detail = "数据库连接与基础查询正常。"
    except Exception as error:
        try:
            db.session.rollback()
        except Exception:
            pass
        db_status = "unhealthy"
        db_detail = f"数据库检查失败（{type(error).__name__}）。"
    checks.append(
        {
            "name": "数据库",
            "status": db_status,
            "latency_ms": round((time.perf_counter() - db_started) * 1000, 2),
            "detail": db_detail,
        }
    )

    log_started = time.perf_counter()
    try:
        log_path = app.extensions.get("system_log_path")
        configured = bool(app.extensions.get("system_log_configured", False))
        writable = (
            isinstance(log_path, Path)
            and log_path.parent.exists()
            and os.access(log_path.parent, os.W_OK)
        )
        fallback = bool(app.extensions.get("system_log_fallback", False))
        if configured and writable:
            log_status = "degraded" if fallback else "healthy"
            log_detail = (
                "配置路径无效，已切换到安全备用日志目录。"
                if fallback
                else f"轮转日志已配置：{log_path.name}。"
            )
        else:
            log_status = "unhealthy"
            error_type = app.extensions.get("system_log_error") or "NotWritable"
            log_detail = f"日志输出不可用（{sanitize_text(error_type, 80)}）。"
    except Exception as error:
        log_status = "unhealthy"
        log_detail = f"日志检查失败（{type(error).__name__}）。"
    checks.append(
        {
            "name": "日志输出",
            "status": log_status,
            "latency_ms": round((time.perf_counter() - log_started) * 1000, 2),
            "detail": log_detail,
        }
    )

    try:
        from api.app.services import ai_gateway

        ai_status = ai_gateway.status
        ai_connected = bool(_status_value(ai_status, "connected", False))
        ai_label = sanitize_text(_status_value(ai_status, "label", "AI"), 80)
        ai_check = {
            "name": "AI 服务配置",
            "status": "healthy" if ai_connected else "degraded",
            "latency_ms": None,
            "detail": (
                f"{ai_label} 已配置；一期未主动联网探测。"
                if ai_connected
                else "当前使用规则降级模式；一期未主动联网探测。"
            ),
        }
    except Exception as error:
        ai_check = {
            "name": "AI 服务配置",
            "status": "unknown",
            "latency_ms": None,
            "detail": f"AI 配置状态不可读取（{type(error).__name__}）。",
        }
    checks.append(ai_check)

    started_at = app.extensions.get("started_at")
    if not isinstance(started_at, datetime):
        started_at = checked_at
    uptime_seconds = (checked_at - started_at).total_seconds()
    statuses = {check["status"] for check in checks}
    overall = (
        "unhealthy"
        if "unhealthy" in statuses
        else "degraded"
        if statuses.intersection({"degraded", "unknown"})
        else "healthy"
    )
    return {
        "overall": overall,
        "checked_at": checked_at,
        "checks": checks,
        "healthy_count": sum(check["status"] == "healthy" for check in checks),
        "uptime": _duration_label(uptime_seconds),
        "runtime": {
            "app_version": sanitize_text(app.config.get("APP_VERSION", "dev"), 80),
            "environment": sanitize_text(app.config.get("APP_ENV", "unknown"), 80),
            "python": platform.python_version(),
            "flask": _flask_version(),
            "started_at": started_at,
        },
    }
