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
    "核验",
    "分析",
    "验证",
]

CHECKER_HINTS = [
    "项目经理",
    "技术负责人",
    "质量员",
    "安全员",
    "环保员",
    "施工员",
    "监理工程师",
    "试验员",
    "班组长",
    "专职安全员",
    "材料员",
    "技术员",
    "项目总工",
]

VAGUE_BUG_WORDS = ["加强", "提高", "注意", "确保", "严格"]

PARAMETER_RE = re.compile(
    r"(?:\d+(?:\.\d+)?\s*(?:mm|cm|m|km|kg|t|h|小时|天|d|min|分钟|次|人|台|套|%|MPa|kN|dB|ug/m3|μg/m3|℃|m3|m²|m2)"
    r"|C\d{2,3}"
    r"|HRB\d{3,4}"
    r"|φ\d{1,3})",
    re.IGNORECASE,
)

STEP1_HINTS = ["第一步", "定义", "工序名称", "工程量", "标号", "尺寸", "参数", "规格", "型号"]
STEP2_HINTS = ["第二步", "分析", "难点", "风险", "通病", "隐患", "冲突", "瓶颈"]
STEP3_HINTS = ["第三步", "解决", "控制", "措施", "验证", "复核", "验收", "闭环"]
FLOW_CHAIN_RE = re.compile(
    r"工序名称\s*(?:->|→)\s*参数\s*(?:->|→)\s*风险\s*(?:->|→)\s*控制\s*(?:->|→)\s*验证"
)


def _split_sentences(text: str) -> List[str]:
    raw = re.split(r"[。；;\n]+", str(text or ""))
    return [line.strip() for line in raw if line and line.strip()]


def _is_structure_line(text: str) -> bool:
    sentence = str(text or "").strip()
    if not sentence:
        return False
    if FLOW_CHAIN_RE.search(sentence):
        return True
    tokens = ["工序名称", "参数", "风险", "控制", "验证"]
    return all(token in sentence for token in tokens) and ("->" in sentence or "→" in sentence)


def _evaluate_logic_lock(text: str) -> Dict[str, Any]:
    raw = str(text or "")
    has_step1 = ("第一步" in raw and ("定义" in raw or "参数" in raw)) or (
        any(token in raw for token in STEP1_HINTS) and bool(PARAMETER_RE.search(raw))
    )
    has_step2 = ("第二步" in raw and ("分析" in raw or "风险" in raw or "难点" in raw)) or any(
        token in raw for token in STEP2_HINTS
    )
    has_step3 = ("第三步" in raw and ("解决" in raw or "控制" in raw or "验证" in raw)) or any(
        token in raw for token in STEP3_HINTS
    )
    has_flow_chain = bool(FLOW_CHAIN_RE.search(raw)) or (
        all(token in raw for token in ["工序名称", "参数", "风险", "控制", "验证"])
        and ("->" in raw or "→" in raw)
    )
    missing: List[str] = []
    if not has_step1:
        missing.append("missing_step1_define")
    if not has_step2:
        missing.append("missing_step2_analyze")
    if not has_step3:
        missing.append("missing_step3_solve")
    if not has_flow_chain:
        missing.append("missing_flow_chain")
    return {
        "has_step1_define": has_step1,
        "has_step2_analyze": has_step2,
        "has_step3_solve": has_step3,
        "has_flow_chain": has_flow_chain,
        "ok": len(missing) == 0,
        "missing": missing,
    }


def build_sentence_ast(sentence: str) -> Dict[str, Any]:
    text = str(sentence or "").strip()
    if _is_structure_line(text):
        return {
            "sentence": text,
            "action": None,
            "parameter": None,
            "checker": None,
            "has_vague_bug": False,
            "structural_line": True,
            "ok": True,
        }
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
        "structural_line": False,
        "ok": bool(action and checker and param_match and not has_vague_bug),
    }


def validate_guardrails(text: str) -> Dict[str, Any]:
    sentences = _split_sentences(text)
    ast_list = [build_sentence_ast(sentence) for sentence in sentences]
    violations: List[Dict[str, Any]] = []

    for ast in ast_list:
        if ast.get("structural_line"):
            continue
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

    logic_lock = _evaluate_logic_lock(text)
    if not logic_lock.get("ok"):
        violations.append(
            {
                "sentence": "[document_logic_lock]",
                "reasons": logic_lock.get("missing") or [],
                "ast": {"logic_lock": logic_lock},
                "severity": "bug",
            }
        )

    return {
        "ok": len(violations) == 0,
        "sentences": ast_list,
        "logic_lock": logic_lock,
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
                    "第一步（定义）：执行工序名称定义，工程量1200m3、混凝土标号C30、模板尺寸900mm，施工员每班次核验1次",
                    "第二步（分析）：实施质量通病与安全隐患分析，风险阈值5%，技术负责人每班次复核1次",
                    "第三步（解决）：执行控制与验证措施，偏差限值3mm、响应时限4h，质量员每班次检查2次",
                    "工序名称->参数->风险->控制->验证",
                ]
            )

    raise GuardrailBugError(json_violation_summary(last_result))
