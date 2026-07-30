"""Risk-assessment orchestration with automatic rule fallback."""
from __future__ import annotations

import json
import re
from typing import Any, Mapping

from ..config import AIConfig
from ..contracts import RiskAssessment, RiskAssessmentRequest
from ..fallback.risk_rules import assess_by_rules
from ..prompts.risk_assessment import build_risk_prompt
from ..providers.base import TextProvider


def _json_object(text: str) -> Mapping[str, Any]:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    candidate = match.group(1) if match else text
    value = json.loads(candidate.strip())
    if not isinstance(value, Mapping):
        raise ValueError("provider response must be a JSON object")
    return value


class RiskAssessmentService:
    def __init__(self, provider: TextProvider, config: AIConfig) -> None:
        self.provider = provider
        self.config = config

    def assess(self, request: RiskAssessmentRequest) -> RiskAssessment:
        if not self.provider.available:
            return assess_by_rules(request, self.config)
        try:
            text = self.provider.converse(
                [{"role": "user", "content": build_risk_prompt(request)}]
            )
            return self._parse_assessment(text)
        except Exception:
            return assess_by_rules(request, self.config)

    @staticmethod
    def _parse_assessment(text: str) -> RiskAssessment:
        payload = _json_object(text)
        score = min(max(float(payload["risk_score"]), 0.0), 1.0)
        decision = str(payload["decision"]).lower()
        if decision not in {"allow", "block", "review"}:
            raise ValueError("invalid risk decision")
        reason = str(payload.get("reason") or "AI风险评估")
        return RiskAssessment(round(score, 2), decision, reason)
