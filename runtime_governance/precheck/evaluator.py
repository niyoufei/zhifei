from __future__ import annotations

from typing import Any

from .engine import PrecheckEngine
from .models import PrecheckContext
from .result import EvaluationResult


def evaluate(context: dict[str, Any]) -> EvaluationResult:
    resolved_context = PrecheckContext.from_dict(context)
    return PrecheckEngine().evaluate(resolved_context)
