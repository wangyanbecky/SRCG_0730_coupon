"""Framework-independent DTOs used by the AI package."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


Identifier = int | str


def _hobbies(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return (str(value).strip(),) if str(value).strip() else ()


@dataclass(frozen=True, slots=True)
class UserProfile:
    age: int | None = None
    gender: str = ""
    hobbies: tuple[str, ...] = ()
    occupation: str = ""
    points: int = 0
    attributes: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "UserProfile":
        known = {"age", "gender", "hobbies", "occupation", "points"}
        return cls(
            age=value.get("age"),
            gender=str(value.get("gender") or ""),
            hobbies=_hobbies(value.get("hobbies")),
            occupation=str(value.get("occupation") or ""),
            points=int(value.get("points") or 0),
            attributes={key: item for key, item in value.items() if key not in known},
        )

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "age": self.age,
            "gender": self.gender,
            "hobbies": list(self.hobbies),
            "occupation": self.occupation,
            "points": self.points,
        }


@dataclass(frozen=True, slots=True)
class Campaign:
    campaign_id: Identifier
    name: str = ""
    amount: float = 0.0
    stock: int = 0
    days_left: int | None = None
    description: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Campaign":
        campaign_id = value.get("campaign_id", value.get("id"))
        if campaign_id is None:
            raise ValueError("campaign_id (or id) is required")
        days_left = value.get("days_left")
        return cls(
            campaign_id=campaign_id,
            name=str(value.get("name") or ""),
            amount=float(value.get("amount") or 0),
            stock=int(value.get("stock") or 0),
            days_left=int(days_left) if days_left is not None else None,
            description=str(value.get("description") or ""),
        )

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "amount": self.amount,
            "stock": self.stock,
            "days_left": self.days_left,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class Recommendation:
    campaign_id: Identifier
    reason: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "reason": self.reason,
            "score": self.score,
        }


@dataclass(frozen=True, slots=True)
class RiskHistoryEntry:
    action: str
    risk_score: float = 0.0
    decision: str = "allow"
    time: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RiskHistoryEntry":
        return cls(
            action=str(value.get("action") or ""),
            risk_score=float(value.get("risk_score", value.get("score", 0.0)) or 0.0),
            decision=str(value.get("decision") or "allow"),
            time=str(value.get("time", value.get("created_at", "")) or ""),
        )

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "risk_score": self.risk_score,
            "decision": self.decision,
            "time": self.time,
        }


@dataclass(frozen=True, slots=True)
class RiskAssessmentRequest:
    user_context: Mapping[str, Any]
    action: str
    recent_history: tuple[RiskHistoryEntry, ...] = ()
    recent_count: int | None = None

    @classmethod
    def from_inputs(
        cls,
        user_context: Mapping[str, Any],
        action: str | None = None,
        recent_history: Sequence[Mapping[str, Any] | RiskHistoryEntry] | None = None,
        recent_count: int | None = None,
    ) -> "RiskAssessmentRequest":
        resolved_action = action or str(user_context.get("action") or "")
        if not resolved_action:
            raise ValueError("action is required")
        raw_history = recent_history
        if raw_history is None:
            candidate = user_context.get("recent_history", ())
            raw_history = candidate if isinstance(candidate, Sequence) else ()
        if recent_count is None and user_context.get("recent_count") is not None:
            recent_count = int(user_context["recent_count"])
        if recent_count is not None and recent_count < 0:
            raise ValueError("recent_count must not be negative")
        history = tuple(
            item if isinstance(item, RiskHistoryEntry) else RiskHistoryEntry.from_mapping(item)
            for item in raw_history
        )
        excluded = {"action", "recent_history", "recent_count"}
        context = {key: value for key, value in user_context.items() if key not in excluded}
        return cls(context, resolved_action, history, recent_count)


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    risk_score: float
    decision: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "decision": self.decision,
            "reason": self.reason,
        }
