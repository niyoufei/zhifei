from fastapi import APIRouter, Query, HTTPException
import os, json

router = APIRouter(prefix="/recommend", tags=["M6 Reuse"])

@router.get("/export_path")
def recommend_export_path(
    doc_type: str = Query(..., description="文档类型，如：施工组织设计"),
    ruleset_version: str = Query(..., description="规则版本号，如：v5.1.0")
):
    json_path = os.path.join("artifacts", "m6_top_paths.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="推荐数据文件不存在，请先运行训练脚本。")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    key = f"{doc_type}|||{ruleset_version}"
    if key not in data:
        raise HTTPException(status_code=404, detail=f"未找到 {key} 的推荐路径。")
    return {"recommendations": data[key]}
