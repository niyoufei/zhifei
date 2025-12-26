# -*- coding: utf-8 -*-
import json
from pathlib import Path

class RuleEngine:
    def __init__(self, rule_path: str = "rules_sample.json"):
        self.rules = self._load_rules(rule_path)

    def _load_rules(self, rule_path: str):
        path = Path(rule_path)
        if not path.exists():
            raise FileNotFoundError(f"规则文件不存在: {rule_path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def evaluate(self, text: str):
        results = []
        total_score = 0.0

        for rule in self.rules:
            matched = all(keyword in text for keyword in rule["criteria"])
            score = rule["weight"] if matched else 0
            results.append({
                "rule_id": rule["id"],
                "name": rule["name"],
                "matched": matched,
                "score": score,
                "criteria": rule["criteria"],
                "description": rule["description"]
            })
            total_score += score

        return {
            "total_score": round(total_score, 2),
            "details": results
        }


# 示例运行（用于快速验证规则引擎功能）
if __name__ == "__main__":
    engine = RuleEngine("rules_sample.json")
    test_text = "本报告包含标题、摘要、正文与结论部分，并附有引用来源。"
    result = engine.evaluate(test_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))

