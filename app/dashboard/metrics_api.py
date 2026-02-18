
from fastapi import APIRouter
import os, csv, json, glob, time
from pathlib import Path
from datetime import datetime, timedelta
import statistics as stats

router = APIRouter(prefix="/dashboard", tags=["M8 Metrics"])

ART_TRAIN = Path("artifacts/m6_export_training.csv")
ART_TOP   = Path("artifacts/m6_top_paths.json")

def _read_training_rows():
    rows=[]
    if ART_TRAIN.exists():
        with open(ART_TRAIN, "r", encoding="utf-8") as f:
            for i, r in enumerate(csv.DictReader(f)):
                try:
                    rows.append(r)
                except: 
                    pass
    return rows

def _read_top_paths():
    if ART_TOP.exists():
        with open(ART_TOP, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _read_m7_logs():
    logs=[]
    for fp in Path("audit_logs/m7").glob("*.jsonl"):
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line: 
                    continue
                try:
                    logs.append(json.loads(line))
                except:
                    pass
    return logs

@router.get("/metrics")
def metrics():
    rows = _read_training_rows()
    top  = _read_top_paths()
    logs = _read_m7_logs()

    total = len(rows)
    succ  = sum(1 for r in rows if r.get("success_label")=="1")
    fail  = total - succ
    success_rate = (succ/total)*100 if total else None

    # 平均质量/耗时（仅统计有值的行）
    qvals = [float(r["quality_score"]) for r in rows if r.get("quality_score")]
    tvals = [float(r["time_cost_s"]) for r in rows if r.get("time_cost_s")]
    q_avg = round(sum(qvals)/len(qvals), 4) if qvals else None
    t_avg = round(sum(tvals)/len(tvals), 3) if tvals else None

    # 推荐命中率（/compose/export 里采用的路径是否是当前 top1）
    # 近似算法：比较每条 /compose/export 的 strategy 与 top_paths 对应 key
    hit_cnt=0; adopt_cnt=0
    # 构造 top1 索引
    top1_index={}
    for k, arr in top.items():
        if arr:
            top1_index[k]=arr[0].get("path_key")

    for ev in logs:
        if ev.get("route")!="/compose/export": 
            continue
        adopt_cnt += 1
        doc_type = (ev.get("context") or {}).get("doc",{}).get("type","unknown")
        rules_v  = (ev.get("context") or {}).get("ruleset_version","unknown")
        key=f"{doc_type}|||{rules_v}"
        tpl = (ev.get("export") or {}).get("template")
        post = (ev.get("export") or {}).get("postprocessors") or []
        adopted = json.dumps({"export_template": tpl, "postprocessors": post}, ensure_ascii=False, sort_keys=True)
        if top1_index.get(key)==adopted:
            hit_cnt += 1

    hit_rate = (hit_cnt/adopt_cnt)*100 if adopt_cnt else None

    # 近24小时活动
    now = datetime.utcnow()
    last24 = [ev for ev in logs if _parse_ts(ev.get("timestamp")) and (now - _parse_ts(ev["timestamp"])).total_seconds()<=24*3600]
    recent_count = len(last24)

    return {
        "artifacts": {
            "training_csv_exists": ART_TRAIN.exists(),
            "top_paths_exists": ART_TOP.exists(),
            "training_csv_mtime": ART_TRAIN.stat().st_mtime if ART_TRAIN.exists() else None,
            "top_paths_mtime": ART_TOP.stat().st_mtime if ART_TOP.exists() else None
        },
        "training": {
            "total_samples": total,
            "success": succ,
            "fail": fail,
            "success_rate_pct": round(success_rate,2) if success_rate is not None else None,
            "quality_avg": q_avg,
            "time_cost_avg_s": t_avg
        },
        "adoption": {
            "compose_export_calls": adopt_cnt,
            "top1_hit": hit_cnt,
            "top1_hit_rate_pct": round(hit_rate,2) if hit_rate is not None else None
        },
        "activity": {
            "recent_24h_events": recent_count
        },
        "top_paths": top
    }

def _parse_ts(ts):
    if not ts: return None
    try:
        # 兼容 2025-10-15T18:55:00Z
        if ts.endswith("Z"):
            from datetime import datetime
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    except:
        return None
    return None
