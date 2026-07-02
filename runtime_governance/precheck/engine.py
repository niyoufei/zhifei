from __future__ import annotations

from .models import PrecheckContext
from .result import Decision, EvaluationResult, RuleOutcome
from .rules import git_rules, lock_rules, port_rules, process_rules, runtime_rules


class PrecheckEngine:
    rule_groups = (
        git_rules,
        runtime_rules,
        port_rules,
        process_rules,
        lock_rules,
    )

    def evaluate(self, context: PrecheckContext) -> EvaluationResult:
        outcomes: list[RuleOutcome] = []
        score = 100

        for rule_group in self.rule_groups:
            outcome = rule_group.evaluate(context)
            outcomes.append(outcome)
            score += outcome.score_delta

        score = max(0, min(100, score))
        reasons = [reason for outcome in outcomes for reason in outcome.reasons]
        actions = [action for outcome in outcomes for action in outcome.actions]
        decision = self._decision(score, outcomes)

        return EvaluationResult(
            decision=decision,
            score=score,
            reasons=reasons,
            actions=actions,
            outcomes=outcomes,
        )

    @staticmethod
    def _decision(score: int, outcomes: list[RuleOutcome]) -> Decision:
        if any(outcome.hard_block for outcome in outcomes):
            return Decision.BLOCK
        if score >= 85:
            return Decision.ALLOW
        if score >= 60:
            return Decision.CONDITIONAL
        return Decision.BLOCK
