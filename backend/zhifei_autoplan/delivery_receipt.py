from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DeliveryReceiptError(RuntimeError):
    """Raised when final files cannot be sealed as a coherent delivery set."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_delivery_receipt_digest(payload: dict[str, Any]) -> str:
    """Return the canonical decision digest for a delivery receipt.

    Volatile persistence fields are deliberately excluded so a stored receipt
    can be verified independently of its write time and filesystem location.
    """

    material = dict(payload)
    for key in ("created_at", "decision_digest", "receipt"):
        material.pop(key, None)
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
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


def _artifact_paths(
    values: Iterable[str | Path | None],
    *,
    label: str,
    count: int,
    optional: bool = False,
) -> list[Path | None]:
    if isinstance(values, (str, bytes, Path)) or values is None:
        raise DeliveryReceiptError(f"{label}必须按方案提供等长路径列表")
    try:
        raw_values = list(values)
    except TypeError as exc:
        raise DeliveryReceiptError(f"{label}必须按方案提供等长路径列表") from exc
    if len(raw_values) != count:
        raise DeliveryReceiptError(f"{label}数量与方案数量不一致")

    paths: list[Path | None] = []
    resolved: set[Path] = set()
    for index, value in enumerate(raw_values, start=1):
        raw = str(value or "").strip()
        if not raw:
            if not optional:
                raise DeliveryReceiptError(f"方案 v{index} {label}路径缺失")
            paths.append(None)
            continue
        path = Path(raw)
        try:
            identity = path.resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            raise DeliveryReceiptError(f"方案 v{index} {label}路径无效") from exc
        if identity in resolved:
            raise DeliveryReceiptError(f"{label}不能在多个方案间复用同一路径")
        resolved.add(identity)
        paths.append(path)
    return paths


def build_delivery_receipt(
    *,
    job_id: str,
    source_docx: Iterable[str | Path],
    professional_docx: Iterable[str | Path],
    professional_json: Iterable[str | Path],
    professional_receipts: Iterable[str | Path],
    compare_docx: Iterable[str | Path],
    focus_xlsx: Iterable[str | Path | None],
    score_overview_xlsx: Iterable[str | Path | None],
    expert_review_docx: Iterable[str | Path | None],
    receipt_path: str | Path | None = None,
) -> dict[str, Any]:
    """Seal every per-variant formal artifact into one delivery chain."""

    if isinstance(professional_docx, (str, bytes, Path)):
        raise DeliveryReceiptError("专业 Word 必须按方案提供等长路径列表")
    try:
        raw_outputs = list(professional_docx)
    except TypeError as exc:
        raise DeliveryReceiptError("专业 Word 必须按方案提供等长路径列表") from exc
    if not raw_outputs:
        raise DeliveryReceiptError("专业 Word 路径列表为空")
    variant_count = len(raw_outputs)
    source_paths = _artifact_paths(
        source_docx,
        label="中间 Word",
        count=variant_count,
    )
    output_paths = _artifact_paths(
        raw_outputs,
        label="专业 Word",
        count=variant_count,
    )
    receipt_paths = _artifact_paths(
        professional_receipts,
        label="渲染凭证",
        count=variant_count,
    )
    if any(path is None for path in source_paths + output_paths + receipt_paths):
        raise DeliveryReceiptError("中间 Word、专业 Word 与渲染凭证路径缺失")
    sources = [path for path in source_paths if path is not None]
    outputs = [path for path in output_paths if path is not None]
    render_receipts = [path for path in receipt_paths if path is not None]
    professional_json_paths = _artifact_paths(
        professional_json,
        label="专业 JSON",
        count=variant_count,
    )
    compare_paths = _artifact_paths(
        compare_docx,
        label="对比 Word",
        count=variant_count,
    )
    optional_paths = {
        "focus_xlsx": _artifact_paths(
            focus_xlsx,
            label="重点清单表",
            count=variant_count,
            optional=True,
        ),
        "score_overview_xlsx": _artifact_paths(
            score_overview_xlsx,
            label="评分点证据总览",
            count=variant_count,
            optional=True,
        ),
        "expert_review_docx": _artifact_paths(
            expert_review_docx,
            label="专家复核提要",
            count=variant_count,
            optional=True,
        ),
    }

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
        if not isinstance(quality_gate, dict) or not all(
            quality_gate.get(key) is True for key in required_gates
        ):
            raise DeliveryReceiptError(f"方案 v{index} 专业 Word 质量门未全部通过")

        structural_path = Path(
            str((render_receipt.get("structural_quality") or {}).get("receipt") or "")
        )
        visual_path = Path(
            str((render_receipt.get("visual_quality") or {}).get("receipt") or "")
        )
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

        professional_json_path = professional_json_paths[index - 1]
        compare_path = compare_paths[index - 1]
        if professional_json_path is None or compare_path is None:  # defensive typing guard
            raise DeliveryReceiptError(f"方案 v{index} 正式交付制品路径缺失")
        row = {
            "variant": index,
            "source_docx": source_artifact,
            "professional_docx": output_artifact,
            "professional_json": _artifact(professional_json_path),
            "professional_render_receipt": render_artifact,
            "compare_docx": _artifact(compare_path),
            "structural_quality_receipt": structural_artifact,
            "visual_quality_receipt": visual_artifact,
            "figure_manifest": figure_artifact,
            "quality_gate": {key: True for key in required_gates},
        }
        for key, paths in optional_paths.items():
            path = paths[index - 1]
            row[key] = _artifact(path) if path is not None else None
        rows.append(row)

    target = Path(receipt_path) if receipt_path else outputs[0].parent / f"delivery_receipt_{job_id}.json"
    receipt = {
        "schema": "zhifei.delivery_receipt.v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "job_id": str(job_id),
        "delivery_profile": "sonnet5_professional_word",
        "variant_count": len(rows),
        "variants": rows,
    }
    receipt["decision_digest"] = canonical_delivery_receipt_digest(receipt)
    _atomic_write_json(target, receipt)
    receipt["receipt"] = str(target)
    return receipt
