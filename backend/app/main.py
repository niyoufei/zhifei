from fastapi import FastAPI, BackgroundTasks, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, json
from pathlib import Path
from datetime import datetime

from compose_engine import Composer
from utils_write_docx import write_compose_to_docx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers: ingest/retrieve/publish/score
from .routers.ingest import router as ingest_router
from .routers.retrieve import router as retrieve_router
from .routers.publish_router import router as publish_router
from .routers.score_router import router as score_router
from .routers.zhifei_autoplan import router as zhifei_autoplan_router
from .routers.zhifei_autoplan_v2 import router as zhifei_autoplan_v2_router
from .routers.actions_bridge import router as actions_bridge_router
from .routers.auth import router as auth_router

app.include_router(ingest_router)
app.include_router(retrieve_router)
app.include_router(publish_router)
app.include_router(score_router)
app.include_router(zhifei_autoplan_router)
app.include_router(zhifei_autoplan_v2_router)
app.include_router(actions_bridge_router)
app.include_router(auth_router)


@app.get("/health")
def health():
    cfg_path = Path("backend/data/autoplan/config.json")
    cfg_mtime = cfg_path.stat().st_mtime if cfg_path.exists() else None
    cfg_version = None
    cfg_version_auto = None
    try:
        if cfg_path.exists():
            cfg_version = json.loads(cfg_path.read_text(encoding="utf-8")).get("config_version")
    except Exception:
        cfg_version = None
    if cfg_mtime is not None:
        try:
            import datetime as _dt
            cfg_version_auto = _dt.datetime.fromtimestamp(cfg_mtime).strftime("%Y-%m-%d")
        except Exception:
            cfg_version_auto = None
    audit_ready = False
    try:
        audit_dir = Path("backend/data/audit")
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_ready = audit_dir.exists() and audit_dir.is_dir()
    except Exception:
        pass
    return {
        "ok": True,
        "version": "autoplan-0.1.0",
        "service": "文档生成系统",
        "config_mtime": cfg_mtime,
        "config_version": cfg_version,
        "config_version_auto": cfg_version_auto,
        "audit_ready": audit_ready,
    }


@app.get("/capabilities")
def capabilities():
    from backend.zhifei_autoplan.kg_store import get_active_kg
    from backend.zhifei_autoplan.tender_store import load_tender_matrix
    from backend.zhifei_autoplan.boq_store import load_boq_data
    from pathlib import Path
    from backend.app.routers.zhifei_autoplan import _job_list_default_fields, _job_list_field_alias
    roles_cfg = Path("backend/data/autoplan/agent_roles.json")
    cfg_version = None
    cfg_version_auto = None
    try:
        cfg_path = Path("backend/data/autoplan/config.json")
        if cfg_path.exists():
            cfg_version = json.loads(cfg_path.read_text(encoding="utf-8")).get("config_version")
    except Exception:
        cfg_version = None
    if cfg_path.exists():
        try:
            import datetime as _dt
            cfg_version_auto = _dt.datetime.fromtimestamp(cfg_path.stat().st_mtime).strftime("%Y-%m-%d")
        except Exception:
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
        "tender_matrix_loaded": bool(load_tender_matrix()),
        "boq_loaded": bool(load_boq_data()),
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
            "field_alias": {k: sorted(list(v)) for k, v in _job_list_field_alias().items()},
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
    from backend.zhifei_autoplan.utils.llm_client import LLMClient
    from backend.app.routers.zhifei_autoplan import _job_list_default_fields, _job_list_field_alias
    defaults = LLMClient.load_defaults()
    cfg_version = None
    cfg_version_auto = None
    try:
        cfg_path = Path("backend/data/autoplan/config.json")
        if cfg_path.exists():
            cfg_version = json.loads(cfg_path.read_text(encoding="utf-8")).get("config_version")
    except Exception:
        cfg_version = None
    if cfg_path.exists():
        try:
            import datetime as _dt
            cfg_version_auto = _dt.datetime.fromtimestamp(cfg_path.stat().st_mtime).strftime("%Y-%m-%d")
        except Exception:
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
            "field_alias": {k: sorted(list(v)) for k, v in _job_list_field_alias().items()},
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
        except Exception:
            cfg = {}
    cfg["config_version"] = version or datetime.now().strftime("%Y-%m-%d")
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        audit_dir = Path("backend/data/audit")
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_path = audit_dir / "config.jsonl"
        record = {
            "ts": datetime.utcnow().isoformat(),
            "action": "config_version_update",
            "config_version": cfg["config_version"],
        }
        audit_path.write_text(
            (audit_path.read_text(encoding="utf-8") if audit_path.exists() else "")
            + json.dumps(record, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass
    return {"ok": True, "config_version": cfg["config_version"]}


@app.get("/model_health")
def model_health():
    """
    返回模型配置是否完整（不调用外部API，避免消耗）
    """
    from backend.zhifei_autoplan.utils.llm_client import LLMClient
    defaults = LLMClient.load_defaults()
    return {
        "ok": True,
        "default_provider": defaults.get("default_provider"),
        "default_model": defaults.get("default_model"),
        "configured": bool(defaults.get("default_provider") and defaults.get("default_model")),
    }


@app.get("/model_ping")
def model_ping():
    """
    触发一次最小模型调用（需要已配置默认模型与密钥）
    """
    from backend.zhifei_autoplan.utils.llm_client import LLMClient
    defaults = LLMClient.load_defaults()
    provider = defaults.get("default_provider")
    model = defaults.get("default_model")
    api_key = os.environ.get("ZF_DEFAULT_API_KEY")
    if not provider or not model or not api_key:
        return {"ok": False, "error": "missing provider/model/api_key"}
    try:
        import asyncio
        llm = LLMClient(provider=provider, model=model, api_key=api_key)
        resp = asyncio.run(llm.complete("ping"))
        return {"ok": True, "provider": provider, "model": model, "resp": resp}
    except Exception as e:
        return {"ok": False, "error": repr(e)}

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
    import os as _os, json as _json
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
            try:
                setattr(req, 'topic', _req_topic)
            except Exception:
                pass
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
    except Exception as _e:
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
    import os as _os_up, json as _json_up
    _os_up.makedirs('build', exist_ok=True)
    with open('build/region_upgrade.json', 'w', encoding='utf-8') as _f_up:
        _json_up.dump(upgrade, _f_up, ensure_ascii=False, indent=2)
    # --------------------------------------------------------------------

    # --- PreCheck Guard: evaluate payload + project_profile (before compose) ---
    # --- KG Context: resolve domain + select base packs (traceable) ---
    from backend.kg_context_service import build_kg_context
    kg_context = build_kg_context(payload, project_profile)
    import os as _os_kg, json as _json_kg
    _os_kg.makedirs('build', exist_ok=True)
    with open('build/kg_context.json', 'w', encoding='utf-8') as _f_kg:
        _json_kg.dump(kg_context, _f_kg, ensure_ascii=False, indent=2)
    # ----------------------------------------------------------------------
    # enrich project_profile (topic/domain_key/region_key) for traceability
    try:
        import os as _os_pp, json as _json_pp
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
    except Exception:
        pass
    from backend.precheck_guard_service import run_precheck_guard
    precheck = run_precheck_guard(payload, project_profile)
    import os as _os2, json as _json2
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
    try:
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
    except Exception as _e:
        # keep original result on any failure
        pass
    # ----------------------------------------------

    # --- AI 正文生成（可选，优先使用 /autoplan/generate 的结果） ---
    try:
        from pathlib import Path as _Path
        _auto_json = _Path("build") / "autoplan_generated.json"
        _auto_enabled = os.environ.get("ZF_AUTOPLAN_AUTO", "0") == "1"
        _auto_provider = os.environ.get("ZF_DEFAULT_PROVIDER")
        _auto_model = os.environ.get("ZF_DEFAULT_MODEL")
        _auto_key = os.environ.get("ZF_DEFAULT_API_KEY")
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
        elif _auto_enabled and _auto_provider and _auto_model:
            # 若未生成过 AI 正文，则自动触发生成（需配置默认模型）
            def _bg_generate():
                from backend.zhifei_autoplan.orchestrator import run_autoplan as _run_autoplan
                from backend.zhifei_autoplan.exporter import export_autoplan_docx_from_file as _export_autoplan_docx
                import asyncio as _asyncio
                payload = {
                    "topic": req.topic,
                    "outline": req.outline,
                    "requirements": [],
                    "provider": _auto_provider,
                    "model": _auto_model,
                    "api_key": _auto_key,
                    "dry_run": False if _auto_key else True,
                    "generate_images": True,
                }
                _auto = _asyncio.run(_run_autoplan(payload))
                _auto_json.write_text(_json.dumps({"variants": [_auto]}, ensure_ascii=False, indent=2), encoding="utf-8")
                _export_autoplan_docx(str(_auto_json), str(_Path("build") / "autoplan_generated.docx"))
            background_tasks.add_task(_bg_generate)
    except Exception:
        pass

    # 证据链摘要（写入 compose.json 便于离线复核）
    try:
        from backend.zhifei_autoplan.kg_store import get_active_kg as _get_active_kg
        from backend.zhifei_autoplan.tender_store import load_tender_matrix as _load_tender_matrix
        from backend.zhifei_autoplan.boq_store import load_boq_data as _load_boq_data
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
    except Exception:
        evidence_summary = {"error": "evidence_summary_build_failed"}

    json.dump({
        "status": "ok",
        "topic": req.topic,
        "outline": req.outline,
        "sections": result["sections"],
        "style": DocStyle().dict(),
        "kg_pack": (locals().get("kg_context") or {}).get("kg_pack"),
        "evidence_summary": evidence_summary,
        "saved_at": compose_json_path
    }, open(compose_json_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

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

from fastapi.responses import FileResponse
from pathlib import Path
import json as _json

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
        from backend.zhifei_autoplan.tender_store import load_tender_matrix as _load_tender_matrix
        from backend.zhifei_autoplan.kg_store import get_active_kg as _get_active_kg
        ak = _get_active_kg()
        audit = {
            "ts": datetime.now().isoformat(),
            "route": "/export",
            "compose_json": compose_json_path,
            "output_docx": output_path,
            "tender_matrix_loaded": bool(_load_tender_matrix()),
            "active_kg_file": ak.get("file_name") if ak else None,
            "active_kg_sha256": ak.get("sha256") if ak else None,
        }
        with (audit_dir / "export.jsonl").open("a", encoding="utf-8") as f:
            f.write(_json.dumps(audit, ensure_ascii=False) + "\n")
    except Exception:
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
    import json
    import hashlib
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
        except Exception as e:
            errors["current_config_pack"] = str(e)

    # 2) last_build_pack (build/kg_context.json)
    last_build_pack = None
    kc_path = root_dir / "build" / "kg_context.json"
    if kc_path.exists():
        try:
            data = json.loads(kc_path.read_text(encoding="utf-8"))
            last_build_pack = data.get("kg_pack")
            sources["last_build_pack"] = "build/kg_context.json"
        except Exception as e:
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
        except Exception:
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
