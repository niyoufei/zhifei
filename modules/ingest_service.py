import os, json, hashlib
from datetime import datetime
from typing import Dict, Any
from modules.parser.parser_unify import UnifiedParser

def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_with_audit(file_path: str, out_dir: str = "logs/parser_audit") -> Dict[str, Any]:
    """统一解析并落盘审计日志，返回结果+日志路径"""
    parser = UnifiedParser(file_path)
    res = parser.parse()  # {"type":..., "content": {...} 或 错误信息}
    content = res.get("content", {}) if isinstance(res.get("content", {}), dict) else {}

    audit = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "input_file": os.path.abspath(file_path),
        "input_sha256": sha256_of(file_path),
        "detected_type": res.get("type"),
        "stats": {
            "paragraphs": len(content.get("paragraphs", [])),
            "tables": len(content.get("tables", [])),
        },
        "preview": {"paragraphs_head": content.get("paragraphs", [])[:3]},
    }

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"parse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"result": res, "audit": audit}, f, ensure_ascii=False, indent=2)

    return {"result": res, "audit": audit, "log_path": out_path}

if __name__ == "__main__":
    # 简易自测：默认解析 example.pdf
    path = os.environ.get("PARSE_FILE", "example.pdf")
    out = parse_with_audit(path)
    print(json.dumps({"ok": True, "log_path": out["log_path"], "detected": out["audit"]["detected_type"]}, ensure_ascii=False, indent=2))
