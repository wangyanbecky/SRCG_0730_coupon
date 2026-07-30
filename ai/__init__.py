"""Standalone coupon recommendation and risk-assessment package."""

from .config import AIConfig
from .contracts import (
    Campaign,
    Recommendation,
    RiskAssessment,
    RiskAssessmentRequest,
    RiskHistoryEntry,
    UserProfile,
)
from .service import CouponAIService

__all__ = [
    "AIConfig",
    "Campaign",
    "CouponAIService",
    "Recommendation",
    "RiskAssessment",
    "RiskAssessmentRequest",
    "RiskHistoryEntry",
    "UserProfile",
]
