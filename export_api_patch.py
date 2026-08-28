from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, JSONResponse
import json, os
from datetime import datetime
from pathlib import Path
from routes import recommend

app = FastAPI()

app.include_router(recommend.router)
EXPORT_DIR = Path(os.environ.get("ZF_EXPORT_DIR") or "artifacts/exports")

@app.get("/export")
def export_latest(response_type: str = "json"):
    """
    导出评分结果与追溯日志的综合文件。
    response_type: json / docx / pdf
    """
    score_file = Path("score_result.json")
    if not score_file.exists():
        return JSONResponse({"error": "尚未生成评分结果文件，请先运行 /score 接口。"}, status_code=404)

    with open(score_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    export_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_name = f"export_{export_time}"
    meta = {
        "export_name": export_name,
        "generated_at": export_time,
        "source": str(score_file),
        "trace_chain": ["评分模块 /score", "导出模块 /export"],
    }

    # 生成导出文件（JSON）
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EXPORT_DIR / f"{export_name}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "data": data}, f, ensure_ascii=False, indent=2)

    if response_type == "json":
        return JSONResponse({"message": "导出成功", "file": str(output_path)})
    elif response_type == "docx":
        # 保留 Word 导出钩子（M4 专业排版模块将接入）
        return JSONResponse({"message": "Word 导出功能占位，稍后集成排版模块。"})
    elif response_type == "pdf":
        return JSONResponse({"message": "PDF 导出功能占位，稍后集成排版模块。"})
    else:
        return JSONResponse({"error": "不支持的导出类型"}, status_code=400)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
