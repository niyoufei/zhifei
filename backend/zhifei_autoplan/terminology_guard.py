from __future__ import annotations

import asyncio
import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Tuple

from backend.zhifei_autoplan.model_aliases import latest_runtime_model_for, normalize_provider_model_pair
from backend.zhifei_autoplan.provider_runtime import resolve_automation_credentials
from backend.zhifei_autoplan.utils.llm_client import LLMClient

_MODULE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _MODULE_DIR.parent.parent
_RULES_REL_PATH = Path("03_系统核心规则与字典/ZhiFei_Engineering_Rules_CN.json")
ENGINEERING_RULES_PATH = _PROJECT_ROOT / _RULES_REL_PATH
_RULES_CACHE_LOCK = threading.Lock()
_RULES_CACHE: Dict[str, Dict[str, Any]] = {}

_DEFAULT_ALIAS_MAP = {
    "塔吊司机": "建筑起重机械司机",
    "吊车司机": "建筑起重机械司机",
    "起重机操作员": "建筑起重机械司机",
    "起重司机": "建筑起重机械司机",
    "信号工": "建筑起重信号司索工",
    "司索工": "建筑起重信号司索工",
    "泥瓦匠": "砌筑工",
    "瓦工": "砌筑工",
    "水电工": "电工",
    "钢构安装工": "钢结构安装工",
}

_TRADE_TOKEN_RE = re.compile(r"[\u4e00-\u9fffA-Za-z]{2,16}(?:司机|工|员|匠)")
_JSON_OBJ_RE = re.compile(r"\{[\s\S]*\}")


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _iter_rules_path_candidates(path: str | Path | None = None) -> List[Path]:
    candidates: List[Path] = []
    if path is not None:
        raw = str(path).strip()
        if raw:
            p = Path(raw).expanduser()
            if p.is_absolute():
                candidates.append(p)
            else:
                candidates.append((Path.cwd() / p).resolve())
                candidates.append((_PROJECT_ROOT / p).resolve())
    else:
        env_path = str(os.environ.get("ZF_ENGINEERING_RULES_PATH") or "").strip()
        if env_path:
            ep = Path(env_path).expanduser()
            if ep.is_absolute():
                candidates.append(ep)
            else:
                candidates.append((Path.cwd() / ep).resolve())
                candidates.append((_PROJECT_ROOT / ep).resolve())
        candidates.append(ENGINEERING_RULES_PATH.resolve())
        candidates.append((_PROJECT_ROOT / _RULES_REL_PATH).resolve())

    # unique + stable order
    uniq: List[Path] = []
    seen: set[str] = set()
    for c in candidates:
        key = str(c)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    return uniq


def resolve_engineering_rules_path(path: str | Path | None = None) -> Path:
    candidates = _iter_rules_path_candidates(path)
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    # keep deterministic fallback path for diagnostics
    return candidates[0] if candidates else ENGINEERING_RULES_PATH.resolve()


def _read_json_cached(path: Path) -> Any:
    p = path.resolve()
    try:
        st = p.stat()
    except Exception:
        return None

    key = str(p)
    with _RULES_CACHE_LOCK:
        cached = _RULES_CACHE.get(key)
        if cached and cached.get("mtime_ns") == st.st_mtime_ns and cached.get("size") == st.st_size:
            return cached.get("data")

    data = _read_json(p)
    with _RULES_CACHE_LOCK:
        _RULES_CACHE[key] = {
            "mtime_ns": st.st_mtime_ns,
            "size": st.st_size,
            "data": data,
        }
    return data


def load_engineering_rules(path: str | Path | None = None) -> Dict[str, Any]:
    p = resolve_engineering_rules_path(path)
    obj = _read_json_cached(p)
    if isinstance(obj, dict):
        return obj
    return {}


def validate_engineering_rules(path: str | Path | None = None) -> Dict[str, Any]:
    p = resolve_engineering_rules_path(path)
    rules = load_engineering_rules(p)
    missing: List[str] = []
    if not isinstance(rules.get("建筑法定术语词典"), dict):
        missing.append("建筑法定术语词典")
    if not isinstance(rules.get("劳动力排班算法矩阵"), dict):
        missing.append("劳动力排班算法矩阵")
    if not isinstance(rules.get("法定工种白名单"), list):
        missing.append("法定工种白名单")
    return {
        "ok": len(missing) == 0,
        "path": str(p),
        "missing_keys": missing,
    }


def load_global_terminology(path: str | Path | None = None) -> List[Dict[str, Any]]:
    """
    兼容旧接口：返回术语条目列表。
    新版唯一来源：ZhiFei_Engineering_Rules_CN.json["建筑法定术语词典"]。
    """
    rules = load_engineering_rules(path)
    glossary = rules.get("建筑法定术语词典")
    if not isinstance(glossary, dict):
        return []
    out: List[Dict[str, Any]] = []
    for term, definition in glossary.items():
        t = str(term or "").strip()
        if not t:
            continue
        out.append(
            {
                "standard_term": t,
                "definition": str(definition or "").strip(),
                "category": "建筑法定术语",
                "synonyms": [],
            }
        )
    return out


def load_labor_allocation_matrix(path: str | Path | None = None) -> Dict[str, Any]:
    """
    兼容旧接口：返回劳动力矩阵对象。
    新版唯一来源：ZhiFei_Engineering_Rules_CN.json["劳动力排班算法矩阵"]。
    """
    rules = load_engineering_rules(path)
    matrix = rules.get("劳动力排班算法矩阵")
    return matrix if isinstance(matrix, dict) else {}


def load_statutory_trade_whitelist(path: str | Path | None = None) -> List[str]:
    rules = load_engineering_rules(path)
    arr = rules.get("法定工种白名单")
    if not isinstance(arr, list):
        return []
    out = []
    for x in arr:
        s = str(x or "").strip()
        if s:
            out.append(s)
    return out


def _resolve_api_key(provider: str) -> str:
    p = str(provider or "").strip().lower()
    env_map = {
        "google": ("ZF_GOOGLE_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"),
        "openai": ("ZF_OPENAI_API_KEY", "OPENAI_API_KEY"),
        "grok": ("ZF_GROK_API_KEY", "GROK_API_KEY", "XAI_API_KEY"),
        "anthropic": ("ANTHROPIC_API_KEY",),
        "deepseek": ("DEEPSEEK_API_KEY",),
        "zhipu": ("ZHIPU_API_KEY",),
        "qwen": ("QWEN_API_KEY", "DASHSCOPE_API_KEY"),
        "baidu": ("BAIDU_API_KEY",),
        "iflytek": ("IFLYTEK_API_KEY",),
        "tencent": ("TENCENT_API_KEY",),
    }
    for k in env_map.get(p, ()):
        v = os.environ.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _resolve_llm_runtime(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> Tuple[str, str, str]:
    auto_provider, auto_model, auto_key = resolve_automation_credentials()
    if not provider and not model and not api_key and auto_provider and auto_model and auto_key:
        return auto_provider, auto_model, auto_key
    p = str(provider or os.environ.get("ZF_LLM_MAIN_PROVIDER") or "openai").strip().lower()
    if not p:
        p = "openai"
    default_model = latest_runtime_model_for(p) or "gpt-5.4"
    p, m = normalize_provider_model_pair(
        p,
        str(model or os.environ.get("ZF_LLM_MAIN_MODEL") or default_model).strip() or default_model,
        fallback=p,
    )
    k = str(api_key or os.environ.get("ZF_LLM_MAIN_API_KEY") or _resolve_api_key(p)).strip()
    return p, m, k


def _safe_json_parse(text: str) -> Dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        pass
    m = _JSON_OBJ_RE.search(raw)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _build_alias_map(whitelist: List[str]) -> Dict[str, str]:
    wl = set(whitelist)
    out: Dict[str, str] = {}
    for src, tgt in _DEFAULT_ALIAS_MAP.items():
        if tgt in wl:
            out[src] = tgt
    return out


def _detect_non_whitelist_terms(text: str, whitelist: List[str], alias_map: Dict[str, str]) -> List[str]:
    content = str(text or "")
    if not content:
        return []
    wl = set(whitelist)
    hits: set[str] = set()
    for token in _TRADE_TOKEN_RE.findall(content):
        t = str(token or "").strip()
        if not t:
            continue
        if len(t) > 8 and t not in alias_map:
            # 避免把整句前缀误识别成“工种词”，仅保留常见长度范围内的术语。
            continue
        if t in wl:
            continue
        hits.add(t)
    for alias in alias_map.keys():
        if alias and alias in content and alias not in wl:
            hits.add(alias)
    return sorted(hits, key=lambda s: (-len(s), s))


async def _llm_correct_terms(
    *,
    terms: List[str],
    context: str,
    whitelist: List[str],
    glossary: Dict[str, str],
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> Dict[str, str]:
    if not terms:
        return {}

    p, m, k = _resolve_llm_runtime(provider=provider, model=model, api_key=api_key)
    if not k:
        return {}

    client = LLMClient(provider=p, model=m, api_key=k)
    whitelist_text = "\n".join(f"- {x}" for x in whitelist)
    # 将命中的术语补充词典解释，给模型更稳定的纠偏上下文。
    glossary_ctx = []
    for t in terms:
        if t in glossary:
            glossary_ctx.append(f"- {t}: {glossary.get(t)}")
    prompt = (
        "你是建筑工程术语审校器。任务：把输入中的非白名单工种词修正为白名单中的法定工种名称。\n"
        "硬规则：\n"
        "1) 输出必须是JSON对象，格式 {\"mapping\": {\"原词\": \"白名单词\"}}。\n"
        "2) 映射值必须严格来自白名单；若无法确定则填空字符串。\n"
        "3) 禁止输出解释文本。\n\n"
        f"法定工种白名单：\n{whitelist_text}\n\n"
        f"待校正词：{json.dumps(terms, ensure_ascii=False)}\n\n"
        f"上下文：\n{context[:1600]}\n\n"
        f"词典补充（命中项）：\n{chr(10).join(glossary_ctx) if glossary_ctx else '（无）'}\n"
    )

    resp = await client.complete(prompt, temperature=0.0)
    text = str(resp.get("text") or "")
    data = _safe_json_parse(text)
    mapping = data.get("mapping") if isinstance(data.get("mapping"), dict) else {}
    wl_set = set(whitelist)
    out: Dict[str, str] = {}
    for src in terms:
        tgt = str(mapping.get(src) or "").strip()
        if tgt and tgt in wl_set:
            out[src] = tgt
    return out


def _apply_mapping(text: str, mapping: Dict[str, str]) -> Tuple[str, List[Dict[str, Any]]]:
    src = str(text or "")
    if not src or not mapping:
        return src, []
    out = src
    details: List[Dict[str, Any]] = []
    for old in sorted(mapping.keys(), key=lambda x: len(x), reverse=True):
        new = str(mapping.get(old) or "").strip()
        if not old or not new or old == new:
            continue
        if old not in out:
            continue
        cnt = out.count(old)
        out = out.replace(old, new)
        details.append({"from": old, "to": new, "count": int(cnt)})
    return out, details


def _normalize_text_sync_no_llm(text: str, rules_path: str | Path | None = None) -> Tuple[str, Dict[str, Any]]:
    src = str(text or "")
    rules = load_engineering_rules(rules_path)
    whitelist = load_statutory_trade_whitelist(rules_path)
    if not src or not whitelist:
        return src, {"changed": False, "replacement_count": 0, "details": [], "llm_invoked": False}
    alias_map = _build_alias_map(whitelist)
    terms = _detect_non_whitelist_terms(src, whitelist, alias_map)
    mapping = {t: alias_map[t] for t in terms if t in alias_map}
    out, details = _apply_mapping(src, mapping)
    replaced_terms = {str(d.get("from") or "") for d in details}
    unresolved = [t for t in terms if t and t not in replaced_terms]
    replacement_count = int(sum(int(d.get("count") or 0) for d in details))
    return out, {
        "changed": out != src,
        "replacement_count": replacement_count,
        "details": details[:100],
        "llm_invoked": False,
        "llm_corrected_count": 0,
        "unresolved_terms": unresolved[:50],
    }


async def normalize_text_terminology_async(
    text: str,
    entries: List[Dict[str, Any]] | None = None,
    *,
    rules_path: str | Path | None = None,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    use_llm: bool = True,
) -> Tuple[str, Dict[str, Any]]:
    src = str(text or "")
    rules = load_engineering_rules(rules_path)
    glossary_obj = rules.get("建筑法定术语词典")
    glossary = {str(k): str(v) for k, v in glossary_obj.items()} if isinstance(glossary_obj, dict) else {}
    whitelist = load_statutory_trade_whitelist(rules_path)
    if not src:
        return src, {"changed": False, "replacement_count": 0, "details": [], "llm_invoked": False}
    if not whitelist:
        return src, {"changed": False, "replacement_count": 0, "details": [], "llm_invoked": False}

    alias_map = _build_alias_map(whitelist)
    terms = _detect_non_whitelist_terms(src, whitelist, alias_map)
    if not terms:
        return src, {"changed": False, "replacement_count": 0, "details": [], "llm_invoked": False}

    seed_mapping = {t: alias_map[t] for t in terms if t in alias_map}
    seed_out, seed_details = _apply_mapping(src, seed_mapping)
    seed_replaced_terms = {str(d.get("from") or "") for d in seed_details}
    unresolved_terms = [t for t in terms if t and t not in seed_replaced_terms]
    llm_mapping: Dict[str, str] = {}
    llm_invoked = False
    if use_llm and unresolved_terms:
        try:
            llm_mapping = await _llm_correct_terms(
                terms=unresolved_terms,
                context=src,
                whitelist=whitelist,
                glossary=glossary,
                provider=provider,
                model=model,
                api_key=api_key,
            )
            llm_invoked = True
        except Exception:
            llm_mapping = {}
            llm_invoked = True

    final_mapping = dict(seed_mapping)
    final_mapping.update(llm_mapping)

    out = seed_out
    details = list(seed_details)
    if llm_mapping:
        out, llm_details = _apply_mapping(seed_out, llm_mapping)
        details.extend(llm_details)
    replaced_terms = {str(d.get("from") or "") for d in details}
    unresolved = [t for t in terms if t and t not in replaced_terms]
    replacement_count = int(sum(int(d.get("count") or 0) for d in details))
    return out, {
        "changed": out != src,
        "replacement_count": replacement_count,
        "details": details[:100],
        "llm_invoked": llm_invoked,
        "llm_corrected_count": len(llm_mapping),
        "unresolved_terms": unresolved[:50],
    }


def normalize_text_terminology(
    text: str,
    entries: List[Dict[str, Any]] | None = None,
    *,
    rules_path: str | Path | None = None,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    use_llm: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    if use_llm:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                normalize_text_terminology_async(
                    text,
                    entries=entries,
                    rules_path=rules_path,
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    use_llm=True,
                )
            )
    # 在同步或已有事件循环上下文中，默认走稳定的别名+白名单替换，不做阻塞LLM调用。
    return _normalize_text_sync_no_llm(text, rules_path=rules_path)


async def normalize_sections_terminology_async(
    sections: List[Dict[str, Any]],
    *,
    rules_path: str | Path | None = None,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    use_llm: bool = True,
) -> Dict[str, Any]:
    rules = load_engineering_rules(rules_path)
    whitelist = rules.get("法定工种白名单")
    glossary = rules.get("建筑法定术语词典")
    if not isinstance(whitelist, list) or not isinstance(glossary, dict):
        return {
            "ok": True,
            "terminology_loaded": False,
            "entry_count": 0,
            "whitelist_count": 0,
            "changed_sections": 0,
            "replacement_count": 0,
            "llm_invoked_sections": 0,
            "details": [],
        }

    changed_sections = 0
    replacement_count = 0
    llm_invoked_sections = 0
    all_details: List[Dict[str, Any]] = []
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        content = str(sec.get("content") or "")
        if not content:
            continue
        normalized, receipt = await normalize_text_terminology_async(
            content,
            rules_path=rules_path,
            provider=provider,
            model=model,
            api_key=api_key,
            use_llm=use_llm,
        )
        if bool(receipt.get("changed")):
            sec["content"] = normalized
            changed_sections += 1
        if bool(receipt.get("llm_invoked")):
            llm_invoked_sections += 1
        replacement_count += int(receipt.get("replacement_count") or 0)
        if receipt.get("details"):
            all_details.append(
                {
                    "title": str(sec.get("title") or ""),
                    "replacement_count": int(receipt.get("replacement_count") or 0),
                    "llm_invoked": bool(receipt.get("llm_invoked")),
                    "details": receipt.get("details"),
                    "unresolved_terms": receipt.get("unresolved_terms") or [],
                }
            )

    return {
        "ok": True,
        "terminology_loaded": True,
        "entry_count": len(glossary),
        "whitelist_count": len(whitelist),
        "changed_sections": int(changed_sections),
        "replacement_count": int(replacement_count),
        "llm_invoked_sections": int(llm_invoked_sections),
        "details": all_details[:60],
    }


def normalize_sections_terminology(
    sections: List[Dict[str, Any]],
    *,
    terminology_path: str | Path | None = None,
) -> Dict[str, Any]:
    # 兼容旧调用：同步入口默认不开启LLM，避免在未知运行上下文阻塞或递归事件循环。
    rules = load_engineering_rules(terminology_path)
    whitelist = rules.get("法定工种白名单")
    glossary = rules.get("建筑法定术语词典")
    if not isinstance(whitelist, list) or not isinstance(glossary, dict):
        return {
            "ok": True,
            "terminology_loaded": False,
            "entry_count": 0,
            "whitelist_count": 0,
            "changed_sections": 0,
            "replacement_count": 0,
            "llm_invoked_sections": 0,
            "details": [],
        }

    changed_sections = 0
    replacement_count = 0
    all_details: List[Dict[str, Any]] = []
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        content = str(sec.get("content") or "")
        if not content:
            continue
        normalized, receipt = _normalize_text_sync_no_llm(content, rules_path=terminology_path)
        if bool(receipt.get("changed")):
            sec["content"] = normalized
            changed_sections += 1
        replacement_count += int(receipt.get("replacement_count") or 0)
        if receipt.get("details"):
            all_details.append(
                {
                    "title": str(sec.get("title") or ""),
                    "replacement_count": int(receipt.get("replacement_count") or 0),
                    "llm_invoked": False,
                    "details": receipt.get("details"),
                    "unresolved_terms": receipt.get("unresolved_terms") or [],
                }
            )
    return {
        "ok": True,
        "terminology_loaded": True,
        "entry_count": len(glossary),
        "whitelist_count": len(whitelist),
        "changed_sections": int(changed_sections),
        "replacement_count": int(replacement_count),
        "llm_invoked_sections": 0,
        "details": all_details[:60],
    }


def _normalize_project_type(project_type: str, matrix_obj: Dict[str, Any]) -> str:
    t = str(project_type or "").strip()
    if t in matrix_obj:
        return t
    if "房屋" in t or "房建" in t or "建筑" in t:
        return "房屋建筑工程"
    if "市政" in t:
        return "市政基础设施工程"
    return "房屋建筑工程" if "房屋建筑工程" in matrix_obj else (next(iter(matrix_obj.keys()), ""))


def _normalize_size(size: str) -> str:
    s = str(size or "").strip()
    if "大型" in s:
        return "大型项目"
    if "中型" in s:
        return "中型项目"
    if "小型" in s:
        return "小型项目"
    return "中型项目"


def _normalize_stage_bucket(stage: str) -> str:
    s = str(stage or "").strip()
    if any(k in s for k in ("前期", "准备", "临建", "基坑", "土方", "地基", "基础")):
        return "前期"
    if any(k in s for k in ("中期", "主体", "结构", "安装", "机电", "桥梁", "隧道")):
        return "中期"
    if any(k in s for k in ("后期", "装饰", "装修", "收尾", "竣工", "交付")):
        return "后期"
    return "中期"


def _pick_trade_stage_map(project_matrix: Dict[str, Any], project_key: str) -> Dict[str, Any]:
    trade_root = project_matrix.get("关键工种配置比例")
    if not isinstance(trade_root, dict):
        return {}
    if isinstance(trade_root.get(project_key), dict):
        return trade_root.get(project_key) or {}
    # 兼容特殊结构：如果“关键工种配置比例”已经是阶段字典，则直接返回。
    return trade_root


def _is_trade_ratio_row(data: Any) -> bool:
    if not isinstance(data, dict) or not data:
        return False
    ratio_cells = 0
    for _, v in data.items():
        if not isinstance(v, dict):
            continue
        if any("占比" in str(kk or "") for kk in v.keys()):
            ratio_cells += 1
    return ratio_cells > 0


def _is_stage_trade_map(data: Any) -> bool:
    if not isinstance(data, dict) or not data:
        return False
    return any(_is_trade_ratio_row(v) for v in data.values())


def _is_domain_trade_map(data: Any) -> bool:
    if not isinstance(data, dict) or not data:
        return False
    return any(_is_stage_trade_map(v) for v in data.values())


def _pick_trade_domain_name(domain_map: Dict[str, Any], stage_hint: str, project_type: str) -> str:
    if not domain_map:
        return ""
    st = str(stage_hint or "")
    pt = str(project_type or "")
    lex = f"{pt} {st}"
    preferred = [
        ("道路", ("道路", "路基", "路面", "路床", "基层")),
        ("桥梁", ("桥", "梁", "桥面", "桥跨")),
        ("排水", ("排水", "雨污", "管沟", "管线")),
        ("燃气", ("燃气", "燃气管", "中压", "低压")),
        ("综合管廊", ("管廊", "廊体")),
        ("河道", ("河道", "护岸", "堤防", "疏浚")),
        ("水利", ("水利", "闸", "坝", "渠", "泵站")),
    ]
    for domain_name in domain_map.keys():
        dn = str(domain_name or "")
        if not dn:
            continue
        if dn in lex or lex in dn:
            return dn
    for domain_kw, hit_tokens in preferred:
        if any(t in lex for t in hit_tokens):
            for domain_name in domain_map.keys():
                dn = str(domain_name or "")
                if domain_kw in dn:
                    return dn
    return str(next(iter(domain_map.keys()), "") or "")


def _resolve_trade_stage_map(project_matrix: Dict[str, Any], *, project_key: str, stage_hint: str) -> Tuple[str, Dict[str, Any]]:
    base = _pick_trade_stage_map(project_matrix, project_key)
    if _is_stage_trade_map(base):
        return project_key, base
    if _is_domain_trade_map(base):
        domain = _pick_trade_domain_name(base, stage_hint=stage_hint, project_type=project_key)
        stage_map = base.get(domain) if isinstance(base.get(domain), dict) else {}
        return domain, stage_map if _is_stage_trade_map(stage_map) else {}
    return "", {}


def _pick_trade_ratio(stage_map: Dict[str, Any], stage: str) -> Dict[str, Any]:
    if _is_trade_ratio_row(stage_map):
        return stage_map
    if not isinstance(stage_map, dict) or not stage_map:
        return {}
    stage_txt = str(stage or "").strip()
    if stage_txt and isinstance(stage_map.get(stage_txt), dict):
        row = stage_map.get(stage_txt) or {}
        return row if _is_trade_ratio_row(row) else {}
    # 模糊匹配：优先包含关系。
    for k, v in stage_map.items():
        kk = str(k or "").strip()
        if not kk or not isinstance(v, dict):
            continue
        if stage_txt and (stage_txt in kk or kk in stage_txt):
            return v if _is_trade_ratio_row(v) else {}
    # 回退：章节语义映射到常见阶段名。
    bucket = _normalize_stage_bucket(stage_txt)
    candidate_keys = {
        "前期": ("地基与基础", "前期"),
        "中期": ("主体结构", "中期"),
        "后期": ("建筑装饰装修", "后期"),
    }.get(bucket, ())
    for ck in candidate_keys:
        if isinstance(stage_map.get(ck), dict):
            row = stage_map.get(ck) or {}
            if _is_trade_ratio_row(row):
                return row
    first_key = next(iter(stage_map.keys()), "")
    row = stage_map.get(first_key) if isinstance(stage_map.get(first_key), dict) else {}
    return row if _is_trade_ratio_row(row) else {}


def suggest_labor_ratio_for_chapter(matrix_obj: Dict[str, Any], *, project_type: str, chapter_title: str) -> Dict[str, Any]:
    matrix = matrix_obj if isinstance(matrix_obj, dict) else load_labor_allocation_matrix()
    if not matrix:
        return {}
    p = _normalize_project_type(project_type, matrix)
    pm = matrix.get(p) if isinstance(matrix.get(p), dict) else {}
    if not pm:
        return {}

    title = str(chapter_title or "").strip()
    size = "大型项目" if any(x in title for x in ("主体", "总平", "组织", "资源")) else "中型项目"
    size = _normalize_size(size)
    stage_hint = title or "主体结构"
    stage_bucket = _normalize_stage_bucket(stage_hint)

    skill_root = pm.get("各等级技能工人配备比例")
    skill_ratio: Dict[str, Any] = {}
    if isinstance(skill_root, dict):
        size_map = skill_root.get(size)
        if not isinstance(size_map, dict) and isinstance(skill_root.get("中型项目"), dict):
            size_map = skill_root.get("中型项目")
            size = "中型项目"
        if isinstance(size_map, dict):
            row = size_map.get(stage_bucket)
            if not isinstance(row, dict):
                row = size_map.get("中期") if isinstance(size_map.get("中期"), dict) else {}
            if isinstance(row, dict):
                skill_ratio = row

    selected_trade_domain, trade_stage_map = _resolve_trade_stage_map(pm, project_key=p, stage_hint=stage_hint)
    trade_ratio = _pick_trade_ratio(trade_stage_map, stage_hint)

    return {
        "project_type": p,
        "trade_domain": selected_trade_domain,
        "size": size,
        "stage": stage_bucket,
        "stage_detail": title or stage_bucket,
        "skill_ratio": skill_ratio if isinstance(skill_ratio, dict) else {},
        "trade_ratio": trade_ratio if isinstance(trade_ratio, dict) else {},
    }


def get_labor_ratio_by_condition(
    *,
    project_type: str,
    size: str,
    stage: str,
    trade_name: str = "木工",
    rules_path: str | Path | None = None,
) -> Dict[str, Any]:
    matrix = load_labor_allocation_matrix(rules_path)
    if not matrix:
        return {"ok": False, "reason": "matrix_missing"}
    p = _normalize_project_type(project_type, matrix)
    size_key = _normalize_size(size)
    pm = matrix.get(p) if isinstance(matrix.get(p), dict) else {}
    if not pm:
        return {"ok": False, "reason": f"project_type_not_found:{p}"}

    skill_root = pm.get("各等级技能工人配备比例")
    skill_row = {}
    if isinstance(skill_root, dict):
        size_map = skill_root.get(size_key)
        if not isinstance(size_map, dict):
            size_map = skill_root.get("中型项目") if isinstance(skill_root.get("中型项目"), dict) else {}
            size_key = "中型项目"
        if isinstance(size_map, dict):
            skill_row = size_map.get(stage)
            if not isinstance(skill_row, dict):
                skill_row = size_map.get(_normalize_stage_bucket(stage), {})
            if not isinstance(skill_row, dict):
                skill_row = {}

    selected_trade_domain, trade_stage_map = _resolve_trade_stage_map(pm, project_key=p, stage_hint=stage)
    trade_row = _pick_trade_ratio(trade_stage_map, stage)
    trade_item = trade_row.get(trade_name) if isinstance(trade_row, dict) else None

    return {
        "ok": True,
        "project_type": p,
        "trade_domain": selected_trade_domain,
        "size": size_key,
        "stage": stage,
        "skill_ratio": skill_row if isinstance(skill_row, dict) else {},
        "trade_ratio": trade_row if isinstance(trade_row, dict) else {},
        "trade_name": trade_name,
        "trade_value": trade_item if isinstance(trade_item, dict) else {},
    }
