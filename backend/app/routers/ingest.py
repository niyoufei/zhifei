from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pypdf import PdfReader

router = APIRouter(prefix="/ingest", tags=["文档解析"])

UPLOAD_DIR = Path("backend/data/uploads")
EXTRACT_DIR = Path("backend/data/extracts")
PREVIEW_DIR = Path("backend/data/previews")
AUDIT_DIR = Path("backend/data/audit")
for d in (UPLOAD_DIR, EXTRACT_DIR, PREVIEW_DIR, AUDIT_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _ext(name: str) -> str:
    return (name.rsplit(".", 1)[-1].lower() if "." in name else "")


def _extract_text_bytes(ext: str, content: bytes) -> Dict[str, Any]:
    if ext in {"txt", "md"}:
        text = content.decode("utf-8", errors="ignore")
        return {
            "doc_type": ext,
            "pages": 1,
            "text_bytes": len(text.encode("utf-8")),
            "extract_text": text,
        }
    if ext == "pdf":
        reader = PdfReader(BytesIO(content))
        texts = []
        for page in reader.pages:
            # Use form-feed as a page boundary so evidence search can recover page numbers
            # without adding alnum/han noise (which would affect OCR heuristics).
            texts.append(page.extract_text() or "")
        text = "\n\n\f\n\n".join(texts)
        return {
            "doc_type": "pdf",
            "pages": len(reader.pages),
            "text_bytes": len(text.encode("utf-8")),
            "extract_text": text,
        }
    return {"doc_type": ext or "unknown", "pages": None, "text_bytes": None}


def _meta_to_text(parsed_type: str | None, parsed_meta: Any) -> str:
    if parsed_type == "cad" and isinstance(parsed_meta, dict):
        layers = parsed_meta.get("layers_count")
        entities = parsed_meta.get("entities_count")
        inserts = parsed_meta.get("insert_blocks") or {}
        top_blocks = []
        if isinstance(inserts, dict):
            for k, v in sorted(inserts.items(), key=lambda x: x[1], reverse=True)[:8]:
                top_blocks.append(f"{k}:{v}")
        return (
            f"图纸类型: CAD(DXF ASCII)\n"
            f"图层数量: {layers}\n"
            f"实体数量: {entities}\n"
            f"块引用: {'; '.join(top_blocks)}"
        )
    if parsed_type == "image" and isinstance(parsed_meta, dict):
        return (
            f"图纸类型: 图片\n"
            f"尺寸: {parsed_meta.get('width')}x{parsed_meta.get('height')}\n"
            f"模式: {parsed_meta.get('mode')}"
        )
    if parsed_type == "dwg" and isinstance(parsed_meta, dict):
        return f"图纸类型: DWG\n说明: {parsed_meta.get('note') or '暂不支持解析'}"
    return ""


def _classify_tags(filename: str | None, ext: str, parsed_type: str | None) -> list[str]:
    name = (filename or "").lower()
    tags = []
    if any(k in name for k in ("logo", "标志", "标识", "徽标")):
        tags.append("logo")
    if any(k in name for k in ("图", "图纸", "施工图", "平面", "剖面", "大样", "节点", "cad", "dwg", "dxf")):
        tags.append("drawing")
    if any(k in name for k in ("清单", "工程量清单", "boq")):
        tags.append("boq")
    if any(k in name for k in ("招标", "招標", "tender")):
        tags.append("tender")
    if any(k in name for k in ("企业标准", "工法", "作业指导", "标准化", "技术标准", "标准图集", "管理标准")):
        tags.append("standard")
    if ext in {"dxf", "dwg"} or parsed_type in {"cad", "dwg"}:
        if "drawing" not in tags:
            tags.append("drawing")
    if ext in {"png", "jpg", "jpeg"} and "drawing" not in tags:
        # 纯图片无法判断用途，默认打上 drawing，便于后续人工筛选
        tags.append("drawing")
    return tags


def _make_preview_image(src_path: Path, dst_path: Path, max_width: int = 1400) -> str | None:
    try:
        from PIL import Image

        with Image.open(src_path) as im:
            im = im.convert("RGB")
            if im.width > max_width:
                h = int(im.height * (max_width / max(1, im.width)))
                im = im.resize((max_width, max(1, h)))
            im.save(dst_path, format="PNG")
        return str(dst_path)
    except Exception:
        return None


def _make_preview_pdf_first_page(src_path: Path, dst_path: Path, scale: float = 2.0, max_width: int = 1600) -> str | None:
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(str(src_path))
        if len(pdf) <= 0:
            return None
        page = pdf[0]
        bitmap = page.render(scale=float(scale))
        im = bitmap.to_pil()
        try:
            pdf.close()
        except Exception:
            pass
        if im.width > max_width:
            from PIL import Image

            h = int(im.height * (max_width / max(1, im.width)))
            im = im.resize((max_width, max(1, h)), resample=Image.BICUBIC)
        im.save(dst_path, format="PNG")
        return str(dst_path)
    except Exception:
        return None


async def _try_ocr(path: Path, ext: str, existing_text: str | None) -> str | None:
    """
    Best-effort OCR. Only runs when tesseract is installed and extracted text is likely empty.
    """
    base = (existing_text or "").strip()
    # If already has meaningful text, skip OCR to keep ingest fast.
    if len(base) >= 200:
        return None
    try:
        from backend.zhifei_autoplan.ocr_runtime import (
            is_tesseract_available,
            guess_ocr_lang,
            is_text_probably_scanned,
            ocr_pdf_path,
        )
    except Exception:
        return None
    if not is_tesseract_available():
        return None

    if ext == "pdf":
        if not is_text_probably_scanned(base, min_han=10, min_alnum=30):
            return None
        lang = guess_ocr_lang(prefer_chinese=True)
        res = await asyncio.to_thread(ocr_pdf_path, str(path), 10, 2.2, lang, True)
        return res.text if res and res.text else None

    if ext in {"png", "jpg", "jpeg"}:
        try:
            import pytesseract
            from PIL import Image
            from backend.zhifei_autoplan.ocr_runtime import guess_ocr_lang

            lang = guess_ocr_lang(prefer_chinese=True)

            def _ocr():
                with Image.open(path) as im:
                    return pytesseract.image_to_string(im, lang=lang)

            txt = await asyncio.to_thread(_ocr)
            return txt.strip() if txt and txt.strip() else None
        except Exception:
            return None
    return None

async def _handle_upload(files: List[UploadFile], project_id: str | None = None):
    if not files:
        raise HTTPException(status_code=400, detail="no files uploaded")

    day = datetime.utcnow().strftime("%Y%m%d")
    target_dir = UPLOAD_DIR / day
    target_dir.mkdir(parents=True, exist_ok=True)

    records = []
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    for uf in files:
        content = await uf.read()
        if not content:
            continue
        digest = _sha256(content)
        ext = _ext(uf.filename or "")

        saved_name = f"{digest[:8]}_{uf.filename}"
        out_path = target_dir / saved_name
        out_path.write_bytes(content)

        parsed = _extract_text_bytes(ext, content)
        parsed_type = None
        parsed_meta = None
        if parsed.get("extract_text") is None and ext not in {"txt", "md", "pdf"}:
            try:
                from modules.parser.parser_unify import UnifiedParser

                uni = UnifiedParser(str(out_path))
                uret = uni.parse()
                parsed_type = uret.get("type")
                parsed_meta = uret.get("meta")
                utext = uret.get("text")
                if isinstance(utext, str) and utext.strip():
                    parsed["extract_text"] = utext
                else:
                    meta_text = _meta_to_text(parsed_type, parsed_meta)
                    if meta_text.strip():
                        parsed["extract_text"] = meta_text
            except Exception as e:
                parsed_meta = {"error": repr(e)}

        # OCR (best-effort): for scanned PDFs / drawings images to improve retrieval & evidence binding
        try:
            ocr_text = await _try_ocr(out_path, ext, parsed.get("extract_text"))
            if ocr_text:
                base = (parsed.get("extract_text") or "").strip()
                merged = (base + "\n\n" + ocr_text).strip() if base else ocr_text.strip()
                parsed["extract_text"] = merged
        except Exception:
            pass

        # Preview (best-effort): generate a PNG thumbnail for drawings/PDFs to embed into DOCX later
        preview_path = None
        try:
            preview_name = f"{digest[:8]}_preview.png"
            preview_out = PREVIEW_DIR / preview_name
            if ext in {"png", "jpg", "jpeg"}:
                preview_path = _make_preview_image(out_path, preview_out)
            elif ext == "pdf":
                preview_path = _make_preview_pdf_first_page(out_path, preview_out, scale=2.0)
        except Exception:
            preview_path = None

        extract_path = None
        if parsed.get("extract_text") is not None:
            extract_path = EXTRACT_DIR / f"{digest[:8]}.txt"
            extract_path.write_text(parsed["extract_text"], encoding="utf-8")
            parsed.pop("extract_text", None)

        rec = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "module": "ingest",
            "project_id": pid,
            "filename": uf.filename,
            "saved_as": str(out_path),
            "bytes": len(content),
            "sha256": digest,
            "extract_saved_as": str(extract_path) if extract_path else None,
            "preview_saved_as": preview_path,
            **parsed,
            "parsed_type": parsed_type,
            "parsed_meta": parsed_meta,
            "tags": _classify_tags(uf.filename, ext, parsed_type),
        }
        records.append(rec)
        with (AUDIT_DIR / "ingest.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if not records:
        raise HTTPException(status_code=400, detail="all files are empty")
    return {"saved": records}


@router.get("/ping")
async def ping():
    return {"module": "ingest", "status": "ok"}


@router.post("/upload")
async def upload(files: List[UploadFile] = File(...), project_id: str | None = None):
    return await _handle_upload(files, project_id=project_id)


@router.post("/ingest")
async def ingest(files: List[UploadFile] = File(...), project_id: str | None = None):
    return await _handle_upload(files, project_id=project_id)
