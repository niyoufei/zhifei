#!/usr/bin/env python3
from __future__ import annotations

"""Bounded real-provider acceptance using synthetic, non-project prompts only.

The script deliberately exercises exactly two short chapters with one primary
and one fallback opportunity per chapter.  It never prints credentials or raw
provider exceptions; the evidence contains provider/model identities, stable
error codes, digests, counts and integrity-bound checkpoints.
"""

import argparse
import asyncio
import hashlib
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.zhifei_autoplan.execution_control import (
    ExecutionBudgetExceededError,
    ExecutionControlRuntime,
)
from backend.zhifei_autoplan.generation_checkpoint import (
    build_generation_binding,
    finalize_generation_checkpoint,
    save_section_checkpoint,
)
from backend.zhifei_autoplan.local_env import load_local_env
from backend.zhifei_autoplan.model_reliability import ModelReliabilityRuntime
from backend.zhifei_autoplan.orchestrator import (
    new_provider_admission_run_coordinator,
    probe_provider_candidate,
)
from backend.zhifei_autoplan.provider_admission import (
    ProviderCandidate,
    public_snapshot,
)
from backend.zhifei_autoplan.provider_runtime import (
    build_server_provider_admission_candidates,
    server_provider_admission_required_roles,
)
from backend.zhifei_autoplan.utils.llm_client import LLMClient


CHAPTERS = (
    (
        "施工部署与现场组织",
        "编写一段600至900字的脱敏合成市政排水工程施工组织正文。"
        "项目不对应任何真实地点、单位或人员。正文须说明施工分区、流水顺序、"
        "临时排水、交通组织和关键接口，使用明确的小标题与可核查措施。",
    ),
    (
        "质量安全与应急保障",
        "编写一段600至900字的脱敏合成市政排水工程施工组织正文。"
        "项目不对应任何真实地点、单位或人员。正文须说明质量控制点、深基坑与"
        "临电风险、监测预警、应急响应和闭环验收，禁止虚构标准编号。",
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_error(result: dict[str, Any]) -> dict[str, Any]:
    info = result.get("error_info") if isinstance(result.get("error_info"), dict) else {}
    return {
        "code": str(info.get("code") or result.get("error") or "provider_error"),
        "message": str(info.get("user_message") or "模型未返回可用正文。"),
        "action": str(info.get("action") or "检查提供商状态后重试。"),
    }


def _select_routes(slots: list[ProviderCandidate]) -> list[ProviderCandidate]:
    if not slots:
        return []
    primary = next((slot for slot in slots if slot.role == "text_review"), None)
    primary = primary or next((slot for slot in slots if slot.role in {"text_main", "text_draft"}), slots[0])
    fallback = next((slot for slot in slots if slot.role == "text_backup"), None)
    if fallback is None:
        fallback = next(
            (
                slot
                for slot in slots
                if (slot.provider, slot.model, slot.credential)
                != (primary.provider, primary.model, primary.credential)
            ),
            None,
        )
    return [primary] + ([fallback] if fallback is not None else [])


async def _run_acceptance(output_dir: Path, *, hard_deadline_seconds: int) -> dict[str, Any]:
    load_local_env(Path(".runtime/local_keys.env"))
    load_local_env()
    run_id = f"real-model-{uuid.uuid4().hex[:12]}"
    started = time.monotonic()
    events: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    checkpoint_root = output_dir / "real_model_checkpoints"

    candidates = build_server_provider_admission_candidates()
    required_roles = server_provider_admission_required_roles(candidates)
    coordinator = new_provider_admission_run_coordinator(
        {"_provider_admission_root": str(output_dir / "provider_admission")}
    )
    events.append(
        {
            "at": _utc_now(),
            "type": "provider_admission_started",
            "candidate_count": len(candidates),
            "required_roles": required_roles,
        }
    )
    try:
        remaining = hard_deadline_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise asyncio.TimeoutError()
        admission_internal = await asyncio.wait_for(
            coordinator.admit_chain_once(
                candidates=candidates,
                probe=probe_provider_candidate,
                required_roles=required_roles,
            ),
            timeout=min(240.0, remaining),
        )
    except asyncio.TimeoutError:
        admission_internal = {
            "generation_allowed": False,
            "status": "failed",
            "missing_roles": required_roles,
        }
    admission_public = public_snapshot(admission_internal)
    events.append(
        {
            "at": _utc_now(),
            "type": "provider_admission_completed",
            "generation_allowed": bool(admission_internal.get("generation_allowed")),
            "admission_digest": str(admission_internal.get("admission_digest") or ""),
            "missing_roles": list(admission_public.get("missing_roles") or []),
        }
    )
    admitted_candidates = [
        candidate
        for candidate in coordinator.bound_candidates
        if str(candidate.role or "").startswith("text_")
        and (
            (admitted := coordinator.admitted_candidate(candidate.role)) is not None
            and admitted.identity_digest == candidate.identity_digest
        )
    ]
    routes = _select_routes(admitted_candidates)

    execution = ExecutionControlRuntime(
        max_concurrency=1,
        max_model_attempts=4,
        max_input_chars=80_000,
        max_requested_output_tokens=16_384,
    )
    reliability = ModelReliabilityRuntime(failure_threshold=2)
    public_routes = [
        {
            "slot": slot.slot,
            "route_index": index,
            "provider": slot.provider,
            "model": slot.model,
        }
        for index, slot in enumerate(routes, start=1)
    ]
    outline = [{"title": title} for title, _prompt in CHAPTERS]
    binding = build_generation_binding(
        topic="脱敏合成市政排水工程",
        project_id="runtime-acceptance-synthetic",
        project_type="市政排水",
        outline=outline,
        style="acceptance-short-form",
        chapter_pages=[1, 1],
        variant_id="acceptance",
        project_fact_digest="synthetic-no-real-project-data",
        requirement_plan_digest="bounded-two-short-chapters",
        provider_routes=public_routes,
        provider_admission_digest=str(
            admission_internal.get("admission_digest") or ""
        ),
    )

    if not bool(admission_internal.get("generation_allowed")) or len(routes) < 2:
        return {
            "schema_version": "runtime-real-model-acceptance-v1",
            "run_id": run_id,
            "started_at": _utc_now(),
            "finished_at": _utc_now(),
            "status": "failed",
            "conclusion": "HOLD_LOCAL_RUNTIME_ACCEPTANCE_REAL_MODEL_CHAIN_NOT_CONFIGURED",
            "routes": public_routes,
            "provider_admission": admission_public,
            "chapters": [],
            "events": [],
            "checkpoint": {"status": "failed_empty", "saved_chapter_count": 0},
            "execution": execution.snapshot(),
            "reliability": reliability.snapshot(),
            "credentials_exposed": False,
        }

    for chapter_index, (title, prompt) in enumerate(CHAPTERS):
        chapter_result: dict[str, Any] | None = None
        chapter_attempts: list[dict[str, Any]] = []
        for route_index, slot in enumerate(routes[:2], start=1):
            attempt_started = time.monotonic()
            event = {
                "at": _utc_now(),
                "type": "provider_attempt_started",
                "chapter_index": chapter_index,
                "chapter_title": title,
                "route_index": route_index,
                "provider": slot.provider,
                "model": slot.model,
            }
            events.append(event)
            client = LLMClient(
                provider=slot.provider,
                model=slot.model,
                api_key=slot.credential,
                reliability_runtime=reliability,
                reliability_identity=slot.identity_digest,
                retry_attempts=1,
                execution_runtime=execution,
            )
            try:
                remaining = hard_deadline_seconds - (time.monotonic() - started)
                if remaining <= 0:
                    raise asyncio.TimeoutError()
                result = await asyncio.wait_for(
                    client.complete(
                        prompt,
                        timeout=min(240.0, remaining),
                        max_tokens=4096,
                        stream=True,
                        retry_attempts=1,
                    ),
                    timeout=min(245.0, remaining),
                )
            except asyncio.TimeoutError:
                result = {
                    "text": "",
                    "error": "timeout",
                    "error_info": {
                        "code": "timeout",
                        "user_message": "模型请求超过本次验收的剩余期限。",
                        "action": "检查提供商可用性后重新验收。",
                    },
                }
            except ExecutionBudgetExceededError as exc:
                result = {"text": "", "error": "budget_exceeded", "error_info": exc.as_dict()}
            finally:
                client.close()

            text = str(result.get("text") or "").strip()
            attempt_evidence = {
                "route_index": route_index,
                "provider": slot.provider,
                "model": slot.model,
                "elapsed_seconds": round(time.monotonic() - attempt_started, 3),
                "ok": bool(text),
                "error": None if text else _safe_error(result),
            }
            chapter_attempts.append(attempt_evidence)
            events.append({"at": _utc_now(), "type": "provider_attempt_finished", **attempt_evidence, "chapter_index": chapter_index})
            if text:
                chapter_result = {
                    "title": title,
                    "content": text,
                    "provider": slot.provider,
                    "model": slot.model,
                    "attempts": route_index,
                }
                checkpoint = save_section_checkpoint(
                    namespace=run_id,
                    scope="acceptance",
                    binding=binding,
                    chapter_index=chapter_index,
                    chapter_title=title,
                    result=chapter_result,
                    root=checkpoint_root,
                )
                events.append(
                    {
                        "at": _utc_now(),
                        "type": "checkpoint_saved",
                        "chapter_index": chapter_index,
                        "saved_chapter_count": checkpoint.get("saved_chapter_count"),
                    }
                )
                break

        if chapter_result is None:
            outcomes.append({"chapter_index": chapter_index, "title": title, "ok": False, "attempts": chapter_attempts})
        else:
            content = str(chapter_result["content"])
            outcomes.append(
                {
                    "chapter_index": chapter_index,
                    "title": title,
                    "ok": True,
                    "provider": chapter_result["provider"],
                    "model": chapter_result["model"],
                    "content_chars": len(content),
                    "content_sha256": _sha256_text(content),
                    "attempts": chapter_attempts,
                }
            )

    succeeded = sum(1 for item in outcomes if item.get("ok"))
    checkpoint_status = "draft_complete" if succeeded == len(CHAPTERS) else ("failed_partial" if succeeded else "failed_empty")
    checkpoint = finalize_generation_checkpoint(
        namespace=run_id,
        scope="acceptance",
        binding=binding,
        status=checkpoint_status,
        root=checkpoint_root,
    )
    passed = succeeded == len(CHAPTERS) and checkpoint.get("saved_chapter_count") == len(CHAPTERS)
    return {
        "schema_version": "runtime-real-model-acceptance-v1",
        "run_id": run_id,
        "started_at": events[0]["at"] if events else _utc_now(),
        "finished_at": _utc_now(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "status": "passed" if passed else "failed",
        "conclusion": "PASS_REAL_MODEL_ACCEPTANCE" if passed else "HOLD_LOCAL_RUNTIME_ACCEPTANCE_REAL_MODEL_VALIDATION_FAILED",
        "synthetic_input_only": True,
        "chapter_total": len(CHAPTERS),
        "chapter_succeeded": succeeded,
        "chapter_failed": len(CHAPTERS) - succeeded,
        "routes": public_routes,
        "provider_admission": admission_public,
        "chapters": outcomes,
        "events": events,
        "checkpoint": checkpoint,
        "execution": execution.snapshot(),
        "reliability": reliability.snapshot(),
        "credentials_exposed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--hard-deadline-seconds", type=int, default=720)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    deadline = max(60, min(720, int(args.hard_deadline_seconds)))
    try:
        evidence = asyncio.run(
            asyncio.wait_for(
                _run_acceptance(output_dir, hard_deadline_seconds=deadline),
                timeout=float(deadline),
            )
        )
    except asyncio.TimeoutError:
        evidence = {
            "schema_version": "runtime-real-model-acceptance-v1",
            "run_id": f"real-model-timeout-{uuid.uuid4().hex[:8]}",
            "finished_at": _utc_now(),
            "status": "failed",
            "conclusion": "HOLD_LOCAL_RUNTIME_ACCEPTANCE_REAL_MODEL_HARD_TIMEOUT",
            "hard_deadline_seconds": deadline,
            "synthetic_input_only": True,
            "credentials_exposed": False,
        }
    evidence_path = output_dir / "real_model_acceptance.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": evidence.get("status"),
                "conclusion": evidence.get("conclusion"),
                "run_id": evidence.get("run_id"),
                "chapter_succeeded": evidence.get("chapter_succeeded", 0),
                "chapter_failed": evidence.get("chapter_failed", 0),
                "evidence": str(evidence_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if evidence.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
