from __future__ import annotations

from ..models import PrecheckContext
from ..result import RuleOutcome


CONTROLLED_PROCESSES = ("uvicorn", "streamlit", "ollama")


def evaluate(context: PrecheckContext) -> RuleOutcome:
    reasons: list[str] = []
    actions: list[str] = []
    missing: list[str] = []
    active: list[str] = []

    for name in CONTROLLED_PROCESSES:
        if name not in context.processes:
            missing.append(name)
        elif context.processes[name]:
            active.append(name)

    if missing:
        reasons.append("missing controlled process keys: " + ", ".join(missing))
    if active:
        reasons.append("controlled processes already active: " + ", ".join(active))
        actions.append("Stop controlled runtime processes before start.")

    cleanup_allowed = context.allow_conditional_cleanup and active and not missing
    hard_block = bool(missing) or (bool(active) and not cleanup_allowed)

    return RuleOutcome(
        name="runtime_rules",
        score_delta=-25 if reasons else 0,
        hard_block=hard_block,
        reasons=reasons,
        actions=actions if cleanup_allowed or hard_block else [],
    )
