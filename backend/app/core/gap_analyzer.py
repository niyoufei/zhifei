# -*- coding: utf-8 -*-
from typing import Dict, Any, List
from .rule_engine import RuleEngine

class GapAnalyzer:
    def __init__(self, rule_path: str = "rules_sample.json"):
        self.engine = RuleEngine(rule_path)

    def analyze(self, text: str) -> Dict[str, Any]:
        covered_weight = 0.0
        total_weight = 0.0
        details: List[Dict[str, Any]] = []
        for rule in self.engine.rules:
            total_weight += rule["weight"]
            missing = [k for k in rule["criteria"] if k not in text]
            matched = (len(missing) == 0)
            if matched:
                covered_weight += rule["weight"]
            details.append({
                "rule_id": rule["id"],
                "name": rule["name"],
                "weight": rule["weight"],
                "criteria": rule["criteria"],
                "matched": matched,
                "missing_criteria": missing
            })
        coverage_ratio = round(covered_weight / total_weight, 4) if total_weight > 0 else 0.0
        return {
            "summary": {
                "covered_weight": round(covered_weight, 4),
                "total_weight": round(total_weight, 4),
                "coverage_ratio": coverage_ratio
            },
            "details": details
        }
