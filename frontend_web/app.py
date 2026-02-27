import datetime
import hashlib
import os
import secrets
import sqlite3
import subprocess
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

try:
    from w4.export_report import register_export_report
except Exception:
    register_export_report = None

try:
    from w3.ingest.ingest_utils import save_file as ingest_save_file
except Exception:
    ingest_save_file = None


BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIRS = {
    "tender_docs": os.path.join(BASE_DIR, "uploads", "tender_docs"),
    "clarifications": os.path.join(BASE_DIR, "uploads", "clarifications"),
    "project_files": os.path.join(BASE_DIR, "uploads", "project_files"),
    "site_photos": os.path.join(BASE_DIR, "uploads", "site_photos"),
    "misc": os.path.join(BASE_DIR, "uploads", "misc"),
}
ALLOWED = {".doc", ".docx", ".xls", ".xlsx", ".pdf", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".dxf", ".dwg"}
CATEGORY_ALIASES = {
    "tender": "tender_docs",
    "tender_docs": "tender_docs",
    "qa": "clarifications",
    "clarifications": "clarifications",
    "attachments": "project_files",
    "project_files": "project_files",
    "photos": "site_photos",
    "site_photos": "site_photos",
    "misc": "misc",
}

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = os.environ.get("TDOCSYS_KEY", secrets.token_hex(16))

DB = os.path.join(BASE_DIR, "users.db")
BYPASS_LOGIN = str(os.environ.get("TDOCSYS_BYPASS_LOGIN", "1")).strip().lower() in {"1", "true", "yes", "on"}
LOCAL_USER = str(os.environ.get("TDOCSYS_LOCAL_USER", "local_user")).strip() or "local_user"


def _hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def init_db() -> None:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, pw_hash TEXT)")
    c.execute("SELECT 1 FROM users WHERE username=?", ("admin",))
    if not c.fetchone():
        c.execute("INSERT INTO users(username,pw_hash) VALUES(?,?)", ("admin", _hash_password("Admin123!")))
    c.execute("SELECT 1 FROM users WHERE username=?", ("user",))
    if not c.fetchone():
        c.execute("INSERT INTO users(username,pw_hash) VALUES(?,?)", ("user", _hash_password("User123!")))
    conn.commit()
    conn.close()


init_db()


def check_login(username: str, password: str) -> bool:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT pw_hash FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0] == _hash_password(password))


def allowed_file(fname: str) -> bool:
    return os.path.splitext(fname.lower())[1] in ALLOWED


def ensure_login() -> bool:
    if "user" in session:
        return True
    if BYPASS_LOGIN:
        session["user"] = LOCAL_USER
        return True
    return False


def _resolve_category(raw: str) -> str:
    key = str(raw or "misc").strip().lower()
    return CATEGORY_ALIASES.get(key, "misc")


def save_upload(category: str, file_obj) -> str:
    if category not in UPLOAD_DIRS:
        raise ValueError("未知上传入口")
    fname = secure_filename(file_obj.filename or "")
    if not fname:
        raise ValueError("空文件名")
    if not allowed_file(fname):
        raise ValueError("不支持的文件类型")

    os.makedirs(UPLOAD_DIRS[category], exist_ok=True)
    path = os.path.join(UPLOAD_DIRS[category], fname)
    file_obj.save(path)

    ext = os.path.splitext(fname)[1].lower()
    if ext == ".dwg":
        try:
            tmpdxf = os.path.join(UPLOAD_DIRS[category], os.path.splitext(fname)[0] + ".dxf")
            subprocess.run(["dwg2dxf", path, tmpdxf], check=True)
        except Exception as e:
            app.logger.warning("DWG→DXF 转换失败：%s", e)
    return path


@app.route("/", methods=["GET", "POST"])
def login():
    if BYPASS_LOGIN:
        session["user"] = session.get("user") or LOCAL_USER
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if check_login(username, password):
            session["user"] = username
            return redirect(url_for("index"))
        flash("账号或密码错误")
    return render_template("login.html")


@app.route("/logout", endpoint="logout")
def logout():
    session.clear()
    if BYPASS_LOGIN:
        return redirect(url_for("index"))
    return redirect(url_for("login"))


@app.route("/index", methods=["GET", "POST"])
def index():
    if not ensure_login():
        return redirect(url_for("login"))

    if request.method == "POST" and request.form.get("action") == "generate":
        fmt = {
            "line_spacing_pt": 22,
            "margins_cm": {"top": 2.5, "left": 2.0, "right": 2.0, "bottom": 2.0},
            "font": "宋体",
            "title_size": "三号",
            "body_size": "四号",
            "first_line_indent_chars": 2,
            "chapter_pages": request.form.get("chapter_pages", "").strip(),
        }
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(BASE_DIR, "..", "deliveries", "web_batches", session["user"], ts)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "_params.txt"), "w", encoding="utf-8") as f:
            f.write(str(fmt))
        flash("参数已保存（下一步接入 Word 生成引擎与下载）。")
        return redirect(url_for("index"))

    return render_template("index.html", user=session["user"], bypass_login=BYPASS_LOGIN)


@app.post("/upload/<category>")
def upload(category):
    if not ensure_login():
        return redirect(url_for("login"))
    mapped = _resolve_category(category)
    f = request.files.get("file")
    if not f or not f.filename:
        flash("未选择文件")
        return redirect(url_for("index"))
    try:
        save_upload(mapped, f)
        flash(f"{f.filename} 已上传到 {mapped}")
    except Exception as e:
        flash(f"上传失败：{e}")
    return redirect(url_for("index"))


@app.post("/upload/batch")
def upload_batch():
    if not ensure_login():
        return redirect(url_for("login"))

    files = request.files.getlist("files")
    mapped = _resolve_category(request.form.get("category", "misc"))
    if not files:
        return jsonify({"ok": False, "msg": "no files"}), 400

    results = []
    for f in files:
        try:
            if ingest_save_file is not None:
                meta = ingest_save_file(f, Path(BASE_DIR) / "uploads", mapped)
                results.append({"ok": True, **meta})
            else:
                path = save_upload(mapped, f)
                results.append({"ok": True, "name": f.filename, "path": path, "category": mapped})
        except Exception as e:
            results.append({"ok": False, "name": getattr(f, "filename", "unnamed"), "error": str(e)})

    return jsonify({"ok": True, "count": len(results), "category": mapped, "results": results})


@app.get("/download/<path:filename>")
def download(filename):
    root = os.path.join(BASE_DIR, "..", "deliveries")
    return send_from_directory(root, filename, as_attachment=True)


if register_export_report is not None:
    try:
        register_export_report(app)
    except Exception as e:
        app.logger.warning("register_export_report failed: %s", e)


if __name__ == "__main__":
    # Avoid watcher-based fd explosion on macOS GUI launches.
    try:
        import resource

        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        target = min(max(soft, 4096), hard if hard > 0 else 4096)
        if target > soft:
            resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
    except Exception:
        pass

    app.run(
        host="127.0.0.1",
        # Keep isolated from other local systems that commonly use :8000.
        port=int(os.environ.get("TDOCSYS_PORT", "18000")),
        debug=False,
        use_reloader=False,
    )
