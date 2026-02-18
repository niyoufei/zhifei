import json
from datetime import datetime

def replay_audit(filter_type=None, start_time=None, end_time=None):
    results = []
    with open("audit_trail.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry["timestamp"])
                if start_time and ts < datetime.fromisoformat(start_time):
                    continue
                if end_time and ts > datetime.fromisoformat(end_time):
                    continue
                if filter_type and entry["event_type"] != filter_type:
                    continue
                results.append(entry)
            except Exception as e:
                print(f"❌ 无法解析行：{e}")
    return results

if __name__ == "__main__":
    logs = replay_audit(filter_type="compose_test")
    print("🔁 日志回放结果：")
    for item in logs:
        print(json.dumps(item, ensure_ascii=False, indent=2))
