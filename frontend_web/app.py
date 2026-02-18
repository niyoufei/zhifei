from w4.export_report import register_export_report
import os, sqlite3, hashlib, secrets, datetime, subprocess
from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory, session
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIRS = {
    "tender_docs": os.path.join(BASE_DIR, "uploads", "tender_docs"),
    "clarifications": os.path.join(BASE_DIR, "uploads", "clarifications"),
    "project_files": os.path.join(BASE_DIR, "uploads", "project_files"),
}
ALLOWED = {".doc",".docx",".xls",".xlsx",".pdf",".ppt",".pptx",".jpg",".jpeg",".png",".dxf",".dwg"}

app = Flask(
    __name__,
    static_folder='static',
    static_url_path='/static',__name__)
app.secret_key = os.environ.get("TDOCSYS_KEY", secrets.token_hex(16))
DB = os.path.join(BASE_DIR, "users.db")

def init_db():
    if not os.path.exists(DB):
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, pw_hash TEXT)")
        def h(p): return hashlib.sha256(p.encode("utf-8")).hexdigest()
        c.execute("INSERT INTO users(username,pw_hash) VALUES(?,?)", ("admin", h("Admin123!")))
        c.execute("INSERT INTO users(username,pw_hash) VALUES(?,?)", ("user",  h("User123!")))
        conn.commit(); conn.close()
init_db()

def check_login(u, p):
    h = hashlib.sha256(p.encode("utf-8")).hexdigest()
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT pw_hash FROM users WHERE username=?", (u,))
    row = c.fetchone(); conn.close()
    return bool(row and row[0] == h)

def allowed_file(fname): return os.path.splitext(fname.lower())[1] in ALLOWED

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","")
        if check_login(u,p):
            session["user"]=u
            return redirect(url_for("index"))
        flash("账号或密码错误")
    return render_template("login.html")

@app.route("/logout", endpoint="logout")
def logout():
    session.clear(); return redirect(url_for("login"))

def ensure_login(): return "user" in session

@app.route("/index", methods=["GET","POST"])
def index():
    if not ensure_login(): return redirect(url_for("login"))
    if request.method=="POST" and request.form.get("action")=="generate":
        fmt = {
          "line_spacing_pt":22,
          "margins_cm":{"top":2.5,"left":2.0,"right":2.0,"bottom":2.0},
          "font":"宋体","title_size":"三号","body_size":"四号",
          "first_line_indent_chars":2,
          "chapter_pages":request.form.get("chapter_pages","").strip()
        }
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(BASE_DIR, "..", "deliveries", "web_batches", session["user"], ts)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir,"_params.txt"),"w",encoding="utf-8") as f: f.write(str(fmt))
        flash("参数已保存（下一步接入 Word 生成引擎与下载）。")
        return redirect(url_for("index"))
    return render_template("index.html", user=session["user"])

def save_upload(category, file):
    fname = secure_filename(file.filename)
    ext = os.path.splitext(fname)[1].lower()
    if not allowed_file(fname): raise ValueError("不支持的文件类型")
    os.makedirs(UPLOAD_DIRS[category], exist_ok=True)
    path = os.path.join(UPLOAD_DIRS[category], fname)
    file.save(path)
    if ext == ".dwg":
        try:
            tmpdxf = os.path.join(UPLOAD_DIRS[category], os.path.splitext(fname)[0]+".dxf")
            subprocess.run(["dwg2dxf", path, tmpdxf], check=True)
        except Exception as e:
            app.logger.warning("DWG→DXF 转换失败：%s", e)
    return path

@app.post("/upload/<category>")
def upload(category):
    if not ensure_login(): return redirect(url_for("login"))
    if category not in UPLOAD_DIRS: flash("未知上传入口"); return redirect(url_for("index"))
    f = request.files.get("file")
    if not f or f.filename=="": flash("未选择文件"); return redirect(url_for("index"))
    try: save_upload(category, f); flash(f"{f.filename} 已上传到 {category}")
    except Exception as e: flash(f"上传失败：{e}")
    return redirect(url_for("index"))

@app.get("/download/<path:filename>")
def download(filename):
    root = os.path.join(BASE_DIR, "..", "deliveries")
    return send_from_directory(root, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)

@app.route("/")
def home():
    return "<h2>✅ Traceable DocSys 启动成功</h2><p>Flask 已正常运行。</p>"

# ---- W3 hotfix: register upload endpoint ----
try:
    app.add_url_rule('/upload/<category>', endpoint='upload', view_func=upload, methods=['POST'])
except Exception:
    pass
# ---- end hotfix ----


# ==== W3 Upload Batch Endpoint ====
from pathlib import Path
from flask import request, jsonify
from w3.ingest.ingest_utils import save_file

UPLOAD_BASE = Path("uploads")

def upload_batch():
    """
    批量上传端点：
      - form 字段：files (可多选)、category(可选：tender/qa/attachments等)
      - 返回：每个文件的保存信息与类型判断结果
    """
    files = request.files.getlist("files")
    category = request.form.get("category","misc")
    if not files:
        return jsonify({"ok": False, "msg": "no files"}), 400
    results = []
    for f in files:
        try:
            meta = save_file(f, UPLOAD_BASE, category)
            results.append({"ok": True, **meta})
        except Exception as e:
            results.append({"ok": False, "name": getattr(f, "filename", "unnamed"), "error": str(e)})
    return jsonify({"ok": True, "count": len(results), "category": category, "results": results})

# 将端点注册为 /upload/batch
try:
    app.add_url_rule("/upload/batch", endpoint="upload_batch", view_func=upload_batch, methods=["POST"])
except Exception:
    pass
# ==================================
