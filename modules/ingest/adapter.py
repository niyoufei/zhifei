"""
modules/ingest/adapter.py
作用：提供统一“解析+审计”入口，供 /ingest API 调用。
输出结构：{ "type": ..., "content": {...}, "audit": {...} }
"""
import os, json, hashlib
from datetime import datetime
from modules.parser.parser_unify import UnifiedParser

def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_with_audit(file_path: str) -> dict:
    """统一解析 + 审计落盘"""
    parser = UnifiedParser(file_path)
    res = parser.parse()  # {"type": ..., "content": {...}} 或 {"error": ...}
    content = res.get("content", {}) if isinstance(res, dict) else {}

    audit = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "input_file": os.path.abspath(file_path),
        "input_sha256": _sha256(file_path),
        "detected_type": res.get("type"),
        "stats": {
            "paragraphs": len(content.get("paragraphs", [])) if isinstance(content, dict) else None,
            "tables": len(content.get("tables", [])) if isinstance(content, dict) else None
        },
        "preview": {"paragraphs_head": content.get("paragraphs", [])[:3] if isinstance(content, dict) else []}
    }

    os.makedirs("logs/parser_audit", exist_ok=True)
    out_name = f"logs/parser_audit/ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_name, "w", encoding="utf-8") as f:
        json.dump({"result": res, "audit": audit}, f, ensure_ascii=False, indent=2)
    audit["log_file"] = out_name
    return {"type": res.get("type"), "content": content, "audit": audit}

if __name__ == "__main__":
    fp = os.environ.get("PARSE_FILE", "example.pdf")
    data = parse_with_audit(fp)
    print(json.dumps({"ok": True, "detected": data["audit"]["detected_type"], "log_file": data["audit"]["log_file"]}, ensure_ascii=False, indent=2))
