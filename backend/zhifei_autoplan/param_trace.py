from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


PARAM_PLACEHOLDER_RE = re.compile(r"\[\[PARAM:(?P<key>[A-Za-z0-9_.\u4e00-\u9fff]+)\]\]")


def flatten_editable_params(params: Dict[str, Any]) -> Dict[str, str]:
    """
    Flatten editable params into a stable key -> string value map.
    Only include values that are expected to show up in text output.
    """
    out: Dict[str, str] = {}
    if not isinstance(params, dict):
        return out

    q = params.get("quant_defaults") if isinstance(params.get("quant_defaults"), dict) else {}
    for k, v in q.items():
        if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
            out[f"quant_defaults.{k.strip()}"] = v.strip()

    card = params.get("boq_focus_card") if isinstance(params.get("boq_focus_card"), dict) else {}
    for k, v in card.items():
        if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
            out[f"boq_focus_card.{k.strip()}"] = v.strip()

    qse = params.get("qse_defaults") if isinstance(params.get("qse_defaults"), dict) else {}
    for k, v in qse.items():
        if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
            out[f"qse_defaults.{k.strip()}"] = v.strip()
    return out


def substitute_param_placeholders(text: str, params_map: Dict[str, str]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Replace [[PARAM:key]] placeholders with current param values.
    Returns (new_text, placeholder_hits) where hits contain placeholder offsets for traceability.
    """
    s = text or ""
    hits: List[Dict[str, Any]] = []

    def _repl(m: re.Match):
        key = (m.group("key") or "").strip()
        hits.append({"key": key, "offset": int(m.start()), "placeholder": m.group(0)})
        val = params_map.get(key)
        return val if isinstance(val, str) and val.strip() else m.group(0)

    out = PARAM_PLACEHOLDER_RE.sub(_repl, s)
    return out, hits


def _find_value_occurrences(text: str, value: str, max_hits: int = 40) -> List[int]:
    if not value:
        return []
    offsets: List[int] = []
    start = 0
    while True:
        idx = (text or "").find(value, start)
        if idx < 0:
            break
        offsets.append(int(idx))
        if len(offsets) >= max_hits:
            break
        start = idx + max(1, len(value))
    return offsets


def build_param_receipt(sections: List[Dict[str, Any]], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a traceability receipt:
    - param_key -> where it appears (placeholder/value) -> impacted chapters
    Also performs placeholder substitution in-place for section content.
    """
    params_map = flatten_editable_params(params)
    receipt: Dict[str, Any] = {
        "version": str((params or {}).get("version") or ""),
        "keys": {},
    }
    for k, v in sorted(params_map.items(), key=lambda x: x[0]):
        receipt["keys"][k] = {
            "value": v,
            "impacted_chapters": [],
            "placeholder_occurrences": [],
            "value_occurrences": [],
        }

    for sec in sections or []:
        title = str(sec.get("title") or "章节")
        text = str(sec.get("content") or "")
        new_text, ph_hits = substitute_param_placeholders(text, params_map)
        sec["content"] = new_text

        # Record placeholder hits (pre-substitution offsets).
        for h in ph_hits:
            key = str(h.get("key") or "").strip()
            if key not in receipt["keys"]:
                receipt["keys"].setdefault(
                    key,
                    {"value": params_map.get(key, ""), "impacted_chapters": [], "placeholder_occurrences": [], "value_occurrences": []},
                )
            item = receipt["keys"][key]
            item["placeholder_occurrences"].append({"title": title, "offset": h.get("offset")})
            if title not in item["impacted_chapters"]:
                item["impacted_chapters"].append(title)

        # Record value hits (post-substitution offsets).
        for key, val in params_map.items():
            offsets = _find_value_occurrences(new_text, val, max_hits=24)
            if not offsets:
                continue
            item = receipt["keys"].get(key)
            if not item:
                continue
            for off in offsets:
                item["value_occurrences"].append({"title": title, "offset": int(off)})
            if title not in item["impacted_chapters"]:
                item["impacted_chapters"].append(title)

    # Sort chapters list to make receipts stable/diff-friendly
    for key, item in (receipt.get("keys") or {}).items():
        try:
            item["impacted_chapters"] = sorted(set(item.get("impacted_chapters") or []))
        except Exception:
            pass
    return receipt


RECEIPT_LATEST_PATH = Path("backend/data/autoplan/param_receipt_latest.json")
PROJECTS_DIR = Path("backend/data/autoplan/projects")


def _safe_project_id(project_id: str, limit: int = 80) -> str:
    from backend.zhifei_autoplan.project_namespace import project_storage_key

    return project_storage_key(project_id, limit=limit)


def receipt_path(project_id: str | None = None) -> Path:
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    if not pid:
        return RECEIPT_LATEST_PATH
    safe = _safe_project_id(pid)
    return PROJECTS_DIR / safe / "param_receipt.json"


def save_latest_receipt(receipt: Dict[str, Any], project_id: str | None = None) -> str:
    path = receipt_path(project_id=project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt or {}, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def load_latest_receipt(project_id: str | None = None) -> Dict[str, Any] | None:
    path = receipt_path(project_id=project_id)
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def diff_params_with_receipt(before: Dict[str, Any], after: Dict[str, Any], receipt: Dict[str, Any] | None) -> Dict[str, Any]:
    before_map = flatten_editable_params(before or {})
    after_map = flatten_editable_params(after or {})
    keys = sorted(set(before_map) | set(after_map))

    receipt_keys = (receipt or {}).get("keys") if isinstance((receipt or {}).get("keys"), dict) else {}

    changes = []
    for k in keys:
        b = before_map.get(k)
        a = after_map.get(k)
        if (b or "") == (a or ""):
            continue
        impacted = []
        placeholder_occ = []
        value_occ = []
        occurrence_positions: Dict[str, List[int]] = {}
        try:
            r = receipt_keys.get(k) or {}
            impacted = list(r.get("impacted_chapters") or [])
            placeholder_occ = list(r.get("placeholder_occurrences") or [])
            value_occ = list(r.get("value_occurrences") or [])
        except Exception:
            impacted = []
            placeholder_occ = []
            value_occ = []
        for it in placeholder_occ + value_occ:
            if not isinstance(it, dict):
                continue
            title = str(it.get("title") or "").strip()
            if not title:
                continue
            try:
                off = int(it.get("offset"))
            except Exception:
                continue
            occurrence_positions.setdefault(title, []).append(off)
        for t, offs in list(occurrence_positions.items()):
            occurrence_positions[t] = sorted(set(offs))[:120]
        changes.append(
            {
                "key": k,
                "before": b,
                "after": a,
                "impacted_chapters": impacted,
                "impacted_chapter_count": len(impacted),
                "placeholder_occurrence_count": len(placeholder_occ),
                "value_occurrence_count": len(value_occ),
                "occurrence_positions": occurrence_positions,
            }
        )
    return {"changed": changes, "changed_count": len(changes)}
