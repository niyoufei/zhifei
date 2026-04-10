from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from pypdf import PdfReader

from backend.zhifei_autoplan.project_types import normalize_project_type
from backend.zhifei_autoplan.workspace import maybe_cleanup_expired_workspaces, resolve_workspace_dir, workspace_paths
from backend.zhifei_autoplan.template_library import (
    TEMPLATE_BENCHMARK_TAG,
    TEMPLATE_LIBRARY_SCOPE,
    TEMPLATE_LIBRARY_TAG,
    build_template_chapter_profiles,
    delete_template_library_item,
    infer_template_scene_tags,
    list_template_library_items,
    normalize_template_page_bucket,
    normalize_template_scene_tags,
    summarize_template_learning_digest,
    summarize_template_library,
    template_page_bucket_label,
)

router = APIRouter(prefix="/ingest", tags=["文档解析"])

UPLOAD_DIR = Path("backend/data/uploads")
EXTRACT_DIR = Path("backend/data/extracts")
PREVIEW_DIR = Path("backend/data/previews")
AUDIT_DIR = Path("backend/data/audit")
for d in (UPLOAD_DIR, EXTRACT_DIR, PREVIEW_DIR, AUDIT_DIR):
    d.mkdir(parents=True, exist_ok=True)


class TemplateLibraryDeletePayload(BaseModel):
    record_id: str


def _resolve_workspace_context(
    session_id: str | None = None,
    workspace_dir: str | None = None,
) -> Dict[str, str]:
    resolved = resolve_workspace_dir(session_id=session_id, workspace_dir=workspace_dir)
    maybe_cleanup_expired_workspaces(exclude_workspace=resolved)
    return {
        "session_id": str(session_id or resolved.name).strip() or resolved.name,
        "workspace_dir": str(resolved),
    }


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
        "template_library": "template_library",
        "benchmark": "template_library",
        "benchmark_library": "template_library",
        "template": "template_library",
        "样板库": "template_library",
        "样板": "template_library",
        "案例库": "template_library",
        "优秀案例": "template_library",
    }
    return aliases.get(raw, raw)


def _normalize_library_scope(library_scope: str | None, source_hint: str | None = None) -> str:
    raw = str(library_scope or "").strip().lower()
    if not raw:
        raw = _normalize_source_hint(source_hint)
    aliases = {
        "template_library": TEMPLATE_LIBRARY_SCOPE,
        "benchmark": TEMPLATE_LIBRARY_SCOPE,
        "benchmark_library": TEMPLATE_LIBRARY_SCOPE,
        "template": TEMPLATE_LIBRARY_SCOPE,
        "样板库": TEMPLATE_LIBRARY_SCOPE,
        "样板": TEMPLATE_LIBRARY_SCOPE,
        "案例库": TEMPLATE_LIBRARY_SCOPE,
    }
    return aliases.get(raw, "")


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
    elif hint == "template_library":
        tags.extend([TEMPLATE_LIBRARY_TAG, TEMPLATE_BENCHMARK_TAG])

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
    session_id: str | None = None,
    workspace_dir: str | None = None,
    source_hint: str | None = None,
    project_type: str | None = None,
    library_scope: str | None = None,
    library_note: str | None = None,
    template_page_bucket: str | None = None,
    template_scene_tags: str | None = None,
    template_feedback_score: int | None = None,
    template_feedback_origin: str | None = None,
    source_job_id: str | None = None,
    source_variant: int | None = None,
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
    normalized_project_type = normalize_project_type(project_type)
    normalized_library_scope = _normalize_library_scope(library_scope, normalized_hint)
    normalized_library_note = str(library_note or "").strip()
    normalized_library_note = normalized_library_note[:240] if normalized_library_note else ""
    requested_template_page_bucket = normalize_template_page_bucket(template_page_bucket)
    normalized_scene_tags = normalize_template_scene_tags(template_scene_tags)
    normalized_feedback_origin = str(template_feedback_origin or "").strip().lower()[:48] or None
    try:
        normalized_feedback_score = int(template_feedback_score) if template_feedback_score is not None else 0
    except Exception:
        normalized_feedback_score = 0
    normalized_feedback_score = max(0, min(normalized_feedback_score, 100))
    normalized_source_job_id = str(source_job_id or "").strip()[:64] or None
    try:
        normalized_source_variant = int(source_variant) if source_variant is not None else None
    except Exception:
        normalized_source_variant = None
    if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE and not normalized_project_type:
        raise HTTPException(status_code=400, detail="template library upload requires valid project_type")
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
            preview_out = preview_dir / preview_name
            if ext in {"png", "jpg", "jpeg"}:
                preview_path = _make_preview_image(out_path, preview_out)
            elif ext == "pdf":
                preview_path = _make_preview_pdf_first_page(out_path, preview_out, scale=2.0)
        except Exception:
            preview_path = None

        extract_path = None
        extract_text = str(parsed.get("extract_text") or "").strip()
        if parsed.get("extract_text") is not None:
            extract_path = extract_dir / f"{digest[:8]}.txt"
            extract_path.write_text(parsed["extract_text"], encoding="utf-8")
            parsed.pop("extract_text", None)
        template_chapter_profiles = (
            build_template_chapter_profiles(extract_text)
            if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE and extract_text
            else []
        )
        inferred_scene_tags = (
            infer_template_scene_tags(
                uf.filename,
                normalized_library_note,
                extract_text,
                project_type=normalized_project_type,
            )
            if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE
            else []
        )
        merged_scene_tags = normalize_template_scene_tags(normalized_scene_tags + inferred_scene_tags)

        rec = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "module": "ingest",
            "project_id": pid,
            "session_id": workspace["session_id"],
            "workspace_dir": workspace["workspace_dir"],
            "filename": uf.filename,
            "saved_as": str(out_path),
            "bytes": len(content),
            "sha256": digest,
            "extract_saved_as": str(extract_path) if extract_path else None,
            "preview_saved_as": preview_path,
            **parsed,
            "parsed_type": parsed_type,
            "parsed_meta": parsed_meta,
            "source_hint": normalized_hint or None,
            "project_type": normalized_project_type or None,
            "library_scope": normalized_library_scope or None,
            "library_note": normalized_library_note or None,
            "template_scene_tags": merged_scene_tags if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE else [],
            "template_feedback_score": normalized_feedback_score if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE else 0,
            "template_feedback_origin": normalized_feedback_origin if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE else None,
            "source_job_id": normalized_source_job_id if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE else None,
            "source_variant": normalized_source_variant if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE else None,
            "template_page_bucket": (
                normalize_template_page_bucket(requested_template_page_bucket, page_count=parsed.get("pages"))
                if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE
                else None
            ),
            "template_chapter_profiles": template_chapter_profiles if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE else [],
            "template_chapter_profile_count": (
                len(template_chapter_profiles)
                if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE
                else 0
            ),
            "template_page_bucket_label": (
                template_page_bucket_label(
                    normalize_template_page_bucket(requested_template_page_bucket, page_count=parsed.get("pages"))
                )
                if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE
                else None
            ),
            "tags": _classify_tags(uf.filename, ext, parsed_type, normalized_hint),
        }
        if normalized_library_scope == TEMPLATE_LIBRARY_SCOPE and not str(rec.get("template_page_bucket") or "").strip():
            raise HTTPException(status_code=400, detail="template library upload requires valid template_page_bucket")
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
    session_id: str | None = None,
    workspace_dir: str | None = None,
    source_hint: str | None = None,
    project_type: str | None = None,
    library_scope: str | None = None,
    library_note: str | None = None,
    template_page_bucket: str | None = None,
    template_scene_tags: str | None = None,
    template_feedback_score: int | None = None,
    template_feedback_origin: str | None = None,
    source_job_id: str | None = None,
    source_variant: int | None = None,
):
    return await _handle_upload(
        files,
        project_id=project_id,
        session_id=session_id,
        workspace_dir=workspace_dir,
        source_hint=source_hint,
        project_type=project_type,
        library_scope=library_scope,
        library_note=library_note,
        template_page_bucket=template_page_bucket,
        template_scene_tags=template_scene_tags,
        template_feedback_score=template_feedback_score,
        template_feedback_origin=template_feedback_origin,
        source_job_id=source_job_id,
        source_variant=source_variant,
    )


@router.post("/ingest")
async def ingest(
    files: List[UploadFile] = File(...),
    project_id: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    source_hint: str | None = None,
    project_type: str | None = None,
    library_scope: str | None = None,
    library_note: str | None = None,
    template_page_bucket: str | None = None,
    template_scene_tags: str | None = None,
    template_feedback_score: int | None = None,
    template_feedback_origin: str | None = None,
    source_job_id: str | None = None,
    source_variant: int | None = None,
):
    return await _handle_upload(
        files,
        project_id=project_id,
        session_id=session_id,
        workspace_dir=workspace_dir,
        source_hint=source_hint,
        project_type=project_type,
        library_scope=library_scope,
        library_note=library_note,
        template_page_bucket=template_page_bucket,
        template_scene_tags=template_scene_tags,
        template_feedback_score=template_feedback_score,
        template_feedback_origin=template_feedback_origin,
        source_job_id=source_job_id,
        source_variant=source_variant,
    )


@router.get("/template-library/summary")
async def template_library_summary(
    session_id: str | None = None,
    workspace_dir: str | None = None,
):
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    return {"ok": True, "summary": summarize_template_library(audit_path=workspace_paths(workspace["workspace_dir"])["ingest_audit"])}


@router.get("/template-library/items")
async def template_library_items(
    project_type: str | None = None,
    template_page_bucket: str | None = None,
    template_scene_tags: str | None = None,
    sort_by: str | None = None,
    limit: int = 20,
    session_id: str | None = None,
    workspace_dir: str | None = None,
):
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    return {
        "ok": True,
        "items": list_template_library_items(
            project_type=project_type,
            template_page_bucket=template_page_bucket,
            scene_tags=normalize_template_scene_tags(template_scene_tags),
            sort_by=sort_by,
            limit=max(1, min(int(limit or 20), 60)),
            audit_path=workspace_paths(workspace["workspace_dir"])["ingest_audit"],
        ),
    }


@router.get("/template-library/learning-digest")
async def template_library_learning_digest(
    project_type: str | None = None,
    template_page_bucket: str | None = None,
    template_scene_tags: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
):
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    return {
        "ok": True,
        "digest": summarize_template_learning_digest(
            project_type=project_type,
            template_page_bucket=template_page_bucket,
            scene_tags=normalize_template_scene_tags(template_scene_tags),
            audit_path=workspace_paths(workspace["workspace_dir"])["ingest_audit"],
        ),
    }


@router.post("/template-library/delete")
async def template_library_delete(
    payload: TemplateLibraryDeletePayload,
    session_id: str | None = None,
    workspace_dir: str | None = None,
):
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    try:
        deleted = delete_template_library_item(
            payload.record_id,
            audit_path=workspace_paths(workspace["workspace_dir"])["ingest_audit"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=404, detail="template library item not found") from e
    return {"ok": True, "deleted": deleted}
