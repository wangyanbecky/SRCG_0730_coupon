"""Prompt construction for coupon-platform risk assessment."""
from __future__ import annotations

import json

from ..contracts import RiskAssessmentRequest


def build_risk_prompt(request: RiskAssessmentRequest) -> str:
    user_json = json.dumps(dict(request.user_context), ensure_ascii=False)
    history_json = json.dumps(
        [item.to_prompt_dict() for item in request.recent_history],
        ensure_ascii=False,
    )
    count_text = "unknown" if request.recent_count is None else str(request.recent_count)
    return (
        "You are a fraud detection system for a coupon platform. Assess the "
        "risk using only the caller-provided context and recent activity.\n\n"
        f"User context: {user_json}\n"
        f"Action: {request.action}\n"
        f"Recent action count: {count_text}\n"
        f"Recent risk history: {history_json}\n\n"
        "Return ONLY valid JSON in this exact shape:\n"
        '{"risk_score":0.0,"decision":"allow|block|review",'
        '"reason":"简短中文说明"}'
    )
