from __future__ import annotations

from ..models import PrecheckContext
from ..result import RuleOutcome


REQUIRED_PORTS = ("8010", "8501")


def evaluate(context: PrecheckContext) -> RuleOutcome:
    reasons: list[str] = []
    actions: list[str] = []
    missing: list[str] = []
    blocked: list[str] = []

    for port in REQUIRED_PORTS:
        state = context.ports.get(port)
        if state is None:
            missing.append(port)
        elif state != "free":
            blocked.append(port)

    if missing:
        reasons.append("missing port states: " + ", ".join(missing))
    if blocked:
        reasons.append("ports are not free: " + ", ".join(blocked))
        actions.append("Free required ports before runtime start.")

    cleanup_allowed = context.allow_conditional_cleanup and blocked and not missing
    hard_block = bool(missing) or (bool(blocked) and not cleanup_allowed)

    return RuleOutcome(
        name="port_rules",
        score_delta=-25 if reasons else 0,
        hard_block=hard_block,
        reasons=reasons,
        actions=actions if cleanup_allowed or hard_block else [],
    )
