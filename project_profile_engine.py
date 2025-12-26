"""
ProjectProfileEngine
--------------------
负责读取《ZhiFei-Auto-Project-Profile-Rules-V1.1.json》，
后续根据招标文件 / 图纸 / 清单自动生成项目画像（ProjectProfile）。
当前版本先仅完成规则加载与基本结构，后续再逐步实现具体逻辑。
"""

import json
from pathlib import Path
from typing import Any, Dict

from kg_loader import get_project_profile_rule_path


class ProjectProfileEngine:
    def __init__(self) -> None:
        self.rule_path: Path = get_project_profile_rule_path()
        self.rules: Dict[str, Any] = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        """读取项目画像规则 JSON。"""
        if not self.rule_path.exists():
            raise FileNotFoundError(f"Project profile rule file not found: {self.rule_path}")
        with self.rule_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    # 占位：后续根据需要逐步实现
    def debug_summary(self) -> Dict[str, Any]:
        """
        返回规则文件中的核心元数据摘要，便于在 /debug 接口或日志中查看。
        不依赖任何外部输入，纯查看。
        """
        meta = self.rules.get("meta", {})
        strategy = self.rules.get("strategy", {})
        return {
            "rule_path": str(self.rule_path),
            "meta": meta,
            "strategy_keys": list(strategy.keys())
        }
