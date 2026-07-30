"""Application configuration for the separated API package."""

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
API_DIR = ROOT_DIR / "api"
DATA_DIR = API_DIR / "data"
DEFAULT_DATABASE_PATH = DATA_DIR / "coupon.db"
LOG_DIR = DATA_DIR / "logs"
DEFAULT_APP_LOG_PATH = LOG_DIR / "app.log"
CONFIG_DIR = ROOT_DIR / "config"
ENV_PATH = CONFIG_DIR / ".env"
UI_DIR = ROOT_DIR / "ui"
TEMPLATE_DIR = UI_DIR / "templates"
STATIC_DIR = UI_DIR / "static"

# Local secrets live in config/.env and remain outside version control.
load_dotenv(ENV_PATH)


def _env_int(name, default, minimum=0):
    try:
        value = int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, value)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "coupon-system-secret-key-2024")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    APP_ROOT_DIR = str(ROOT_DIR)
    APP_VERSION = os.environ.get("APP_VERSION", "dev")
    APP_ENV = os.environ.get("APP_ENV", "development")
    APP_LOG_ROOT = os.environ.get("APP_LOG_ROOT", str(LOG_DIR))
    APP_LOG_FILE = os.environ.get(
        "APP_LOG_FILE",
        str(DEFAULT_APP_LOG_PATH),
    )
    APP_LOG_LEVEL = os.environ.get("APP_LOG_LEVEL", "INFO").upper()
    APP_LOG_MAX_BYTES = _env_int("APP_LOG_MAX_BYTES", 5 * 1024 * 1024, 1024)
    APP_LOG_BACKUP_COUNT = _env_int("APP_LOG_BACKUP_COUNT", 5, 0)
    APP_LOG_SCAN_LINES = _env_int("APP_LOG_SCAN_LINES", 2000, 100)
    APP_LOG_VIEW_MAX_LIMIT = _env_int("APP_LOG_VIEW_MAX_LIMIT", 100, 1)

    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "deepseek.v3.2")
    AWS_BEARER_TOKEN_BEDROCK = os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")
    AI_MOCK_MODE = os.environ.get("AI_MOCK_MODE", "true").lower() == "true"
    BEDROCK_LIST_MODELS_TIMEOUT = _env_int("BEDROCK_LIST_MODELS_TIMEOUT", 10, 1)
    BEDROCK_CONVERSE_TIMEOUT = _env_int("BEDROCK_CONVERSE_TIMEOUT", 60, 1)

    RISK_HIGH_THRESHOLD = 0.7
    RISK_MEDIUM_THRESHOLD = 0.4
    RISK_CLAIM_WINDOW_SECONDS = _env_int("RISK_CLAIM_WINDOW_SECONDS", 10, 1)
    RISK_MAX_CLAIMS_IN_WINDOW = _env_int("RISK_MAX_CLAIMS_IN_WINDOW", 5, 1)

    POINTS_CLAIM = 10
    POINTS_VERIFY = 5
    POINTS_EXPIRE = -5
    POINTS_INACTIVE = -3
    INACTIVE_DAYS_THRESHOLD = 7
