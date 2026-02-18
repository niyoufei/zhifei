import os, json, hashlib
from datetime import datetime
from modules.parser.parser_unify import UnifiedParser

# 允许通过环境变量指定文件；默认为 example.pdf
file_path = os.environ.get("PARSE_FILE", "example.pdf")

# 计算输入文件哈希，满足“输入可追溯”要求
def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

parser = UnifiedParser(file_path)
res = parser.parse()                      # {"type": ..., "content": {...}}
content = res.get("content", {})

log = {
    "ts": datetime.now().isoformat(timespec="seconds"),
    "input_file": os.path.abspath(file_path),
    "input_sha256": sha256_of(file_path),
    "detected_type": res.get("type"),
    "stats": {
        "paragraphs": len(content.get("paragraphs", [])) if isinstance(content, dict) else None,
        "tables": len(content.get("tables", [])) if isinstance(content, dict) else None
    },
    "preview": {
        "paragraphs_head": content.get("paragraphs", [])[:3]
    }
}

os.makedirs("logs/parser_audit", exist_ok=True)
out_name = f"logs/parser_audit/parse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(out_name, "w", encoding="utf-8") as f:
    json.dump({"result": res, "audit": log}, f, ensure_ascii=False, indent=2)

print(f"✅ 审计日志已生成: {out_name}")
