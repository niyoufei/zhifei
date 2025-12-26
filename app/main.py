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
# ============================
# Audit & Replay (traceability)
# ============================

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

