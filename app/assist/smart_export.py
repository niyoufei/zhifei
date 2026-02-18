import requests, os, json

def choose_export_strategy(doc_type: str, ruleset_version: str):
    try:
        url = "http://127.0.0.1:8000/recommend/export_path"
        r = requests.get(url, params={"doc_type": doc_type, "ruleset_version": ruleset_version}, timeout=2)
        if r.status_code == 200:
            data = r.json().get("recommendations", [])
            if data:
                best = data[0]
                path_cfg = json.loads(best["path_key"])
                print(f"[M6] 推荐导出路径：{path_cfg}")
                return path_cfg
        print("[M6] 无推荐命中，使用默认路径。")
    except Exception as e:
        print("[M6] 推荐查询失败：", e)
    return {"export_template": "default", "postprocessors": []}
