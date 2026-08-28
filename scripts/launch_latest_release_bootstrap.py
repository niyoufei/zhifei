#!/usr/bin/python3
"""Python 3.9 trust-root: verify sealed source/runtime before exec."""

import hashlib
import json
import os
import pwd
import re
import stat
import subprocess
import sys
from pathlib import Path


DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
RELEASE_RE = re.compile(r"^release-[0-9a-f]{24}$")
SYSTEM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
MANIFEST_NAME = "release-manifest.json"
PROVENANCE_NAME = "release-provenance.json"
CURRENT_FIELDS = frozenset((
    "schema_version", "system_id", "release_id", "manifest_digest",
    "source_digest", "runtime_digest", "release_dir", "python_executable",
    "env_file", "state_dir", "log_dir", "backend_port", "ui_port",
))
PROVENANCE_FIELDS = frozenset((
    "schema_version", "build_sha", "source_branch", "source_dirty",
    "runtime_digest",
))


class BootstrapError(RuntimeError):
    def __init__(self, code, message):
        RuntimeError.__init__(self, message)
        self.code = code
        self.message = message


def _fail(code, message):
    raise BootstrapError(code, message)


def _os_home():
    try:
        value = pwd.getpwuid(os.getuid()).pw_dir
    except (KeyError, OSError) as exc:
        raise BootstrapError("LAUNCH_BOOTSTRAP_HOME_UNAVAILABLE", "系统用户主目录无法核验") from exc
    home = Path(value)
    if not home.is_absolute() or home != Path(os.path.abspath(value)):
        _fail("LAUNCH_BOOTSTRAP_HOME_UNAVAILABLE", "系统用户主目录不是规范绝对路径")
    return home


def _minimal_environment(home):
    environment = {
        "HOME": str(home),
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUTF8": "1",
    }
    for name in ("LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR", "USER", "LOGNAME"):
        value = os.environ.get(name)
        if value and "\x00" not in value:
            environment[name] = value
    return environment


def _sha_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def _sha_file(path):
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise BootstrapError("LAUNCH_BOOTSTRAP_FILE_UNREADABLE", "封存文件无法读取") from exc
    return digest.hexdigest()


def _owned_dir(path, exact=None, read_only=False, code="LAUNCH_BOOTSTRAP_PATH_UNTRUSTED"):
    try:
        info = path.lstat()
    except OSError as exc:
        raise BootstrapError(code, "启动目录不可用") from exc
    mode = stat.S_IMODE(info.st_mode)
    if not stat.S_ISDIR(info.st_mode) or path.is_symlink() or info.st_uid != os.getuid():
        _fail(code, "启动目录类型或所有者不可信")
    if exact is not None and mode != exact:
        _fail(code, "启动目录权限不可信")
    if read_only and mode & 0o222:
        _fail(code, "封存目录仍可写")
    return info


def _read_regular(path, exact_mode, maximum, code):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(str(path), flags)
    except OSError as exc:
        raise BootstrapError(code, "必需封存文件无法打开") from exc
    try:
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != exact_mode or info.st_size > maximum):
            _fail(code, "必需封存文件的类型、所有者、权限或大小不可信")
        chunks = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        latest = os.fstat(descriptor)
        if (len(payload) != info.st_size or len(payload) > maximum
                or latest.st_dev != info.st_dev or latest.st_ino != info.st_ino
                or latest.st_size != info.st_size or latest.st_mtime_ns != info.st_mtime_ns):
            _fail(code, "必需封存文件在读取期间发生变化")
        return payload
    finally:
        os.close(descriptor)


def _json(raw, code, label):
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise BootstrapError(code, "%s 不是有效 UTF-8 JSON" % label) from exc
    if not isinstance(result, dict):
        _fail(code, "%s 顶层必须是对象" % label)
    return result


def _absolute(value, field):
    if not isinstance(value, str) or not value or "\x00" in value:
        _fail("LAUNCH_BOOTSTRAP_CURRENT_INVALID", "current.json %s 无效" % field)
    result = Path(value)
    if not result.is_absolute() or result != Path(os.path.abspath(value)):
        _fail("LAUNCH_BOOTSTRAP_PATH_MISMATCH", "%s 未使用规范绝对路径" % field)
    return result


def _relative(value, field):
    if (not isinstance(value, str) or not value or "\x00" in value
            or "\\" in value or value.startswith("/")):
        _fail("LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "%s path 无效" % field)
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts) or "/".join(parts) != value:
        _fail("LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "%s path 无效" % field)
    if value == MANIFEST_NAME:
        _fail("LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "manifest 自身不得列入发布条目")
    return value


def _mode(value, field):
    if isinstance(value, bool):
        _fail("LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "%s mode 无效" % field)
    if isinstance(value, int):
        result = value
    elif isinstance(value, str):
        try:
            raw = value.strip().lower()
            result = int(raw[2:] if raw.startswith("0o") else raw, 8)
        except ValueError as exc:
            raise BootstrapError("LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "%s mode 无效" % field) from exc
    else:
        _fail("LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "%s mode 无效" % field)
    if not 0 <= result <= 0o7777:
        _fail("LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "%s mode 无效" % field)
    return result


def _read_current(base):
    raw = _read_regular(base / "current.json", 0o600, 128 * 1024,
                        "LAUNCH_BOOTSTRAP_CURRENT_UNTRUSTED")
    record = _json(raw, "LAUNCH_BOOTSTRAP_CURRENT_INVALID", "current.json")
    if record.get("schema_version") != 1 or frozenset(record) != CURRENT_FIELDS:
        _fail("LAUNCH_BOOTSTRAP_CURRENT_INVALID", "current.json 字段或版本无效")
    try:
        info = (base / "current").lstat()
        target = os.readlink(base / "current")
    except OSError as exc:
        raise BootstrapError("LAUNCH_CURRENT_POINTER_MISMATCH", "current 链接无法核验") from exc
    if not stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid():
        _fail("LAUNCH_CURRENT_POINTER_MISMATCH", "current 链接类型或所有者不可信")
    return {"raw": raw, "digest": _sha_bytes(raw), "target": target, "record": record}


def _validate_current(base, snapshot):
    record = snapshot["record"]
    system_id = record.get("system_id")
    release_id = record.get("release_id")
    source_digest = record.get("source_digest")
    runtime_digest = record.get("runtime_digest")
    manifest_digest = record.get("manifest_digest")
    if not isinstance(system_id, str) or not SYSTEM_RE.fullmatch(system_id):
        _fail("LAUNCH_BOOTSTRAP_IDENTITY_INVALID", "system_id 格式无效")
    if (not isinstance(release_id, str) or not RELEASE_RE.fullmatch(release_id)
            or not isinstance(source_digest, str) or not DIGEST_RE.fullmatch(source_digest)
            or release_id != "release-%s" % source_digest[:24]
            or not isinstance(runtime_digest, str) or not DIGEST_RE.fullmatch(runtime_digest)
            or not isinstance(manifest_digest, str) or not DIGEST_RE.fullmatch(manifest_digest)):
        _fail("LAUNCH_BOOTSTRAP_IDENTITY_INVALID", "当前发布身份或内容寻址关系无效")
    release_dir = _absolute(record.get("release_dir"), "release_dir")
    if release_dir != base / "releases" / release_id or snapshot["target"] != str(release_dir):
        _fail("LAUNCH_CURRENT_POINTER_MISMATCH", "current 与 current.json 未指向同一发布")
    retired_dir = base / "state" / "retired-releases"
    _owned_dir(retired_dir, exact=0o700,
               code="LAUNCH_BOOTSTRAP_RETIRED_STATE_UNTRUSTED")
    retired_marker = retired_dir / (release_id + ".json")
    try:
        marker_info = retired_marker.lstat()
    except FileNotFoundError:
        marker_info = None
    except OSError as exc:
        raise BootstrapError("LAUNCH_BOOTSTRAP_RETIRED_STATE_UNTRUSTED", "退役发布记录无法核验") from exc
    if marker_info is not None:
        if (not stat.S_ISREG(marker_info.st_mode) or retired_marker.is_symlink()
                or marker_info.st_uid != os.getuid()
                or stat.S_IMODE(marker_info.st_mode) != 0o600
                or marker_info.st_size > 128 * 1024):
            _fail("LAUNCH_BOOTSTRAP_RETIRED_STATE_UNTRUSTED", "退役发布记录类型、所有者、权限或大小不可信")
        _fail("LAUNCH_BOOTSTRAP_ROLLBACK_BLOCKED", "当前指针命中已退役发布，拒绝回滚启动")
    _owned_dir(release_dir, read_only=True, code="LAUNCH_BOOTSTRAP_RELEASE_UNTRUSTED")
    runtime_root = base / "runtimes" / runtime_digest / "venv"
    python = _absolute(record.get("python_executable"), "python_executable")
    if python not in (runtime_root / "bin" / "python", runtime_root / "bin" / "python3"):
        _fail("LAUNCH_BOOTSTRAP_RUNTIME_PATH_MISMATCH", "Python 未绑定当前摘要运行时")
    env_file = _absolute(record.get("env_file"), "env_file")
    state_dir = _absolute(record.get("state_dir"), "state_dir")
    log_dir = _absolute(record.get("log_dir"), "log_dir")
    if env_file != base / "secrets" / "runtime.env":
        _fail("LAUNCH_BOOTSTRAP_PATH_MISMATCH", "env_file 未绑定固定密钥文件")
    if state_dir != base / "state" / "supervisor" or log_dir != state_dir / "logs":
        _fail("LAUNCH_BOOTSTRAP_PATH_MISMATCH", "监管状态路径未绑定固定目录")
    _read_regular(env_file, 0o600, 1024 * 1024, "LAUNCH_BOOTSTRAP_ENV_UNTRUSTED")
    _owned_dir(state_dir, exact=0o700, code="LAUNCH_BOOTSTRAP_STATE_UNTRUSTED")
    _owned_dir(log_dir, exact=0o700, code="LAUNCH_BOOTSTRAP_STATE_UNTRUSTED")
    ports = (record.get("backend_port"), record.get("ui_port"))
    if any(isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535 for value in ports) or ports[0] == ports[1]:
        _fail("LAUNCH_BOOTSTRAP_PORT_INVALID", "current.json 端口无效")
    return release_dir, python


def _release_entries(root):
    result = {}
    def visit(directory, prefix=""):
        try:
            children = sorted(os.scandir(str(directory)), key=lambda item: item.name)
        except OSError as exc:
            raise BootstrapError("LAUNCH_BOOTSTRAP_RELEASE_TREE_UNREADABLE", "发布目录无法遍历") from exc
        for child in children:
            relative = "%s/%s" % (prefix, child.name) if prefix else child.name
            if relative == MANIFEST_NAME:
                continue
            if child.is_symlink():
                result[relative] = "mutable_link"
            elif child.is_dir(follow_symlinks=False):
                result[relative] = "directory"
                visit(Path(child.path), relative)
            elif child.is_file(follow_symlinks=False):
                result[relative] = "file"
            else:
                result[relative] = "unsupported"
    visit(root)
    return result


def _source_digest(files, directories, links):
    seen = set()
    def unique(item, field):
        if not isinstance(item, dict):
            _fail("LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "%s 条目无效" % field)
        path = _relative(item.get("path"), field)
        if path in seen:
            _fail("LAUNCH_BOOTSTRAP_MANIFEST_DUPLICATE", "发布清单重复条目: %s" % path)
        seen.add(path)
        return path
    canonical_files = []
    for item in files:
        path = unique(item, "files")
        size, digest = item.get("size"), item.get("sha256")
        if (isinstance(size, bool) or not isinstance(size, int) or size < 0
                or not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest)):
            _fail("LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "发布文件元数据无效: %s" % path)
        canonical_files.append({"path": path, "size": size, "mode": _mode(item.get("mode"), path), "sha256": digest})
    canonical_dirs = []
    for item in directories:
        path = unique(item, "directories")
        canonical_dirs.append({"path": path, "mode": _mode(item.get("mode"), path)})
    canonical_links = []
    for item in links:
        path = unique(item, "mutable_links")
        canonical_links.append({"path": path, "kind": "mutable_link"})
    raw = json.dumps({"schema_version": 1,
        "files": sorted(canonical_files, key=lambda item: item["path"]),
        "directories": sorted(canonical_dirs, key=lambda item: item["path"]),
        "mutable_links": sorted(canonical_links, key=lambda item: item["path"])},
        ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha_bytes(raw)


def _verify_provenance(root, manifest, runtime_digest):
    listed = {str(item.get("path") or "") for item in manifest["files"] if isinstance(item, dict)}
    if PROVENANCE_NAME not in listed:
        _fail("LAUNCH_BOOTSTRAP_PROVENANCE_MISSING", "发布清单缺少必需来源记录")
    raw = _read_regular(root / PROVENANCE_NAME, 0o444, 16 * 1024,
                        "LAUNCH_BOOTSTRAP_PROVENANCE_UNTRUSTED")
    payload = _json(raw, "LAUNCH_BOOTSTRAP_PROVENANCE_INVALID", "发布来源记录")
    if payload.get("schema_version") != 1 or frozenset(payload) != PROVENANCE_FIELDS:
        _fail("LAUNCH_BOOTSTRAP_PROVENANCE_INVALID", "发布来源记录字段或版本无效")
    sha, branch, dirty = payload.get("build_sha"), payload.get("source_branch"), payload.get("source_dirty")
    if sha is not None and (not isinstance(sha, str) or not GIT_SHA_RE.fullmatch(sha)):
        _fail("LAUNCH_BOOTSTRAP_PROVENANCE_INVALID", "发布来源 build_sha 无效")
    if branch is not None and (not isinstance(branch, str) or not branch or len(branch) > 255 or any(c in branch for c in "\x00\r\n")):
        _fail("LAUNCH_BOOTSTRAP_PROVENANCE_INVALID", "发布来源分支无效")
    if dirty is not None and not isinstance(dirty, bool):
        _fail("LAUNCH_BOOTSTRAP_PROVENANCE_INVALID", "发布来源 dirty 状态无效")
    if payload.get("runtime_digest") != runtime_digest:
        _fail("LAUNCH_BOOTSTRAP_PROVENANCE_INVALID", "发布来源未绑定当前运行时摘要")


def _verify_release(root, record):
    raw = _read_regular(root / MANIFEST_NAME, 0o444, 16 * 1024 * 1024,
                        "LAUNCH_BOOTSTRAP_MANIFEST_UNTRUSTED")
    if _sha_bytes(raw) != record["manifest_digest"]:
        _fail("LAUNCH_BOOTSTRAP_MANIFEST_DIGEST_MISMATCH", "发布清单摘要与当前身份不一致")
    manifest = _json(raw, "LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "发布清单")
    fields = frozenset(("schema_version", "release_id", "source_digest", "runtime_digest",
                        "files", "directories", "mutable_links"))
    if manifest.get("schema_version") != 1 or frozenset(manifest) != fields:
        _fail("LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "发布清单字段或版本无效")
    for key in ("release_id", "source_digest", "runtime_digest"):
        if manifest.get(key) != record[key]:
            _fail("LAUNCH_BOOTSTRAP_MANIFEST_IDENTITY_MISMATCH", "发布清单 %s 不匹配" % key)
    files, directories, links = manifest.get("files"), manifest.get("directories"), manifest.get("mutable_links")
    if not isinstance(files, list) or not isinstance(directories, list) or not isinstance(links, list):
        _fail("LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "发布清单条目列表缺失")
    expected = {}
    def register(item, kind, field):
        if not isinstance(item, dict):
            _fail("LAUNCH_BOOTSTRAP_MANIFEST_INVALID", "%s 条目无效" % field)
        relative = _relative(item.get("path"), field)
        if relative in expected:
            _fail("LAUNCH_BOOTSTRAP_MANIFEST_DUPLICATE", "发布清单重复条目: %s" % relative)
        expected[relative] = kind
        return relative, root / relative
    for item in files:
        relative, path = register(item, "file", "files")
        try:
            info = path.lstat()
        except OSError as exc:
            raise BootstrapError("LAUNCH_BOOTSTRAP_RELEASE_FILE_MISSING", "发布文件缺失: %s" % relative) from exc
        size, digest = item.get("size"), item.get("sha256")
        if (not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_uid != os.getuid()
                or isinstance(size, bool) or not isinstance(size, int) or size < 0
                or not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest)
                or info.st_size != size or stat.S_IMODE(info.st_mode) != _mode(item.get("mode"), relative)):
            _fail("LAUNCH_BOOTSTRAP_RELEASE_FILE_METADATA_MISMATCH", "发布文件类型、所有者、大小或权限不符: %s" % relative)
        if _sha_file(path) != digest:
            _fail("LAUNCH_BOOTSTRAP_RELEASE_FILE_DIGEST_MISMATCH", "发布文件摘要不符: %s" % relative)
    for item in directories:
        relative, path = register(item, "directory", "directories")
        try:
            info = path.lstat()
        except OSError as exc:
            raise BootstrapError("LAUNCH_BOOTSTRAP_RELEASE_DIRECTORY_MISSING", "发布目录缺失: %s" % relative) from exc
        if (not stat.S_ISDIR(info.st_mode) or path.is_symlink() or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != _mode(item.get("mode"), relative)):
            _fail("LAUNCH_BOOTSTRAP_RELEASE_DIRECTORY_MISMATCH", "发布目录类型、所有者或权限不符: %s" % relative)
    for item in links:
        relative, path = register(item, "mutable_link", "mutable_links")
        target = item.get("target")
        if not isinstance(target, str) or not target or "\x00" in target or not Path(target).is_absolute():
            _fail("LAUNCH_BOOTSTRAP_MUTABLE_LINK_INVALID", "可变链接目标无效: %s" % relative)
        target_path = Path(target)
        try:
            target_info, link_info, actual = target_path.lstat(), path.lstat(), os.readlink(path)
        except OSError as exc:
            raise BootstrapError("LAUNCH_BOOTSTRAP_MUTABLE_LINK_MISSING", "可变链接或目标缺失: %s" % relative) from exc
        if (not stat.S_ISDIR(target_info.st_mode) or target_path.is_symlink()
                or target_info.st_uid != os.getuid() or stat.S_IMODE(target_info.st_mode) != 0o700
                or not stat.S_ISLNK(link_info.st_mode) or link_info.st_uid != os.getuid() or actual != target):
            _fail("LAUNCH_BOOTSTRAP_MUTABLE_LINK_MISMATCH", "可变链接或目标不可信: %s" % relative)
        try:
            target_path.resolve(strict=False).relative_to(root.resolve())
        except ValueError:
            pass
        else:
            _fail("LAUNCH_BOOTSTRAP_MUTABLE_LINK_INVALID", "可变链接不得指回发布树: %s" % relative)
    actual = _release_entries(root)
    if actual != expected:
        details = sorted(set(expected) ^ set(actual)) or sorted(path for path in actual if actual[path] != expected[path])
        _fail("LAUNCH_BOOTSTRAP_RELEASE_TREE_MISMATCH", "发布树存在未清单、缺失或类型错误条目: %s" % ((details or ["unknown"])[0]))
    if _source_digest(files, directories, links) != record["source_digest"]:
        _fail("LAUNCH_BOOTSTRAP_SOURCE_DIGEST_MISMATCH", "发布清单条目与 source_digest 不一致")
    _verify_provenance(root, manifest, record["runtime_digest"])


def _validate_python(logical):
    try:
        logical_info = logical.lstat()
        resolved = logical.resolve(strict=True)
        resolved_info = resolved.stat()
    except OSError as exc:
        raise BootstrapError("LAUNCH_BOOTSTRAP_RUNTIME_UNTRUSTED", "冻结 Python 不可用") from exc
    if (logical_info.st_uid not in (0, os.getuid()) or resolved_info.st_uid not in (0, os.getuid())
            or not (stat.S_ISREG(logical_info.st_mode) or stat.S_ISLNK(logical_info.st_mode))
            or not stat.S_ISREG(resolved_info.st_mode) or not os.access(str(logical), os.X_OK)):
        _fail("LAUNCH_BOOTSTRAP_RUNTIME_UNTRUSTED", "冻结 Python 类型、所有者或权限不可信")
    return resolved


MACHO_MAGICS = frozenset((
    b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca",
))


def _is_macho(path):
    try:
        with path.open("rb") as handle:
            return handle.read(4) in MACHO_MAGICS
    except OSError as exc:
        raise BootstrapError("LAUNCH_BOOTSTRAP_RUNTIME_DEPENDENCY_UNREADABLE",
                             "冻结运行时 Mach-O 文件无法读取") from exc


def _otool(path, option):
    executable = Path("/usr/bin/otool")
    if not executable.is_file():
        _fail("LAUNCH_BOOTSTRAP_RUNTIME_DEPENDENCY_TOOL_MISSING",
              "系统缺少可信 Mach-O 依赖检查工具")
    try:
        completed = subprocess.run(
            [str(executable), option, str(path)], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
            timeout=10, check=False,
            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LC_ALL": "C"})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BootstrapError("LAUNCH_BOOTSTRAP_RUNTIME_DEPENDENCY_INSPECTION_FAILED",
                             "Mach-O 依赖检查未能完成") from exc
    if completed.returncode != 0:
        _fail("LAUNCH_BOOTSTRAP_RUNTIME_DEPENDENCY_INSPECTION_FAILED",
              "Mach-O 依赖检查返回失败")
    return completed.stdout.splitlines()


def _macho_rpaths(path, executable_dir):
    result, expect_path = [], False
    for line in _otool(path, "-l"):
        stripped = line.strip()
        if stripped == "cmd LC_RPATH":
            expect_path = True
            continue
        if expect_path and stripped.startswith("path "):
            raw = stripped[5:].split(" (offset ", 1)[0]
            if raw.startswith("@loader_path/"):
                candidate = path.parent / raw[len("@loader_path/"):]
            elif raw == "@loader_path":
                candidate = path.parent
            elif raw.startswith("@executable_path/"):
                candidate = executable_dir / raw[len("@executable_path/"):]
            elif raw == "@executable_path":
                candidate = executable_dir
            elif raw.startswith("/"):
                candidate = Path(raw)
            else:
                expect_path = False
                continue
            result.append(Path(os.path.abspath(str(candidate))))
            expect_path = False
    return result


def _system_library(path):
    value = str(path)
    return value.startswith("/System/Library/") or value.startswith("/usr/lib/")


def _resolve_dependency(raw, loader, executable_dir):
    if raw.startswith("/"):
        candidates = [Path(raw)]
    elif raw.startswith("@loader_path/"):
        candidates = [loader.parent / raw[len("@loader_path/"):]]
    elif raw.startswith("@executable_path/"):
        candidates = [executable_dir / raw[len("@executable_path/"):]]
    elif raw.startswith("@rpath/"):
        suffix = raw[len("@rpath/"):]
        candidates = [loader.parent / suffix]
        candidates.extend(root / suffix for root in _macho_rpaths(loader, executable_dir))
    else:
        candidates = [loader.parent / raw]
    for candidate in candidates:
        absolute = Path(os.path.abspath(str(candidate)))
        if _system_library(absolute):
            return None
        try:
            return absolute.resolve(strict=True)
        except OSError:
            continue
    if any(_system_library(Path(os.path.abspath(str(item)))) for item in candidates):
        return None
    _fail("LAUNCH_BOOTSTRAP_RUNTIME_DEPENDENCY_UNRESOLVED",
          "非系统 Mach-O 依赖无法解析")


def _dependency_closure(roots, runtime_root, executable):
    if sys.platform != "darwin":
        return []
    queue = sorted(set(path.resolve(strict=True) for path in roots), key=str)
    inspected, external = set(), {}
    executable_dir = executable.resolve(strict=True).parent
    while queue:
        loader = queue.pop(0)
        if loader in inspected:
            continue
        inspected.add(loader)
        install_names = set(
            line.strip() for line in _otool(loader, "-D")[1:]
            if line.strip() and not line.strip().endswith(":"))
        for line in _otool(loader, "-L")[1:]:
            stripped = line.strip()
            if not stripped or " (compatibility version " not in stripped:
                continue
            raw = stripped.split(" (compatibility version ", 1)[0]
            if raw in install_names:
                continue
            dependency = _resolve_dependency(raw, loader, executable_dir)
            if dependency is None or dependency == loader:
                continue
            try:
                info = dependency.stat()
            except OSError as exc:
                raise BootstrapError("LAUNCH_BOOTSTRAP_RUNTIME_DEPENDENCY_UNREADABLE",
                                     "非系统 Mach-O 依赖无法读取") from exc
            if (not stat.S_ISREG(info.st_mode)
                    or info.st_uid not in (0, os.getuid())):
                _fail("LAUNCH_BOOTSTRAP_RUNTIME_DEPENDENCY_UNTRUSTED",
                      "非系统 Mach-O 依赖类型或所有者不可信")
            try:
                dependency.relative_to(runtime_root)
            except ValueError:
                external[str(dependency)] = {
                    "path": str(dependency), "size": info.st_size,
                    "mode": stat.S_IMODE(info.st_mode),
                    "sha256": _sha_file(dependency)}
            if _is_macho(dependency) and dependency not in inspected:
                queue.append(dependency)
    return [external[key] for key in sorted(external)]


def _runtime_snapshot(logical):
    logical = Path(os.path.abspath(os.fspath(logical)))
    resolved = _validate_python(logical)
    root = None
    for candidate in (logical.parent.parent / "pyvenv.cfg", logical.parent / "pyvenv.cfg"):
        if candidate.is_file() and not candidate.is_symlink():
            root = candidate.parent
            break
    if root is None:
        _fail("LAUNCH_BOOTSTRAP_RUNTIME_LAYOUT_INVALID", "冻结运行时缺少 pyvenv.cfg")
    try:
        logical_entry = logical.relative_to(root).as_posix()
        root_info = root.lstat()
    except (OSError, ValueError) as exc:
        raise BootstrapError("LAUNCH_BOOTSTRAP_RUNTIME_LAYOUT_INVALID", "冻结运行时根目录无效") from exc
    if not stat.S_ISDIR(root_info.st_mode) or root.is_symlink():
        _fail("LAUNCH_BOOTSTRAP_RUNTIME_LAYOUT_INVALID", "冻结运行时根目录类型无效")
    directories = [{"path": ".", "mode": stat.S_IMODE(root_info.st_mode)}]
    files, links = [], []
    macho_roots = [resolved] if _is_macho(resolved) else []
    def visit(directory, prefix=""):
        try:
            children = sorted(os.scandir(str(directory)), key=lambda item: item.name)
        except OSError as exc:
            raise BootstrapError("LAUNCH_BOOTSTRAP_RUNTIME_TREE_UNREADABLE", "冻结运行时目录无法遍历") from exc
        for child in children:
            relative = "%s/%s" % (prefix, child.name) if prefix else child.name
            path = Path(child.path)
            try:
                info = path.lstat()
                if child.is_symlink():
                    raw_target = os.readlink(path)
                    resolved_target = path.resolve(strict=True)
                    try:
                        resolved_target.relative_to(root)
                        external = None
                    except ValueError:
                        target_info = resolved_target.stat()
                        if not stat.S_ISREG(target_info.st_mode):
                            _fail("LAUNCH_BOOTSTRAP_RUNTIME_EXTERNAL_LINK_INVALID", "冻结运行时外部链接不是普通文件: %s" % relative)
                        external = {"size": target_info.st_size, "mode": stat.S_IMODE(target_info.st_mode), "sha256": _sha_file(resolved_target)}
                        if _is_macho(resolved_target):
                            macho_roots.append(resolved_target)
                    links.append({"path": relative, "target": raw_target, "external_file": external})
                elif child.is_dir(follow_symlinks=False):
                    directories.append({"path": relative, "mode": stat.S_IMODE(info.st_mode)})
                    visit(path, relative)
                elif child.is_file(follow_symlinks=False):
                    files.append({"path": relative, "size": info.st_size,
                                  "mode": stat.S_IMODE(info.st_mode), "sha256": _sha_file(path)})
                    if _is_macho(path):
                        macho_roots.append(path)
                else:
                    _fail("LAUNCH_BOOTSTRAP_RUNTIME_ENTRY_UNSUPPORTED", "冻结运行时包含不支持的条目: %s" % relative)
            except BootstrapError:
                raise
            except OSError as exc:
                raise BootstrapError("LAUNCH_BOOTSTRAP_RUNTIME_TREE_UNREADABLE", "冻结运行时条目无法读取: %s" % relative) from exc
    visit(root)
    closure = _dependency_closure(macho_roots, root, resolved)
    return {"schema_version": 3,
            "dependency_policy": "non_system_macho_closure_v1",
            "python_logical_entry": logical_entry,
            "python_resolved_size": resolved.stat().st_size,
            "python_resolved_sha256": _sha_file(resolved),
            "directories": sorted(directories, key=lambda item: item["path"]),
            "files": sorted(files, key=lambda item: item["path"]),
            "links": sorted(links, key=lambda item: item["path"]),
            "external_macho_dependencies": closure}


def compute_runtime_digest(python_executable):
    raw = json.dumps(_runtime_snapshot(python_executable), ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha_bytes(raw)


def _assert_current_unchanged(base, first):
    latest = _read_current(base)
    if latest["digest"] != first["digest"] or latest["raw"] != first["raw"] or latest["target"] != first["target"]:
        _fail("LAUNCH_BOOTSTRAP_CURRENT_CHANGED", "启动核验期间 current 指针发生变化")


def _verify_fixed_trust_root(base):
    """Bind production execution to the builder-installed external bytes."""

    expected = base / "bootstrap" / "launch_current.py"
    actual = Path(os.path.abspath(__file__))
    if actual != expected:
        _fail("LAUNCH_BOOTSTRAP_LOCATION_UNTRUSTED", "启动入口不是固定外置信任根")
    _owned_dir(expected.parent, exact=0o555,
               code="LAUNCH_BOOTSTRAP_LOCATION_UNTRUSTED")
    try:
        info = expected.lstat()
    except OSError as exc:
        raise BootstrapError("LAUNCH_BOOTSTRAP_LOCATION_UNTRUSTED", "固定外置启动入口不可用") from exc
    if (not stat.S_ISREG(info.st_mode) or expected.is_symlink()
            or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o444
            or info.st_size > 2 * 1024 * 1024):
        _fail("LAUNCH_BOOTSTRAP_LOCATION_UNTRUSTED", "固定外置启动入口类型、所有者、权限或大小不可信")


def _verified_exec_spec(base):
    base = Path(os.path.abspath(os.fspath(base)))
    _owned_dir(base, exact=0o700, code="LAUNCH_BOOTSTRAP_BASE_UNTRUSTED")
    _owned_dir(base / "releases", exact=0o700, code="LAUNCH_BOOTSTRAP_BASE_UNTRUSTED")
    _owned_dir(base / "runtimes", exact=0o700, code="LAUNCH_BOOTSTRAP_BASE_UNTRUSTED")
    first = _read_current(base)
    release_dir, python = _validate_current(base, first)
    _verify_release(release_dir, first["record"])
    if compute_runtime_digest(python) != first["record"]["runtime_digest"]:
        _fail("LAUNCH_BOOTSTRAP_RUNTIME_DIGEST_MISMATCH", "运行时完整物理摘要反向校验失败")
    launcher = release_dir / "scripts" / "launch_latest_release.py"
    if not launcher.is_file() or launcher.is_symlink():
        _fail("LAUNCH_BOOTSTRAP_LAUNCHER_UNTRUSTED", "冻结启动器不可用")
    _assert_current_unchanged(base, first)
    return base, python, launcher, first


def load_exec_spec(base):
    selected, python, launcher, _snapshot = _verified_exec_spec(base)
    return selected, python, launcher


def main(argv=None):
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        _fail(
            "LAUNCH_BOOTSTRAP_INTERPRETER_NOT_ISOLATED",
            "固定启动入口必须由 Python -I -B 隔离执行",
        )
    arguments = list(sys.argv[1:] if argv is None else argv)
    if any(arg == "--base" or arg.startswith("--base=") for arg in arguments):
        _fail("LAUNCH_BOOTSTRAP_ARGUMENT_REJECTED", "固定启动入口不允许覆盖发布基础目录")
    home = _os_home()
    base = home / "Library" / "Application Support" / "com.zhifei.construction-expert"
    _verify_fixed_trust_root(base)
    base, python, launcher, first = _verified_exec_spec(base)
    _assert_current_unchanged(base, first)
    os.execve(
        str(python),
        [str(python), "-I", "-B", str(launcher)] + arguments + ["--base", str(base)],
        _minimal_environment(home),
    )
    return 127


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootstrapError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "message": exc.message},
                         ensure_ascii=False, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
    except Exception:
        print(json.dumps({
            "ok": False,
            "error_code": "LAUNCH_BOOTSTRAP_UNEXPECTED_FAILURE",
            "message": "固定启动入口发生未分类故障，请查看监管日志",
        }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
