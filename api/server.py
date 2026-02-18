from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os, shutil, uuid
from modules.ingest.adapter import parse_with_audit

app = FastAPI(title="TraceableDocSys /ingest", version="0.1.0")

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    # 基础校验（扩展名白名单）
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    allowed = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg", ".dwg"}
    if ext and ext not in allowed:
        raise HTTPException(status_code=400, detail=f"unsupported file extension: {ext}")

    # 落盘保存
    save_name = f"{uuid.uuid4().hex}{ext if ext else ''}"
    save_path = os.path.join(UPLOAD_DIR, save_name)
    with open(save_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    # 统一解析 + 审计
    out = parse_with_audit(save_path)

    return JSONResponse(content={
        "ok": True,
        "detected_type": out["audit"]["detected_type"],
        "stats": out["audit"]["stats"],
        "preview": out["audit"]["preview"],
        "log_file": out["audit"]["log_file"],
        "saved_file": os.path.abspath(save_path)
    })
