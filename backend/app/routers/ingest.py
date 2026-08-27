from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import hmac
import json
import multiprocessing
import os
import shutil
import subprocess
import tempfile
import threading
import time
from concurrent.futures.process import BrokenProcessPool
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pypdf import PdfReader

from backend.zhifei_autoplan.case_library_service import CASE_LIBRARY_SCOPE
from backend.zhifei_autoplan.image_library import IMAGE_LIBRARY_SCOPE, normalize_text_list
from backend.zhifei_autoplan.project_types import normalize_project_type
from backend.zhifei_autoplan.job_store import create_job, get_job, heartbeat_job, merge_job
from backend.zhifei_autoplan.local_job_queue import submit_local_job
from backend.zhifei_autoplan.runtime_events import append_runtime_event

try:
    from backend.zhifei_autoplan.local_adapter_shim import normalize_input as _local_adapter_normalize_input
except Exception:
    _local_adapter_normalize_input = None

router = APIRouter(prefix="/ingest", tags=["文档解析"])

PARSE_CACHE_DIR = Path(
    os.environ.get("ZF_AUTOPLAN_INGEST_CACHE_DIR", "backend/data/autoplan/ingest_cache")
)
INGEST_SPOOL_DIR = Path(
    os.environ.get("ZF_AUTOPLAN_INGEST_SPOOL_DIR", "backend/data/autoplan/ingest_spool")
)
PARSER_VERSION = "2026.08.runtime-v2"
PARSE_CACHE_TEXT_SIDECAR_BYTES = 256 * 1024
FILE_ID_SEARCH_ROOTS = (
    Path("backend/data/uploads"),
    Path("backend/data/workspaces"),
)
MAX_BATCH_FILES = 40
MAX_BATCH_BYTES = 512 * 1024 * 1024
PARSE_TIMEOUT_SECONDS = 180
INGEST_HEARTBEAT_SECONDS = 10
try:
    INGEST_WORKERS = max(1, min(2, int(os.getenv("ZF_AUTOPLAN_INGEST_WORKERS", "2"))))
except (TypeError, ValueError):
    INGEST_WORKERS = 2
_PARSE_EXECUTOR: concurrent.futures.ProcessPoolExecutor | None = None
_PARSE_EXECUTOR_LOCK = threading.Lock()


def _parse_executor() -> concurrent.futures.ProcessPoolExecutor:
    global _PARSE_EXECUTOR
    with _PARSE_EXECUTOR_LOCK:
        if _PARSE_EXECUTOR is None:
            _PARSE_EXECUTOR = concurrent.futures.ProcessPoolExecutor(
                max_workers=INGEST_WORKERS,
                mp_context=multiprocessing.get_context("spawn"),
            )
    return _PARSE_EXECUTOR


def _discard_parse_executor(
    executor: concurrent.futures.ProcessPoolExecutor,
    *,
    terminate: bool = False,
) -> None:
    """Remove an unhealthy native-parser pool without taking down FastAPI."""

    global _PARSE_EXECUTOR
    with _PARSE_EXECUTOR_LOCK:
        if _PARSE_EXECUTOR is executor:
            _PARSE_EXECUTOR = None
    if terminate:
        processes = getattr(executor, "_processes", None)
        if isinstance(processes, dict):
            for process in list(processes.values()):
                try:
                    process.terminate()
                except Exception:
                    pass
    try:
        executor.shutdown(wait=False, cancel_futures=True)
    except Exception:
        pass


async def _run_isolated_process(
    func: Any,
    *args: Any,
    timeout: float = PARSE_TIMEOUT_SECONDS,
) -> Any:
    """Run native/CPU parsing outside the API process and recycle bad pools."""

    executor = _parse_executor()
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(executor, func, *args)
    try:
        return await asyncio.wait_for(future, timeout=timeout)
    except (asyncio.TimeoutError, BrokenProcessPool):
        _discard_parse_executor(executor, terminate=True)
        raise


async def _extract_text_path_bounded(ext: str, path: Path, total_bytes: int) -> Dict[str, Any]:
    if ext in {"pdf", "doc", "docx"} and int(total_bytes) >= 1024 * 1024:
        return await _run_isolated_process(
            _extract_text_path,
            ext,
            path,
            timeout=PARSE_TIMEOUT_SECONDS,
        )
    else:
        future = asyncio.to_thread(_extract_text_path, ext, path)
    return await asyncio.wait_for(future, timeout=PARSE_TIMEOUT_SECONDS)
try:
    MAX_UPLOAD_BYTES = max(1, int(os.getenv("ZHIFEI_MAX_UPLOAD_BYTES", str(100 * 1024 * 1024))))
except (TypeError, ValueError):
    MAX_UPLOAD_BYTES = 100 * 1024 * 1024


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


def _attach_local_adapter_ingest_result(result: Dict[str, Any], project_id: str | None = None) -> Dict[str, Any]:
    if _local_adapter_normalize_input is None or not isinstance(result, dict):
        return result
    try:
        saved = result.get("saved") if isinstance(result.get("saved"), list) else []
        source_files = [
            {
                "filename": rec.get("filename"),
                "sha256": rec.get("sha256"),
                "doc_type": rec.get("doc_type"),
            }
            for rec in saved
            if isinstance(rec, dict)
        ]
        envelope = _local_adapter_normalize_input({"project_id": project_id, "source_files": source_files})
        result["local_adapter"] = {
            "status": "normalized",
            "source_file_count": len(envelope.get("source_files") or []),
            "missing_params": envelope.get("missing_params") or [],
        }
    except Exception as exc:
        result["local_adapter"] = {
            "status": "normalizer_error",
            "issues": [{"code": "LOCAL_ADAPTER_INPUT_NORMALIZE_FAILED", "message": repr(exc)}],
        }
    return result


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
    if ext == "docx":
        from docx import Document

        document = Document(str(path))
        lines = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
        for table in document.tables:
            for row in table.rows:
                values = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
                if values:
                    lines.append(" | ".join(values))
        text = "\n".join(lines)
        return {
            "doc_type": "docx",
            "pages": None,
            "text_bytes": len(text.encode("utf-8")),
            "extract_text": text,
        }
    if ext == "doc":
        office = shutil.which("soffice") or shutil.which("libreoffice")
        if not office:
            raise RuntimeError("LEGACY_DOC_CONVERTER_UNAVAILABLE")
        with tempfile.TemporaryDirectory(prefix="zhifei-doc-convert-") as temp_dir:
            completed = subprocess.run(
                [
                    office,
                    "--headless",
                    "--convert-to",
                    "docx",
                    "--outdir",
                    temp_dir,
                    str(path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
            )
            converted = Path(temp_dir) / f"{path.stem}.docx"
            if completed.returncode != 0 or not converted.exists():
                raise RuntimeError("LEGACY_DOC_CONVERSION_FAILED")
            parsed = _extract_text_path("docx", converted)
            parsed["doc_type"] = "doc"
            parsed["converted_via"] = "libreoffice"
            return parsed
    return {"doc_type": ext or "unknown", "pages": None, "text_bytes": None}


def _parse_cache_path(digest: str) -> Path:
    version_digest = hashlib.sha256(PARSER_VERSION.encode("utf-8")).hexdigest()[:12]
    return PARSE_CACHE_DIR / f"{str(digest)}.{version_digest}.json"


def _parse_cache_text_path(digest: str) -> Path:
    """Return the versioned sidecar used for potentially large extracted text."""

    return _parse_cache_path(digest).with_suffix(".txt")


def _resolve_ingested_files(file_ids: List[str] | None) -> list[tuple[str, Path]]:
    """Resolve full-SHA file IDs to content-verified local upload paths."""

    resolved: list[tuple[str, Path]] = []
    for raw in file_ids or []:
        digest = str(raw or "").strip().lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise HTTPException(status_code=400, detail={"code": "INVALID_FILE_ID"})
        match: Path | None = None
        for root in FILE_ID_SEARCH_ROOTS:
            if not root.exists():
                continue
            for candidate in root.rglob(f"{digest[:8]}_*"):
                if not candidate.is_file():
                    continue
                hasher = hashlib.sha256()
                with candidate.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        hasher.update(chunk)
                if hasher.hexdigest() == digest:
                    match = candidate
                    break
            if match is not None:
                break
        if match is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "FILE_ID_NOT_FOUND", "file_id": digest},
            )
        resolved.append((digest, match))
    return resolved


def resolve_ingested_file_ids(file_ids: List[str] | None) -> list[str]:
    """Resolve full-SHA file IDs to verified local upload paths."""

    return [str(path) for _digest, path in _resolve_ingested_files(file_ids)]


def resolve_ingested_tender_sources(
    file_ids: List[str] | None,
) -> list[dict[str, str | None]]:
    """Resolve Tender sources and reuse only the current validated text cache."""

    sources: list[dict[str, str | None]] = []
    for digest, path in _resolve_ingested_files(file_ids):
        cached = _load_parse_cache(digest)
        base = cached.get("base") if isinstance(cached, dict) else None
        extract_text = base.get("extract_text") if isinstance(base, dict) else None
        sources.append(
            {
                "path": str(path),
                "cached_text": extract_text if isinstance(extract_text, str) else None,
            }
        )
    return sources


def _load_parse_cache(digest: str) -> Dict[str, Any] | None:
    path = _parse_cache_path(digest)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if (
        not isinstance(data, dict)
        or data.get("parser_version") != PARSER_VERSION
        or not isinstance(data.get("sha256"), str)
        or not hmac.compare_digest(data["sha256"].lower(), str(digest).lower())
    ):
        return None
    parsed = data.get("parsed")
    if not isinstance(parsed, dict):
        return None
    result = dict(parsed)
    sidecar = data.get("extract_text_sidecar")
    if sidecar is None:
        # Compatibility with caches written before extracted text was split
        # from JSON metadata.  They remain valid until naturally replaced.
        return result
    if not isinstance(sidecar, dict):
        return None
    text_path = _parse_cache_text_path(digest)
    if str(sidecar.get("filename") or "") != text_path.name:
        return None
    try:
        expected_bytes = int(sidecar["bytes"])
        if expected_bytes < 0 or text_path.stat().st_size != expected_bytes:
            return None
        encoded_text = text_path.read_bytes()
        if len(encoded_text) != expected_bytes:
            return None
        expected_sha256 = sidecar["sha256"]
        if not isinstance(expected_sha256, str) or not hmac.compare_digest(
            hashlib.sha256(encoded_text).hexdigest(),
            expected_sha256.lower(),
        ):
            return None
        extracted_text = encoded_text.decode("utf-8")
    except (KeyError, OSError, UnicodeError, TypeError, ValueError):
        return None
    base = result.get("base")
    if not isinstance(base, dict):
        return None
    hydrated_base = dict(base)
    hydrated_base["extract_text"] = extracted_text
    result["base"] = hydrated_base
    return result


def _save_parse_cache(digest: str, parsed: Dict[str, Any]) -> None:
    PARSE_CACHE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = _parse_cache_path(digest)
    text_path = _parse_cache_text_path(digest)
    temp_suffix = f".{os.getpid()}.{threading.get_ident()}.tmp"
    temp = path.with_suffix(path.suffix + temp_suffix)
    temp_text = text_path.with_suffix(text_path.suffix + temp_suffix)
    parsed_for_disk = dict(parsed)
    base = parsed_for_disk.get("base")
    extracted_text_bytes: bytes | None = None
    if isinstance(base, dict):
        persisted_base = dict(base)
        candidate = persisted_base.pop("extract_text", None)
        if isinstance(candidate, str):
            encoded_candidate = candidate.encode("utf-8")
            if len(encoded_candidate) >= PARSE_CACHE_TEXT_SIDECAR_BYTES:
                extracted_text_bytes = encoded_candidate
            else:
                persisted_base["extract_text"] = candidate
        parsed_for_disk["base"] = persisted_base
    payload = {
        "parser_version": PARSER_VERSION,
        "sha256": str(digest),
        "saved_at": time.time(),
        "parsed": parsed_for_disk,
    }
    try:
        if extracted_text_bytes is not None:
            temp_text.write_bytes(extracted_text_bytes)
            temp_text.replace(text_path)
            try:
                text_path.chmod(0o600)
            except OSError:
                pass
            payload["extract_text_sidecar"] = {
                "filename": text_path.name,
                "bytes": len(extracted_text_bytes),
                "encoding": "utf-8",
                "sha256": hashlib.sha256(extracted_text_bytes).hexdigest(),
            }
        temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temp.replace(path)
        try:
            path.chmod(0o600)
        except OSError:
            pass
    finally:
        temp.unlink(missing_ok=True)
        temp_text.unlink(missing_ok=True)


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
    temp_name = f".upload_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}_{filename}"
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
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_BYTES:
                fh.close()
                temp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail={
                        "code": "UPLOAD_TOO_LARGE",
                        "filename": filename,
                        "max_bytes": MAX_UPLOAD_BYTES,
                    },
                )
            digest.update(chunk)
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
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    target_dir = ws_paths["uploads"] / day
    target_dir.mkdir(parents=True, exist_ok=True)
    extract_dir = ws_paths["extracts"]
    preview_dir = ws_paths["previews"]
    audit_file = ws_paths["ingest_audit"]
    extract_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    audit_file.parent.mkdir(parents=True, exist_ok=True)

    records = []
    rejected: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    cache_hits = 0
    seen_digests: dict[str, Path] = {}
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
            rejected.append({"filename": uf.filename, "code": "EMPTY_FILE"})
            continue

        prior_path = seen_digests.get(digest)
        if prior_path is not None:
            if out_path != prior_path:
                out_path.unlink(missing_ok=True)
            rejected.append(
                {
                    "filename": uf.filename,
                    "code": "DUPLICATE_FILE",
                    "sha256": digest,
                    "duplicate_of": str(prior_path),
                }
            )
            continue
        seen_digests[digest] = out_path

        cached = await asyncio.to_thread(_load_parse_cache, digest)
        cache_hit = isinstance(cached, dict)
        if cache_hit:
            cache_hits += 1
            parsed = dict(cached.get("base") or {})
            parsed_type = cached.get("parsed_type")
            parsed_meta = cached.get("parsed_meta")
        else:
            try:
                parsed = await _extract_text_path_bounded(ext, out_path, total_bytes)
            except Exception as exc:
                rejected.append(
                    {
                        "filename": uf.filename,
                        "code": "FILE_PARSE_TIMEOUT" if isinstance(exc, asyncio.TimeoutError) else "FILE_PARSE_FAILED",
                        "sha256": digest,
                        "file_id": digest,
                        "saved_as": str(out_path),
                        "error_type": type(exc).__name__,
                    }
                )
                continue
            parsed_type = None
            parsed_meta = None
            if parsed.get("extract_text") is None and ext not in {"txt", "md", "pdf", "doc", "docx"}:
                try:
                    def _parse_unified() -> Dict[str, Any]:
                        from modules.parser.parser_unify import UnifiedParser

                        return UnifiedParser(str(out_path)).parse()

                    uret = await asyncio.wait_for(
                        asyncio.to_thread(_parse_unified),
                        timeout=PARSE_TIMEOUT_SECONDS,
                    )
                    parsed_type = uret.get("type")
                    parsed_meta = uret.get("meta")
                    utext = uret.get("text")
                    if isinstance(utext, str) and utext.strip():
                        parsed["extract_text"] = utext
                    else:
                        meta_text = _meta_to_text(parsed_type, parsed_meta)
                        if meta_text.strip():
                            parsed["extract_text"] = meta_text
                except Exception as exc:
                    parsed_meta = {"error_type": type(exc).__name__}

            # OCR is cached with the parser result so repeated 268 MiB imports
            # do not repeat the most expensive extraction path.
            try:
                ocr_text = await _try_ocr(out_path, ext, parsed.get("extract_text"))
                if ocr_text:
                    base = (parsed.get("extract_text") or "").strip()
                    merged = (base + "\n\n" + ocr_text).strip() if base else ocr_text.strip()
                    parsed["extract_text"] = merged
            except Exception:
                pass
            await asyncio.to_thread(
                _save_parse_cache,
                digest,
                {
                    "base": dict(parsed),
                    "parsed_type": parsed_type,
                    "parsed_meta": parsed_meta,
                },
            )

        meaningful_text = str(parsed.get("extract_text") or "").strip()
        if normalized_hint in {"tender_qa", "boq"} and not meaningful_text:
            rejected.append(
                {
                    "filename": uf.filename,
                    "code": "UNPARSED_MANDATORY_FILE",
                    "sha256": digest,
                    "file_id": digest,
                    "saved_as": str(out_path),
                }
            )
            continue

        # Preview (best-effort): reuse a content-addressed thumbnail whenever
        # possible.  PDFium is native code and a malformed page can segfault;
        # keep it in the same disposable process boundary as document parsing.
        preview_path = None
        preview_cache_hit = False
        preview_warning: dict[str, Any] | None = None
        try:
            preview_name = f"{digest[:8]}_preview.png"
            preview_out = preview_dir / preview_name
            if preview_out.is_file() and preview_out.stat().st_size > 0:
                preview_path = str(preview_out)
                preview_cache_hit = True
            elif ext in {"png", "jpg", "jpeg"}:
                preview_path = await asyncio.to_thread(_make_preview_image, out_path, preview_out)
            elif ext == "pdf":
                preview_path = await _run_isolated_process(
                    _make_preview_pdf_first_page,
                    out_path,
                    preview_out,
                    2.0,
                    timeout=PARSE_TIMEOUT_SECONDS,
                )
        except BrokenProcessPool:
            preview_warning = {
                "code": "PDF_PREVIEW_WORKER_CRASHED",
                "message": "PDF 首页预览进程异常退出，正文解析结果已保留。",
                "action": "系统已隔离并回收异常进程；可继续使用正文，或重新生成预览。",
                "filename": str(uf.filename or ""),
            }
            preview_path = None
        except asyncio.TimeoutError:
            preview_warning = {
                "code": "PDF_PREVIEW_TIMEOUT",
                "message": "PDF 首页预览超时，正文解析结果已保留。",
                "action": "可继续使用正文，或稍后重新生成预览。",
                "filename": str(uf.filename or ""),
            }
            preview_path = None
        except Exception:
            preview_warning = {
                "code": "PDF_PREVIEW_UNAVAILABLE",
                "message": "PDF 首页预览生成失败，正文解析结果已保留。",
                "action": "可继续使用正文，或稍后重新生成预览。",
                "filename": str(uf.filename or ""),
            }
            preview_path = None
        if ext == "pdf" and not preview_path and preview_warning is None:
            preview_warning = {
                "code": "PDF_PREVIEW_UNAVAILABLE",
                "message": "PDF 首页预览生成失败，正文解析结果已保留。",
                "action": "可继续使用正文，或稍后重新生成预览。",
                "filename": str(uf.filename or ""),
            }
        if preview_warning is not None:
            warnings.append(preview_warning)

        extract_path = None
        if parsed.get("extract_text") is not None:
            extract_path = extract_dir / f"{digest[:8]}.txt"
            await asyncio.to_thread(extract_path.write_text, parsed["extract_text"], encoding="utf-8")
            parsed.pop("extract_text", None)

        rec = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "module": "ingest",
            "project_id": pid,
            "workspace_dir": workspace["workspace_dir"],
            "filename": uf.filename,
            "saved_as": str(out_path),
            "bytes": int(total_bytes),
            "sha256": digest,
            "file_id": digest,
            "parser_version": PARSER_VERSION,
            "cache_hit": cache_hit,
            "preview_cache_hit": preview_cache_hit,
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
        if rejected and all(item.get("code") == "EMPTY_FILE" for item in rejected):
            raise HTTPException(status_code=400, detail="all files are empty")
        raise HTTPException(
            status_code=422,
            detail={"code": "ALL_FILES_REJECTED", "rejected": rejected},
        )
    if normalized_hint in {"tender_qa", "boq"} and rejected:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "MANDATORY_SOURCE_REJECTED",
                "message": "招标、补疑或工程量清单存在未解析文件，已阻止进入生成。",
                "accepted": records,
                "rejected": rejected,
            },
        )
    if rejected:
        warnings.append(
            {
                "code": "OPTIONAL_SOURCE_DEGRADED",
                "message": f"{len(rejected)} 个可选资料未完成解析。",
            }
        )
    return {
        "saved": records,
        "accepted": records,
        "rejected": rejected,
        "warnings": warnings,
        "cache_hits": cache_hits,
        "parser_version": PARSER_VERSION,
    }


class _SpoolUpload:
    def __init__(self, path: Path, filename: str) -> None:
        self.filename = filename
        self._handle = path.open("rb")

    async def read(self, size: int = -1) -> bytes:
        return self._handle.read(size)

    async def seek(self, offset: int, whence: int = 0) -> int:
        return self._handle.seek(offset, whence)

    async def close(self) -> None:
        self._handle.close()


def _process_spooled_entry(
    job_id: str,
    index: int,
    total: int,
    entry: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    current = get_job(job_id) or {}
    if str(current.get("status") or "").strip().lower() == "cancelled":
        return {"cancelled": True, "index": index}
    filename = str(entry.get("filename") or "upload.bin")
    started = time.monotonic()
    merge_job(
        job_id,
        progress={
            "phase": "ingest",
            "stage": "ingest",
            "work_state": "processing_file",
            "current_file": filename,
        },
    )
    append_runtime_event(
        job_id,
        "ingest_file_started",
        filename=filename,
        file_index=index,
        files_total=total,
    )
    upload = _SpoolUpload(Path(str(entry["path"])), filename)
    try:
        result = asyncio.run(_handle_upload([upload], **options))
        rows = result.get("accepted") if isinstance(result.get("accepted"), list) else result.get("saved") or []
        elapsed_seconds = round(time.monotonic() - started, 3)
        outcome = {
            "index": index,
            "filename": filename,
            "elapsed_seconds": elapsed_seconds,
            "accepted": [
                {**item, "elapsed_seconds": elapsed_seconds}
                for item in rows
                if isinstance(item, dict)
            ],
            "rejected": [
                {**item, "elapsed_seconds": elapsed_seconds}
                for item in (result.get("rejected") or [])
                if isinstance(item, dict)
            ],
            "warnings": [item for item in (result.get("warnings") or []) if isinstance(item, dict)],
            "cache_hits": int(result.get("cache_hits") or 0),
        }
        append_runtime_event(
            job_id,
            "ingest_file_finished",
            filename=filename,
            ok=True,
            cache_hit=bool(result.get("cache_hits")),
            elapsed_seconds=elapsed_seconds,
        )
        for warning in outcome["warnings"]:
            append_runtime_event(
                job_id,
                "ingest_warning",
                filename=filename,
                code=str(warning.get("code") or "INGEST_WARNING"),
                message=str(warning.get("message") or "")[:500],
            )
        return outcome
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {
            "code": "FILE_PARSE_FAILED",
            "message": str(exc.detail),
        }
        rows = detail.get("rejected") if isinstance(detail.get("rejected"), list) else []
        rejected = [item for item in rows if isinstance(item, dict)]
        if not rejected:
            rejected = [{"filename": filename, "code": str(detail.get("code") or "FILE_PARSE_FAILED")}]
        elapsed_seconds = round(time.monotonic() - started, 3)
        rejected = [{**item, "elapsed_seconds": elapsed_seconds} for item in rejected]
        append_runtime_event(
            job_id,
            "ingest_file_finished",
            filename=filename,
            ok=False,
            code=detail.get("code"),
            elapsed_seconds=elapsed_seconds,
        )
        return {
            "index": index,
            "filename": filename,
            "elapsed_seconds": elapsed_seconds,
            "accepted": [],
            "rejected": rejected,
            "warnings": [],
            "cache_hits": 0,
        }
    except Exception as exc:
        elapsed_seconds = round(time.monotonic() - started, 3)
        append_runtime_event(
            job_id,
            "ingest_file_finished",
            filename=filename,
            ok=False,
            error_type=type(exc).__name__,
            elapsed_seconds=elapsed_seconds,
        )
        return {
            "index": index,
            "filename": filename,
            "elapsed_seconds": elapsed_seconds,
            "accepted": [],
            "rejected": [
                {
                    "filename": filename,
                    "code": "FILE_PARSE_FAILED",
                    "error_type": type(exc).__name__,
                    "elapsed_seconds": elapsed_seconds,
                }
            ],
            "warnings": [],
            "cache_hits": 0,
        }
    finally:
        asyncio.run(upload.close())


def _run_ingest_job(
    job_id: str,
    entries: list[dict[str, Any]],
    options: dict[str, Any],
    initial_rejected: list[dict[str, Any]],
) -> None:
    accepted: list[dict[str, Any]] = []
    rejected = list(initial_rejected)
    warnings: list[dict[str, Any]] = []
    cache_hits = 0
    total = len(entries)
    file_items: list[dict[str, Any]] = [
        {
            "index": index,
            "filename": str(entry.get("filename") or "upload.bin"),
            "file_id": entry.get("file_id"),
            "bytes": int(entry.get("bytes") or 0),
            "status": "queued",
            "cache_hit": False,
            "elapsed_seconds": None,
        }
        for index, entry in enumerate(entries, start=1)
    ]
    file_items.extend(
        {
            "index": total + index,
            "filename": str(item.get("filename") or "upload.bin"),
            "status": "rejected",
            "code": str(item.get("code") or "UPLOAD_REJECTED"),
            "cache_hit": False,
            "elapsed_seconds": 0.0,
        }
        for index, item in enumerate(initial_rejected, start=1)
        if isinstance(item, dict)
    )
    mandatory = _normalize_source_hint(options.get("source_hint")) in {"tender_qa", "boq"}
    merge_job(
        job_id,
        status="running",
        progress={
            "phase": "ingest",
            "stage": "ingest",
            "work_state": "processing_file",
            "percent": 0,
            "files": {
                "completed": 0,
                "accepted": 0,
                "rejected": len(rejected),
                "total": total + len(initial_rejected),
                "items": file_items,
            },
        },
    )
    append_runtime_event(job_id, "ingest_started", files_total=total)
    try:
        completed = 0
        max_workers = min(INGEST_WORKERS, max(1, total))
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=f"ingest-{job_id[:8]}",
        ) as executor:
            entry_iter = iter(enumerate(entries, start=1))
            inflight: dict[concurrent.futures.Future, int] = {}
            active_files: dict[int, str] = {}

            def _submit_next() -> bool:
                try:
                    index, entry = next(entry_iter)
                except StopIteration:
                    return False
                filename = str(entry.get("filename") or "upload.bin")
                file_items[index - 1]["status"] = "processing"
                file_items[index - 1]["started_at"] = time.time()
                active_files[index] = filename
                future = executor.submit(
                    _process_spooled_entry,
                    job_id,
                    index,
                    total,
                    entry,
                    options,
                )
                inflight[future] = index
                return True

            for _ in range(max_workers):
                _submit_next()

            while inflight:
                finished, _pending = concurrent.futures.wait(
                    tuple(inflight),
                    timeout=INGEST_HEARTBEAT_SECONDS,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                if not finished:
                    heartbeat_job(
                        job_id,
                        activity=f"{len(active_files)} 个文件正在解析",
                        progress_updates={
                            "phase": "ingest",
                            "stage": "ingest",
                            "work_state": "processing_file",
                            "current_file": list(active_files.values()),
                        },
                    )
                    continue
                for future in finished:
                    index = inflight.pop(future)
                    active_files.pop(index, None)
                    outcome = future.result()
                    item = file_items[index - 1]
                    item["elapsed_seconds"] = outcome.get("elapsed_seconds")
                    item["finished_at"] = time.time()
                    item["cache_hit"] = bool(outcome.get("cache_hits"))
                    if outcome.get("cancelled"):
                        item["status"] = "cancelled"
                    else:
                        accepted_rows = outcome.get("accepted") or []
                        rejected_rows = outcome.get("rejected") or []
                        item["status"] = "accepted" if accepted_rows else "rejected"
                        if accepted_rows:
                            first_accepted = accepted_rows[0]
                            item["pages"] = first_accepted.get("pages")
                            item["file_id"] = first_accepted.get("file_id") or item.get("file_id")
                            item["preview_cache_hit"] = bool(
                                first_accepted.get("preview_cache_hit")
                            )
                        if rejected_rows:
                            item["code"] = str(rejected_rows[0].get("code") or "FILE_PARSE_FAILED")
                    accepted.extend(outcome.get("accepted") or [])
                    rejected.extend(outcome.get("rejected") or [])
                    warnings.extend(outcome.get("warnings") or [])
                    cache_hits += int(outcome.get("cache_hits") or 0)
                    completed += 1
                    _submit_next()
                    merge_job(
                        job_id,
                        progress={
                            "percent": int((completed / max(1, total)) * 95),
                            "current_file": list(active_files.values()),
                            "files": {
                                "completed": completed,
                                "accepted": len(accepted),
                                "rejected": len(rejected),
                                "total": total + len(initial_rejected),
                                "items": file_items,
                            },
                            "cache_hits": cache_hits,
                        },
                    )
        if str((get_job(job_id) or {}).get("status") or "").strip().lower() == "cancelled":
            append_runtime_event(job_id, "ingest_cancelled", completed=completed)
            return

        result = {
            "accepted": accepted,
            "saved": accepted,
            "rejected": rejected,
            "warnings": warnings,
            "cache_hits": cache_hits,
            "parser_version": PARSER_VERSION,
        }
        if (mandatory and rejected) or not accepted:
            error = {
                "code": "MANDATORY_SOURCE_REJECTED" if mandatory else "ALL_FILES_REJECTED",
                "message": "强制资料存在未解析文件，已阻止进入生成。" if mandatory else "所有文件均未完成解析。",
                "action": "修复或转换失败文件后重新导入。",
            }
            merge_job(
                job_id,
                status="failed",
                error=error,
                result=result,
                progress={"work_state": "idle", "current_file": None, "detail": error["message"]},
            )
            append_runtime_event(job_id, "ingest_failed", code=error["code"], rejected=len(rejected))
            return
        if rejected:
            warnings.append(
                {
                    "code": "OPTIONAL_SOURCE_DEGRADED",
                    "message": f"{len(rejected)} 个可选资料未完成解析。",
                }
            )
            result["warnings"] = warnings
        merge_job(
            job_id,
            status="succeeded",
            result=result,
            error=None,
            progress={
                "percent": 100,
                "phase": "ingest",
                "stage": "done",
                "work_state": "idle",
                "current_file": None,
                "detail": "资料导入完成。",
                "warnings": warnings,
            },
        )
        append_runtime_event(
            job_id,
            "ingest_succeeded",
            accepted=len(accepted),
            rejected=len(rejected),
            cache_hits=cache_hits,
        )
    finally:
        spool_dir = INGEST_SPOOL_DIR / job_id
        if spool_dir.exists():
            shutil.rmtree(spool_dir, ignore_errors=True)


@router.post("/jobs")
async def create_ingest_job(
    files: List[UploadFile] = File(...),
    project_id: str | None = None,
    source_hint: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
):
    if not files:
        raise HTTPException(status_code=400, detail={"code": "NO_FILES"})
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=413,
            detail={"code": "TOO_MANY_FILES", "max_files": MAX_BATCH_FILES},
        )
    job_id = create_job(
        {
            "action": "ingest",
            "project_id": project_id,
            "source_hint": source_hint,
            "file_count": len(files),
            "filenames": [Path(str(item.filename or "upload.bin")).name for item in files],
        }
    )
    spool_dir = INGEST_SPOOL_DIR / job_id
    spool_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    entries: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    total_bytes = 0
    seen: dict[str, str] = {}
    try:
        for index, upload in enumerate(files):
            filename = Path(str(upload.filename or "upload.bin")).name or "upload.bin"
            target = spool_dir / f"{index:03d}_{filename}"
            digest = hashlib.sha256()
            size = 0
            await upload.seek(0)
            with target.open("wb") as handle:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    total_bytes += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail={"code": "UPLOAD_TOO_LARGE", "filename": filename, "max_bytes": MAX_UPLOAD_BYTES},
                        )
                    if total_bytes > MAX_BATCH_BYTES:
                        raise HTTPException(
                            status_code=413,
                            detail={"code": "BATCH_TOO_LARGE", "max_bytes": MAX_BATCH_BYTES},
                        )
                    digest.update(chunk)
                    handle.write(chunk)
            if size <= 0:
                target.unlink(missing_ok=True)
                rejected.append({"filename": filename, "code": "EMPTY_FILE"})
                continue
            sha256 = digest.hexdigest()
            if sha256 in seen:
                target.unlink(missing_ok=True)
                rejected.append(
                    {
                        "filename": filename,
                        "code": "DUPLICATE_FILE",
                        "sha256": sha256,
                        "duplicate_of": seen[sha256],
                    }
                )
                continue
            seen[sha256] = filename
            entries.append(
                {
                    "filename": filename,
                    "path": str(target),
                    "bytes": size,
                    "sha256": sha256,
                    "file_id": sha256,
                }
            )
    except Exception:
        merge_job(job_id, status="failed", error={"code": "INGEST_UPLOAD_REJECTED"})
        shutil.rmtree(spool_dir, ignore_errors=True)
        raise

    if not entries:
        merge_job(
            job_id,
            status="failed",
            error={"code": "ALL_FILES_REJECTED", "message": "所有上传文件为空或重复。"},
            result={"accepted": [], "rejected": rejected},
        )
        shutil.rmtree(spool_dir, ignore_errors=True)
        raise HTTPException(
            status_code=422,
            detail={"code": "ALL_FILES_REJECTED", "job_id": job_id, "rejected": rejected},
        )

    options = {
        "project_id": project_id,
        "source_hint": source_hint,
        "session_id": session_id,
        "workspace_dir": workspace_dir,
    }
    queue_depth = submit_local_job(job_id, _run_ingest_job, job_id, entries, options, rejected)
    return {
        "ok": True,
        "job_id": job_id,
        "status": "queued",
        "queue_depth": queue_depth,
        "files_total": len(entries) + len(rejected),
        "bytes_total": total_bytes,
        "file_ids": [entry["file_id"] for entry in entries],
        "rejected": rejected,
    }


@router.get("/jobs/{job_id}")
async def get_ingest_job(job_id: str):
    job = get_job(job_id)
    if not job or str((job.get("payload") or {}).get("action") or "") != "ingest":
        raise HTTPException(status_code=404, detail={"code": "INGEST_JOB_NOT_FOUND"})
    return {
        "ok": True,
        "job": {
            "job_id": job.get("job_id"),
            "status": job.get("status"),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
            "progress": job.get("progress") or {},
            "result": job.get("result") or {},
            "error": job.get("error"),
        },
    }


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
    result = await _handle_upload(
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
    return _attach_local_adapter_ingest_result(result, project_id=project_id)


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
    result = await _handle_upload(
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
    return _attach_local_adapter_ingest_result(result, project_id=project_id)
