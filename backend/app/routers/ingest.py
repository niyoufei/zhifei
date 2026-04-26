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

from backend.zhifei_autoplan.case_library_service import CASE_LIBRARY_SCOPE
from backend.zhifei_autoplan.image_library import IMAGE_LIBRARY_SCOPE, normalize_text_list
from backend.zhifei_autoplan.project_types import normalize_project_type

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


def _resolve_workspace_context(
    session_id: str | None = None,
    workspace_dir: str | None = None,
) -> Dict[str, str]:
    if workspace_dir:
        root = Path(workspace_dir)
    elif session_id:
        safe_session = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(session_id))
        root = Path("backend/data/workspaces") / (safe_session or "default")
    else:
        root = Path("backend/data")
    root.mkdir(parents=True, exist_ok=True)
    return {"session_id": str(session_id or ""), "workspace_dir": str(root)}


def workspace_paths(workspace_dir: str | Path) -> Dict[str, Path]:
    root = Path(workspace_dir)
    paths = {
        "uploads": root / "uploads",
        "extracts": root / "extracts",
        "previews": root / "previews",
        "ingest_audit": root / "audit" / "ingest.jsonl",
    }
    for key, path in paths.items():
        if key == "ingest_audit":
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
    return paths


def _extract_text_path(ext: str, path: Path) -> Dict[str, Any]:
    if ext in {"txt", "md"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return {
            "doc_type": ext,
            "pages": 1,
            "text_bytes": len(text.encode("utf-8")),
            "extract_text": text,
        }
    if ext == "pdf":
        reader = PdfReader(str(path))
        texts = []
        for page in reader.pages:
            texts.append(page.extract_text() or "")
        text = "\n\n\f\n\n".join(texts)
        return {
            "doc_type": "pdf",
            "pages": len(reader.pages),
            "text_bytes": len(text.encode("utf-8")),
            "extract_text": text,
        }
    return {"doc_type": ext or "unknown", "pages": None, "text_bytes": None}


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


async def _persist_upload_file(
    uf: UploadFile,
    *,
    target_dir: Path,
) -> tuple[Path | None, str | None, int]:
    filename = Path(str(uf.filename or "upload.bin")).name or "upload.bin"
    temp_name = f".upload_{datetime.utcnow().strftime('%Y%m%dT%H%M%S%f')}_{filename}"
    temp_path = target_dir / temp_name
    digest = hashlib.sha256()
    total_bytes = 0
    try:
        await uf.seek(0)
    except Exception:
        pass
    with temp_path.open("wb") as fh:
        while True:
            chunk = await uf.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            total_bytes += len(chunk)
            fh.write(chunk)
    try:
        await uf.seek(0)
    except Exception:
        pass
    if total_bytes <= 0:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return None, None, 0
    digest_hex = digest.hexdigest()
    out_path = target_dir / f"{digest_hex[:8]}_{filename}"
    if out_path.exists():
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
    else:
        temp_path.replace(out_path)
    return out_path, digest_hex, total_bytes


def _meta_to_text(parsed_type: str | None, parsed_meta: Any) -> str:
    if parsed_type == "cad" and isinstance(parsed_meta, dict):
        layers = parsed_meta.get("layers_count")
        entities = parsed_meta.get("entities_count")
        inserts = parsed_meta.get("insert_blocks") or {}
        topo = parsed_meta.get("topology") if isinstance(parsed_meta.get("topology"), dict) else {}
        top_blocks = []
        if isinstance(inserts, dict):
            for k, v in sorted(inserts.items(), key=lambda x: x[1], reverse=True)[:8]:
                top_blocks.append(f"{k}:{v}")
        topo_lines = []
        if topo:
            topo_lines.append(f"拓扑节点: {topo.get('nodes_count')}")
            topo_lines.append(f"拓扑边: {topo.get('edges_count')}")
            topo_lines.append(f"连通分量: {topo.get('components_count')}")
            topo_lines.append(f"端点: {topo.get('endpoint_count')}")
            topo_lines.append(f"主干长度: {topo.get('trunk_length')}")
            topo_lines.append(f"建议流水段: {topo.get('suggested_flow_segments')}")
            if topo.get("topology_confidence"):
                topo_lines.append(f"拓扑置信度: {topo.get('topology_confidence')}")
        topo_text = ("\n" + "\n".join(topo_lines)) if topo_lines else ""
        return (
            f"图纸类型: CAD(DXF ASCII)\n"
            f"图层数量: {layers}\n"
            f"实体数量: {entities}\n"
            f"块引用: {'; '.join(top_blocks)}"
            f"{topo_text}"
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


def _normalize_source_hint(source_hint: str | None) -> str:
    raw = str(source_hint or "").strip().lower()
    if not raw:
        return ""
    aliases = {
        "tender": "tender_qa",
        "qa": "tender_qa",
        "answer": "tender_qa",
        "答疑": "tender_qa",
        "招标": "tender_qa",
        "boq": "boq",
        "quantity": "boq",
        "drawing": "drawing_standard",
        "cad": "drawing_standard",
        "standard": "drawing_standard",
        "图纸": "drawing_standard",
        "标准": "drawing_standard",
        "photo": "site_photo",
        "site_photo": "site_photo",
        "现场照片": "site_photo",
    }
    return aliases.get(raw, raw)


def _normalize_library_scope(library_scope: str | None, source_hint: str | None = None) -> str:
    raw = str(library_scope or "").strip().lower()
    if not raw:
        raw = _normalize_source_hint(source_hint)
    aliases = {
        "case": CASE_LIBRARY_SCOPE,
        "case_library": CASE_LIBRARY_SCOPE,
        "template_library": CASE_LIBRARY_SCOPE,
        "benchmark": CASE_LIBRARY_SCOPE,
        "样板库": CASE_LIBRARY_SCOPE,
        "案例库": CASE_LIBRARY_SCOPE,
        "image": IMAGE_LIBRARY_SCOPE,
        "image_library": IMAGE_LIBRARY_SCOPE,
        "图片库": IMAGE_LIBRARY_SCOPE,
        "图库": IMAGE_LIBRARY_SCOPE,
    }
    return aliases.get(raw, raw)


def _normalize_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on", "启用", "可用"}:
        return True
    if text in {"0", "false", "no", "n", "off", "禁用", "不可用"}:
        return False
    return bool(default)


def _classify_tags(filename: str | None, ext: str, parsed_type: str | None, source_hint: str | None = None) -> list[str]:
    name = (filename or "").lower()
    tags = []
    hint = _normalize_source_hint(source_hint)
    is_site_photo = hint == "site_photo"

    if hint == "tender_qa":
        tags.extend(["tender", "qa"])
    elif hint == "boq":
        tags.append("boq")
    elif hint == "drawing_standard":
        # Keep file-name/extension heuristics for precise split between drawing vs standard.
        # Do not force both tags on every file in this mixed upload group.
        pass
    elif hint == "site_photo":
        tags.append("site_photo")

    if any(k in name for k in ("logo", "标志", "标识", "徽标")):
        tags.append("logo")
    if (not is_site_photo) and any(k in name for k in ("图", "图纸", "施工图", "平面", "剖面", "大样", "节点", "cad", "dwg", "dxf")):
        tags.append("drawing")
    if any(k in name for k in ("清单", "工程量清单", "boq")):
        tags.append("boq")
    if any(k in name for k in ("招标", "招標", "tender")):
        tags.append("tender")
    if any(k in name for k in ("企业标准", "工法", "作业指导", "标准化", "技术标准", "标准图集", "管理标准")):
        tags.append("standard")
    if (not is_site_photo) and (ext in {"dxf", "dwg"} or parsed_type in {"cad", "dwg"}):
        if "drawing" not in tags:
            tags.append("drawing")
    if (not is_site_photo) and ext in {"png", "jpg", "jpeg"} and "drawing" not in tags:
        # 纯图片无法判断用途，默认打上 drawing，便于后续人工筛选
        tags.append("drawing")
    dedup: list[str] = []
    seen: set[str] = set()
    for t in tags:
        tt = str(t).strip()
        if not tt or tt in seen:
            continue
        seen.add(tt)
        dedup.append(tt)
    return dedup


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

async def _handle_upload(
    files: List[UploadFile],
    project_id: str | None = None,
    source_hint: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    library_scope: str | None = None,
    project_type: str | None = None,
    title: str | None = None,
    tags: str | None = None,
    chapter_scope: str | None = None,
    process_scope: str | None = None,
    summary: str | None = None,
    style_profile: str | None = None,
    caption: str | None = None,
    description: str | None = None,
    usable: bool | str | None = True,
):
    if not files:
        raise HTTPException(status_code=400, detail="no files uploaded")

    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    ws_paths = workspace_paths(workspace["workspace_dir"])
    day = datetime.utcnow().strftime("%Y%m%d")
    target_dir = ws_paths["uploads"] / day
    target_dir.mkdir(parents=True, exist_ok=True)
    extract_dir = ws_paths["extracts"]
    preview_dir = ws_paths["previews"]
    audit_file = ws_paths["ingest_audit"]
    extract_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    audit_file.parent.mkdir(parents=True, exist_ok=True)

    records = []
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    normalized_hint = _normalize_source_hint(source_hint)
    normalized_library_scope = _normalize_library_scope(library_scope, normalized_hint)
    normalized_project_type = normalize_project_type(project_type)
    normalized_title = str(title or "").strip()[:240] or None
    normalized_tags = normalize_text_list(tags)
    normalized_chapter_scope = normalize_text_list(chapter_scope)
    normalized_process_scope = normalize_text_list(process_scope)
    normalized_summary = str(summary or "").strip()[:1000]
    normalized_style_profile = str(style_profile or "").strip()[:1000]
    normalized_caption = str(caption or "").strip()[:500]
    normalized_description = str(description or "").strip()[:1000]
    normalized_usable = _normalize_bool(usable, default=True)
    if normalized_library_scope in {CASE_LIBRARY_SCOPE, IMAGE_LIBRARY_SCOPE} and not normalized_project_type:
        if normalized_library_scope == IMAGE_LIBRARY_SCOPE:
            raise HTTPException(status_code=400, detail="image library upload requires valid project_type")
        raise HTTPException(status_code=400, detail="case library upload requires valid project_type")
    for uf in files:
        ext = _ext(uf.filename or "")
        if normalized_library_scope == IMAGE_LIBRARY_SCOPE and ext not in {"png", "jpg", "jpeg", "webp", "gif"}:
            raise HTTPException(status_code=400, detail="image library upload requires image files")

        out_path, digest, total_bytes = await _persist_upload_file(uf, target_dir=target_dir)
        if not out_path or not digest or total_bytes <= 0:
            continue

        parsed = _extract_text_path(ext, out_path)
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
            preview_out = preview_dir / preview_name
            if ext in {"png", "jpg", "jpeg"}:
                preview_path = _make_preview_image(out_path, preview_out)
            elif ext == "pdf":
                preview_path = _make_preview_pdf_first_page(out_path, preview_out, scale=2.0)
        except Exception:
            preview_path = None

        extract_path = None
        if parsed.get("extract_text") is not None:
            extract_path = extract_dir / f"{digest[:8]}.txt"
            extract_path.write_text(parsed["extract_text"], encoding="utf-8")
            parsed.pop("extract_text", None)

        rec = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "module": "ingest",
            "project_id": pid,
            "workspace_dir": workspace["workspace_dir"],
            "filename": uf.filename,
            "saved_as": str(out_path),
            "bytes": int(total_bytes),
            "sha256": digest,
            "extract_saved_as": str(extract_path) if extract_path else None,
            "preview_saved_as": preview_path,
            **parsed,
            "parsed_type": parsed_type,
            "parsed_meta": parsed_meta,
            "source_hint": normalized_hint or None,
            "project_type": normalized_project_type or None,
            "library_scope": normalized_library_scope or None,
            "library_title": normalized_title,
            "library_tags": normalized_tags,
            "chapter_scope": normalized_chapter_scope,
            "process_scope": normalized_process_scope,
            "library_summary": normalized_summary,
            "library_style_profile": normalized_style_profile,
            "library_caption": normalized_caption,
            "library_description": normalized_description,
            "enabled": normalized_usable,
            "usable": normalized_usable,
            "tags": _classify_tags(uf.filename, ext, parsed_type, normalized_hint),
        }
        records.append(rec)
        with audit_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if not records:
        raise HTTPException(status_code=400, detail="all files are empty")
    return {"saved": records}


@router.get("/ping")
async def ping():
    return {"module": "ingest", "status": "ok"}


@router.post("/upload")
async def upload(
    files: List[UploadFile] = File(...),
    project_id: str | None = None,
    source_hint: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    library_scope: str | None = None,
    project_type: str | None = None,
    title: str | None = None,
    tags: str | None = None,
    chapter_scope: str | None = None,
    process_scope: str | None = None,
    summary: str | None = None,
    style_profile: str | None = None,
    caption: str | None = None,
    description: str | None = None,
    usable: bool | str | None = True,
):
    return await _handle_upload(
        files,
        project_id=project_id,
        source_hint=source_hint,
        session_id=session_id,
        workspace_dir=workspace_dir,
        library_scope=library_scope,
        project_type=project_type,
        title=title,
        tags=tags,
        chapter_scope=chapter_scope,
        process_scope=process_scope,
        summary=summary,
        style_profile=style_profile,
        caption=caption,
        description=description,
        usable=usable,
    )


@router.post("/ingest")
async def ingest(
    files: List[UploadFile] = File(...),
    project_id: str | None = None,
    source_hint: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    library_scope: str | None = None,
    project_type: str | None = None,
    title: str | None = None,
    tags: str | None = None,
    chapter_scope: str | None = None,
    process_scope: str | None = None,
    summary: str | None = None,
    style_profile: str | None = None,
    caption: str | None = None,
    description: str | None = None,
    usable: bool | str | None = True,
):
    return await _handle_upload(
        files,
        project_id=project_id,
        source_hint=source_hint,
        session_id=session_id,
        workspace_dir=workspace_dir,
        library_scope=library_scope,
        project_type=project_type,
        title=title,
        tags=tags,
        chapter_scope=chapter_scope,
        process_scope=process_scope,
        summary=summary,
        style_profile=style_profile,
        caption=caption,
        description=description,
        usable=usable,
    )
