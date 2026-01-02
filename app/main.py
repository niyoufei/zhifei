from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, json

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
def compose(req: ComposeRequest):
    # --- ProjectProfile: build for traceability & downstream rules ---
    from project_profile_service import generate_project_profile
    payload = req.dict() if hasattr(req, 'dict') else req.model_dump()
    project_profile = generate_project_profile(payload)
    import os as _os, json as _json
    # --- Compose Engine: build sections using KG context (demo) ---
    try:
        from compose_engine_service import build_sections_from_kg
        _req_outline = getattr(req, 'outline', None)
        _req_topic = getattr(req, 'topic', None)
        # sanitize topic: strip Hefei suffixes to avoid leaking city name
        if isinstance(_req_topic, str):
            _req_topic = _req_topic.replace('（合肥）','').replace('(合肥)','')
            _req_topic = _req_topic.replace('（安徽合肥）','').replace('(安徽合肥)','')
            _req_topic = _req_topic.strip()
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
    from region_upgrade_service import resolve_region_upgrade
    upgrade = resolve_region_upgrade(payload, project_profile)
    import os as _os_up, json as _json_up
    _os_up.makedirs('build', exist_ok=True)
    with open('build/region_upgrade.json', 'w', encoding='utf-8') as _f_up:
        _json_up.dump(upgrade, _f_up, ensure_ascii=False, indent=2)
    # --------------------------------------------------------------------

    # --- PreCheck Guard: evaluate payload + project_profile (before compose) ---
    # --- KG Context: resolve domain + select base packs (traceable) ---
    from kg_context_service import build_kg_context
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
        _topic = None
        if isinstance(project_profile, dict):
            _topic = project_profile.get('topic')
        if not _topic:
            _topic = payload.get('topic') if isinstance(payload, dict) else None
        if not _topic:
            _topic = _req_topic
        if isinstance(project_profile, dict):
            if isinstance(_topic, str):
                _topic = _topic.replace('（合肥）','').replace('(合肥)','')
                _topic = _topic.replace('（安徽合肥）','').replace('(安徽合肥)','')
                _topic = _topic.strip()
            project_profile['topic'] = _topic
            if isinstance(kg_context, dict):
                _dr = kg_context.get(domain_resolution)
                _dk = None
                if isinstance(_dr, dict):
                    _dk = _dr.get(domain_key)
                if not _dk:
                    _dk = kg_context.get(domain_key)
                if not _dk:
                    _dk = decoration
                project_profile[domain_key] = project_profile.get(domain_key) or _dk
            if isinstance(upgrade, dict) and upgrade.get('region_key'):
                project_profile['region_key'] = project_profile.get('region_key') or upgrade.get('region_key')
            with open('build/project_profile.json', 'w', encoding='utf-8') as _f_pp:
                _json_pp.dump(project_profile, _f_pp, ensure_ascii=False, indent=2)
    except Exception:
        pass
    from precheck_guard_service import run_precheck_guard
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
        from compose_engine_service import build_sections_from_kg
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

    json.dump({
        "status": "ok",
        "topic": req.topic,
        "outline": req.outline,
        "sections": result["sections"],
        "style": DocStyle().dict(),
        "kg_pack": (locals().get("kg_context") or {}).get("kg_pack"),
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

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="compose_output.docx"
    )


@app.get("/debug/project_profile_rules")
def debug_project_profile_rules():
    from project_profile_engine import ProjectProfileEngine
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
    from audit_service import build_audit_report
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
    from retrieve_service import retrieve
    return retrieve(req.query, top_k=req.top_k)

