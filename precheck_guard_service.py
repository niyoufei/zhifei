# -*- coding: utf-8 -*-
"""
PreCheck Guard 服务（V1）
- 规则文件来源：kg_config.json -> precheck_guard_rules
- 输入：payload(请求体dict) + project_profile(dict)
- 输出：evaluation(dict)，并可用于 /compose 前置阻断
- 说明：先实现“保守型可追溯阻断”，后续再扩展为完整规则解释器
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import kg_loader


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _stable_sha256(obj: Any) -> str:
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8", "replace")
    return hashlib.sha256(data).hexdigest()


def _is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return (v.strip() == "")
    if isinstance(v, (list, tuple, set, dict)):
        return (len(v) == 0)
    return False


def _humanize(evaluation: Dict[str, Any]) -> str:
    passed = evaluation.get("passed", False)
    lines: List[str] = []
    lines.append(f"PreCheck Guard 结果：{'通过' if passed else '阻断'}")
    lines.append(f"- rule_path: {evaluation.get('rule_path')}")
    lines.append(f"- rule_sha256: {evaluation.get('rule_sha256')}")
    lines.append(f"- project_profile_decision: {evaluation.get('project_profile_decision')}")
    lines.append("")
    lines.append("命中问题：")
    reasons = evaluation.get("reasons") or []
    if not reasons:
        lines.append("- 无")
    else:
        for r in reasons:
            code = r.get("code")
            msg = r.get("message")
            sev = r.get("severity")
            lines.append(f"- [{sev}] {code}: {msg}")
    lines.append("")
    lines.append("建议动作：")
    actions = evaluation.get("suggested_actions") or []
    if not actions:
        lines.append("- 无")
    else:
        for a in actions:
            lines.append(f"- {a}")
    return "\n".join(lines)


def run_precheck_guard(payload: Dict[str, Any], project_profile: Dict[str, Any]) -> Dict[str, Any]:
    cfg = kg_loader.load_kg_config()
    rule_path: Path = kg_loader.get_precheck_guard_rule_path(cfg)

    raw_rules: Dict[str, Any] = {}
    rule_sha256 = None
    if rule_path.exists():
        rb = rule_path.read_bytes()
        rule_sha256 = _sha256_bytes(rb)
        try:
            raw_rules = json.loads(rb.decode("utf-8", "replace"))
        except Exception:
            raw_rules = {"_raw_text": rb.decode("utf-8", "replace")}

    details: List[Dict[str, Any]] = []
    reasons: List[Dict[str, Any]] = []
    suggested_actions: List[str] = []

    # A) 基础字段检查（兜底，避免空请求）
    topic = payload.get("topic")
    ok_topic = (isinstance(topic, str) and topic.strip() != "")
    details.append({
        "check_id": "TOPIC_REQUIRED",
        "passed": ok_topic,
        "observed": topic,
        "message": "topic 不能为空（用于项目意图/专业方向判定）"
    })
    if not ok_topic:
        reasons.append({"code": "TOPIC_EMPTY", "severity": "ERROR", "message": "请求字段 topic 为空"})
        suggested_actions.append("补充 topic，例如：'合肥市政排水工程施工组织设计（雨污分流）'")

    outline = payload.get("outline")
    ok_outline = (isinstance(outline, list) and len(outline) > 0)
    details.append({
        "check_id": "OUTLINE_REQUIRED",
        "passed": ok_outline,
        "observed": outline,
        "message": "outline 至少包含 1 个条目（用于章节/组稿边界）"
    })
    if not ok_outline:
        reasons.append({"code": "OUTLINE_EMPTY", "severity": "ERROR", "message": "请求字段 outline 为空或非列表"})
        suggested_actions.append("补充 outline，例如：['工程概况','施工准备','施工方法','质量安全']")

    # B) 项目画像决策门控（当前阶段最关键）
    pp_decision = (project_profile or {}).get("decision")
    ok_pp = (pp_decision != "block_and_review")
    details.append({
        "check_id": "PROJECT_PROFILE_DECISION",
        "passed": ok_pp,
        "observed": pp_decision,
        "message": "项目画像 decision=block_and_review 时，禁止进入生成（需补充信息或人工确认）"
    })
    if not ok_pp:
        reasons.append({
            "code": "LOW_CONFIDENCE_PROFILE",
            "severity": "ERROR",
            "message": "项目画像置信度不足（decision=block_and_review），不允许继续生成"
        })
        suggested_actions.append("补充项目关键信息（工程类型/地区/规模/关键词），或在请求中显式提供 project_type")
        suggested_actions.append("将 topic 替换为包含明确专业关键词的描述（如：'装修'/'幕墙'/'市政排水'/'市政道路'/'机电'等）")

    # C) 尝试读取 Guard 规则文件中的“显式必填字段”列表（若存在）
    # 兼容：required_fields: ["project_name", ...]
    rf = None
    if isinstance(raw_rules, dict):
        rf = raw_rules.get("required_fields")
    if isinstance(rf, list) and rf:
        missing = []
        for f in rf:
            if not isinstance(f, str):
                continue
            if _is_empty(payload.get(f)):
                missing.append(f)
        details.append({
            "check_id": "REQUIRED_FIELDS_FROM_RULE",
            "passed": (len(missing) == 0),
            "observed": {"missing": missing},
            "message": "来自 PreCheck Guard 规则文件的必填字段检查"
        })
        if missing:
            reasons.append({
                "code": "MISSING_REQUIRED_FIELDS",
                "severity": "ERROR",
                "message": f"缺少必填字段：{', '.join(missing)}"
            })
            suggested_actions.append(f"按 Guard 规则补齐字段：{', '.join(missing)}")

    passed = all(d.get("passed") for d in details)

    evaluation = {
        "passed": passed,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),

        "rule_path": str(rule_path),
        "rule_sha256": rule_sha256,

        "input_sha256": _stable_sha256(payload),
        "project_profile_decision": pp_decision,

        "reasons": reasons,
        "suggested_actions": suggested_actions,
        "details": details,
    }
    evaluation["human_readable"] = _humanize(evaluation)
    return evaluation


__all__ = ["run_precheck_guard"]
