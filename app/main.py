from fastapi import FastAPI
from app.routes import recommend
from app.compose import export_api
from app.dashboard import metrics_api

app = FastAPI(title="专业级可追溯文档自动化生成系统", version="M6")

# 注册 M6 推荐路由
app.include_router(recommend.router)
app.include_router(export_api.router)
app.include_router(metrics_api.router)

@app.get("/")
def root():
    return {"status": "ok", "service": "traceable-docs", "stage": "M6"}
