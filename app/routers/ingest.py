from typing import List
from datetime import datetime
from pathlib import Path
from io import BytesIO
import hashlib, json

from fastapi import APIRouter, UploadFile, File, HTTPException
from pypdf import PdfReader  # 新增：PDF 解析

router = APIRouter()

# 存储与审计目录
UPLOAD_DIR = Path("backend/data/uploads")
EXTRACT_DIR = Path("backend/data/extracts")
AUDIT_DIR  = Path("backend/data/audit")
for d in (UPLOAD_DIR, EXTRACT_DIR, AUDIT_DIR):
    d.mkdir(parents=True, exist_ok=True)

@router.get("/ping")
async def ping():
    return {"module": "ingest", "status": "ok"}

def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _ext(name: str) -> str:
    return (name.rsplit(".", 1)[-1].lower() if "." in name else "")

def _extract_text_bytes(ext: str, content: bytes) -> dict:
    """
    针对不同类型做最小抽取：
    - txt/md：按 UTF-8 解码为文本
    - pdf   ：用 pypdf 逐页提取文本并合并
    其他类型暂不处理（返回占位信息）
    """
    if ext in {"txt", "md"}:
        text = content.decode("utf-8", errors="ignore")
        text_bytes = len(text.encode("utf-8"))
        return {"doc_type": ext, "pages": 1, "text_bytes": text_bytes, "extract_text": text}

    if ext == "pdf":
        reader = PdfReader(BytesIO(content))
        pages = len(reader.pages)
        texts = []
        for i in range(pages):
            t = reader.pages[i].extract_text() or ""
            texts.append(t)
        text = "\n\n".join(texts)
        text_bytes = len(text.encode("utf-8"))
        return {"doc_type": "pdf", "pages": pages, "text_bytes": text_bytes, "extract_text": text}

    return {"doc_type": ext or "unknown", "pages": None, "text_bytes": None}

@router.post("/upload")
async def upload(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="no files uploaded")

    day = datetime.utcnow().strftime("%Y%m%d")
    target_dir = UPLOAD_DIR / day
    target_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for uf in files:
        content = await uf.read()
        digest  = _sha256(content)
        ext = _ext(uf.filename)

        saved_name = f"{digest[:8]}_{uf.filename}"
        out_path = target_dir / saved_name
        out_path.write_bytes(content)

        # 解析（txt/md/pdf）
        parsed = _extract_text_bytes(ext, content)
        extract_path = None
        if parsed.get("extract_text") is not None:
            extract_path = EXTRACT_DIR / f"{digest[:8]}.txt"
            extract_path.write_text(parsed["extract_text"], encoding="utf-8")
            parsed.pop("extract_text", None)

        rec = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "module": "ingest",
            "filename": uf.filename,
            "saved_as": str(out_path),
            "bytes": len(content),
            "sha256": digest,
            "extract_saved_as": str(extract_path) if extract_path else None,
            **parsed,
            "tags": [],
        }
        records.append(rec)
        with (AUDIT_DIR / "ingest.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return {"saved": records}

# 供 main.py 或 routers/__init__.py 聚合
ingest_router = router
