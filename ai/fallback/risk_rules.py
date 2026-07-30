"""Deterministic risk-assessment fallback rules."""
from __future__ import annotations

from ..config import AIConfig
from ..contracts import RiskAssessment, RiskAssessmentRequest


def assess_by_rules(
    request: RiskAssessmentRequest, config: AIConfig
) -> RiskAssessment:
    """Assess caller-supplied recent activity without database access."""
    if request.recent_count is not None:
        recent_count = request.recent_count
    else:
        recent_count = sum(
            1 for item in request.recent_history if item.action == request.action
        )

    maximum = config.risk_max_claims_in_window
    risk_score = min(recent_count / maximum, 1.0)

    # Reaching the configured maximum is already a block, not one request later.
    if recent_count >= maximum:
        decision = "block"
        reason = (
            f"检测到异常高频操作：{config.risk_claim_window_seconds}秒内"
            f"{recent_count}次{request.action}请求"
        )
    elif recent_count > maximum // 2:
        decision = "review"
        reason = (
            f"操作频率偏高：{config.risk_claim_window_seconds}秒内"
            f"{recent_count}次{request.action}请求，需人工审核"
        )
    else:
        decision = "allow"
        reason = "正常操作频率"

    return RiskAssessment(round(risk_score, 2), decision, reason)
