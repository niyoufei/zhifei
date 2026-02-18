from fastapi import APIRouter
from pydantic import BaseModel
from backend.assistants.codex_agent import CodexAgent

router = APIRouter()
_agent = CodexAgent()

class SuggestReq(BaseModel):
    code: str
    goal: str

@router.get("/codex/selftest")
def codex_selftest():
    mode = "online" if _agent.online else "offline"
    demo = _agent.suggest_patch("def hello():\n    prin('hi')", "修复语法错误并返回'hi'")
    return {"ok": True, "mode": mode, "demo": demo[:4000]}

@router.post("/codex/suggest")
def codex_suggest(req: SuggestReq):
    return {"ok": True, "result": _agent.suggest_patch(req.code, req.goal)}