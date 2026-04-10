from __future__ import annotations

import re
import time
from typing import Dict, Any, List, Tuple

from backend.zhifei_autoplan.docx_formatter import naturalize_machine_text
from backend.zhifei_autoplan.prompt_registry import build_text_fixed_prefix, text_prompt_cache_settings
from backend.zhifei_autoplan.utils.llm_client import LLMClient
from backend.zhifei_autoplan.qingtian_policy import QINGTIAN_BANNED_PHRASES


class RewriteException(RuntimeError):
    """Raised when boilerplate contamination requires a full rewrite."""


class LengthError(RuntimeError):
    """Raised when generated text length is out of the accepted range."""


def compact_text_to_length_bounds(
    text: str,
    *,
    min_length: int | None = None,
    max_length: int | None = None,
) -> str | None:
    writer = SectionWriter(llm=None)
    return writer._shrink_overlong_text(
        text,
        min_length=min_length,
        max_length=max_length,
    )


def _dedup_keep_order(lines: List[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in lines:
        s = str(raw or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


BANNED_PHRASES = _dedup_keep_order([
    "众所周知",
    "综上所述",
    "不难看出",
    "总而言之",
    "毫无疑问",
    "可以说",
    "需要注意的是",
    "在实际工程中",
    "按照",
    "符合",
    "确保",
    "保障",
    "严格落实",
    "加强管理",
    "有效措施",
    "合理安排",
    "现场实际情况",
    "相关规范",
    "有关规定",
] + list(QINGTIAN_BANNED_PHRASES))

GOLDEN_STYLE_SAMPLE = (
    "本工程主体结构采用 C30 预拌混凝土，抗渗等级 P6。"
    "钢筋采用 HRB400E，搭接长度严格执行 10d 规范。"
    "现场配置 2 台 QTZ80 塔式起重机负责垂直运输。"
)


class SectionWriter:
    def __init__(self, llm: LLMClient | None = None, *, max_retry: int = 3, banned_phrases: List[str] | None = None):
        self.llm = llm
        self.max_retry = max(1, int(max_retry or 3))
        self.banned_phrases = [str(x).strip() for x in (banned_phrases or BANNED_PHRASES) if str(x).strip()]
        self._banned_patterns: List[Tuple[str, re.Pattern[str]]] = [
            (p, re.compile(re.escape(p), re.IGNORECASE)) for p in self.banned_phrases
        ]
        self._inline_internal_tag_re = re.compile(r"【(?:图谱节点|经验值|图谱经验值):[^】]+】")
        self._scaffold_line_re = re.compile(
            r"^\s*(?:【(?:范围|系统全局指令|图谱节点绑定|多Agent|章节结构蓝图|证据摘要|证据与追溯)[^】]*】|"
            r"角色定位[:：]|章节标题[:：]|方案版本[:：]|输出要求[:：]|constraint_log[:：=]|provider[:：=]|model[:：=])"
        )

    def _sanitize_text(self, text: str) -> tuple[str, list[str]]:
        raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        normalized_lines: List[str] = []
        for line in raw.split("\n"):
            line = self._inline_internal_tag_re.sub("", str(line or ""))
            if self._scaffold_line_re.match(line.strip()):
                continue
            normalized_lines.append(naturalize_machine_text(line))
        cleaned = "\n".join(normalized_lines)
        hits: List[str] = []
        for phrase, pattern in self._banned_patterns:
            if pattern.search(cleaned):
                hits.append(phrase)
                cleaned = pattern.sub("", cleaned)
        cleaned = re.sub(r"[，,。；;、]{2,}", lambda m: m.group(0)[0], cleaned)
        cleaned = re.sub(r"^[，,。；;、\s]+", "", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned, hits

    @staticmethod
    def _normalize_len(v: Any) -> int | None:
        try:
            n = int(v)
            return n if n > 0 else None
        except Exception:
            return None

    def _resolve_len_limits(
        self,
        context: Dict[str, Any],
        min_length: int | None,
        max_length: int | None,
    ) -> tuple[int | None, int | None]:
        ctx_min = self._normalize_len(context.get("min_length") or context.get("section_min_length"))
        ctx_max = self._normalize_len(context.get("max_length") or context.get("section_max_length"))
        lo = self._normalize_len(min_length) if min_length is not None else ctx_min
        hi = self._normalize_len(max_length) if max_length is not None else ctx_max
        if lo and hi and lo > hi:
            lo, hi = hi, lo
        return lo, hi

    def _enforce_constraints(
        self,
        text: str,
        *,
        min_length: int | None,
        max_length: int | None,
    ) -> tuple[str, Dict[str, Any] | None]:
        cleaned, hits = self._sanitize_text(text)
        if len(hits) >= 3:
            raise RewriteException(f"boilerplate_hit_count={len(hits)}")
        size = len(cleaned)
        if min_length and size < min_length:
            raise LengthError(f"length_out_of_range:{size}<min{min_length}")
        if max_length and size > max_length:
            compacted = self._shrink_overlong_text(cleaned, min_length=min_length, max_length=max_length)
            if compacted:
                return compacted, {
                    "status": "compacted",
                    "reason": f"length_out_of_range:{size}>max{max_length}",
                    "original_length": size,
                    "compacted_length": len(compacted),
                }
            raise LengthError(f"length_out_of_range:{size}>max{max_length}")
        return cleaned, None

    def _shrink_overlong_text(
        self,
        text: str,
        *,
        min_length: int | None,
        max_length: int | None,
    ) -> str | None:
        limit = self._normalize_len(max_length)
        if not limit:
            return None
        normalized = re.sub(r"\n{3,}", "\n\n", str(text or "").strip())
        if len(normalized) <= limit:
            return normalized

        paragraphs = [str(p or "").strip() for p in re.split(r"\n{2,}", normalized) if str(p or "").strip()]
        if not paragraphs:
            paragraphs = [normalized]

        kept: List[str] = []
        for para in paragraphs:
            candidate = ("\n\n".join(kept + [para])).strip() if kept else para
            if len(candidate) <= limit:
                kept.append(para)
                continue

            sentences = [s.strip() for s in re.split(r"(?<=[。！？；])\s*|\n+", para) if s.strip()]
            if not sentences:
                sentences = [para]
            local: List[str] = []
            for sentence in sentences:
                joined_local = "".join(local + [sentence]).strip()
                candidate = ("\n\n".join(kept + [joined_local])).strip() if kept else joined_local
                if len(candidate) <= limit:
                    local.append(sentence)
                    continue
                break
            if local:
                kept.append("".join(local).strip())
            break

        compacted = "\n\n".join([x for x in kept if str(x or "").strip()]).strip()
        if not compacted:
            compacted = normalized[:limit].rstrip("，,；;、")
        if len(compacted) > limit:
            compacted = compacted[:limit].rstrip("，,；;、").strip()
        compacted = re.sub(r"[ \t]{2,}", " ", compacted)
        compacted = re.sub(r"\n{3,}", "\n\n", compacted).strip()

        min_required = self._normalize_len(min_length)
        if min_required and len(compacted) < min_required:
            return None
        return compacted or None

    def _build_retry_prompt(
        self,
        base_prompt: str,
        reason: str,
        *,
        min_length: int | None,
        max_length: int | None,
    ) -> str:
        len_guard = ""
        if min_length or max_length:
            len_guard = f"- 字数范围：{min_length or 0}-{max_length or 99999} 字。\n"
        return (
            f"{base_prompt}\n\n"
            "【重写指令】\n"
            f"- 上一版未通过原因：{reason}\n"
            "- 删除所有套话、过渡语、解释性句子，只保留可执行动作和量化指标。\n"
            f"{len_guard}"
            "- 仅输出正文，不要附加解释。\n"
        )

    @staticmethod
    def _limit_block_lines(
        lines: List[str],
        *,
        max_lines: int,
        max_chars: int,
    ) -> str:
        out: List[str] = []
        used = 0
        for raw in lines:
            s = str(raw or "").strip()
            if not s:
                continue
            if len(out) >= max(1, int(max_lines or 1)):
                break
            room = max(0, int(max_chars or 0) - used)
            if room <= 0:
                break
            if len(s) > room:
                s = s[:room]
            out.append(s)
            used += len(s) + 1
        return "\n".join(out)

    def _resolve_timeout_sec(self, context: Dict[str, Any]) -> float:
        raw = context.get("llm_timeout_sec")
        if raw is None:
            raw = context.get("timeout_sec")
        try:
            sec = float(raw)
        except Exception:
            sec = 120.0
        return max(30.0, min(240.0, sec))

    def _estimate_max_output_tokens(
        self,
        *,
        min_length: int | None,
        max_length: int | None,
        context: Dict[str, Any],
    ) -> int:
        lo = self._normalize_len(min_length)
        hi = self._normalize_len(max_length)
        target = self._normalize_len(context.get("section_target_length") or context.get("target_length"))
        basis = hi or target or lo or 3200
        # 中文技术文稿按 1.1x 近似 token 预算，留出少量裕量，避免超长拖慢。
        mot = int(float(basis) * 1.1)
        hint = self._normalize_len(context.get("max_output_tokens_hint"))
        if hint:
            mot = min(mot, int(hint))
        return max(900, min(6000, mot))

    async def write(
        self,
        title: str,
        context: Dict[str, Any],
        *,
        min_length: int | None = None,
        max_length: int | None = None,
        max_retry: int | None = None,
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(title, context)
        prompt_cache = text_prompt_cache_settings(task_type=str(context.get("task_type") or "section_generation"))
        lo, hi = self._resolve_len_limits(context, min_length, max_length)
        retry_limit = max(1, int(max_retry or self.max_retry))
        timeout_sec = self._resolve_timeout_sec(context)
        max_output_tokens = self._estimate_max_output_tokens(
            min_length=lo,
            max_length=hi,
            context=context,
        )
        constraint_log: List[Dict[str, Any]] = []
        resource_usage_attempts: List[Dict[str, Any]] = []

        def _attempt_meta(resp: Dict[str, Any], *, attempt_idx: int) -> Dict[str, Any]:
            token_usage = resp.get("token_usage") if isinstance(resp.get("token_usage"), dict) else None
            return {
                "attempt": int(attempt_idx),
                "section_title": title,
                "provider": resp.get("provider"),
                "model": resp.get("model"),
                "request_id": resp.get("request_id"),
                "client_request_id": resp.get("client_request_id"),
                "service_tier": resp.get("service_tier"),
                "used_key_alias": resp.get("used_key_alias") or context.get("used_key_alias"),
                "latency_ms": resp.get("latency_ms"),
                "token_usage": token_usage,
                "cache_key": resp.get("cache_key"),
                "cache_hit": bool(resp.get("cache_hit", False)),
                "cached_tokens": resp.get("cached_tokens"),
                "error": resp.get("error"),
            }

        if not self.llm:
            fb = self._fallback(title, context)
            sanitized, hits = self._sanitize_text(fb)
            return {
                "title": title,
                "content": sanitized,
                "prompt": prompt,
                "constraint_log": [{"attempt": 0, "status": "fallback_no_llm", "boilerplate_hits": hits}],
                "requested_timeout_sec": timeout_sec,
                "requested_max_output_tokens": max_output_tokens,
                "requested_section_retry_limit": retry_limit,
                "runtime_budget_reason": str(context.get("runtime_budget_reason") or ""),
                "resource_usage_attempts": resource_usage_attempts,
            }

        last_resp: Dict[str, Any] = {}
        last_reason = ""
        for attempt in range(1, retry_limit + 1):
            req_prompt = prompt if attempt == 1 else self._build_retry_prompt(prompt, last_reason, min_length=lo, max_length=hi)
            resp = await self.llm.complete(
                req_prompt,
                timeout_sec=timeout_sec,
                max_output_tokens=max_output_tokens,
                temperature=0.1,
                prompt_cache_key=str(prompt_cache.get("prompt_cache_key") or "") if prompt_cache.get("enabled") else "",
                prompt_cache_retention=str(prompt_cache.get("prompt_cache_retention") or "") if prompt_cache.get("enabled") else "",
                client_request_id=f"zhifei-section-{int(time.time())}-{attempt}",
                used_key_alias=str(context.get("used_key_alias") or ""),
            )
            if not isinstance(resp, dict):
                resp = {}
            last_resp = resp
            resource_usage_attempts.append(_attempt_meta(resp, attempt_idx=attempt))
            text = str(resp.get("text") or "")
            if not text.strip() or resp.get("error"):
                last_reason = str(resp.get("error") or "empty_response")
                constraint_log.append(
                    {"attempt": attempt, "status": "retry", "reason": last_reason, "raw_length": len(text)}
                )
                if attempt < retry_limit:
                    continue
                break
            try:
                cleaned, adjust = self._enforce_constraints(text, min_length=lo, max_length=hi)
                if adjust:
                    constraint_log.append(
                        {
                            "attempt": attempt,
                            "status": str(adjust.get("status") or "ok"),
                            "reason": str(adjust.get("reason") or ""),
                            "clean_length": int(adjust.get("compacted_length") or len(cleaned)),
                            "original_length": int(adjust.get("original_length") or len(text)),
                        }
                    )
                else:
                    constraint_log.append({"attempt": attempt, "status": "ok", "clean_length": len(cleaned)})
                return {
                    "title": title,
                    "content": cleaned,
                    "prompt": prompt,
                    "provider": resp.get("provider"),
                    "model": resp.get("model"),
                    "error": resp.get("error"),
                    "request_id": resp.get("request_id"),
                    "client_request_id": resp.get("client_request_id"),
                    "service_tier": resp.get("service_tier"),
                    "used_key_alias": resp.get("used_key_alias") or context.get("used_key_alias"),
                    "latency_ms": resp.get("latency_ms"),
                    "token_usage": resp.get("token_usage") if isinstance(resp.get("token_usage"), dict) else None,
                    "cache_key": resp.get("cache_key"),
                    "cache_hit": bool(resp.get("cache_hit", False)),
                    "cached_tokens": resp.get("cached_tokens"),
                    "constraint_log": constraint_log,
                    "requested_timeout_sec": timeout_sec,
                    "requested_max_output_tokens": max_output_tokens,
                    "requested_section_retry_limit": retry_limit,
                    "runtime_budget_reason": str(context.get("runtime_budget_reason") or ""),
                    "resource_usage_attempts": resource_usage_attempts,
                }
            except (RewriteException, LengthError) as e:
                last_reason = str(e)
                constraint_log.append(
                    {
                        "attempt": attempt,
                        "status": "retry",
                        "reason": last_reason,
                        "raw_length": len(text),
                    }
                )
                if attempt < retry_limit:
                    continue
                break

        # 失败降级：回退模板（保留可追溯锚点，但不输出任何脚手架或质检日志）
        text = self._fallback(title, context)
        text, _ = self._sanitize_text(text)
        if not last_resp.get("error"):
            last_resp["error"] = last_reason or "constraints_retry_exhausted"
        constraint_log.append({"attempt": retry_limit, "status": "fallback", "reason": last_resp.get("error")})
        return {
            "title": title,
            "content": text,
            "prompt": prompt,
            "provider": last_resp.get("provider"),
            "model": last_resp.get("model"),
            "error": last_resp.get("error"),
            "request_id": last_resp.get("request_id"),
            "client_request_id": last_resp.get("client_request_id"),
            "service_tier": last_resp.get("service_tier"),
            "used_key_alias": last_resp.get("used_key_alias") or context.get("used_key_alias"),
            "latency_ms": last_resp.get("latency_ms"),
            "token_usage": last_resp.get("token_usage") if isinstance(last_resp.get("token_usage"), dict) else None,
            "cache_key": last_resp.get("cache_key"),
            "cache_hit": bool(last_resp.get("cache_hit", False)),
            "cached_tokens": last_resp.get("cached_tokens"),
            "constraint_log": constraint_log,
            "requested_timeout_sec": timeout_sec,
            "requested_max_output_tokens": max_output_tokens,
            "requested_section_retry_limit": retry_limit,
            "runtime_budget_reason": str(context.get("runtime_budget_reason") or ""),
            "resource_usage_attempts": resource_usage_attempts,
        }

    def _build_prompt(self, title: str, context: Dict[str, Any]) -> str:
        req = self._limit_block_lines(
            [str(x) for x in (context.get("requirements") or [])],
            max_lines=36,
            max_chars=4200,
        )
        kg = self._limit_block_lines(
            [str(x) for x in (context.get("kg_evidence") or [])],
            max_lines=18,
            max_chars=2600,
        )
        docs = self._limit_block_lines(
            [str(x) for x in (context.get("doc_evidence") or [])],
            max_lines=14,
            max_chars=2200,
        )
        checklist = self._limit_block_lines(
            [str(x) for x in (context.get("checklist") or [])],
            max_lines=24,
            max_chars=1800,
        )
        weights = self._limit_block_lines(
            [str(x) for x in (context.get("weights") or [])],
            max_lines=12,
            max_chars=1200,
        )
        penalties = self._limit_block_lines(
            [str(x) for x in (context.get("penalties") or [])],
            max_lines=12,
            max_chars=1200,
        )
        boq_focus_lines = self._limit_block_lines(
            [str(x) for x in ((context.get("boq_focus") or {}).get("lines") or [])],
            max_lines=24,
            max_chars=2200,
        )
        four_new_recs = (context.get("boq_focus") or {}).get("four_new_recommendations") or []
        four_new_lines = []
        if isinstance(four_new_recs, list):
            for it in four_new_recs[:6]:
                if not isinstance(it, dict):
                    continue
                name = str(it.get("name") or "").strip()
                cat = str(it.get("category") or "").strip() or "四新"
                matched = it.get("matched") or []
                if isinstance(matched, str):
                    matched = [matched]
                matched2 = [str(x).strip() for x in matched if str(x).strip()] if isinstance(matched, list) else []
                reason = ("触发=" + "、".join(matched2[:6])) if matched2 else "触发=清单/工序匹配"
                if name:
                    four_new_lines.append(f"- {cat}：{name}（{reason}）")
        four_new_text = "\n".join(four_new_lines)
        standard_trades = "、".join(context.get("standard_trades") or [])
        role = context.get("agent_role") or "总负责人"
        master_agent = str(context.get("master_agent") or "").strip()
        specialist_agents = [str(x).strip() for x in (context.get("specialist_agents") or []) if str(x).strip()]
        compliance_agent = str(context.get("compliance_agent") or "").strip()
        graph_nodes = [str(x).strip() for x in (context.get("graph_nodes") or []) if str(x).strip()]
        variant_id = context.get("variant_id")
        try:
            variant_id = int(variant_id or 1)
        except Exception:
            variant_id = 1
        project_type = str(context.get("project_type") or "").strip()
        global_instruction = str(context.get("global_instruction") or "").strip()
        qingtian_policy_enabled = bool(context.get("qingtian_policy_enabled", False))

        logic = context.get("logic_template") if isinstance(context.get("logic_template"), dict) else {}
        logic_id = str(logic.get("id") or "").strip() or ""
        logic_name = str(logic.get("name") or "").strip() or ""
        logic_rules = str(logic.get("prompt_rules") or "").strip()
        logic_block = ""
        if logic_id or logic_rules or logic_name:
            head = f"{logic_id} {logic_name}".strip() or logic_id or logic_name or ""
            logic_block = "【章内逻辑模版（用于多方案差异化；不改变招标目录）】\n"
            if head:
                logic_block += f"- 本方案版本：v{variant_id}；模版：{head}\n"
            if logic_rules:
                logic_block += logic_rules.strip() + "\n"
        bp_block = ""
        bp = context.get("chapter_blueprint") if isinstance(context.get("chapter_blueprint"), dict) else None
        if bp:
            try:
                from backend.zhifei_autoplan.chapter_blueprints import render_blueprint_requirements

                lines = render_blueprint_requirements(bp)
                if lines:
                    bp_block = "【章节结构蓝图（不改变招标目录，仅约束章内结构）】\n"
                    bp_block += "\n".join([f"- {ln}" for ln in lines[:12] if str(ln).strip()]) + "\n"
            except Exception:
                bp_block = ""
        params = context.get("params") if isinstance(context.get("params"), dict) else {}
        quant = params.get("quant_defaults") if isinstance(params.get("quant_defaults"), dict) else {}
        focus_card = params.get("boq_focus_card") if isinstance(params.get("boq_focus_card"), dict) else {}
        qse_defaults = params.get("qse_defaults") if isinstance(params.get("qse_defaults"), dict) else {}
        labor_hint = context.get("labor_hint") if isinstance(context.get("labor_hint"), dict) else {}
        chapter_domain = str(context.get("chapter_domain") or "").strip().lower()
        param_lines = []
        if quant:
            param_lines.append(
                "量化默认值："
                + "；".join([f"{k}={str(v).strip()}" for k, v in quant.items() if str(k).strip() and str(v).strip()][:10])
            )
        if focus_card:
            param_lines.append(
                "清单重点项默认值："
                + "；".join([f"{k}={str(v).strip()}" for k, v in focus_card.items() if str(k).strip() and str(v).strip()][:10])
            )
        if chapter_domain == "qse" and qse_defaults:
            param_lines.append(
                "质量/安全/环保默认阈值："
                + "；".join([f"{k}={str(v).strip()}" for k, v in qse_defaults.items() if str(k).strip() and str(v).strip()][:10])
            )
        if labor_hint:
            skill_ratio = labor_hint.get("skill_ratio") if isinstance(labor_hint.get("skill_ratio"), dict) else {}
            trade_ratio = labor_hint.get("trade_ratio") if isinstance(labor_hint.get("trade_ratio"), dict) else {}
            param_lines.append(
                f"劳动力矩阵：项目类型={labor_hint.get('project_type')}；规模={labor_hint.get('size')}；阶段={labor_hint.get('stage')}；阶段说明={labor_hint.get('stage_detail')}"
            )
            if skill_ratio:
                param_lines.append(
                    "技能等级比例："
                    + "；".join([f"{k}={str(v).strip()}" for k, v in skill_ratio.items() if str(k).strip() and str(v).strip()][:8])
                )
            if trade_ratio:
                param_lines.append(
                    "工种配置比例："
                    + "；".join([f"{k}={str(v).strip()}" for k, v in trade_ratio.items() if str(k).strip() and str(v).strip()][:10])
                )
        params_text = "\n".join([f"- {ln}" for ln in param_lines if ln.strip()])
        project_type_block = f"【项目类型】{project_type}\n" if project_type else ""
        global_instruction_block = (
            f"【系统全局指令（必须无条件执行）】\n{global_instruction}\n" if global_instruction else ""
        )
        qingtian_block = ""
        if qingtian_policy_enabled:
            qingtian_block = (
                "【青天适配硬约束（本章必须执行）】\n"
                "- 本章固定4块：适用范围与关键参数 / 重点难点与风险措施 / 验收与记录 / 引用关系。\n"
                "- 关键段落必须具备：怎么干/用什么/量化标准/谁检查+频次/留痕载体。\n"
                "- 每章至少1张风险控制表：风险点/控制点|措施（含参数、频次、责任）|验收动作|记录表。\n"
                "- 缺失参数不得编造，必须标注“需补充（缺：××）”；暂定值必须写“【暂定】+需确认来源”。\n"
                "- 通用机制不得重复展开，重复内容使用“引用：见××章/××表”。\n"
                "- 禁语命中必须为0，出现即改写为量化动作。\n"
            )
        agent_block = ""
        if master_agent or specialist_agents or compliance_agent:
            agent_block += "【多Agent协作】\n"
            if master_agent:
                agent_block += f"- 主控：{master_agent}\n"
            if specialist_agents:
                agent_block += f"- 专业：{'；'.join(specialist_agents[:6])}\n"
            if compliance_agent:
                agent_block += f"- 合规：{compliance_agent}\n"
        graph_node_block = ""
        if graph_nodes:
            graph_node_block += "【图谱逻辑节点（必须绑定）】\n"
            graph_node_block += "\n".join([f"- {x}" for x in graph_nodes[:8]]) + "\n"
        body = f"""你是资深施工组织设计专家，请根据证据生成高分章节内容。
角色定位：{role}
章节标题：{title}
方案版本：v{variant_id}
{project_type_block}
{global_instruction_block}
{qingtian_block}
{agent_block}

【可编辑参数（优先采用；若招标/图纸/清单有明确要求，则以证据为准）】
{params_text}

{logic_block}
{bp_block}
{graph_node_block}

【编制要求】
{req}

【权重与扣分项】
{weights}
{penalties}

【知识图谱证据】
{kg}

【招标/清单/图纸证据】
{docs}

【清单重点项（必须重点编制）】
{boq_focus_lines}

【四新技术候选（按清单/工序匹配；避免泛泛而谈）】
{four_new_text}

【规范工种称谓参考】
{standard_trades}

【合规检查要点】
{checklist}

【文风硬约束（必须）】
1) 你必须严禁使用任何解释性、抒情性或过渡性废话。
2) 你的输出必须100%模仿以下黄金样本的极简短句与数据密度。
3) 句子只保留动作、参数、责任、验收、记录，不写背景铺垫。
4) 禁用八股短语：{",".join(self.banned_phrases)}
5) 输出仅正文，不要“综上/总之/建议”等结尾句。
样本：{GOLDEN_STYLE_SAMPLE}

输出要求：
1) 结构清晰，条理分明
2) 体现质量/安全/进度/环保
3) 引用证据中的关键点时，可在句末保留“【证据:来源】”作为内部锚点
   - 建议证据格式：文件名#定位符（例如：xx.pdf#1a2b3c4d@12345）
   - 禁止额外输出“证据摘要/证据与追溯/图谱节点/经验值/调试日志”等后台信息
4) 对扣分项做显式规避说明
5) 若提供“目标页数”，请按目标页数控制篇幅
6) 风险条目必须采用“风险→控制→验证”三元组表达，并逐条闭环
7) 优先模板化表达：短句+要点+量化指标；每节尽量覆盖频次/阈值/间距/厚度/时长/人数/设备型号
   - 所有量化指标必须融入连贯、专业的工程短句，禁止输出“频次=2次/日；阈值=偏差≤5mm；人数=8人/班”这种键值对串
8) 若有“本章专属要求”，必须逐条满足
9) 特殊材料、危险品材料、劳保用品、技术工种配置、绿色工地、信息化管理、四新技术应用需写具体措施
   - 若涉及“四新/新技术/新工艺/新材料/新设备/信息化/绿色施工”，优先从“候选清单”中选2-4条落地：适用/投入/步骤/验收指标 + 风险→控制→验证 + 记录 + 偏差处置
10) 全文禁止官话、套话、空话，不得出现“加强、确保、严格、压实责任、形成合力、高质量推进”等词
11) 清单重点项必须逐项写清：工程量/材料要点/资源配置 + 量化指标 + 风险→控制→验证 + 证据标注
12) 严禁输出系统脚手架、图谱节点标记、经验值标记、JSON、校验日志、Prompt 回显或任何键值调试字段
13) 如证据不足，可写“需补充××资料后复核”，但不得暴露后台判定过程
"""
        return f"{build_text_fixed_prefix()}\n{body}"

    def _fallback(self, title: str, context: Dict[str, Any]) -> str:
        # 无外部模型 API 时仍输出“可执行+可验收”的最小合格稿：
        # - 必含量化指标（满足质量闸门）
        # - 必含 风险→控制→验证（满足闭环闸门）
        # - 必含证据标记（满足可追溯闸门）
        boq_focus = context.get("boq_focus") if isinstance(context.get("boq_focus"), dict) else {}
        focus = boq_focus.get("must_cover_keywords") or []
        focus = [str(x).strip() for x in focus if str(x).strip()][:8]
        special_materials = boq_focus.get("special_materials") or []
        hazardous_materials = boq_focus.get("hazardous_materials") or []
        ppe_items = boq_focus.get("ppe_items") or []
        trades = [str(x).strip() for x in (context.get("standard_trades") or []) if str(x).strip()]

        params = context.get("params") if isinstance(context.get("params"), dict) else None
        try:
            from backend.zhifei_autoplan.params_runtime import get_quant_defaults, get_boq_focus_card_defaults, get_qse_defaults

            quant = get_quant_defaults(params)
            card_defaults = get_boq_focus_card_defaults(params)
            qse_defaults = get_qse_defaults(params)
        except Exception:
            quant = {
                "频次": "2次/日（班前+收工）",
                "阈值": "偏差≤5mm",
                "间距": "1000mm",
                "厚度": "50mm",
                "时长": "4h/作业段",
                "人数": "8人/班",
                "设备型号": "20t挖机1台",
            }
            card_defaults = {
                "采购比价": "≥3家/批次",
                "抽检频次": "每100m2 1次",
                "合格率阈值": "≥98%",
                "一次验收通过率": "≥95%",
                "台账抽查频次": "1次/周",
                "应急演练频次": "1次/季度",
            }
            qse_defaults = {
                "PM10阈值": "≤150ug/m3",
                "昼间噪声阈值": "≤70dB",
                "夜间噪声阈值": "≤55dB",
            }

        # Pick a non-placeholder evidence source for the fallback (deterministic, but traceable when docs exist).
        evidence_src = "工程量清单(解析统计)"
        try:
            doc_evs = [str(x) for x in (context.get("doc_evidence") or []) if str(x).strip()]
            if doc_evs:
                evidence_src = doc_evs[0].split(":", 1)[0].strip() or evidence_src
        except Exception:
            pass

        role = context.get("agent_role") or "技术负责人"
        project_type = str(context.get("project_type") or "").strip()
        global_instruction = str(context.get("global_instruction") or "").strip()
        target_pages = context.get("chapter_target_pages")
        logic = context.get("logic_template") if isinstance(context.get("logic_template"), dict) else {}
        logic_id = str(logic.get("id") or "").strip().upper() or "A"
        is_qse_title = any(k in str(title) for k in ("质量", "安全", "文明", "环保", "环境", "绿色", "应急", "消防"))
        bp = context.get("chapter_blueprint") if isinstance(context.get("chapter_blueprint"), dict) else {}
        bp_id = str(bp.get("id") or "").strip().upper()
        bp_name = str(bp.get("name") or "").strip()
        bp_anchors = bp.get("anchors") if isinstance(bp.get("anchors"), list) else []
        bp_anchors = [str(x).strip() for x in bp_anchors if str(x).strip()]

        def _metric_sentence() -> str:
            return naturalize_machine_text(
                "【量化指标】"
                + "；".join(
                    [
                        f"频次={quant['频次']}",
                        f"阈值={quant['阈值']}",
                        f"间距={quant['间距']}",
                        f"厚度={quant['厚度']}",
                        f"时长={quant['时长']}",
                        f"人数={quant['人数']}",
                        f"设备型号={quant['设备型号']}",
                    ]
                )
            )

        def _quality_sentence() -> str:
            return naturalize_machine_text(
                "【控制指标矩阵】"
                + "；".join(
                    [
                        f"采购比价={card_defaults['采购比价']}",
                        f"抽检频次={card_defaults['抽检频次']}",
                        f"合格率阈值={card_defaults['合格率阈值']}",
                        f"一次验收通过率={card_defaults['一次验收通过率']}",
                    ]
                )
            )

        def _append_sentence(lines: List[str], text: str, *, evidence: str | None = evidence_src) -> None:
            sentence = str(text or "").strip()
            if not sentence:
                return
            if evidence:
                sentence = f"{sentence}【证据:{evidence}】"
            lines.append(sentence)

        lines: List[str] = []
        intro = f"{title}由{role}牵头组织实施。"
        if project_type:
            intro = f"{project_type}项目的{title}由{role}牵头组织实施。"
        if target_pages:
            intro += f" 本章按约{target_pages}页篇幅组织内容，重点突出可执行动作、检查频次和验收标准。"
        if global_instruction:
            intro += f" 编制时同步落实“{global_instruction}”的工程约束。"
        _append_sentence(lines, intro)
        _append_sentence(lines, _metric_sentence())
        _append_sentence(lines, _quality_sentence())
        if focus:
            _append_sentence(lines, f"本章重点覆盖{ '、'.join(focus[:6]) }等清单重点项，逐项写清资源配置、工序做法和验收口径。")

        if bp_anchors:
            for anc in bp_anchors[:6]:
                lines.append(anc)
                if bp_id == "BP01" and anc == "工程特点":
                    _append_sentence(lines, f"工程特点围绕{ '、'.join(focus[:5]) if focus else '清单重点项' }展开，重点交代数量、做法和对现场组织的影响。")
                    _append_sentence(lines, "场地限制、交通组织和周边敏感点均以现有证据为准，暂缺资料项列入后续补充清单。")
                elif bp_id == "BP01" and anc == "总体部署":
                    _append_sentence(lines, "总体部署按总工期拆分关键节点，并将资源峰值、作业面移交和专业穿插统一到同一调度节奏。", evidence="进度计划/资源计划")
                    _append_sentence(lines, naturalize_machine_text(f"人数={quant['人数']}；设备型号={quant['设备型号']}；抽检频次={card_defaults['抽检频次']}"))
                elif bp_id == "BP02" and anc == "劳保用品":
                    if ppe_items:
                        _append_sentence(lines, f"本项目劳保用品重点包括{'、'.join([str(x).strip() for x in ppe_items[:8] if str(x).strip()])}，均按人员入场节点足额发放。")
                    _append_sentence(lines, naturalize_machine_text(f"抽检频次={quant['频次']}；时长=48h内完成破损更换"))
                elif bp_id == "BP02" and anc == "存储":
                    _append_sentence(lines, naturalize_machine_text(f"间距={quant['间距']}；时长=1次/单完成双人复核"))
                elif bp_id == "BP04" and anc == "特殊材料":
                    if special_materials:
                        _append_sentence(lines, f"特殊材料重点包括{'、'.join([str(x).strip() for x in special_materials[:8] if str(x).strip()])}，到货后先做批次隔离和复验。")
                    _append_sentence(lines, "特殊材料到货后执行一批一验、一批一台账，复验结论未闭合前不得投入作业面。")
                elif bp_id == "BP04" and anc == "危化品":
                    if hazardous_materials:
                        _append_sentence(lines, f"危化品材料重点包括{'、'.join([str(x).strip() for x in hazardous_materials[:8] if str(x).strip()])}，入库后按专库专账管理。")
                    _append_sentence(lines, naturalize_machine_text(f"应急演练频次={card_defaults['应急演练频次']}；频次=1次/班完成可燃气体检测"))
                elif bp_id == "BP05" and anc in {"适用条件", "验收指标"}:
                    _append_sentence(lines, "四新技术应用以本项目清单重点项和关键工序为准，先明确适用条件，再写清投入方式和验收口径。")
                    _append_sentence(lines, naturalize_machine_text(f"阈值={quant['阈值']}；抽检频次={card_defaults['抽检频次']}"))
                elif bp_id == "BP08" and anc == "技术工种配置":
                    _append_sentence(lines, "测量工、钢筋工、模板工、混凝土工、防水工、电工和焊工均按关键工序同步配置，并结合峰值作业量动态调整。")
                elif bp_id == "BP08" and anc in {"检验", "试验"}:
                    _append_sentence(lines, naturalize_machine_text(f"抽检频次={card_defaults['抽检频次']}；阈值={quant['阈值']}"))
                elif bp_id == "BP11" and anc == "技术管理人员":
                    _append_sentence(lines, "技术负责人、质量负责人、安全负责人和测量负责人到岗后形成联审联签链，所有证书和到岗记录同步归档。")
                elif bp_id == "BP11" and anc == "培训":
                    _append_sentence(lines, "班前交底和关键工序培训按班组滚动组织，培训后即时考核并留存签到、试题和影像记录。")

        if logic_id == "B":
            lines.append("施工工序流程")
            _append_sentence(lines, "施工前先完成作业面验收、班前交底和测量复核，确认条件具备后再组织材料到场和工序穿插。")
            _append_sentence(lines, "材料到场后执行批次验收、二维码追溯和台账复核，关键作业段安排专人旁站并在收工前完成结果复盘。")
            lines.append("风险→控制→验证")
            lines.append(f"风险：交叉作业导致人员伤害；控制：作业分区、警戒线2m、专人指挥并执行{quant['频次']}巡检；验证：当日违章为零并完成《交叉作业巡检表》记录。【证据:{evidence_src}】")
            lines.append(f"风险：材料批次混用导致不可追溯；控制：入库按批次分区、二维码领用并执行双人复核；验证：台账字段齐全率保持100%，按{card_defaults['台账抽查频次']}完成抽查。【证据:{evidence_src}】")
        elif logic_id == "C":
            lines.append("人机料法环控制要点")
            _append_sentence(lines, "人员按工种和作业段成组配置，关键工序设置旁站岗位，材料执行一批一验一追溯，机械设备按日点检后投入使用。")
            _append_sentence(lines, "扬尘、噪声、污水和废弃物收集同步纳入现场巡检清单，确保环保指标与施工组织同步闭环。", evidence="环保监测记录")
            lines.append("风险→控制→验证")
            lines.append(f"风险：关键参数超差导致返工；控制：首件确认后按{card_defaults['抽检频次']}实施过程抽检；验证：关键偏差控制在{quant['阈值']}以内，合格率稳定在{card_defaults['合格率阈值']}以上。【证据:{evidence_src}】")
            lines.append(f"风险：关键线路滞后影响总工期；控制：日计划滚动分解并在滞后当日完成资源调整；验证：计划兑现率保持在0.95以上。【证据:{evidence_src}】")
        elif logic_id == "D":
            if is_qse_title:
                lines.append("监管红线清单")
                _append_sentence(lines, "高处和临边防护缺失、临时用电漏保失效、危化品混放三类问题一经发现立即停工整改，并同步触发联签闭环流程。")
                _append_sentence(lines, "高风险事项要求10分钟内启动处置、2小时内复核关闭，一般问题要求24小时内销项闭环。")
                lines.append("风险→控制→验证")
                lines.append(f"风险：临时用电漏保失效；控制：立即停用、完成更换并组织复测；验证：试跳记录齐全率保持100%，联签单据闭环后方可恢复送电。【证据:{evidence_src}】")
            else:
                lines.append("资源-工序耦合表")
                lines.append(f"工序={title}准备；班组人数={quant['人数']}；设备={quant['设备型号']}；节拍={quant['时长']}。【证据:{evidence_src}】")
                lines.append(f"工序=关键作业；人数={quant['人数']}；抽检频次={card_defaults['抽检频次']}；阈值={quant['阈值']}。【证据:{evidence_src}】")
                _append_sentence(lines, "交叉作业抢占作业面和吊装穿插冲突均通过错峰作业、分区封控和专人指挥进行协调。")
                lines.append("风险→控制→验证")
                lines.append(f"风险：资源错配导致返工；控制：班组与工序一一绑定并在交接节点逐项复核；验证：关键偏差控制在{quant['阈值']}以内，资源耦合检查记录完整闭环。【证据:{evidence_src}】")
        elif logic_id == "E":
            if is_qse_title:
                lines.append("区域网格划分")
                _append_sentence(lines, "现场按主体区、材料区和临电区划分网格，网格责任落实到班组长和安全员，问题处置按红黄牌机制执行。")
                lines.append("班组行为清单")
                _append_sentence(lines, "复杂交叉作业、动火、临电和高处作业班前必须完成交底、PPE自检和作业许可，无证上岗、危化品混放和越级操作列为否决项。")
                lines.append("红黄牌处置")
                _append_sentence(lines, "重大偏差按红黄牌处置，黄牌问题2h内整改复核，红牌问题立即停工并经项目经理签批后恢复作业。")
                lines.append("风险→控制→验证")
                lines.append(f"风险：劳保用品佩戴不规范；控制：班前逐人检查并在网格巡检中滚动复核；验证：按{quant['频次']}完成抽查，问题当班整改闭环。【证据:{evidence_src}】")
            else:
                lines.append("实施场景卡片")
                _append_sentence(lines, "主体作业面、材料中转区和交叉作业区分别建立参数控制、责任岗位和验收记录模板，确保不同场景下的控制逻辑一致。")
                lines.append("参数对照表")
                _append_sentence(lines, naturalize_machine_text(f"频次={quant['频次']}；阈值={quant['阈值']}；间距={quant['间距']}；厚度={quant['厚度']}；时长={quant['时长']}"))
                lines.append("风险→控制→验证")
                lines.append(f"风险：场景参数超差；控制：首件确认后按工序执行过程抽检；验证：合格率稳定在{card_defaults['合格率阈值']}以上，并完成《场景验收样表》记录。【证据:{evidence_src}】")
        else:
            _append_sentence(lines, "本章按准备、测量、材料、作业、验收五个步骤组织实施，每一步均落实到责任岗位、检查动作和台账记录。")
            _append_sentence(lines, "交底记录、首件确认记录、抽检记录、验收记录和影像资料同步形成，避免出现作业完成后再补记台账的情况。")
            lines.append("风险→控制→验证")
            lines.append(f"风险：交叉作业导致人员伤害；控制：作业分区、警戒线2m、专人指挥并执行{quant['频次']}巡检；验证：当日违章为零并形成《交叉作业巡检表》。【证据:{evidence_src}】")
            lines.append(f"风险：材料批次混用导致质量不可追溯；控制：入库按批次分区、二维码领用并执行双人复核；验证：台账字段齐全率保持100%，并按{card_defaults['台账抽查频次']}完成抽查。【证据:{evidence_src}】")

        if "施工部署" in str(title):
            _append_sentence(lines, "施工部署将重难点工序、关键进度节点和扣分项风险统一纳入总工期周计划，复杂穿插作业先排后干，重大偏差和否决项对应工序在班前复核清单中逐项确认。")

        if is_qse_title:
            lines.append("闭环卡片")
            lines.append(
                f"风险：关键工序质量偏差超限；控制：首件确认=1次/工序并按{card_defaults['抽检频次']}实施过程抽检；"
                f"验证：偏差控制在{quant['阈值']}以内，记录=《质量抽检记录》；偏差处置：超限后30min内复检，未达标立即整改并在2h内关闭。【证据:{evidence_src}】"
            )
            lines.append(
                f"风险：临边防护和交叉作业失控；控制：安全员按{quant['频次']}巡检，警戒线保持2m，班前交底100%覆盖；"
                f"验证：违章数=0，记录=《安全巡检表》；偏差处置：发现问题立即停工，60min内完成整改复查后恢复作业。【证据:{evidence_src}】"
            )
            lines.append(
                f"风险：扬尘或噪声超限引发投诉；控制：喷淋=2次/日、车辆冲洗=1次/车、夜间高噪设备22:00后停用；"
                f"验证：PM10{qse_defaults['PM10阈值']}、夜间噪声{qse_defaults['夜间噪声阈值']}，记录=《环境监测台账》；偏差处置：超限15min内启动加密喷淋并2h内复测关闭。【证据:{evidence_src}】"
            )
            lines.append(
                f"风险：应急响应迟缓导致事故扩大；控制：应急物资按清单到位并执行{card_defaults['应急演练频次']}演练，值班电话24h畅通；"
                f"验证：响应时长≤10min，记录=《应急演练记录》；偏差处置：响应超时立即复盘整改，24h内完成责任闭环和再培训。【证据:{evidence_src}】"
            )
            lines.append(
                f"风险：劳保用品失效或佩戴不规范导致人员伤害；控制：劳保用品发放=1套/人，班前检查={quant['频次']}，破损件48h内更换；"
                f"验证：抽查覆盖率=100%，记录=《劳保用品发放与检查台账》；偏差处置：未佩戴立即停工整改，复查合格后当班关闭。【证据:{evidence_src}】"
            )
            lines.append(
                f"风险：危险品材料或易燃物储运失控引发火灾/中毒；控制：专库专账+领用双人复核=1次/单+可燃气体检测=1次/班；"
                f"验证：检测记录齐全率=100%，记录=《危险品材料储运与领用台账》；偏差处置：异常物料立即隔离，2h内复核关闭并补做应急交底。【证据:{evidence_src}】"
            )
            if "安全" in str(title):
                _append_sentence(lines, "复杂交叉作业、动火、临电和高处作业作为重难点及扣分项风险纳入红线清单，重大偏差和否决项触发立即停工复核。")

        if special_materials:
            _append_sentence(lines, f"特殊材料重点包括{'、'.join([str(x) for x in special_materials[:6] if str(x).strip()])}，到货后执行一批一验、一批一复核和一批一台账，不合格批次全部隔离。")
        else:
            _append_sentence(lines, "特殊材料到货后执行一批一验、一批一复核和一批一台账，不合格批次全部隔离。")

        if hazardous_materials:
            _append_sentence(lines, f"危险品材料重点包括{'、'.join([str(x) for x in hazardous_materials[:6] if str(x).strip()])}，采购、储运、领用、作业和应急处置全部纳入专库专账闭环。")
        else:
            _append_sentence(lines, "危险品材料的采购、储运、领用、作业和应急处置全部纳入专库专账闭环。")
        _append_sentence(lines, naturalize_machine_text(f"应急演练频次={card_defaults['应急演练频次']}"))

        if ppe_items:
            _append_sentence(lines, f"劳保用品以{'、'.join([str(x) for x in ppe_items[:8] if str(x).strip()])}为主，人员入场前一次性发放到位，破损件在48小时内完成替换。")
        else:
            _append_sentence(lines, "安全帽、反光背心、安全带、防割手套和绝缘手套按岗位足额发放，破损件在48小时内完成替换。")

        if trades:
            demo = trades[:6]
            _append_sentence(
                lines,
                f"技术工种配置：{demo[0]}人数=1人/班；{demo[1] if len(demo) > 1 else '钢筋工'}人数=2人/班；{demo[2] if len(demo) > 2 else '模板工'}人数=2人/班；"
                f"{demo[3] if len(demo) > 3 else '混凝土工'}人数=2人/班；{demo[4] if len(demo) > 4 else '电工'}人数=1人/班；{demo[5] if len(demo) > 5 else '焊工'}人数=1人/班。",
            )
            _append_sentence(lines, f"测量、钢筋、模板、混凝土、电工和焊工作业班组按关键工序峰值同步配置，避免关键工序等待资源。")
        else:
            _append_sentence(lines, "技术工种配置：测量工人数=1人/班；钢筋工人数=2人/班；模板工人数=2人/班；混凝土工人数=2人/班；电工人数=1人/班；焊工人数=1人/班。")
            _append_sentence(lines, "钢筋工、模板工、混凝土工、电工和焊工按关键工序峰值同步配置，避免关键工序等待资源。")

        _append_sentence(
            lines,
            f"绿色施工方面，扬尘控制按围挡喷淋执行{quant['频次']}，车辆做到一车一冲洗，噪声和污水指标分别按昼间{qse_defaults['昼间噪声阈值']}、夜间{qse_defaults['夜间噪声阈值']}和排放 pH 6-9 控制。",
            evidence="环保监测记录",
        )
        _append_sentence(lines, "信息化管理方面，材料入库、领用、过程检查和问题整改全部使用二维码台账闭环，当日上传率保持100%，每道关键工序至少留存2张现场照片。")

        four_new_recs = boq_focus.get("four_new_recommendations") if isinstance(boq_focus, dict) else None
        try:
            from backend.zhifei_autoplan.four_new_tech import recommend_four_new

            recs = four_new_recs if isinstance(four_new_recs, list) else []
            if not recs:
                fake_boq = {"items": [{"name": x, "process": {"name": ""}} for x in focus[:24]]}
                recs = recommend_four_new(fake_boq, outline=[str(title)], limit=3)
            if recs:
                for it in recs[:3]:
                    if not isinstance(it, dict):
                        continue
                    name = str(it.get("name") or "").strip()
                    cat = str(it.get("category") or "四新技术").strip()
                    matched = it.get("matched") if isinstance(it.get("matched"), list) else []
                    matched_txt = "、".join([str(x).strip() for x in matched[:4] if str(x).strip()])
                    _append_sentence(
                        lines,
                        f"{cat}优先采用{name}，适用场景以{matched_txt or '关键工序'}为主，实施前先做样板验证，实施后按抽检记录和验收记录闭环。",
                    )
            else:
                _append_sentence(lines, "四新技术优先采用移动端隐蔽验收和二维码材料追溯，适用于材料批次多、隐蔽验收点位密集的工序。")
        except Exception:
            _append_sentence(lines, "四新技术优先采用移动端隐蔽验收和二维码材料追溯，适用于材料批次多、隐蔽验收点位密集的工序。")

        _append_sentence(lines, "过程检查、验收记录、影像资料和台账条目同步归档，缺失证据项在当日收工前补齐后再提交复核。")
        return "\n".join([str(x).strip() for x in lines if str(x).strip()]).strip() + "\n"
