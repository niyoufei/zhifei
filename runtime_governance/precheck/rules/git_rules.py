from __future__ import annotations

from ..models import PrecheckContext
from ..result import RuleOutcome


def evaluate(context: PrecheckContext) -> RuleOutcome:
    reasons: list[str] = []

    checks = (
        (context.branch == "main", "branch is not main"),
        (context.head == context.expected_head, "head does not match expected_head"),
        (context.origin_head == context.expected_head, "origin_head does not match expected_head"),
        (context.head == context.origin_head, "head does not match origin_head"),
        (context.head_tree == context.expected_tree, "head_tree does not match expected_tree"),
        (context.origin_tree == context.expected_tree, "origin_tree does not match expected_tree"),
        (context.working_tree_clean, "working tree is not clean"),
        (context.local_tag_target == context.expected_head, "local tag does not match expected_head"),
        (context.remote_tag_target == context.expected_head, "remote tag does not match expected_head"),
    )

    for passed, reason in checks:
        if not passed:
            reasons.append(reason)

    return RuleOutcome(
        name="git_rules",
        score_delta=-40 if reasons else 0,
        hard_block=bool(reasons),
        reasons=reasons,
        actions=["Restore repository baseline before runtime precheck."] if reasons else [],
    )
