#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
M6 - Export Path Reuse & Recommendation (v0.1)
从审计日志中学习“导出路径”成功经验，产出两个工件：
1) artifacts/m6_export_training.csv      —— 可追溯训练样本（特征 + 标签 + 证据指针）
2) artifacts/m6_top_paths.json           —— 按(doc_type, ruleset_version)聚合的最佳导出路径候选
脚本设计为纯标准库依赖，可直接运行；日志目录可通过环境变量 AUDIT_LOG_DIR 覆盖。
"""

import os, json, csv, hashlib, datetime, glob
from collections import defaultdict, Counter

LOG_DIR = os.environ.get("AUDIT_LOG_DIR", "./audit_logs")
OUT_DIR = "./artifacts"
os.makedirs(OUT_DIR, exist_ok=True)

def iter_logs(path):
    if not os.path.isdir(path):
        print(f"[WARN] 日志目录不存在：{path}")
        return
    for fp in glob.glob(os.path.join(path, "**/*"), recursive=True):
        if not os.path.isfile(fp): 
            continue
        if fp.endswith(".jsonl"):
            with open(fp, "r", encoding="utf-8") as f:
                for line in f:
                    line=line.strip()
                    if not line: 
                        continue
                    try:
                        obj=json.loads(line)
                        obj["_log_file"]=fp
                        yield obj
                    except Exception as e:
                        print(f"[SKIP] JSONL 解析失败: {fp}: {e}")
        elif fp.endswith(".json"):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    obj=json.load(f)
                    if isinstance(obj, list):
                        for it in obj:
                            it["_log_file"]=fp
                            yield it
                    elif isinstance(obj, dict):
                        obj["_log_file"]=fp
                        yield obj
            except Exception as e:
                print(f"[SKIP] JSON 解析失败: {fp}: {e}")

def norm_str(x, default=""):
    if x is None: return default
    if isinstance(x, (dict, list)):
        try:
            return json.dumps(x, ensure_ascii=False, sort_keys=True)
        except:
            return str(x)
    return str(x)

def dig(d, *keys, default=None):
    cur=d
    for k in keys:
        if not isinstance(cur, dict): 
            return default
        cur=cur.get(k, default)
    return cur

def to_bool(v):
    if isinstance(v, bool): return v
    if isinstance(v, (int, float)): return v!=0
    if isinstance(v, str): 
        return v.lower() in {"1","true","yes","y","ok"}
    return False

def safe_float(v, default=None):
    try:
        return float(v)
    except:
        return default

def feature_row(ev):
    """抽取导出相关的可学习特征"""
    # 关键维度（按你的系统习惯可调整字段名）
    route       = dig(ev,"route") or dig(ev,"meta","route")
    if route not in ("/export","export","/compose/export","compose.export"):
        return None  # 只学习导出阶段
    
    verified    = to_bool(dig(ev,"verified")) or to_bool(dig(ev,"result","verified"))
    status      = norm_str(dig(ev,"status") or dig(ev,"result","status") or "")
    quality     = safe_float(dig(ev,"metrics","quality_score"), None)
    time_cost_s = safe_float(dig(ev,"metrics","time_cost_s"), None)

    # 输入侧/上下文特征
    doc_type    = norm_str(dig(ev,"context","doc","type") or dig(ev,"input","doc_type") or "unknown")
    page_cnt    = safe_float(dig(ev,"context","doc","page_count"), None)
    rules_ver   = norm_str(dig(ev,"context","ruleset_version") or dig(ev,"rules","version") or "unknown")
    rules_hit   = safe_float(dig(ev,"metrics","rules_hit_count"), None)
    rag_cov     = safe_float(dig(ev,"metrics","rag_coverage"), None)  # 命中率/覆盖度(0~1)

    # 导出路径（我们要学习的“策略”）
    export_tpl  = norm_str(dig(ev,"export","template") or dig(ev,"params","export_template") or "default")
    postprocs   = dig(ev,"export","postprocessors") or dig(ev,"params","postprocessors") or []
    postprocs   = postprocs if isinstance(postprocs,list) else [postprocs]
    postprocs_s = norm_str(postprocs,"[]")

    # 证据与可追溯
    ev_hash     = dig(ev,"hash") or dig(ev,"meta","hash")
    model_ver   = norm_str(dig(ev,"model","name") or dig(ev,"model","version"))
    ts          = dig(ev,"timestamp") or dig(ev,"time") or ""
    log_file    = ev.get("_log_file","")
    file_fprint = norm_str(dig(ev,"context","doc","fingerprint") or dig(ev,"input","file_digest") or "")

    # 标签：导出成功的“确定性”定义（可按需要收紧）
    success = (
        verified and 
        (status in ("ok","success","done","succeeded")) and 
        (quality is None or quality>=0.8)
    )

    # path_key 用于统计算法：同类文档下哪条“导出路径”最稳
    path_key = json.dumps({
        "export_template": export_tpl,
        "postprocessors":  postprocs,
    }, ensure_ascii=False, sort_keys=True)

    return {
        "timestamp": ts,
        "route": route,
        "doc_type": doc_type,
        "page_count": page_cnt,
        "ruleset_version": rules_ver,
        "rules_hit_count": rules_hit,
        "rag_coverage": rag_cov,
        "export_template": export_tpl,
        "postprocessors": postprocs_s,
        "status": status,
        "verified": str(bool(verified)),
        "quality_score": quality,
        "time_cost_s": time_cost_s,
        "model_version": model_ver,
        "doc_fingerprint": file_fprint,
        "event_hash": ev_hash or "",
        "log_file": log_file,
        "success_label": "1" if success else "0",
        "path_key": path_key,
    }

def main():
    rows=[]
    for ev in iter_logs(LOG_DIR):
        r=feature_row(ev)
        if r: rows.append(r)

    if not rows:
        print("[M6] 未从日志中解析到导出事件（/export）。请确认日志目录与格式。")
        return

    # 写出训练样本（CSV，便于审阅/溯源）
    csv_path = os.path.join(OUT_DIR,"m6_export_training.csv")
    fieldnames = list(rows[0].keys())
    with open(csv_path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows: w.writerow(r)

    # 计算“最佳导出路径”候选：在 (doc_type, ruleset_version) 条件下，
    #   以成功次数优先；并用质量分与耗时作为加权因子进行排序打分。
    buckets=defaultdict(list)
    for r in rows:
        key=(r["doc_type"], r["ruleset_version"])
        buckets[key].append(r)

    def score_group(items):
        # 统计每条 path_key 的成功/失败与质量、耗时
        stat=defaultdict(lambda: {"ok":0,"fail":0,"qsum":0.0,"qcnt":0,"tsum":0.0,"tcnt":0})
        for it in items:
            pk=it["path_key"]
            if it["success_label"]=="1":
                stat[pk]["ok"]+=1
            else:
                stat[pk]["fail"]+=1
            q=it["quality_score"]
            if isinstance(q,(int,float)):
                stat[pk]["qsum"]+=q; stat[pk]["qcnt"]+=1
            t=it["time_cost_s"]
            if isinstance(t,(int,float)):
                stat[pk]["tsum"]+=t; stat[pk]["tcnt"]+=1

        ranked=[]
        for pk, s in stat.items():
            ok, fail = s["ok"], s["fail"]
            qavg = (s["qsum"]/s["qcnt"]) if s["qcnt"]>0 else None
            tavg = (s["tsum"]/s["tcnt"]) if s["tcnt"]>0 else None

            # 组合评分（可替换为更复杂的策略）：成功优先，其次质量，最后耗时
            # 为避免除零，用 +1 平滑；耗时越低越好
            score = (ok*10) - (fail*3)
            if qavg is not None: score += qavg*2
            if tavg is not None: score += max(0, 30.0 - min(30.0, tavg)) * 0.1

            ranked.append({
                "path_key": pk,
                "success": ok,
                "fail": fail,
                "quality_avg": qavg,
                "time_avg_s": tavg,
                "score": round(score,3),
            })

        ranked.sort(key=lambda x: (-x["score"], -x["success"], x["time_avg_s"] if x["time_avg_s"] is not None else 1e9))
        return ranked

    result={}
    for key, items in buckets.items():
        ranked = score_group(items)
        # 仅保留 Top-3 候选，便于在导出时做“智能推荐+回退”
        result[f"{key[0]}|||{key[1]}"] = ranked[:3]

    out_json = os.path.join(OUT_DIR,"m6_top_paths.json")
    with open(out_json,"w",encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("[M6] 已生成：")
    print(" -", csv_path)
    print(" -", out_json)
    # 简要可视化摘要
    total=len(rows)
    pos=sum(1 for r in rows if r["success_label"]=="1")
    neg=total-pos
    print(f"[M6] 样本总数={total}，成功={pos}，失败={neg}，成功率={(pos/max(1,total))*100:.2f}%")

if __name__=="__main__":
    main()
