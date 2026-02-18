from pathlib import Path
p = Path("backend/app/main.py")
s = p.read_text(encoding="utf-8")

if "from .routers import ingest_router, retrieve_router" not in s:
    if "from .routers import ingest_router" in s:
        s = s.replace("from .routers import ingest_router",
                      "from .routers import ingest_router, retrieve_router")
    else:
        s = "from .routers import ingest_router, retrieve_router\n" + s

if "app.include_router(retrieve_router" not in s:
    s = s.replace(
        'app.include_router(ingest_router, prefix="/ingest", tags=["文档解析"])',
        'app.include_router(ingest_router, prefix="/ingest", tags=["文档解析"])\n'
        'app.include_router(retrieve_router, prefix="/retrieve", tags=["检索"])'
    )

p.write_text(s, encoding="utf-8")
print("✅ /retrieve 已注册完成")
