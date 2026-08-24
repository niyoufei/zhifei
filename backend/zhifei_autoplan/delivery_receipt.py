from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class DeliveryReceiptError(RuntimeError):
    """Raised when final files cannot be sealed as a coherent delivery set."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_digest(payload: dict[str, Any]) -> str:
    material = dict(payload)
    for key in ("created_at", "decision_digest", "receipt"):
        material.pop(key, None)
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.chmod(0o600)
        os.replace(temp_path, path)
        path.chmod(0o600)
    finally:
        temp_path.unlink(missing_ok=True)


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise DeliveryReceiptError(f"{label}不存在：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DeliveryReceiptError(f"{label}无法读取：{exc}") from exc
    if not isinstance(payload, dict):
        raise DeliveryReceiptError(f"{label}不是 JSON 对象")
    return payload


def _artifact(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise DeliveryReceiptError(f"交付制品不存在或为空：{path}")
    return {
        "path": str(path),
        "size": path.stat().st_size,
        "sha256": _sha256_file(path),
    }


def build_delivery_receipt(
    *,
    job_id: str,
    source_docx: Iterable[str | Path],
    professional_docx: Iterable[str | Path],
    professional_receipts: Iterable[str | Path],
    receipt_path: str | Path | None = None,
) -> dict[str, Any]:
    """Seal the final Word set and every quality receipt into one chain."""

    sources = [Path(value) for value in source_docx]
    outputs = [Path(value) for value in professional_docx]
    render_receipts = [Path(value) for value in professional_receipts]
    if not sources or len(sources) != len(outputs) or len(outputs) != len(render_receipts):
        raise DeliveryReceiptError("中间 Word、专业 Word 与渲染凭证数量不一致")

    rows: list[dict[str, Any]] = []
    for index, (source, output, render_receipt_path) in enumerate(
        zip(sources, outputs, render_receipts), start=1
    ):
        if source.resolve() == output.resolve():
            raise DeliveryReceiptError(f"方案 v{index} 未生成独立专业 Word")
        source_artifact = _artifact(source)
        output_artifact = _artifact(output)
        render_artifact = _artifact(render_receipt_path)
        render_receipt = _read_json(render_receipt_path, label=f"方案 v{index} 渲染凭证")
        if str(render_receipt.get("job_id") or "") != str(job_id):
            raise DeliveryReceiptError(f"方案 v{index} 渲染凭证 job_id 不匹配")
        if int(render_receipt.get("variant") or 0) != index:
            raise DeliveryReceiptError(f"方案 v{index} 渲染凭证序号不匹配")
        if str(render_receipt.get("professional_docx_sha256") or "") != output_artifact["sha256"]:
            raise DeliveryReceiptError(f"方案 v{index} 专业 Word 哈希与渲染凭证不匹配")

        quality_gate = render_receipt.get("quality_gate")
        required_gates = (
            "original_preserved",
            "titles_preserved",
            "evidence_not_reduced",
            "tender_style_fields_preserved",
            "export_succeeded",
            "structural_quality_passed",
            "visual_page_quality_passed",
            "no_blank_pages",
            "no_orphan_headings",
        )
        if not isinstance(quality_gate, dict) or not all(quality_gate.get(key) is True for key in required_gates):
            raise DeliveryReceiptError(f"方案 v{index} 专业 Word 质量门未全部通过")

        structural_path = Path(str((render_receipt.get("structural_quality") or {}).get("receipt") or ""))
        visual_path = Path(str((render_receipt.get("visual_quality") or {}).get("receipt") or ""))
        structural_artifact = _artifact(structural_path)
        visual_artifact = _artifact(visual_path)
        structural_receipt = _read_json(structural_path, label=f"方案 v{index} 结构凭证")
        visual_receipt = _read_json(visual_path, label=f"方案 v{index} 视觉凭证")
        if str(structural_receipt.get("status") or "").lower() != "pass":
            raise DeliveryReceiptError(f"方案 v{index} 结构门未通过")
        if str(structural_receipt.get("docx_sha256") or "") != output_artifact["sha256"]:
            raise DeliveryReceiptError(f"方案 v{index} 结构凭证未绑定最终 Word")
        if str(visual_receipt.get("status") or "").lower() != "pass":
            raise DeliveryReceiptError(f"方案 v{index} 视觉门未通过")
        visual_docx_sha256 = str(visual_receipt.get("docx_sha256") or "")
        if visual_docx_sha256 and visual_docx_sha256 != output_artifact["sha256"]:
            raise DeliveryReceiptError(f"方案 v{index} 视觉凭证未绑定最终 Word")

        figure_manifest_path = output.with_suffix(".figure_manifest.json")
        figure_artifact = _artifact(figure_manifest_path)
        figure_manifest = _read_json(figure_manifest_path, label=f"方案 v{index} 图表凭证")
        if figure_manifest.get("delivery_allowed") is not True:
            raise DeliveryReceiptError(f"方案 v{index} 图表交付门未通过")

        rows.append(
            {
                "variant": index,
                "source_docx": source_artifact,
                "professional_docx": output_artifact,
                "professional_render_receipt": render_artifact,
                "structural_quality_receipt": structural_artifact,
                "visual_quality_receipt": visual_artifact,
                "figure_manifest": figure_artifact,
                "quality_gate": {key: True for key in required_gates},
            }
        )

    target = Path(receipt_path) if receipt_path else outputs[0].parent / f"delivery_receipt_{job_id}.json"
    receipt = {
        "schema": "zhifei.delivery_receipt.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "job_id": str(job_id),
        "delivery_profile": "sonnet5_professional_word",
        "variant_count": len(rows),
        "variants": rows,
    }
    receipt["decision_digest"] = _canonical_digest(receipt)
    _atomic_write_json(target, receipt)
    receipt["receipt"] = str(target)
    return receipt
