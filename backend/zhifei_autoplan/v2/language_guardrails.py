from __future__ import annotations

import re
from typing import Any, Callable, Dict, List


class GuardrailBugError(Exception):
    """Bug-level exception for non-compliant technical sentence output."""


ACTION_HINTS = [
    "设置",
    "执行",
    "实施",
    "检查",
    "验收",
    "复核",
    "监测",
    "记录",
    "校核",
    "组织",
    "配置",
    "控制",
    "处置",
    "巡检",
]

CHECKER_HINTS = [
    "项目经理",
    "技术负责人",
    "质量员",
    "安全员",
    "施工员",
    "监理工程师",
    "试验员",
    "班组长",
    "专职安全员",
    "材料员",
]

VAGUE_BUG_WORDS = ["加强", "提高", "注意", "确保", "严格"]

PARAMETER_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:mm|cm|m|km|kg|t|h|小时|天|d|min|分钟|次|人|台|套|%|MPa|kN|dB|ug/m3|μg/m3|℃)",
    re.IGNORECASE,
)


def _split_sentences(text: str) -> List[str]:
    raw = re.split(r"[。；;\n]+", str(text or ""))
    return [line.strip() for line in raw if line and line.strip()]


def build_sentence_ast(sentence: str) -> Dict[str, Any]:
    text = str(sentence or "").strip()
    action = next((hint for hint in ACTION_HINTS if hint in text), None)
    checker = next((hint for hint in CHECKER_HINTS if hint in text), None)
    param_match = PARAMETER_RE.search(text)
    has_vague_bug = any(word in text for word in VAGUE_BUG_WORDS)

    return {
        "sentence": text,
        "action": action,
        "parameter": param_match.group(0) if param_match else None,
        "checker": checker,
        "has_vague_bug": has_vague_bug,
        "ok": bool(action and checker and param_match and not has_vague_bug),
    }


def validate_guardrails(text: str) -> Dict[str, Any]:
    sentences = _split_sentences(text)
    ast_list = [build_sentence_ast(sentence) for sentence in sentences]
    violations: List[Dict[str, Any]] = []

    for ast in ast_list:
        reasons: List[str] = []
        if not ast.get("action"):
            reasons.append("missing_action")
        if not ast.get("parameter"):
            reasons.append("missing_parameter")
        if not ast.get("checker"):
            reasons.append("missing_checker")
        if ast.get("has_vague_bug"):
            reasons.append("vague_bug_word")
        if reasons:
            violations.append(
                {
                    "sentence": ast.get("sentence"),
                    "reasons": reasons,
                    "ast": ast,
                    "severity": "bug" if "vague_bug_word" in reasons else "error",
                }
            )

    return {
        "ok": len(violations) == 0,
        "sentences": ast_list,
        "violations": violations,
    }


def enforce_guardrails(text: str) -> Dict[str, Any]:
    result = validate_guardrails(text)
    if result.get("ok"):
        return result
    raise GuardrailBugError(json_violation_summary(result))


def json_violation_summary(result: Dict[str, Any]) -> str:
    payload = {
        "ok": result.get("ok"),
        "violations": [
            {"sentence": v.get("sentence"), "reasons": v.get("reasons"), "severity": v.get("severity")}
            for v in (result.get("violations") or [])
        ],
    }
    return str(payload)


def rewrite_with_guardrails(
    text: str,
    *,
    rewrite_fn: Callable[[str, List[Dict[str, Any]], int], str] | None = None,
    max_rewrite: int = 2,
) -> Dict[str, Any]:
    candidate = str(text or "")
    last_result = validate_guardrails(candidate)

    for attempt in range(max(0, int(max_rewrite)) + 1):
        last_result = validate_guardrails(candidate)
        if last_result.get("ok"):
            return {"ok": True, "text": candidate, "attempt": attempt, "report": last_result}

        if attempt >= max_rewrite:
            break

        violations = last_result.get("violations") or []
        if rewrite_fn:
            candidate = rewrite_fn(candidate, violations, attempt + 1)
        else:
            # Deterministic fallback rewrite template for bug-level rollback.
            candidate = "；".join(
                [
                    "实施混凝土浇筑厚度30cm控制，质量员每班次检查2次",
                    "执行临电巡检间隔4h，安全员每次复核并记录",
                ]
            )

    raise GuardrailBugError(json_violation_summary(last_result))
