from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REVISION_ROOT = Path("build") / "review_revisions"
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def result_version(variants: Iterable[dict[str, Any]]) -> str:
    return canonical_digest(list(variants))


def variant_version(variant: dict[str, Any]) -> str:
    return canonical_digest(variant)


def issue_fingerprint(item: dict[str, Any], *, section_digest: str = "") -> str:
    stable = {
        "source": str(item.get("source") or ""),
        "title": str(item.get("title") or ""),
        "type": str(item.get("type") or ""),
        "severity": str(item.get("severity") or ""),
        "problem": str(item.get("problem") or ""),
        "suggestion": str(item.get("suggestion") or ""),
        "section_digest": str(section_digest or ""),
    }
    return canonical_digest(stable)


def stable_issue_id(item: dict[str, Any], *, section_digest: str = "") -> str:
    return f"ISS-{issue_fingerprint(item, section_digest=section_digest)[:16]}"


def issue_set_digest(items: Iterable[dict[str, Any]]) -> str:
    rows = []
    for item in items:
        rows.append(
            {
                "issue_id": str(item.get("issue_id") or ""),
                "title": str(item.get("title") or ""),
                "type": str(item.get("type") or ""),
                "severity": str(item.get("severity") or ""),
                "problem": str(item.get("problem") or ""),
                "suggestion": str(item.get("suggestion") or ""),
            }
        )
    rows.sort(key=lambda row: row["issue_id"])
    return canonical_digest(rows)


def _safe_id(value: str) -> str:
    raw = str(value or "").strip()
    if ".." in raw or "/" in raw or "\\" in raw:
        raise ValueError("invalid identifier")
    normalized = _SAFE_ID_RE.sub("_", raw).strip("._")
    if not normalized:
        raise ValueError("invalid identifier")
    return normalized[:160]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_manifest(result: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for kind, raw in sorted((result or {}).items()):
        values = raw if isinstance(raw, list) else [raw]
        for index, value in enumerate(values, start=1):
            path = Path(str(value or ""))
            if not value or not path.is_file():
                continue
            rows.append(
                {
                    "kind": str(kind),
                    "index": index,
                    "path": str(path),
                    "size": path.stat().st_size,
                    "sha256": _sha256_file(path),
                }
            )
    return rows


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
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _snapshot_digest(payload: dict[str, Any]) -> str:
    sealed = dict(payload)
    sealed.pop("snapshot_digest", None)
    sealed.pop("path", None)
    return canonical_digest(sealed)


def _seal_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(payload)
    sealed["snapshot_digest"] = _snapshot_digest(sealed)
    return sealed


def create_revision_snapshot(
    *,
    job_id: str,
    variants: list[dict[str, Any]],
    result: dict[str, Any] | None,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_job_id = _safe_id(job_id)
    base_version = result_version(variants)
    created_at = datetime.now(timezone.utc).isoformat()
    revision_seed = {
        "job_id": safe_job_id,
        "base_version": base_version,
        "created_at": created_at,
        "reason": str(reason or "review_apply"),
    }
    revision_id = f"REV-{canonical_digest(revision_seed)[:20]}"
    snapshot = _seal_snapshot({
        "schema_version": "review-revision-v1",
        "revision_id": revision_id,
        "job_id": safe_job_id,
        "created_at": created_at,
        "reason": str(reason or "review_apply"),
        "result_version": base_version,
        "variant_count": len(variants),
        "variants": variants,
        "artifacts": artifact_manifest(result),
        "metadata": dict(metadata or {}),
    })
    path = REVISION_ROOT / safe_job_id / f"{revision_id}.json"
    _atomic_write_json(path, snapshot)
    return {
        "revision_id": revision_id,
        "path": str(path),
        "result_version": base_version,
        "created_at": created_at,
    }


def load_revision_snapshot(*, job_id: str, revision_id: str) -> dict[str, Any]:
    safe_job_id = _safe_id(job_id)
    safe_revision_id = _safe_id(revision_id)
    path = REVISION_ROOT / safe_job_id / f"{safe_revision_id}.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if str(payload.get("job_id") or "") != safe_job_id:
        raise ValueError("revision job mismatch")
    variants = payload.get("variants")
    if not isinstance(variants, list):
        raise ValueError("invalid revision variants")
    if result_version(variants) != str(payload.get("result_version") or ""):
        raise ValueError("revision digest mismatch")
    recorded_snapshot_digest = str(payload.get("snapshot_digest") or "")
    if recorded_snapshot_digest and _snapshot_digest(payload) != recorded_snapshot_digest:
        raise ValueError("revision snapshot seal mismatch")
    payload["path"] = str(path)
    return payload


def finalize_revision_snapshot(
    *,
    job_id: str,
    revision_id: str,
    promotion: dict[str, Any],
) -> dict[str, Any]:
    """Append the verified promotion receipt to an existing revision snapshot.

    The snapshot remains the recoverable pre-change state; this receipt binds it
    to the candidate version and exact artifact hashes that were promoted.
    """

    payload = load_revision_snapshot(job_id=job_id, revision_id=revision_id)
    path = Path(str(payload.pop("path")))
    if isinstance(payload.get("promotion"), dict):
        raise ValueError("revision promotion already finalized")
    receipt = dict(promotion or {})
    committed_at = datetime.now(timezone.utc).isoformat()
    receipt["state"] = "committed"
    receipt.setdefault("committed_at", committed_at)
    receipt.setdefault("promoted_at", committed_at)
    payload["promotion"] = receipt
    payload = _seal_snapshot(payload)
    _atomic_write_json(path, payload)
    return {"revision_id": revision_id, "path": str(path), "promotion": receipt}


def prepare_revision_promotion(
    *,
    job_id: str,
    revision_id: str,
    promotion: dict[str, Any],
) -> dict[str, Any]:
    """Seal a candidate receipt without claiming that the job was promoted.

    This write intentionally precedes the job-store CAS.  A failed CAS leaves
    a recoverable ``candidate_prepared`` receipt whose artifact hashes can be
    audited, but it can never be mistaken for a committed promotion.
    """

    payload = load_revision_snapshot(job_id=job_id, revision_id=revision_id)
    path = Path(str(payload.pop("path")))
    existing = payload.get("promotion")
    if isinstance(existing, dict):
        raise ValueError("revision promotion already prepared")
    receipt = dict(promotion or {})
    receipt.pop("promoted_at", None)
    receipt.pop("committed_at", None)
    receipt["state"] = "candidate_prepared"
    receipt.setdefault("prepared_at", datetime.now(timezone.utc).isoformat())
    payload["promotion"] = receipt
    payload = _seal_snapshot(payload)
    _atomic_write_json(path, payload)
    return {"revision_id": revision_id, "path": str(path), "promotion": receipt}


def commit_revision_promotion(
    *,
    job_id: str,
    revision_id: str,
    candidate_artifact_digest: str,
    promoted_job_revision: int,
    promoted_job_status: str,
) -> dict[str, Any]:
    """Atomically mark a prepared candidate as the job-store CAS winner.

    The operation is idempotent for recovery: replaying the same commit after
    an ambiguous response returns the existing committed receipt.  A different
    candidate digest or job revision is rejected fail-closed.
    """

    payload = load_revision_snapshot(job_id=job_id, revision_id=revision_id)
    path = Path(str(payload.pop("path")))
    receipt = payload.get("promotion")
    if not isinstance(receipt, dict):
        raise ValueError("revision promotion was not prepared")
    expected_digest = str(candidate_artifact_digest or "").strip()
    if not expected_digest or str(receipt.get("candidate_artifact_digest") or "") != expected_digest:
        raise ValueError("candidate artifact digest mismatch")
    try:
        committed_revision = int(promoted_job_revision)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid promoted job revision") from exc
    if committed_revision <= 0:
        raise ValueError("invalid promoted job revision")
    committed_status = str(promoted_job_status or "").strip().lower()
    if committed_status not in {"done", "succeeded"}:
        raise ValueError("invalid promoted job status")

    state = str(receipt.get("state") or "").strip()
    if state == "committed":
        try:
            recorded_revision = int(receipt.get("promoted_job_revision") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("committed promotion identity mismatch") from exc
        if (
            recorded_revision != committed_revision
            or str(receipt.get("promoted_job_status") or "").strip().lower()
            != committed_status
        ):
            raise ValueError("committed promotion identity mismatch")
        return {"revision_id": revision_id, "path": str(path), "promotion": receipt}
    if state != "candidate_prepared":
        raise ValueError("revision promotion state is not candidate_prepared")

    committed_at = datetime.now(timezone.utc).isoformat()
    committed = dict(receipt)
    committed["state"] = "committed"
    committed["promoted_job_revision"] = committed_revision
    committed["promoted_job_status"] = committed_status
    committed["committed_at"] = committed_at
    committed["promoted_at"] = committed_at
    payload["promotion"] = committed
    payload = _seal_snapshot(payload)
    _atomic_write_json(path, payload)
    return {"revision_id": revision_id, "path": str(path), "promotion": committed}


def list_revision_snapshots(*, job_id: str) -> list[dict[str, Any]]:
    safe_job_id = _safe_id(job_id)
    directory = REVISION_ROOT / safe_job_id
    if not directory.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("REV-*.json"), reverse=True):
        try:
            payload = load_revision_snapshot(job_id=safe_job_id, revision_id=path.stem)
        except Exception:
            continue
        rows.append(
            {
                "revision_id": str(payload.get("revision_id") or path.stem),
                "created_at": str(payload.get("created_at") or ""),
                "reason": str(payload.get("reason") or ""),
                "result_version": str(payload.get("result_version") or ""),
                "variant_count": int(payload.get("variant_count") or 0),
                "promotion": payload.get("promotion") if isinstance(payload.get("promotion"), dict) else None,
                "path": str(path),
            }
        )
    return rows
