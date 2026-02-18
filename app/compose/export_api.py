from fastapi import APIRouter, Query
from app.assist.smart_export import choose_export_strategy
from app.audit.m7_logger import log_export_decision
import subprocess

router = APIRouter(prefix="/compose", tags=["M6 Smart Export"])

@router.get("/export")
def compose_export(doc_type: str = Query(...), ruleset_version: str = Query(...)):
    # 1) 调用推荐，选择导出策略
    strategy = choose_export_strategy(doc_type, ruleset_version)

    # 2) 回写一条审计日志（M7）
    _log = log_export_decision(
        doc_type=doc_type,
        ruleset_version=ruleset_version,
        export_template=strategy.get("export_template"),
        postprocessors=strategy.get("postprocessors") or [],
        file_fingerprint="",      # 如有上游指纹，这里可替换
        status="ok",
        verified=True,
    )

    # 3) 返回决策结果（含选用的策略）
    # --- M7: 自动再学习 ---
    try:
        subprocess.Popen(['python', 'm6_recommend_train.py'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print('[M7] 已触发自动再训练 (m6_recommend_train.py)')
    except Exception as e:
        print('[M7] 自动再训练失败:', e)

    return {
        "status": "ok",
        "doc_type": doc_type,
        "ruleset_version": ruleset_version,
        "selected_template": strategy.get("export_template"),
        "postprocessors": strategy.get("postprocessors"),
        "audit_log": _log,   # {path, event_hash}
    }
