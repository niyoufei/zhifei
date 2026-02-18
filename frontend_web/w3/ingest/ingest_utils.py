from pathlib import Path
import uuid, filetype

ALLOWED_EXT = {
    # 文档
    ".pdf",".doc",".docx",".xls",".xlsx",".ppt",".pptx",".txt",
    # 图片/照片
    ".png",".jpg",".jpeg",".bmp",".tiff",
    # CAD
    ".dxf",".dwg"
}

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def detect_kind(data: bytes, fallback_ext: str) -> str:
    try:
        k = filetype.guess(data)
        if k: 
            return k.mime
    except Exception:
        pass
    # 粗略兜底：用扩展名回退
    return f"ext/{fallback_ext.lstrip('.').lower()}" if fallback_ext else "ext/unknown"

def save_file(storage, base_dir: Path, category: str) -> dict:
    """storage 为 Flask 的 FileStorage；返回 {name,path,kind,ext}"""
    orig = storage.filename or "unnamed"
    ext = (Path(orig).suffix or "").lower()
    # 非允许类型也先保存（后续解析时再过滤），但在 meta 里标注
    uid = uuid.uuid4().hex[:12]
    safe = f"{Path(orig).stem}_{uid}{ext}"
    outdir = ensure_dir(base_dir/category)
    outpath = outdir/safe
    data = storage.read()
    outpath.write_bytes(data)
    kind = detect_kind(data, ext)
    return {"name": orig, "saved_as": safe, "path": str(outpath), "ext": ext, "kind": kind, "allowed": ext in ALLOWED_EXT}
