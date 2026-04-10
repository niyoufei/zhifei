"""Legacy local launcher shim.

Current production-like online chain runs:
    python -m uvicorn backend.app.main:app ...

This file is kept only for local historical compatibility and should not be
treated as the authoritative online entrypoint for the V2 Web UI.
"""

from fastapi import FastAPI
from export_router_clean import router as export_router
app = FastAPI()

# —— 挂载导出路由（自动生成） ——
app.include_router(export_router)

from backend.app.routers import score_router, publish_router, publish_router
app.include_router(score_router.router)
app.include_router(publish_router.router)

import uvicorn
if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
