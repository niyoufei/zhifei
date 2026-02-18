import json
import hashlib
from datetime import datetime

def log_audit(event_type, input_data, output_data, model_version):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "input_hash": hashlib.sha256(json.dumps(input_data, sort_keys=True).encode()).hexdigest(),
        "output_hash": hashlib.sha256(json.dumps(output_data, sort_keys=True).encode()).hexdigest(),
        "model_version": model_version
    }
    with open("audit_trail.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    return log_entry
