from __future__ import annotations

from ..models import PrecheckContext
from ..result import RuleOutcome


REQUIRED_LOCKS = ("pid_exists", "log_lock", "runtime_lock")


def evaluate(context: PrecheckContext) -> RuleOutcome:
    reasons: list[str] = []
    actions: list[str] = []
    missing: list[str] = []
    active: list[str] = []

    for name in REQUIRED_LOCKS:
        if name not in context.runtime_locks:
            missing.append(name)
        elif context.runtime_locks[name]:
            active.append(name)

    if missing:
        reasons.append("missing runtime lock states: " + ", ".join(missing))
    if active:
        reasons.append("runtime locks are active: " + ", ".join(active))
        actions.append("Clear runtime lock markers before runtime start.")

    cleanup_allowed = context.allow_conditional_cleanup and active and not missing
    hard_block = bool(missing) or (bool(active) and not cleanup_allowed)

    return RuleOutcome(
        name="lock_rules",
        score_delta=-25 if reasons else 0,
        hard_block=hard_block,
        reasons=reasons,
        actions=actions if cleanup_allowed or hard_block else [],
    )
