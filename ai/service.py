"""Public facade for the standalone coupon AI package."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .config import AIConfig
from .contracts import (
    Campaign,
    RiskAssessmentRequest,
    RiskHistoryEntry,
    UserProfile,
)
from .providers.base import TextProvider
from .providers.bedrock import BedrockProvider
from .services.recommendation import RecommendationService
from .services.risk_assessment import RiskAssessmentService


class CouponAIService:
    """Unified, framework-independent recommendation and risk API."""

    def __init__(
        self,
        config: AIConfig | Mapping[str, Any] | None = None,
        *,
        provider: TextProvider | None = None,
    ) -> None:
        if config is None:
            resolved_config = AIConfig.from_env()
        elif isinstance(config, AIConfig):
            resolved_config = config
        else:
            resolved_config = AIConfig.from_mapping(config)
        self.config = resolved_config
        self.provider = provider or BedrockProvider(resolved_config)
        self._recommendations = RecommendationService(self.provider)
        self._risk = RiskAssessmentService(self.provider, resolved_config)

    @property
    def status(self) -> dict[str, Any]:
        """Return non-secret status data suitable for API/UI display."""
        return dict(self.provider.status)

    def recommend_coupons(
        self,
        user_profile: UserProfile | Mapping[str, Any],
        campaigns: Sequence[Campaign | Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return items containing campaign_id, reason, and score."""
        return [
            item.to_dict()
            for item in self._recommendations.recommend(user_profile, campaigns)
        ]

    def assess_risk(
        self,
        user_context: Mapping[str, Any] | RiskAssessmentRequest,
        action: str | None = None,
        recent_history: Sequence[Mapping[str, Any] | RiskHistoryEntry] | None = None,
        recent_count: int | None = None,
    ) -> dict[str, Any]:
        """Assess risk from caller-provided context/history/count only."""
        request = (
            user_context
            if isinstance(user_context, RiskAssessmentRequest)
            else RiskAssessmentRequest.from_inputs(
                user_context,
                action=action,
                recent_history=recent_history,
                recent_count=recent_count,
            )
        )
        return self._risk.assess(request).to_dict()

    def list_text_models(self) -> list[dict[str, Any]]:
        """List Bedrock TEXT models, returning an empty list on provider failure."""
        try:
            return self.provider.list_text_models()
        except Exception:
            return []
