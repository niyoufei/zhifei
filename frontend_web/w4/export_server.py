# -*- coding: utf-8 -*-
from flask import Flask, send_file, jsonify, Response
from io import BytesIO
import zipfile, json
from pathlib import Path

app = Flask(__name__)

# CORS (ascii-only)
@app.after_request
def _add_cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp

@app.route('/export/report', methods=['OPTIONS'])
def _preflight():
    return Response(status=204)

@app.get('/ping')
def ping():
    return jsonify(ok=True, msg='w4 export server alive')

def _load_jsons():
    comp = Path('w3_compose_preview.json')
    ext  = Path('w3_extract_preview.json')
    if not comp.exists() or not ext.exists():
        return None, None
    return json.loads(comp.read_text(encoding='utf-8')), json.loads(ext.read_text(encoding='utf-8'))

def _ensure_artifacts(compose, extract):
    report = Path('w4_report.docx')
    trace  = Path('w4_trace.json')
    if not report.exists() or not trace.exists():
        return None, None
    return report, trace

@app.get('/export/report')
def export_report():
    compose, extract = _load_jsons()
    if compose is None or extract is None:
        return jsonify(ok=False, msg='Missing W3 outputs'), 400
    report, trace = _ensure_artifacts(compose, extract)
    if report is None:
        return jsonify(ok=False, msg='Missing W4 artifacts (w4_report.docx / w4_trace.json)'), 400

    mem = BytesIO()
    with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(report, arcname=report.name)
        zf.write(trace,  arcname=trace.name)
    mem.seek(0)
    resp = send_file(mem, as_attachment=True, download_name='w4_export_bundle.zip', mimetype='application/zip')
    resp.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return resp

@app.get('/page')
def page():
    return """<!doctype html><meta charset='utf-8'>
    <body style='margin:40px;font-family:system-ui,Segoe UI,Arial;'>
      <h2>W4 export test (port 5001)</h2>
      <p><a href='/export/report' download>1) Direct download w4_export_bundle.zip</a></p>
      <button id='btn' style='padding:10px 16px;border:1px solid #333;border-radius:8px;background:#fff;cursor:pointer;'>
        2) JS trigger download
      </button>
      <script>
      document.getElementById('btn').onclick = async () => {
        const r = await fetch('/export/report');
        if(!r.ok){ alert('Export failed: '+r.status); return; }
        const b = await r.blob();
        const u = URL.createObjectURL(b);
        const a = document.createElement('a');
        a.href = u; a.download = 'w4_export_bundle.zip'; a.click(); a.remove();
      };
      </script>
    </body>"""
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001)
