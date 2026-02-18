import os, json, hashlib, platform, datetime, uuid
from pathlib import Path

def _sha256(s: str) -> str:
    try:
        return hashlib.sha256(s.encode('utf-8')).hexdigest()
    except Exception:
        return ''

def env_info():
    import sys
    return {
        'host': platform.node(),
        'system': platform.platform(),
        'python': sys.version.split()[0],
        'app_env': os.getenv('APP_ENV','dev'),
        'model_hint': os.getenv('OPENAI_CODE_MODEL','gpt-4o-mini'),
    }

def write_export_log(event: str, inputs: dict=None, outputs: dict=None, meta: dict=None) -> str:
    inputs, outputs, meta = inputs or {}, outputs or {}, meta or {}
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    day = datetime.datetime.now().strftime('%Y%m%d')
    base = Path('logs/exports')/day
    base.mkdir(parents=True, exist_ok=True)
    rid = f"{ts}-{uuid.uuid4().hex[:8]}"
    payload = {'inputs':inputs,'outputs':outputs,'meta':meta}
    data = {
        'rid': rid,
        'ts': ts,
        'event': event,
        'env': env_info(),
        'payload': payload,
        'payload_sha256': _sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True)),
    }
    p = base / f"{rid}.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(p)
