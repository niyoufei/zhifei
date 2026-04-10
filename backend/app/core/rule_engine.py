# -*- coding: utf-8 -*-
import json
import re
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_RULE_EXECUTION_LOG_PATH = _PROJECT_ROOT / "runtime" / "logs" / "rule-execution.log"


def _stable_rule_name(rule: dict) -> str:
    for key in ("name", "id"):
        value = str(rule.get(key) or "").strip()
        if value:
            return re.sub(r"\s+", "_", value)
    return "unnamed_rule"


def _append_rule_execution_log(success: bool, rule_name: str) -> None:
    _RULE_EXECUTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"success={'true' if success else 'false'} time={timestamp} rule={rule_name}\n"
    with _RULE_EXECUTION_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line)

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

        if not self.rules:
            _append_rule_execution_log(False, "rule_engine_empty")
            return {
                "total_score": 0.0,
                "details": []
            }

        for rule in self.rules:
            rule_name = _stable_rule_name(rule)
            matched = False
            try:
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
            except Exception:
                _append_rule_execution_log(False, rule_name)
                raise
            else:
                _append_rule_execution_log(matched, rule_name)

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
