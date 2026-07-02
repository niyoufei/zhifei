from __future__ import annotations

from ..models import PrecheckContext
from ..result import RuleOutcome


CONTROLLED_PROCESSES = {"uvicorn", "streamlit", "ollama"}


def evaluate(context: PrecheckContext) -> RuleOutcome:
    reasons: list[str] = []
    actions: list[str] = []
    missing = sorted(CONTROLLED_PROCESSES.difference(context.processes))
    unknown_active = sorted(
        name for name, active in context.processes.items() if name not in CONTROLLED_PROCESSES and active
    )

    if missing:
        reasons.append("controlled process keys are not explicit: " + ", ".join(missing))
    if unknown_active:
        reasons.append("unknown controlled process markers are active: " + ", ".join(unknown_active))
        actions.append("Review and clear unknown active process markers before runtime start.")

    cleanup_allowed = context.allow_conditional_cleanup and unknown_active and not missing
    hard_block = bool(missing) or (bool(unknown_active) and not cleanup_allowed)

    return RuleOutcome(
        name="process_rules",
        score_delta=-20 if reasons else 0,
        hard_block=hard_block,
        reasons=reasons,
        actions=actions if cleanup_allowed or hard_block else [],
    )
