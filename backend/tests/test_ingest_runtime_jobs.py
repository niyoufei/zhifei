from __future__ import annotations

import asyncio
import hashlib
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path
from typing import Any

import pytest

from backend.app.routers import ingest as ingest_router
from backend.zhifei_autoplan.ocr_runtime import OcrResult


class _Upload:
    def __init__(self, data: bytes, filename: str) -> None:
        self._data = data
        self._offset = 0
        self.filename = filename

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._data):
            return b""
        if size < 0:
            size = len(self._data) - self._offset
        end = min(len(self._data), self._offset + size)
        chunk = self._data[self._offset:end]
        self._offset = end
        return chunk

    async def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._offset = offset
        elif whence == 2:
            self._offset = len(self._data) + offset
        return self._offset


def _isolate_workspace(monkeypatch, tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(
        ingest_router,
        "_resolve_workspace_context",
        lambda session_id=None, workspace_dir=None: {
            "session_id": "test",
            "workspace_dir": str(workspace),
        },
    )
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")

    async def _no_ocr(
        path: Path,
        ext: str,
        text: str | None,
        **_kwargs: Any,
    ) -> None:
        return None

    monkeypatch.setattr(ingest_router, "_try_ocr", _no_ocr)
    return workspace


def test_full_sha_cache_skips_second_parse(monkeypatch, tmp_path: Path) -> None:
    _isolate_workspace(monkeypatch, tmp_path)
    calls = 0
    original = ingest_router._extract_text_path

    def _parse(ext: str, path: Path) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return original(ext, path)

    monkeypatch.setattr(ingest_router, "_extract_text_path", _parse)
    first = asyncio.run(ingest_router._handle_upload([_Upload(b"cached text", "a.txt")]))
    second = asyncio.run(ingest_router._handle_upload([_Upload(b"cached text", "b.txt")]))

    assert calls == 1
    assert first["cache_hits"] == 0
    assert second["cache_hits"] == 1
    assert second["saved"][0]["file_id"] == first["saved"][0]["file_id"]


def test_parse_cache_spills_extracted_text_to_validated_sidecar(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"source").hexdigest()
    extracted_text = "有效正文" * 100_000
    parsed = {
        "base": {
            "doc_type": "txt",
            "pages": 1,
            "text_bytes": len(extracted_text.encode("utf-8")),
            "extract_text": extracted_text,
        },
        "parsed_type": None,
        "parsed_meta": None,
    }

    ingest_router._save_parse_cache(digest, parsed)

    metadata_path = ingest_router._parse_cache_path(digest)
    text_path = ingest_router._parse_cache_text_path(digest)
    metadata = metadata_path.read_text(encoding="utf-8")
    assert extracted_text not in metadata
    assert text_path.read_text(encoding="utf-8") == extracted_text
    assert ingest_router._load_parse_cache(digest) == parsed

    metadata_without_sha = ingest_router.json.loads(metadata)
    metadata_without_sha["extract_text_sidecar"].pop("sha256")
    metadata_path.write_text(
        ingest_router.json.dumps(metadata_without_sha, ensure_ascii=False),
        encoding="utf-8",
    )
    assert ingest_router._load_parse_cache(digest) is None

    ingest_router._save_parse_cache(digest, parsed)
    text_path.write_text(extracted_text[:-1], encoding="utf-8")
    assert ingest_router._load_parse_cache(digest) is None


def test_parse_cache_rejects_same_length_sidecar_content_tamper(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"tamper-source").hexdigest()
    extracted_text = "有效正文" * 100_000
    parsed = {
        "base": {"doc_type": "txt", "extract_text": extracted_text},
        "parsed_type": None,
        "parsed_meta": None,
    }
    ingest_router._save_parse_cache(digest, parsed)
    text_path = ingest_router._parse_cache_text_path(digest)
    original_bytes = text_path.read_bytes()

    text_path.write_text("无" + extracted_text[1:], encoding="utf-8")

    assert text_path.stat().st_size == len(original_bytes)
    assert ingest_router._load_parse_cache(digest) is None


def test_parse_cache_keeps_legacy_inline_text_compatible(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"legacy-source").hexdigest()
    path = ingest_router._parse_cache_path(digest)
    path.parent.mkdir(parents=True)
    parsed = {
        "base": {"doc_type": "txt", "extract_text": "旧缓存正文"},
        "parsed_type": None,
        "parsed_meta": None,
    }
    path.write_text(
        ingest_router.json.dumps(
            {
                "parser_version": ingest_router.PARSER_VERSION,
                "ocr_policy": ingest_router.OCR_POLICY_ORDINARY,
                "sha256": digest,
                "parsed": parsed,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert ingest_router._load_parse_cache(digest) == parsed


def test_parse_cache_does_not_reuse_runtime_v3_ocr_cache(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"drawing-cache-source").hexdigest()
    old_version = "2026.08.runtime-v3-page-ocr"
    old_version_digest = hashlib.sha256(old_version.encode("utf-8")).hexdigest()[:12]
    old_path = ingest_router.PARSE_CACHE_DIR / f"{digest}.{old_version_digest}.json"
    old_path.parent.mkdir(parents=True)
    old_path.write_text(
        ingest_router.json.dumps(
            {
                "parser_version": old_version,
                "sha256": digest,
                "parsed": {
                    "base": {
                        "doc_type": "pdf",
                        "pages": 27,
                        "extract_text": "旧版前十页 OCR 结果",
                    },
                    "parsed_type": None,
                    "parsed_meta": None,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert ingest_router.PARSER_VERSION != old_version
    assert ingest_router._parse_cache_path(digest) != old_path
    assert ingest_router._load_parse_cache(digest) is None


def test_same_pdf_ordinary_cache_does_not_pollute_drawing_cache(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"same-pdf-cross-policy").hexdigest()
    ordinary = {
        "base": {
            "doc_type": "pdf",
            "pages": 27,
            "ocr_pages": 10,
            "ocr_page_mapping": "source_page_prefix",
            "extract_text": "普通资料前十页 OCR",
        },
        "parsed_type": None,
        "parsed_meta": None,
    }
    ingest_router._save_parse_cache(digest, ordinary, source_hint="tender_qa")

    assert ingest_router._load_parse_cache(digest, source_hint="tender") == ordinary
    assert ingest_router._parse_cache_path(
        digest,
        "tender_qa",
    ) != ingest_router._parse_cache_path(digest, "drawing_standard")
    assert ingest_router._load_parse_cache(digest, source_hint="drawing") is None


def test_drawing_cache_requires_ocr_for_every_declared_page(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"drawing-full-page-cache").hexdigest()
    complete = {
        "base": {
            "doc_type": "pdf",
            "pages": 27,
            "ocr_pages": 27,
            "ocr_page_text_count": 27,
            "ocr_page_mapping": "source_page_all",
            "extract_text": "完整图纸 OCR",
        },
        "parsed_type": None,
        "parsed_meta": None,
    }
    ingest_router._save_parse_cache(digest, complete, source_hint="drawing")
    assert ingest_router._load_parse_cache(digest, source_hint="图纸") == complete

    metadata_path = ingest_router._parse_cache_path(digest, "drawing_standard")
    metadata = ingest_router.json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["parsed"]["base"]["ocr_page_text_count"] = 26
    metadata_path.write_text(
        ingest_router.json.dumps(metadata, ensure_ascii=False),
        encoding="utf-8",
    )
    assert ingest_router._load_parse_cache(digest, source_hint="cad") is None

    incomplete_digest = hashlib.sha256(b"drawing-incomplete-cache").hexdigest()
    incomplete = {
        **complete,
        "base": {
            **complete["base"],
            "ocr_pages": 26,
            "ocr_page_text_count": 26,
        },
    }
    ingest_router._save_parse_cache(
        incomplete_digest,
        incomplete,
        source_hint="drawing_standard",
    )
    assert not ingest_router._parse_cache_path(
        incomplete_digest,
        "drawing_standard",
    ).exists()
    assert ingest_router._load_parse_cache(
        incomplete_digest,
        source_hint="cad",
    ) is None


def test_handle_upload_reparses_same_pdf_when_ocr_policy_changes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _isolate_workspace(monkeypatch, tmp_path)
    parse_calls: list[str] = []
    ocr_policies: list[str] = []

    async def _parse(ext: str, _path: Path, _total_bytes: int) -> dict[str, Any]:
        parse_calls.append(ext)
        return {
            "doc_type": "pdf",
            "pages": 3,
            "text_bytes": 2,
            "extract_text": "\f\f",
        }

    async def _ocr(
        _path: Path,
        _ext: str,
        _text: str | None,
        *,
        source_hint: str | None = None,
        declared_pages: int | None = None,
    ) -> OcrResult:
        policy = ingest_router._ocr_cache_policy(source_hint)
        ocr_policies.append(policy)
        pages = declared_pages if policy == ingest_router.OCR_POLICY_DRAWING else 2
        assert isinstance(pages, int)
        return OcrResult(
            text="\f".join(f"第{index + 1}页" for index in range(pages)),
            pages=pages,
            lang="chi_sim+eng",
            page_texts=tuple(f"第{index + 1}页" for index in range(pages)),
        )

    monkeypatch.setattr(ingest_router, "_extract_text_path_bounded", _parse)
    monkeypatch.setattr(ingest_router, "_try_ocr", _ocr)
    monkeypatch.setattr(
        ingest_router,
        "_run_isolated_process",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=None),
    )
    payload = b"same-pdf-content"

    ordinary = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(payload, "ordinary.pdf")],
            source_hint="tender_qa",
        )
    )
    drawing = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(payload, "drawing.pdf")],
            source_hint="drawing_standard",
        )
    )
    drawing_cached = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(payload, "drawing-again.pdf")],
            source_hint="drawing",
        )
    )

    assert ordinary["cache_hits"] == 0
    assert ordinary["saved"][0]["ocr_pages"] == 2
    assert ordinary["saved"][0]["ocr_page_mapping"] == "source_page_prefix"
    assert drawing["cache_hits"] == 0
    assert drawing["saved"][0]["ocr_pages"] == 3
    assert drawing["saved"][0]["ocr_page_text_count"] == 3
    assert drawing["saved"][0]["ocr_page_mapping"] == "source_page_all"
    assert drawing_cached["cache_hits"] == 1
    assert drawing_cached["saved"][0]["ocr_pages"] == 3
    assert drawing_cached["saved"][0]["ocr_page_mapping"] == "source_page_all"
    assert parse_calls == ["pdf", "pdf"]
    assert ocr_policies == [
        ingest_router.OCR_POLICY_ORDINARY,
        ingest_router.OCR_POLICY_DRAWING,
    ]


def test_parse_cache_keeps_small_extracted_text_inline(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"small-source").hexdigest()
    parsed = {
        "base": {"doc_type": "txt", "extract_text": "短正文"},
        "parsed_type": None,
        "parsed_meta": None,
    }

    ingest_router._save_parse_cache(digest, parsed)

    metadata = ingest_router._parse_cache_path(digest).read_text(encoding="utf-8")
    assert "短正文" in metadata
    assert not ingest_router._parse_cache_text_path(digest).exists()
    assert ingest_router._load_parse_cache(digest) == parsed


def test_pdf_preview_reuses_content_addressed_thumbnail(monkeypatch, tmp_path: Path) -> None:
    workspace = _isolate_workspace(monkeypatch, tmp_path)
    content = b"cached-pdf-content"
    digest = hashlib.sha256(content).hexdigest()
    preview = workspace / "previews" / f"{digest[:8]}_preview.png"
    preview.parent.mkdir(parents=True, exist_ok=True)
    preview.write_bytes(b"existing-preview")
    monkeypatch.setattr(
        ingest_router,
        "_load_parse_cache",
        lambda _digest, **_kwargs: {
            "base": {"doc_type": "pdf", "pages": 1, "extract_text": "有效正文"},
            "parsed_type": None,
            "parsed_meta": None,
        },
    )

    async def _must_not_render(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("cached preview must not invoke PDFium")

    monkeypatch.setattr(ingest_router, "_run_isolated_process", _must_not_render)
    result = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(content, "招标文件.pdf")],
            source_hint="tender_qa",
        )
    )

    saved = result["saved"][0]
    assert saved["preview_saved_as"] == str(preview)
    assert saved["preview_cache_hit"] is True
    assert result["warnings"] == []


def test_pdf_preview_worker_crash_is_a_stable_warning(monkeypatch, tmp_path: Path) -> None:
    _isolate_workspace(monkeypatch, tmp_path)
    monkeypatch.setattr(
        ingest_router,
        "_load_parse_cache",
        lambda _digest, **_kwargs: {
            "base": {"doc_type": "pdf", "pages": 1, "extract_text": "有效正文"},
            "parsed_type": None,
            "parsed_meta": None,
        },
    )

    async def _crash(*_args: Any, **_kwargs: Any) -> Any:
        raise BrokenProcessPool("native preview worker exited")

    monkeypatch.setattr(ingest_router, "_run_isolated_process", _crash)
    result = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(b"uncached-pdf-content", "招标文件.pdf")],
            source_hint="tender_qa",
        )
    )

    assert len(result["saved"]) == 1
    assert result["saved"][0]["preview_saved_as"] is None
    assert result["warnings"][0]["code"] == "PDF_PREVIEW_WORKER_CRASHED"
    assert "正文解析结果已保留" in result["warnings"][0]["message"]


def test_legacy_doc_fails_closed_without_converter(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "supplement.doc"
    source.write_bytes(b"legacy-doc")
    monkeypatch.setattr(ingest_router.shutil, "which", lambda _name: None)

    with pytest.raises(RuntimeError, match="LEGACY_DOC_CONVERTER_UNAVAILABLE"):
        ingest_router._extract_text_path("doc", source)


def test_create_ingest_job_spools_and_dispatches(monkeypatch, tmp_path: Path) -> None:
    job_id = "a" * 32
    dispatched: dict[str, Any] = {}
    monkeypatch.setattr(ingest_router, "INGEST_SPOOL_DIR", tmp_path / "spool")
    monkeypatch.setattr(ingest_router, "create_job", lambda payload: job_id)

    def _submit(current_job_id: str, callback: Any, *args: Any, **kwargs: Any) -> int:
        dispatched.update({"job_id": current_job_id, "callback": callback, "args": args})
        return 1

    monkeypatch.setattr(ingest_router, "submit_local_job", _submit)
    response = asyncio.run(
        ingest_router.create_ingest_job(
            [_Upload(b"one", "一.txt"), _Upload(b"two", "二.txt")],
            project_id="p1",
            source_hint="drawing_standard",
        )
    )

    assert response["job_id"] == job_id
    assert response["files_total"] == 2
    assert len(response["file_ids"]) == 2
    assert dispatched["job_id"] == job_id
    assert dispatched["callback"] is ingest_router._run_ingest_job
    assert len(list((tmp_path / "spool" / job_id).iterdir())) == 2


def test_ingest_worker_persists_file_level_status_elapsed_pages_and_cache(monkeypatch, tmp_path: Path) -> None:
    updates: list[dict[str, Any]] = []

    def _merge(_job_id: str, **fields: Any) -> dict[str, Any]:
        updates.append(fields)
        return fields

    def _process(
        _job_id: str,
        index: int,
        _total: int,
        entry: dict[str, Any],
        _options: dict[str, Any],
        _attempt_id: str,
        _owner_instance_id: str,
    ) -> dict[str, Any]:
        elapsed = round(index / 100, 3)
        return {
            "index": index,
            "filename": entry["filename"],
            "elapsed_seconds": elapsed,
            "accepted": [
                {
                    "filename": entry["filename"],
                    "file_id": entry["file_id"],
                    "pages": index,
                    "elapsed_seconds": elapsed,
                }
            ],
            "rejected": [],
            "warnings": [],
            "cache_hits": 1 if index == 2 else 0,
        }

    monkeypatch.setattr(
        ingest_router,
        "acquire_job_lease",
        lambda _job_id: {
            "attempt_id": "a" * 32,
            "owner_instance_id": "test-worker",
        },
    )
    monkeypatch.setattr(ingest_router, "job_lease_active", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        ingest_router,
        "run_with_job_lease",
        lambda _job_id, *, callback, callback_args=(), callback_kwargs=None, **_kwargs: callback(
            *callback_args,
            **dict(callback_kwargs or {}),
        ),
    )
    monkeypatch.setattr(ingest_router, "merge_job", _merge)
    monkeypatch.setattr(
        ingest_router,
        "transition_job",
        lambda _job_id, **fields: _merge(_job_id, **fields),
    )
    monkeypatch.setattr(ingest_router, "append_runtime_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ingest_router, "get_job", lambda _job_id: {"status": "running"})
    monkeypatch.setattr(ingest_router, "_process_spooled_entry", _process)
    monkeypatch.setattr(ingest_router, "INGEST_SPOOL_DIR", tmp_path / "spool")
    entries = [
        {
            "filename": f"file-{index}.txt",
            "path": str(tmp_path / f"file-{index}.txt"),
            "bytes": 10,
            "sha256": str(index) * 64,
            "file_id": str(index) * 64,
        }
        for index in range(1, 4)
    ]

    ingest_router._run_ingest_job("b" * 32, entries, {}, [])

    file_updates = [
        item["progress"]["files"]
        for item in updates
        if isinstance(item.get("progress"), dict)
        and isinstance(item["progress"].get("files"), dict)
    ]
    final_files = file_updates[-1]
    assert final_files["completed"] == 3
    assert final_files["accepted"] == 3
    assert [item["status"] for item in final_files["items"]] == ["accepted"] * 3
    assert [item["pages"] for item in final_files["items"]] == [1, 2, 3]
    assert final_files["items"][1]["cache_hit"] is True
    assert all(float(item["elapsed_seconds"]) > 0 for item in final_files["items"])
    terminal = next(item for item in reversed(updates) if item.get("status") == "succeeded")
    assert all("elapsed_seconds" in row for row in terminal["result"]["accepted"])


def test_ingest_worker_heartbeats_while_file_is_still_processing(monkeypatch, tmp_path: Path) -> None:
    heartbeats: list[dict[str, Any]] = []
    real_wait = ingest_router.concurrent.futures.wait
    wait_calls = 0

    def _wait(
        futures: Any,
        *,
        timeout: float | None = None,
        return_when: str,
    ) -> tuple[set[Any], set[Any]]:
        nonlocal wait_calls
        wait_calls += 1
        if wait_calls == 1:
            assert timeout == ingest_router.INGEST_HEARTBEAT_SECONDS
            return set(), set(futures)
        return real_wait(futures, timeout=timeout, return_when=return_when)

    def _process(
        _job_id: str,
        index: int,
        _total: int,
        entry: dict[str, Any],
        _options: dict[str, Any],
        _attempt_id: str,
        _owner_instance_id: str,
    ) -> dict[str, Any]:
        return {
            "index": index,
            "filename": entry["filename"],
            "elapsed_seconds": 0.1,
            "accepted": [{"filename": entry["filename"], "file_id": entry["file_id"]}],
            "rejected": [],
            "warnings": [],
            "cache_hits": 0,
        }

    monkeypatch.setattr(ingest_router.concurrent.futures, "wait", _wait)
    monkeypatch.setattr(
        ingest_router,
        "acquire_job_lease",
        lambda _job_id: {
            "attempt_id": "a" * 32,
            "owner_instance_id": "test-worker",
        },
    )
    monkeypatch.setattr(ingest_router, "job_lease_active", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        ingest_router,
        "run_with_job_lease",
        lambda _job_id, *, callback, callback_args=(), callback_kwargs=None, **_kwargs: callback(
            *callback_args,
            **dict(callback_kwargs or {}),
        ),
    )
    monkeypatch.setattr(ingest_router, "merge_job", lambda _job_id, **fields: fields)
    monkeypatch.setattr(ingest_router, "transition_job", lambda _job_id, **fields: fields)
    monkeypatch.setattr(
        ingest_router,
        "heartbeat_job",
        lambda _job_id, **fields: (
            heartbeats.append(fields) or {"status": "running"}
        ),
    )
    monkeypatch.setattr(ingest_router, "append_runtime_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ingest_router, "get_job", lambda _job_id: {"status": "running"})
    monkeypatch.setattr(ingest_router, "_process_spooled_entry", _process)
    monkeypatch.setattr(ingest_router, "INGEST_SPOOL_DIR", tmp_path / "spool")
    entries = [
        {
            "filename": "large.pdf",
            "path": str(tmp_path / "large.pdf"),
            "bytes": 10,
            "sha256": "a" * 64,
            "file_id": "a" * 64,
        }
    ]

    ingest_router._run_ingest_job("c" * 32, entries, {}, [])

    assert len(heartbeats) == 1
    assert heartbeats[0]["activity"] == "1 个文件正在解析"
    assert heartbeats[0]["progress_updates"]["current_file"] == ["large.pdf"]
    assert heartbeats[0]["progress_updates"]["work_state"] == "processing_file"
