import asyncio
import json
import os
import stat
import subprocess
import time
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.zhifei_autoplan.local_env import load_local_env
from compose_engine import Composer
from utils_write_docx import write_compose_to_docx

load_local_env()

@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    _reconcile_runtime_jobs()
    reaper = asyncio.create_task(_orphan_job_reaper(), name="autoplan-orphan-job-reaper")
    try:
        yield
    finally:
        reaper.cancel()
        with suppress(asyncio.CancelledError):
            await reaper


app = FastAPI(lifespan=_app_lifespan)
_SERVICE_STARTED_AT = time.time()
_STARTUP_RECONCILED_JOBS: list[str] = []
_STARTUP_RECONCILED_FAILED_JOBS: list[str] = []
_ORPHAN_REAPER_STATE: dict[str, object] = {
    "running": False,
    "interval_seconds": 15,
    "stale_after_seconds": 60,
    "last_run_at": None,
    "last_reconciled": 0,
    "last_error": None,
}


def _git_runtime_identity() -> dict[str, object]:
    def _run(*args: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=str(Path.cwd()),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=0.35,
                check=False,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if completed.returncode != 0:
            return None
        return completed.stdout.strip()

    sealed_head = str(os.environ.get("ZF_BUILD_SHA") or "").strip()
    sealed_branch = str(os.environ.get("ZF_BUILD_BRANCH") or "").strip()
    sealed_dirty_raw = str(os.environ.get("ZF_BUILD_DIRTY") or "").strip()
    head = sealed_head or _run("rev-parse", "HEAD")
    branch = sealed_branch or _run("branch", "--show-current")
    porcelain = None if sealed_dirty_raw in {"0", "1"} else _run(
        "status", "--porcelain=v1", "--untracked-files=all"
    )
    dirty = (
        sealed_dirty_raw == "1"
        if sealed_dirty_raw in {"0", "1"}
        else (None if porcelain is None else bool(porcelain))
    )
    return {
        "build_sha": head,
        "build_branch": branch,
        "dirty": dirty,
    }


_RUNTIME_IDENTITY_AT_START = _git_runtime_identity()


def _release_runtime_identity() -> dict[str, object]:
    """Freeze the content-addressed release identity at process start."""
    values = {
        "release_id": str(os.environ.get("ZF_RELEASE_ID") or "").strip(),
        "manifest_digest": str(
            os.environ.get("ZF_RELEASE_MANIFEST_DIGEST") or ""
        ).strip(),
        "source_digest": str(
            os.environ.get("ZF_RELEASE_SOURCE_DIGEST") or ""
        ).strip(),
        "runtime_digest": str(os.environ.get("ZF_RUNTIME_DIGEST") or "").strip(),
        "release_root": str(os.environ.get("ZF_RELEASE_ROOT") or "").strip(),
    }
    values["managed"] = all(bool(values[key]) for key in values)
    values["mode"] = "sealed_release" if values["managed"] else "development"
    return values


_RELEASE_IDENTITY_AT_START = _release_runtime_identity()
_SUPERVISOR_STATE_FILE_AT_START = str(
    os.environ.get("ZF_SUPERVISOR_STATE_FILE") or ""
).strip()
_SUPERVISOR_PUBLIC_FIELDS = {
    "status",
    "release_id",
    "backend_pid",
    "ui_pid",
    "circuit_open",
    "restart_count_window",
    "last_health_at",
    "last_error_code",
    "health_degraded",
    "consecutive_health_failures",
    "first_health_failure_at",
    "last_probe_error_code",
    "started_at",
    "updated_at",
}


def _supervisor_runtime_status() -> dict[str, object]:
    """Read a small, permission-checked state projection without leaking secrets."""
    managed = bool(_RELEASE_IDENTITY_AT_START.get("managed"))
    if not _SUPERVISOR_STATE_FILE_AT_START:
        return {"managed": managed, "available": False, "status": "unmanaged"}
    path = Path(_SUPERVISOR_STATE_FILE_AT_START)
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
            return {
                "managed": managed,
                "available": False,
                "status": "state_untrusted",
            }
        if info.st_size > 64 * 1024:
            return {
                "managed": managed,
                "available": False,
                "status": "state_oversized",
            }
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError("invalid supervisor state")
        public = {
            key: raw.get(key)
            for key in _SUPERVISOR_PUBLIC_FIELDS
            if key in raw
        }
        public.update({"managed": managed, "available": True})
        return public
    except (OSError, TypeError, UnicodeError, json.JSONDecodeError):
        return {
            "managed": managed,
            "available": False,
            "status": "state_unavailable",
        }


def _offline_provider_admission_status(*, detailed: bool = False) -> dict[str, object]:
    """Evaluate the latest receipt without importing an SDK or touching network."""

    from backend.zhifei_autoplan.provider_admission import evaluate_latest_snapshot
    from backend.zhifei_autoplan.provider_runtime import (
        build_server_provider_admission_candidates,
        server_provider_admission_required_roles,
    )

    candidates = build_server_provider_admission_candidates()
    required_roles = server_provider_admission_required_roles(candidates)
    snapshot = evaluate_latest_snapshot(
        candidates,
        required_roles,
        root=os.environ.get("ZF_PROVIDER_ADMISSION_STATE_DIR") or None,
    )
    if detailed:
        return snapshot
    return {
        "configured": bool(snapshot.get("configured_slots")),
        "admitted": str(snapshot.get("status") or "") in {"admitted", "degraded"},
        "state": str(snapshot.get("status") or "missing"),
        "generation_allowed": bool(snapshot.get("generation_allowed")),
        "degraded": bool(snapshot.get("degraded")),
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers: ingest/retrieve/publish/score
from .routers.actions_bridge import router as actions_bridge_router
from .routers.auth import router as auth_router
from .routers.ingest import router as ingest_router
from .routers.kg_read_only_preview import router as kg_read_only_preview_router
from .routers.local_llm_preview_safe import router as local_llm_preview_safe_router
from .routers.local_trial_preview_only import router as local_trial_preview_only_router
from .routers.publish_router import router as publish_router
from .routers.retrieve import router as retrieve_router
from .routers.score_router import router as score_router
from .routers.zhifei_autoplan import router as zhifei_autoplan_router

app.include_router(ingest_router)
app.include_router(retrieve_router)
app.include_router(publish_router)
app.include_router(score_router)
app.include_router(zhifei_autoplan_router)
app.include_router(actions_bridge_router)
app.include_router(auth_router)
app.include_router(local_llm_preview_safe_router)
app.include_router(local_trial_preview_only_router)
app.include_router(kg_read_only_preview_router)


def _reconcile_runtime_jobs() -> None:
    from backend.zhifei_autoplan.job_store import (
        get_job,
        reconcile_legacy_failed_jobs,
        reconcile_stale_jobs,
    )
    from backend.zhifei_autoplan.local_job_queue import ensure_worker_started
    from backend.zhifei_autoplan.runtime_events import append_runtime_event

    global _STARTUP_RECONCILED_JOBS, _STARTUP_RECONCILED_FAILED_JOBS
    _STARTUP_RECONCILED_JOBS = reconcile_stale_jobs(stale_after_seconds=60)
    for job_id in _STARTUP_RECONCILED_JOBS:
        append_runtime_event(job_id, "startup_reconciled", status="interrupted_recoverable")
    _STARTUP_RECONCILED_FAILED_JOBS = reconcile_legacy_failed_jobs()
    for job_id in _STARTUP_RECONCILED_FAILED_JOBS:
        repaired = get_job(job_id) or {}
        checkpoint = (
            (repaired.get("progress") or {}).get("checkpoint")
            if isinstance(repaired.get("progress"), dict)
            else {}
        )
        append_runtime_event(
            job_id,
            "startup_failed_checkpoint_reconciled",
            checkpoint_status=str((checkpoint or {}).get("status") or "failed_empty"),
        )
    ensure_worker_started()


async def _orphan_job_reaper() -> None:
    from backend.zhifei_autoplan.job_store import reconcile_stale_jobs
    from backend.zhifei_autoplan.local_job_queue import local_dispatch_job_ids
    from backend.zhifei_autoplan.runtime_events import append_runtime_event

    _ORPHAN_REAPER_STATE["running"] = True
    try:
        while True:
            await asyncio.sleep(int(_ORPHAN_REAPER_STATE["interval_seconds"]))
            try:
                reconciled = await asyncio.to_thread(
                    reconcile_stale_jobs,
                    stale_after_seconds=int(_ORPHAN_REAPER_STATE["stale_after_seconds"]),
                    protected_job_ids=local_dispatch_job_ids(),
                )
                _ORPHAN_REAPER_STATE["last_run_at"] = time.time()
                _ORPHAN_REAPER_STATE["last_reconciled"] = len(reconciled)
                _ORPHAN_REAPER_STATE["last_error"] = None
                for job_id in reconciled:
                    with suppress(Exception):
                        append_runtime_event(
                            job_id,
                            "stale_job_reconciled",
                            status="interrupted_recoverable",
                        )
            except Exception as exc:  # noqa: BLE001 - isolate malformed historical jobs.
                # One malformed/disappearing historical record must not kill
                # the permanent reconciliation loop.
                _ORPHAN_REAPER_STATE["last_run_at"] = time.time()
                _ORPHAN_REAPER_STATE["last_error"] = type(exc).__name__
    finally:
        _ORPHAN_REAPER_STATE["running"] = False


@app.get("/health")
def health():
    from backend.zhifei_autoplan.job_store import job_runtime_counts
    from backend.zhifei_autoplan.local_job_queue import local_queue_snapshot

    cfg_path = Path("backend/data/autoplan/config.json")
    cfg_mtime = cfg_path.stat().st_mtime if cfg_path.exists() else None
    cfg_version = None
    cfg_version_auto = None
    try:
        if cfg_path.exists():
            cfg_version = json.loads(cfg_path.read_text(encoding="utf-8")).get("config_version")
    except (AttributeError, OSError, UnicodeError, json.JSONDecodeError):
        cfg_version = None
    if cfg_mtime is not None:
        cfg_version_auto = datetime.fromtimestamp(
            cfg_mtime, timezone.utc
        ).strftime("%Y-%m-%d")
    audit_dir = Path("backend/data/audit")
    audit_ready = audit_dir.exists() and audit_dir.is_dir()
    identity = dict(_RUNTIME_IDENTITY_AT_START)
    release_identity = dict(_RELEASE_IDENTITY_AT_START)
    return {
        "ok": True,
        "process_pid": os.getpid(),
        "version": "autoplan-0.1.0",
        "service": "文档生成系统",
        "system_id": os.environ.get("ZF_SYSTEM_ID", "docgen-system"),
        "workspace_root": str(Path.cwd()),
        "config_mtime": cfg_mtime,
        "config_version": cfg_version,
        "config_version_auto": cfg_version_auto,
        "audit_ready": audit_ready,
        "build_sha": identity.get("build_sha"),
        "build_branch": identity.get("build_branch"),
        "dirty": identity.get("dirty"),
        "release_id": release_identity.get("release_id"),
        "manifest_digest": release_identity.get("manifest_digest"),
        "source_digest": release_identity.get("source_digest"),
        "runtime_digest": release_identity.get("runtime_digest"),
        "release_root": release_identity.get("release_root"),
        "runtime_mode": release_identity.get("mode"),
        "release_managed": release_identity.get("managed"),
        "supervisor": _supervisor_runtime_status(),
        "started_at": _SERVICE_STARTED_AT,
        "uptime_seconds": max(0, int(time.time() - _SERVICE_STARTED_AT)),
        "jobs": job_runtime_counts(stale_after_seconds=60),
        "queue": local_queue_snapshot(),
        "provider_admission": _offline_provider_admission_status(),
        "startup_reconciled_jobs": len(_STARTUP_RECONCILED_JOBS),
        "startup_reconciled_failed_jobs": len(_STARTUP_RECONCILED_FAILED_JOBS),
        "self_heal": {
            "enabled": str(os.environ.get("ZF_ENABLE_SELF_HEAL") or "0").strip().lower()
            in {"1", "true", "yes", "on"},
            "mode": "opt_in",
            "orphan_reaper": dict(_ORPHAN_REAPER_STATE),
        },
        "p0_readiness_supported": True,
        "p0_readiness_path": "/p0/readiness",
    }


@app.get("/livez")
async def livez():
    """Constant-time supervisor probe with the frozen release identity.

    This endpoint deliberately performs no job-directory scan, provider
    admission evaluation, network access, or mutable-state read.  Rich runtime
    diagnostics remain on ``/health`` for the UI and operators.
    """

    identity = dict(_RUNTIME_IDENTITY_AT_START)
    release_identity = dict(_RELEASE_IDENTITY_AT_START)
    return {
        "ok": True,
        "system_id": os.environ.get("ZF_SYSTEM_ID", "docgen-system"),
        "build_sha": identity.get("build_sha"),
        "release_id": release_identity.get("release_id"),
        "manifest_digest": release_identity.get("manifest_digest"),
        "source_digest": release_identity.get("source_digest"),
        "runtime_digest": release_identity.get("runtime_digest"),
        "started_at": _SERVICE_STARTED_AT,
        "uptime_seconds": max(0, int(time.time() - _SERVICE_STARTED_AT)),
    }


@app.get("/p0/readiness")
def p0_readiness():
    from backend.zhifei_autoplan.p0_readiness import build_p0_readiness_snapshot

    return build_p0_readiness_snapshot(Path.cwd())


@app.get("/capabilities")
def capabilities(project_id: str | None = None):
    from pathlib import Path

    from backend.app.routers.zhifei_autoplan import (
        _job_list_default_fields,
        _job_list_field_alias,
    )
    from backend.zhifei_autoplan.boq_store import load_boq_data
    from backend.zhifei_autoplan.kg_store import get_active_kg
    from backend.zhifei_autoplan.tender_store import load_tender_matrix
    roles_cfg = Path("backend/data/autoplan/agent_roles.json")
    cfg_version = None
    cfg_version_auto = None
    cfg_path = Path("backend/data/autoplan/config.json")
    try:
        if cfg_path.exists():
            cfg_version = json.loads(cfg_path.read_text(encoding="utf-8")).get("config_version")
    except (AttributeError, OSError, UnicodeError, json.JSONDecodeError):
        cfg_version = None
    if cfg_path.exists():
        try:
            cfg_version_auto = datetime.fromtimestamp(
                cfg_path.stat().st_mtime, timezone.utc
            ).strftime("%Y-%m-%d")
        except OSError:
            cfg_version_auto = None
    return {
        "ok": True,
        "config_version": cfg_version,
        "config_version_auto": cfg_version_auto,
        "models": [
            "openai",
            "anthropic",
            "google",
            "zhipu",
            "qwen",
            "deepseek",
            "baidu",
            "iflytek",
            "tencent",
        ],
        "kg_active": bool(get_active_kg()),
        "project_id": str(project_id or "").strip() or None,
        "tender_matrix_loaded": bool(load_tender_matrix(project_id=project_id)),
        "boq_loaded": bool(load_boq_data(project_id=project_id)),
        "agent_roles_configured": roles_cfg.exists(),
        "modules": {
            "tender_parser": True,
            "boq_parser": True,
            "kg_binding": True,
            "multi_agent": True,
            "image_charts": True,
            "auth_billing": True,
        },
        "job_list": {
            "default_fields": sorted(_job_list_default_fields()),
            "field_alias": {k: sorted(v) for k, v in _job_list_field_alias().items()},
        },
        "audit": {
            "logging": True,
            "query": True,
            "summary": True,
            "stats": True,
            "export": ["json", "csv", "xlsx"],
            "export_file_list": True,
            "export_file_cleanup": True,
        },
    }


@app.get("/config")
def config():
    # 仅输出非敏感配置（不返回密钥）
    from backend.app.routers.zhifei_autoplan import (
        _job_list_default_fields,
        _job_list_field_alias,
    )
    from backend.zhifei_autoplan.utils.llm_client import LLMClient
    defaults = LLMClient.load_defaults()
    cfg_version = None
    cfg_version_auto = None
    cfg_path = Path("backend/data/autoplan/config.json")
    try:
        if cfg_path.exists():
            cfg_version = json.loads(cfg_path.read_text(encoding="utf-8")).get("config_version")
    except (AttributeError, OSError, UnicodeError, json.JSONDecodeError):
        cfg_version = None
    if cfg_path.exists():
        try:
            cfg_version_auto = datetime.fromtimestamp(
                cfg_path.stat().st_mtime, timezone.utc
            ).strftime("%Y-%m-%d")
        except OSError:
            cfg_version_auto = None
    return {
        "ok": True,
        "autoplan_auto": os.environ.get("ZF_AUTOPLAN_AUTO", "0"),
        "default_provider": defaults.get("default_provider") or os.environ.get("ZF_DEFAULT_PROVIDER"),
        "default_model": defaults.get("default_model") or os.environ.get("ZF_DEFAULT_MODEL"),
        "daily_limit_default": os.environ.get("ZF_DAILY_LIMIT", "50"),
        "job_cost": os.environ.get("ZF_JOB_COST", "1"),
        "config_version": cfg_version,
        "config_version_auto": cfg_version_auto,
        "job_list": {
            "default_fields": sorted(_job_list_default_fields()),
            "field_alias": {k: sorted(v) for k, v in _job_list_field_alias().items()},
        },
    }


@app.post("/config/version")
def update_config_version(version: str | None = None, authorization: str | None = Header(default=None)):
    admin_key = os.environ.get("ZF_ADMIN_KEY", "")
    if not admin_key:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {admin_key}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    cfg_path = Path("backend/data/autoplan/config.json")
    cfg = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            cfg = {}
    cfg["config_version"] = version or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        audit_dir = Path("backend/data/audit")
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_path = audit_dir / "config.jsonl"
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": "config_version_update",
            "config_version": cfg["config_version"],
        }
        audit_path.write_text(
            (audit_path.read_text(encoding="utf-8") if audit_path.exists() else "")
            + json.dumps(record, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
    except (OSError, UnicodeError):
        pass
    return {"ok": True, "config_version": cfg["config_version"]}


@app.get("/model_health")
def model_health():
    """
    兼容接口：仅离线返回模型配置与准入聚合，不调用外部API。
    """
    status = _offline_provider_admission_status()
    return {
        "ok": True,
        **status,
    }


@app.get("/model_ping")
def model_ping():
    raise HTTPException(
        status_code=410,
        detail={
            "code": "MODEL_PING_RETIRED",
            "message": "无上下文模型探测已停用；系统只在项目证据门通过后执行供应商准入。",
        },
    )

class DocStyle(BaseModel):
    paper: str = "A4"
    margins: list = [20,20,20,20]
    font: str = "SimSun"
    font_size: int = 12
    line_spacing: float = 1.5
    auto_page_break: bool = True

class ComposeRequest(BaseModel):
    topic: str
    outline: list[str]

class ComposeResponse(BaseModel):
    status: str
    topic: str
    outline: list
    sections: list
    style: dict
    saved_at: str

composer = Composer()

@app.post("/compose", response_model=ComposeResponse)
def compose(req: ComposeRequest, background_tasks: BackgroundTasks):
    # --- ProjectProfile: build for traceability & downstream rules ---
    from backend.project_profile_service import generate_project_profile
    payload = req.dict() if hasattr(req, 'dict') else req.model_dump()
    project_profile = generate_project_profile(payload)
    import json as _json
    import os as _os
    # --- Compose Engine: build sections using KG context (demo) ---
    try:
        from backend.compose_engine_service import build_sections_from_kg
        _req_outline = getattr(req, 'outline', None)
        _req_topic = getattr(req, 'topic', None)
        # sanitize topic: strip Hefei suffixes to avoid leaking city name
        if isinstance(_req_topic, str):
            _req_topic = _req_topic.replace('（合肥）','').replace('(合肥)','')
            _req_topic = _req_topic.replace('（安徽合肥）','').replace('(安徽合肥)','')
            _req_topic = _req_topic.strip()
            # propagate sanitized topic into payload/request to prevent downstream Hefei leakage
            if isinstance(payload, dict) and _req_topic:
                payload['topic'] = _req_topic
            with suppress(Exception):
                req.topic = _req_topic
        result = {
            'sections': build_sections_from_kg(
                payload=locals().get('payload'),
                project_profile=locals().get('project_profile'),
                precheck=locals().get('precheck'),
                region_upgrade=locals().get('region_upgrade'),
                kg_context=locals().get('kg_context'),
                outline=_req_outline,
                topic=_req_topic,
            )
        }
    except Exception as _e:  # noqa: BLE001 - preserve the legacy compose fallback.
        _old = locals().get('result')
        if isinstance(_old, dict) and isinstance(_old.get('sections'), list):
            result = _old
        else:
            result = {'sections': [{'title': 'Compose Engine Fallback', 'content': f'compose_engine_service failed: {_e!r}'}]}
    # --- end Compose Engine block ---

    _os.makedirs('build', exist_ok=True)
    with open('build/project_profile.json', 'w', encoding='utf-8') as _f:
        _json.dump(project_profile, _f, ensure_ascii=False, indent=2)
    # --------------------------------------------------------------
    # --- Region Upgrade: resolve 安徽/青天 upgrade rules (trace only) ---
    from backend.region_upgrade_service import resolve_region_upgrade
    upgrade = resolve_region_upgrade(payload, project_profile)
    import json as _json_up
    import os as _os_up
    _os_up.makedirs('build', exist_ok=True)
    with open('build/region_upgrade.json', 'w', encoding='utf-8') as _f_up:
        _json_up.dump(upgrade, _f_up, ensure_ascii=False, indent=2)
    # --------------------------------------------------------------------

    # --- PreCheck Guard: evaluate payload + project_profile (before compose) ---
    # --- KG Context: resolve domain + select base packs (traceable) ---
    from backend.kg_context_service import build_kg_context
    kg_context = build_kg_context(payload, project_profile)
    import json as _json_kg
    import os as _os_kg
    _os_kg.makedirs('build', exist_ok=True)
    with open('build/kg_context.json', 'w', encoding='utf-8') as _f_kg:
        _json_kg.dump(kg_context, _f_kg, ensure_ascii=False, indent=2)
    # ----------------------------------------------------------------------
    # enrich project_profile (topic/domain_key/region_key) for traceability
    with suppress(Exception):
        import json as _json_pp
        import os as _os_pp
        _os_pp.makedirs('build', exist_ok=True)
        # normalize project_profile to dict for stable persistence
        if project_profile is None:
            project_profile = {}
        elif not isinstance(project_profile, dict):
            if hasattr(project_profile, 'model_dump'):
                project_profile = project_profile.model_dump()
            elif hasattr(project_profile, 'dict'):
                project_profile = project_profile.dict()
            else:
                project_profile = dict(project_profile)

        # topic backfill + sanitize (remove Hefei suffix markers)
        _topic = project_profile.get('topic') if isinstance(project_profile, dict) else None
        if not _topic and isinstance(payload, dict):
            _topic = payload.get('topic')
        if not _topic:
            _topic = _req_topic
        if isinstance(_topic, str):
            for _sfx in ('（合肥）','(合肥)','（安徽合肥）','(安徽合肥)'):
                _topic = _topic.replace(_sfx, '')
            _topic = _topic.strip()
        if isinstance(project_profile, dict) and _topic:
            project_profile['topic'] = _topic

        # domain_key backfill: prefer kg_context.domain_resolution.domain_key, fallback decoration
        _dk = None
        if isinstance(kg_context, dict):
            _dr = kg_context.get('domain_resolution')
            if isinstance(_dr, dict):
                _dk = _dr.get('domain_key')
            if not _dk:
                _dk = kg_context.get('domain_key')
        if not _dk:
            _dk = 'decoration'
        if isinstance(project_profile, dict):
            project_profile['domain_key'] = project_profile.get('domain_key') or _dk

        # region_key backfill (if available)
        if isinstance(upgrade, dict):
            _rk = upgrade.get('region_key')
            if _rk and isinstance(project_profile, dict):
                project_profile['region_key'] = project_profile.get('region_key') or _rk

        with open('build/project_profile.json', 'w', encoding='utf-8') as _f_pp:
            _json_pp.dump(project_profile, _f_pp, ensure_ascii=False, indent=2)
    from backend.precheck_guard_service import run_precheck_guard
    precheck = run_precheck_guard(payload, project_profile)
    import json as _json2
    import os as _os2
    _os2.makedirs('build', exist_ok=True)
    with open('build/precheck_guard.json', 'w', encoding='utf-8') as _f:
        _json2.dump(precheck, _f, ensure_ascii=False, indent=2)
    if not precheck.get('passed', False):
        _blocked = {
            'status': 'blocked',
            'topic': payload.get('topic'),
            'outline': payload.get('outline'),
            'sections': [
                {
                    'title': 'PreCheck Guard 阻断报告',
                    'content': precheck.get('human_readable') or _json2.dumps(precheck, ensure_ascii=False, indent=2)
                }
            ],
            'style': {
                'paper': 'A4',
                'margins': [20, 20, 20, 20],
                'font': 'SimSun',
                'font_size': 12,
                'line_spacing': 1.5,
                'auto_page_break': True
            },
            'saved_at': 'build/compose.json'
        }
        with open('build/compose.json', 'w', encoding='utf-8') as _f2:
            _json2.dump(_blocked, _f2, ensure_ascii=False, indent=2)
        return _blocked
    # ---------------------------------------------------------------------------
    result = composer.compose(
        topic=req.topic,
        outline=req.outline,
        max_pages=50
    )

    os.makedirs("build", exist_ok=True)
    compose_json_path = "build/compose.json"

    # --- Compose Engine override (before compose.json write) ---
    with suppress(Exception):
        from backend.compose_engine_service import build_sections_from_kg
        if not isinstance(locals().get('result'), dict):
            result = {'sections': []}
        result['sections'] = build_sections_from_kg(
            payload=locals().get('payload'),
            project_profile=locals().get('project_profile'),
            precheck=locals().get('precheck'),
            region_upgrade=(locals().get('upgrade') or locals().get('region_upgrade')),
            kg_context=locals().get('kg_context'),
            outline=getattr(req, 'outline', None),
            topic=getattr(req, 'topic', None),
        )
        # keep original result on any failure
    # ----------------------------------------------

    # --- AI 正文复用（仅读） ---
    # 严禁在 /compose 请求中隐式发起模型调用。生成必须通过受控的
    # /actions/runs 或 /autoplan/generate 入口，先完成证据门和供应商准入。
    # 这里只允许复用已有、已持久化的结果。
    with suppress(Exception):
        from pathlib import Path as _Path
        _auto_json = _Path("build") / "autoplan_generated.json"
        if _auto_json.exists():
            import json as _json
            _auto = _json.loads(_auto_json.read_text(encoding="utf-8"))
            if isinstance(_auto, dict) and isinstance(_auto.get("variants"), list) and _auto["variants"]:
                _auto = _auto["variants"][0]
            if isinstance(_auto, dict) and _auto.get("sections"):
                # 用 AI 正文覆盖章节内容
                result["sections"] = [
                    {"title": s.get("title"), "content": s.get("content")}
                    for s in _auto.get("sections", [])
                    if isinstance(s, dict)
                ]

    # 证据链摘要（写入 compose.json 便于离线复核）
    try:
        from backend.zhifei_autoplan.boq_store import load_boq_data as _load_boq_data
        from backend.zhifei_autoplan.kg_store import get_active_kg as _get_active_kg
        from backend.zhifei_autoplan.tender_store import (
            load_tender_matrix as _load_tender_matrix,
        )
        _ak = _get_active_kg()
        _ingest = Path("backend/data/audit/ingest.jsonl")
        _ingest_cnt = len(_ingest.read_text(encoding="utf-8").splitlines()) if _ingest.exists() else 0
        _sel = (locals().get("kg_context") or {}).get("selected_packs") or []
        _sel_names = []
        for _p in _sel:
            if isinstance(_p, dict):
                _sel_names.append(_p.get("name") or _p.get("path"))
            else:
                _sel_names.append(str(_p))
        evidence_summary = {
            "tender_matrix_loaded": bool(_load_tender_matrix()),
            "boq_loaded": bool(_load_boq_data()),
            "active_kg_file": _ak.get("file_name") if _ak else None,
            "active_kg_sha256": _ak.get("sha256") if _ak else None,
            "ingest_records": _ingest_cnt,
            "selected_packs": [n for n in _sel_names if n],
        }
    except Exception:  # noqa: BLE001 - evidence summary must not block compose output.
        evidence_summary = {"error": "evidence_summary_build_failed"}

    with Path(compose_json_path).open("w", encoding="utf-8") as compose_handle:
        json.dump({
            "status": "ok",
            "topic": req.topic,
            "outline": req.outline,
            "sections": result["sections"],
            "style": DocStyle().dict(),
            "kg_pack": (locals().get("kg_context") or {}).get("kg_pack"),
            "evidence_summary": evidence_summary,
            "saved_at": compose_json_path
        }, compose_handle, ensure_ascii=False, indent=2)

    output_docx = write_compose_to_docx(
        result["sections"],
        DocStyle().dict(),
        output_path="build/compose_output.docx"
    )

    return {
        "status": "ok",
        "topic": req.topic,
        "outline": req.outline,
        "sections": result["sections"],
        "style": DocStyle().dict(),
        "kg_pack": (locals().get("kg_context") or {}).get("kg_pack"),
        "saved_at": compose_json_path
    }

import json as _json

from fastapi.responses import FileResponse


@app.post("/export")
def export_doc():
    compose_json_path = "build/compose.json"
    output_path = "build/compose_output.docx"

    if not os.path.exists(compose_json_path):
        return {"error": "compose.json not found. Please run /compose first."}

    import json
    with open(compose_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    write_compose_to_docx(
        data["sections"],
        DocStyle().dict(),
        output_path=output_path
    )

    # 审计日志写入（保持与 publish 的 trace_chain 一致）
    try:
        audit_dir = Path("backend/data/audit")
        audit_dir.mkdir(parents=True, exist_ok=True)
        from backend.zhifei_autoplan.kg_store import get_active_kg as _get_active_kg
        from backend.zhifei_autoplan.tender_store import (
            load_tender_matrix as _load_tender_matrix,
        )
        ak = _get_active_kg()
        audit = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "route": "/export",
            "compose_json": compose_json_path,
            "output_docx": output_path,
            "tender_matrix_loaded": bool(_load_tender_matrix()),
            "active_kg_file": ak.get("file_name") if ak else None,
            "active_kg_sha256": ak.get("sha256") if ak else None,
        }
        with (audit_dir / "export.jsonl").open("a", encoding="utf-8") as f:
            f.write(_json.dumps(audit, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001, S110 - export audit is best-effort.
        pass

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="compose_output.docx"
    )


@app.get("/debug/project_profile_rules")
def debug_project_profile_rules():
    from backend.project_profile_engine import ProjectProfileEngine
    engine = ProjectProfileEngine()
    return engine.debug_summary()

@app.get("/debug/kg_pack")
def debug_kg_pack():
    """
    Return KG pack metadata from two perspectives:
    - current_config_pack: derived from kg_config.json + manifest hash (authoritative runtime intent)
    - last_build_pack: read from build/kg_context.json (what the last build actually used)
    - stale: True if they disagree (or if last_build exists but current_config cannot be derived)
    """
    import hashlib
    import json
    from pathlib import Path

    root_dir = Path(__file__).resolve().parent.parent  # backend/

    def _sha256_file(fp: Path) -> str:
        h = hashlib.sha256()
        with fp.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    errors = {}
    sources = {}

    # 1) current_config_pack (kg_config.json + manifest)
    current_config_pack = None
    cfg_path = root_dir / "kg_config.json"
    if not cfg_path.exists():
        errors["kg_config.json"] = "not found"
    else:
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            active = cfg.get("active_pack") if isinstance(cfg, dict) else None
            packs = cfg.get("packs") if isinstance(cfg, dict) else None
            pcfg = packs.get(active, {}) if isinstance(packs, dict) and active else {}

            base_dir = pcfg.get("base_dir") or pcfg.get("base_path") or pcfg.get("root") or "."
            pack_version = pcfg.get("pack_version") or pcfg.get("version") or active
            manifest_rel = pcfg.get("manifest") or f"{base_dir}/manifest.json"
            manifest_path = (root_dir / manifest_rel).resolve()

            manifest_exists = bool(manifest_path.exists())
            manifest_sha256 = _sha256_file(manifest_path) if manifest_exists else None

            current_config_pack = {
                "active_pack": active,
                "pack_version": pack_version,
                "base_dir": base_dir,
                "base_dir_abs": str((root_dir / base_dir).resolve()) if base_dir else str(root_dir.resolve()),
                "manifest": str(manifest_rel),
                "manifest_exists": manifest_exists,
                "manifest_sha256": manifest_sha256,
                "schema_version": pcfg.get("schema_version") if isinstance(pcfg, dict) else None,
                "created_at": pcfg.get("created_at") if isinstance(pcfg, dict) else None,
            }
            sources["current_config_pack"] = "kg_config.json+manifest"
        except (AttributeError, OSError, TypeError, UnicodeError, ValueError) as e:
            errors["current_config_pack"] = str(e)

    # 2) last_build_pack (build/kg_context.json)
    last_build_pack = None
    kc_path = root_dir / "build" / "kg_context.json"
    if kc_path.exists():
        try:
            data = json.loads(kc_path.read_text(encoding="utf-8"))
            last_build_pack = data.get("kg_pack")
            sources["last_build_pack"] = "build/kg_context.json"
        except (AttributeError, OSError, TypeError, UnicodeError, ValueError) as e:
            errors["last_build_pack"] = str(e)

    # 3) stale determination
    stale = False
    if last_build_pack is None:
        stale = False
    elif current_config_pack is None:
        stale = True
    else:
        try:
            stale = (
                current_config_pack.get("active_pack") != last_build_pack.get("active_pack")
                or current_config_pack.get("manifest_sha256") != last_build_pack.get("manifest_sha256")
            )
        except (AttributeError, TypeError):
            stale = True

    return {
        "sources": sources,
        "stale": stale,
        "current_config_pack": current_config_pack,
        "last_build_pack": last_build_pack,
        "errors": errors,
    }


@app.get("/audit")
def audit():
    from backend.audit_service import build_audit_report
    return build_audit_report()

# ============================
# Retrieve (BM25-lite + trace)
# ============================
from pydantic import BaseModel as _RetrieveBaseModel


class RetrieveRequest(_RetrieveBaseModel):
    query: str
    top_k: int = 10

@app.post("/retrieve")
def retrieve_api(req: RetrieveRequest):
    from backend.retrieve_service import retrieve
    return retrieve(req.query, top_k=req.top_k)
