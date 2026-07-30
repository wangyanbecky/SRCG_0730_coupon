import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load .env file if present (for local development)
load_dotenv(os.path.join(BASE_DIR, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'coupon-system-secret-key-2024')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(BASE_DIR, "coupon.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Amazon Bedrock configuration
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    BEDROCK_MODEL_ID = os.environ.get(
        'BEDROCK_MODEL_ID',
        'deepseek.v3.2'
    )
    # API Key (Bearer token) for Bedrock — takes priority over SDK credentials
    AWS_BEARER_TOKEN_BEDROCK = os.environ.get('AWS_BEARER_TOKEN_BEDROCK', '')
    # Enable mock mode when neither API Key nor AWS credentials are available
    AI_MOCK_MODE = os.environ.get('AI_MOCK_MODE', 'true').lower() == 'true'
    # Bedrock request timeouts (seconds)
    BEDROCK_LIST_MODELS_TIMEOUT = int(os.environ.get('BEDROCK_LIST_MODELS_TIMEOUT', '10'))
    BEDROCK_CONVERSE_TIMEOUT = int(os.environ.get('BEDROCK_CONVERSE_TIMEOUT', '60'))

    # Risk assessment thresholds
    RISK_HIGH_THRESHOLD = 0.7   # Block
    RISK_MEDIUM_THRESHOLD = 0.4  # Manual review
    RISK_CLAIM_WINDOW_SECONDS = 10  # 10秒时间窗口
    RISK_MAX_CLAIMS_IN_WINDOW = 49  # 窗口内最多49次，第50次触发拦截

    # Points system
    POINTS_CLAIM = 10
    POINTS_VERIFY = 5
    POINTS_EXPIRE = -5
    POINTS_INACTIVE = -3
    INACTIVE_DAYS_THRESHOLD = 7
