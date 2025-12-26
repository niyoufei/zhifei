from pathlib import Path
import json, re
from typing import List, Dict, Any
from fastapi import APIRouter, Query, HTTPException

router = APIRouter()
AUDIT_PATH = Path("backend/data/audit/ingest.jsonl")

def _load_records() -> List[Dict[str, Any]]:
    if not AUDIT_PATH.exists():
        return []
    recs = []
    for ln in AUDIT_PATH.read_text(encoding="utf-8").splitlines():
        try:
            recs.append(json.loads(ln))
        except Exception:
            continue
    return recs

@router.get("/search")
async def search(q: str = Query(..., min_length=1), limit: int = 20) -> Dict[str, Any]:
    recs = _load_records()
    if not recs:
        raise HTTPException(status_code=404, detail="no ingested documents")

    results: List[Dict[str, Any]] = []
    pat = re.compile(re.escape(q), re.IGNORECASE)
    scanned = 0
    for rec in reversed(recs):
        p = Path(rec.get("extract_saved_as") or "")
        if not p.exists() or not p.is_file():
            continue
        scanned += 1
        text = p.read_text(encoding="utf-8", errors="ignore")
        for m in pat.finditer(text):
            start = max(0, m.start() - 80)
            end   = min(len(text), m.end() + 80)
            snippet = text[start:end].replace("\n", " ")
            results.append({
                "filename": rec.get("filename"),
                "sha256": rec.get("sha256"),
                "extract_saved_as": str(p),
                "offset": m.start(),
                "snippet": snippet
            })
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break
    return {"query": q, "scanned_files": scanned, "hits": results}

retrieve_router = router
