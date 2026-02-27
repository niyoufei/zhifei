from __future__ import annotations

import asyncio
import json
import re
import sys
from typing import Any, Dict, List

from backend.app.routers.actions_bridge import (
    _apply_generation_mode_policy,
    _normalize_logic_template_id,
    _rebuild_postprocessed_artifacts,
    _save_outputs,
)
from backend.zhifei_autoplan.job_store import get_job, update_job
from backend.zhifei_autoplan.orchestrator import run_autoplan
from backend.zhifei_autoplan.params_runtime import load_params
from backend.zhifei_autoplan.variant_cycle import reserve_variant_ids


def _clamp_int(v: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(v)
    except Exception:
        n = int(default)
    return max(lo, min(hi, n))


def _is_cancelled(job_id: str) -> bool:
    j = get_job(job_id) or {}
    return str(j.get("status") or "").strip().lower() == "cancelled"


def _update_progress(job_id: str, agent_runtime: Dict[str, Any], variants_total: int, percent: int, stage: str, detail: str = "") -> None:
    p = max(0, min(100, int(percent)))
    update_job(
        job_id,
        progress={
            "percent": p,
            "stage": str(stage or ""),
            "detail": str(detail or ""),
            "variants_total": variants_total,
            "variants_done": int(agent_runtime.get("variants_done") or 0),
        },
        agent_runtime=agent_runtime,
    )


def execute_job(job_id: str) -> None:
    job = get_job(job_id)
    if not job:
        return
    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    try:
        local_payload = _apply_generation_mode_policy(json.loads(json.dumps(payload)))

        variants_total = _clamp_int(local_payload.get("variants") or 1, 1, 1, 5)
        agent_parallelism = _clamp_int(local_payload.get("agent_parallelism") or 4, 4, 1, 16)
        variant_parallelism = _clamp_int(local_payload.get("variant_parallelism") or 1, 1, 1, 5)
        local_payload["agent_parallelism"] = agent_parallelism
        local_payload["variant_parallelism"] = variant_parallelism

        agent_runtime = {
            "mode": "parallel",
            "master_agent": "主控Agent",
            "compliance_agent": "合规Agent",
            "agent_parallelism": agent_parallelism,
            "variant_parallelism": variant_parallelism,
            "variants_total": variants_total,
            "variants_done": 0,
            "worker_mode": "subprocess",
            "worker_pid": str(__import__("os").getpid()),
        }

        if _is_cancelled(job_id):
            update_job(job_id, status="cancelled", error="cancelled_by_user")
            return
        update_job(job_id, status="running", agent_runtime=agent_runtime)
        _update_progress(job_id, agent_runtime, variants_total, 5, "job_started", "任务已启动，正在分配多Agent")
        mode_policy = local_payload.get("_mode_policy") if isinstance(local_payload.get("_mode_policy"), dict) else {}
        mode_name = str(mode_policy.get("mode_effective") or local_payload.get("generation_mode") or "quality_200")
        pages_planned = int(mode_policy.get("planned_total_pages") or 0)
        if bool(mode_policy.get("auto_switched")):
            _update_progress(
                job_id,
                agent_runtime,
                variants_total,
                8,
                "mode_switch",
                f"页数规划={pages_planned}，已自动切换到高质量加速模式（{mode_name})",
            )
        else:
            _update_progress(
                job_id,
                agent_runtime,
                variants_total,
                8,
                "mode_ready",
                f"生成模式={mode_name}，页数规划={pages_planned}",
            )
        variant_plan = local_payload.get("_variant_plan")
        normalized_plan: List[Dict[str, Any]] = []
        if isinstance(variant_plan, list) and variant_plan:
            for it in variant_plan:
                if not isinstance(it, dict):
                    continue
                try:
                    vid = int(it.get("variant_id") or 0)
                except Exception:
                    vid = 0
                if vid <= 0:
                    continue
                rec: Dict[str, Any] = {"variant_id": vid}
                tid = _normalize_logic_template_id(it.get("logic_template_id"))
                if tid:
                    rec["logic_template_id"] = tid
                normalized_plan.append(rec)
        if not normalized_plan:
            variants = variants_total
            variant_ids = local_payload.get("_variant_ids")
            if not isinstance(variant_ids, list) or not variant_ids:
                variant_ids = reserve_variant_ids(
                    project_id=str(local_payload.get("project_id") or "").strip() or None,
                    count=max(1, variants),
                    explicit_variant_id=local_payload.get("variant_id"),
                    explicit_template_id=local_payload.get("logic_template_id") or local_payload.get("logic_template"),
                )
            for vid in variant_ids:
                try:
                    normalized_plan.append({"variant_id": int(vid)})
                except Exception:
                    continue
        if not normalized_plan:
            normalized_plan = [{"variant_id": 1}]
        variant_plan = normalized_plan
        variants_total = max(1, len(variant_plan))
        agent_runtime["variants_total"] = variants_total
        if variant_parallelism > variants_total:
            variant_parallelism = variants_total
            local_payload["variant_parallelism"] = variant_parallelism
            agent_runtime["variant_parallelism"] = variant_parallelism
        _update_progress(
            job_id,
            agent_runtime,
            variants_total,
            10,
            "agent_ready",
            f"多Agent协作已启用：章节并行={agent_parallelism}，方案并行={variant_parallelism}",
        )

        async def _run_variants_parallel() -> list[dict]:
            sem = asyncio.Semaphore(max(1, int(variant_parallelism)))
            lock = asyncio.Lock()
            done_count = 0
            ordered: list[dict | None] = [None for _ in range(len(variant_plan))]

            async def _run_one(pos: int, item: Dict[str, Any]):
                nonlocal done_count
                if _is_cancelled(job_id):
                    return
                vid = int(item.get("variant_id") or 1)
                tid = _normalize_logic_template_id(item.get("logic_template_id"))
                lp = json.loads(json.dumps(local_payload))
                lp["variant_id"] = int(vid)
                if tid:
                    lp["logic_template_id"] = tid
                lp["agent_parallelism"] = agent_parallelism
                async with sem:
                    if _is_cancelled(job_id):
                        return
                    detail = f"正在并行编制方案 v{int(vid)}"
                    if tid:
                        detail += f"（模板{tid}）"
                    _update_progress(
                        job_id,
                        agent_runtime,
                        variants_total,
                        15 + int((done_count / max(1, variants_total)) * 65),
                        "variant_running",
                        detail,
                    )
                    res = await run_autoplan(lp)
                    ordered[pos] = res
                async with lock:
                    done_count += 1
                    agent_runtime["variants_done"] = int(done_count)
                    _update_progress(
                        job_id,
                        agent_runtime,
                        variants_total,
                        15 + int((done_count / max(1, variants_total)) * 65),
                        "variant_running",
                        f"方案完成进度：{done_count}/{variants_total}",
                    )

            await asyncio.gather(*[_run_one(i, item) for i, item in enumerate(variant_plan)])
            return [x for x in ordered if isinstance(x, dict)]

        results = asyncio.run(_run_variants_parallel())
        if _is_cancelled(job_id):
            update_job(job_id, status="cancelled", error="cancelled_by_user")
            return
        if len(results) >= 2:
            try:
                from backend.zhifei_autoplan.variant_similarity import compute_variant_similarity
                from backend.zhifei_autoplan.diversity_autofix import apply_diversity_autofix

                params = load_params()
                overrides = local_payload.get("params_override")
                if isinstance(overrides, dict) and overrides:
                    for k, v in overrides.items():
                        if isinstance(v, dict) and isinstance(params.get(k), dict):
                            merged = dict(params.get(k) or {})
                            merged.update(v)
                            params[k] = merged
                        else:
                            params[k] = v
                div_cfg = params.get("variant_diversity") if isinstance(params.get("variant_diversity"), dict) else {}

                def _run_report():
                    return compute_variant_similarity(
                        results,
                        chapter_threshold=float(div_cfg.get("chapter_threshold") or 0.90),
                        overall_threshold=float(div_cfg.get("overall_threshold") or 0.85),
                        min_chars=int(div_cfg.get("min_chars") or 800),
                        ignore_title_keywords=(div_cfg.get("ignore_title_keywords") if isinstance(div_cfg.get("ignore_title_keywords"), list) else None),
                        relaxed_title_keywords=(div_cfg.get("relaxed_title_keywords") if isinstance(div_cfg.get("relaxed_title_keywords"), list) else None),
                        relaxed_chapter_threshold=(float(div_cfg.get("relaxed_chapter_threshold")) if div_cfg.get("relaxed_chapter_threshold") is not None else None),
                    )

                report = _run_report()
                max_rounds = int(div_cfg.get("auto_fix_rounds") or 1)
                if max_rounds < 0:
                    max_rounds = 0
                rounds = 0
                while rounds < max_rounds and report.get("ok") is False and report.get("flagged"):
                    changed_any = False
                    for f in (report.get("flagged") or [])[:24]:
                        title = str(f.get("title") or "").strip()
                        pair = str(f.get("pair") or "").strip()
                        m = re.match(r"^v(\\d+)_v(\\d+)$", pair)
                        if not m or not title:
                            continue
                        a = int(m.group(1))
                        b = int(m.group(2))
                        target_idx = max(a, b)
                        if target_idx <= 1 or target_idx > len(results):
                            continue
                        target = results[target_idx - 1]
                        secs = target.get("sections") if isinstance(target, dict) else None
                        if not isinstance(secs, list):
                            continue
                        for sec in secs:
                            if not isinstance(sec, dict):
                                continue
                            if str(sec.get("title") or "").strip() != title:
                                continue
                            if apply_diversity_autofix(sec, params=params, evidence_hint=str(pair)):
                                changed_any = True
                            break
                    if not changed_any:
                        break
                    report = _run_report()
                    rounds += 1
                _update_progress(job_id, agent_runtime, variants_total, 86, "cross_variant_check", "正在执行跨方案一致性与差异性审计")
                _rebuild_postprocessed_artifacts(results, payload=local_payload, report=report, params=params)
            except Exception:
                pass
        if _is_cancelled(job_id):
            update_job(job_id, status="cancelled", error="cancelled_by_user")
            return
        _update_progress(job_id, agent_runtime, variants_total, 92, "exporting", "正在导出 DOCX / 对照稿 / 问题清单")
        outputs = _save_outputs(f"actions_{job_id}", results)
        if _is_cancelled(job_id):
            update_job(job_id, status="cancelled", error="cancelled_by_user", result=outputs)
            return
        _update_progress(job_id, agent_runtime, variants_total, 100, "done", "任务完成")
        update_job(job_id, status="done", result=outputs, agent_runtime=agent_runtime)
    except Exception as e:
        update_job(
            job_id,
            status="failed",
            error=repr(e),
            progress={"percent": 100, "stage": "failed", "detail": repr(e)},
        )


def main() -> int:
    job_id = str(sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if not job_id:
        return 2
    execute_job(job_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
