from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    CONDITIONAL = "CONDITIONAL"


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    name: str
    score_delta: int
    hard_block: bool
    reasons: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score_delta": self.score_delta,
            "hard_block": self.hard_block,
            "reasons": list(self.reasons),
            "actions": list(self.actions),
        }


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    decision: Decision
    score: int
    reasons: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    outcomes: list[RuleOutcome] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "score": self.score,
            "reasons": list(self.reasons),
            "actions": list(self.actions),
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }
