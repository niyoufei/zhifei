from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.zhifei_autoplan.kg_store import get_active_kg


def _tokenize(query: str) -> List[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+", query or "")
    out: List[str] = []
    seen: set[str] = set()
    for t in tokens:
        tt = t.strip()
        if len(tt) < 2:
            continue
        if tt not in seen:
            seen.add(tt)
            out.append(tt)
    return out


def _extract_docs(obj: Any, path: str = "$") -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []

    def add_doc(title: str, text: str, p: str):
        if not text or len(text) < 20:
            return
        docs.append({"title": title, "text": text, "path": p})

    def flatten(x: Any, prefix: str = "") -> List[str]:
        out: List[str] = []
        if x in (None, "", [], {}):
            return out
        if isinstance(x, dict):
            for k, v in x.items():
                np = f"{prefix}.{k}" if prefix else str(k)
                if isinstance(v, (dict, list)):
                    out.extend(flatten(v, np))
                else:
                    if v in (None, "", [], {}):
                        continue
                    out.append(f"{np}: {v}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                np = f"{prefix}[{i}]" if prefix else f"[{i}]"
                if isinstance(v, (dict, list)):
                    out.extend(flatten(v, np))
                else:
                    if v in (None, "", [], {}):
                        continue
                    out.append(f"{np}: {v}")
        else:
            out.append(f"{prefix}: {x}" if prefix else str(x))
        return out

    def walk(x: Any, p: str):
        if isinstance(x, dict):
            title = (
                x.get("工序名称")
                or x.get("name")
                or x.get("title")
                or x.get("node_id")
                or x.get("id")
            )
            if title:
                parts = flatten(x)
                if parts:
                    add_doc(str(title), "\n".join(parts), p)
            for k, v in x.items():
                if isinstance(v, (dict, list)):
                    walk(v, f"{p}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{p}[{i}]")

    walk(obj, path)
    return docs

def search_kg(query: str, top_k: int = 6, *, workspace_dir: str | None = None) -> Dict[str, Any]:
    active = get_active_kg(workspace_dir=workspace_dir)
    if not active:
        return {"results": [], "error": "no_active_kg"}

    path = Path(active["stored_as"])
    if not path.exists():
        return {"results": [], "error": "kg_file_missing"}

    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"results": [], "error": f"kg_parse_error: {e!r}"}

    tokens = _tokenize(query)
    if not tokens:
        return {"results": [], "error": "empty_query"}

    docs = _extract_docs(obj)
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for d in docs:
        text = d.get("text", "")
        score = 0.0
        for t in tokens:
            if t in text:
                score += 1.0
        if score > 0:
            scored.append((score, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for sc, d in scored[:top_k]:
        results.append(
            {
                "title": d.get("title"),
                "text": d.get("text")[:900],
                "score": sc,
                "path": d.get("path"),
            }
        )
    return {"results": results}
