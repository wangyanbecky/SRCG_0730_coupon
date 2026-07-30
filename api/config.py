"""Application configuration for the separated API package."""

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
API_DIR = ROOT_DIR / "api"
DATA_DIR = API_DIR / "data"
DEFAULT_DATABASE_PATH = DATA_DIR / "coupon.db"
CONFIG_DIR = ROOT_DIR / "config"
ENV_PATH = CONFIG_DIR / ".env"
UI_DIR = ROOT_DIR / "ui"
TEMPLATE_DIR = UI_DIR / "templates"
STATIC_DIR = UI_DIR / "static"

# Local secrets live in config/.env and remain outside version control.
load_dotenv(ENV_PATH)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "coupon-system-secret-key-2024")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "deepseek.v3.2")
    AWS_BEARER_TOKEN_BEDROCK = os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")
    AI_MOCK_MODE = os.environ.get("AI_MOCK_MODE", "true").lower() == "true"
    BEDROCK_LIST_MODELS_TIMEOUT = int(
        os.environ.get("BEDROCK_LIST_MODELS_TIMEOUT", "10")
    )
    BEDROCK_CONVERSE_TIMEOUT = int(
        os.environ.get("BEDROCK_CONVERSE_TIMEOUT", "60")
    )

    RISK_HIGH_THRESHOLD = 0.7
    RISK_MEDIUM_THRESHOLD = 0.4
    RISK_CLAIM_WINDOW_SECONDS = int(
        os.environ.get("RISK_CLAIM_WINDOW_SECONDS", "10")
    )
    RISK_MAX_CLAIMS_IN_WINDOW = int(
        os.environ.get("RISK_MAX_CLAIMS_IN_WINDOW", "50")
    )

    POINTS_CLAIM = 10
    POINTS_VERIFY = 5
    POINTS_EXPIRE = -5
    POINTS_INACTIVE = -3
    INACTIVE_DAYS_THRESHOLD = 7
