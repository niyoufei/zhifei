#!/usr/bin/env python3
from __future__ import annotations

"""Rebuild the current formal acceptance gate without provider activity."""

import argparse
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.zhifei_autoplan.no_model_formal_acceptance import (
    AcceptanceError,
    FileSnapshot,
    canonical_digest,
    read_regular_file_snapshot,
    run_acceptance,
    run_current_runtime_acceptance_write,
)
from backend.zhifei_autoplan.sealed_compliance import (
    sealed_official_registry_path,
)
from scripts.build_local_release import ReleaseBuildError, default_release_base
from scripts.launch_latest_release import (
    CommandRunner,
    CurrentSnapshot,
    HttpGetter,
    LaunchError,
    ReleaseSpec,
    _assert_current_unchanged,
    _assert_running_identity,
    _default_http_get,
    _default_runner,
    _read_status,
    load_current_snapshot,
    parse_release_spec,
    preflight_release,
)
from scripts.runtime_supervisor import SupervisorError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="离线重建图纸、标准、参数、交叉索引与正式交付门。"
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--release-base", type=Path)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--source-job-id")
    parser.add_argument(
        "--write",
        action="store_true",
        help="写入不可变run回执并原子更新latest；默认仅输出dry-run JSON。",
    )
    return parser


def _sealed_release_context(release_base: Path) -> tuple[CurrentSnapshot, ReleaseSpec]:
    base = Path(os.path.abspath(os.fspath(release_base)))
    snapshot = load_current_snapshot(base / "current.json")
    spec = parse_release_spec(snapshot, base)
    preflight_release(spec)
    try:
        Path(__file__).resolve().relative_to(spec.release_dir.resolve())
    except ValueError as exc:
        raise AcceptanceError(
            "ACCEPTANCE_CODE_NOT_CURRENT_SEALED_RELEASE",
            "验收CLI必须从current密封发布目录执行",
        ) from exc
    try:
        same_python = os.path.samefile(sys.executable, spec.python_executable)
    except OSError:
        same_python = False
    if not same_python:
        raise AcceptanceError(
            "ACCEPTANCE_PYTHON_NOT_CURRENT_RUNTIME",
            "验收CLI必须使用current.json绑定的Python运行时",
        )
    return snapshot, spec


def _positive_pid(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 1


def _supervisor_projection(status: Mapping[str, Any]) -> dict[str, Any]:
    projection = {
        "schema_version": status.get("schema_version"),
        "status": status.get("status"),
        "running": status.get("running"),
        "release_id": status.get("release_id"),
        "manifest_digest": status.get("manifest_digest"),
        "source_digest": status.get("source_digest"),
        "runtime_digest": status.get("runtime_digest"),
        "release_root": status.get("release_root"),
        "supervisor_pid": status.get("supervisor_pid"),
        "supervisor_instance_id": status.get("supervisor_instance_id"),
        "backend_pid": status.get("backend_pid"),
        "ui_pid": status.get("ui_pid"),
        "circuit_open": status.get("circuit_open"),
        "restart_count_window": status.get("restart_count_window"),
        "health_degraded": status.get("health_degraded"),
        "consecutive_health_failures": status.get("consecutive_health_failures"),
    }
    if (
        projection["schema_version"] != 1
        or projection["status"] != "healthy"
        or projection["running"] is not True
        or projection["circuit_open"] is not False
        or projection["health_degraded"] is not False
        or projection["restart_count_window"] != 0
        or projection["consecutive_health_failures"] != 0
        or not str(projection["supervisor_instance_id"] or "").strip()
        or not all(
            _positive_pid(projection[field])
            for field in ("supervisor_pid", "backend_pid", "ui_pid")
        )
    ):
        raise AcceptanceError(
            "ACCEPTANCE_RUNTIME_UNHEALTHY", "监管器未处于稳定健康单实例状态"
        )
    return projection


def _backend_health_projection(
    payload: Any,
    *,
    spec: ReleaseSpec,
    supervisor: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise AcceptanceError(
            "ACCEPTANCE_RUNTIME_HEALTH_INVALID", "后端健康响应无效"
        )
    for field, expected in spec.identity.as_dict().items():
        if str(payload.get(field) or "") != expected:
            raise AcceptanceError(
                "ACCEPTANCE_RUNTIME_IDENTITY_UNTRUSTED", "后端与current发布身份不一致"
            )
    if (
        str(payload.get("release_root") or "") != str(spec.release_dir)
        or payload.get("release_managed") is not True
        or payload.get("runtime_mode") != "sealed_release"
    ):
        raise AcceptanceError(
            "ACCEPTANCE_RUNTIME_IDENTITY_UNTRUSTED", "后端未运行于current密封发布"
        )
    jobs = payload.get("jobs")
    queue = payload.get("queue")
    health_supervisor = payload.get("supervisor")
    job_fields = ("active", "queued", "running", "cancel_requested", "stale")
    if (
        not isinstance(jobs, dict)
        or any(jobs.get(field) != 0 for field in job_fields)
        or not isinstance(queue, dict)
        or queue.get("queue_depth") != 0
        or queue.get("dispatched_jobs") != 0
        or queue.get("active_process_alive") is not False
    ):
        raise AcceptanceError(
            "ACCEPTANCE_RUNTIME_BUSY", "当前仍有活动、排队或未清理任务"
        )
    if (
        payload.get("process_pid") != supervisor.get("backend_pid")
        or
        not isinstance(health_supervisor, dict)
        or health_supervisor.get("available") is not True
        or health_supervisor.get("managed") is not True
        or health_supervisor.get("status") != "healthy"
        or health_supervisor.get("circuit_open") is not False
        or health_supervisor.get("health_degraded") is not False
        or health_supervisor.get("restart_count_window") != 0
        or health_supervisor.get("backend_pid") != supervisor.get("backend_pid")
        or health_supervisor.get("ui_pid") != supervisor.get("ui_pid")
        or health_supervisor.get("release_id") != supervisor.get("release_id")
    ):
        raise AcceptanceError(
            "ACCEPTANCE_RUNTIME_HEALTH_INVALID", "后端与监管器健康状态不一致"
        )
    return {
        "identity": {
            **spec.identity.as_dict(),
            "release_root": str(spec.release_dir),
            "release_managed": True,
            "runtime_mode": "sealed_release",
        },
        "process_pid": int(payload["process_pid"]),
        "jobs": {field: jobs[field] for field in job_fields},
        "queue": {
            "queue_depth": 0,
            "dispatched_jobs": 0,
            "active_process_alive": False,
        },
        "supervisor": {
            "available": True,
            "managed": True,
            "status": "healthy",
            "release_id": health_supervisor.get("release_id"),
            "backend_pid": health_supervisor.get("backend_pid"),
            "ui_pid": health_supervisor.get("ui_pid"),
            "circuit_open": False,
            "health_degraded": False,
            "restart_count_window": 0,
        },
    }


def _attest_runtime(
    snapshot: CurrentSnapshot,
    spec: ReleaseSpec,
    *,
    runner: CommandRunner,
    http_get: HttpGetter,
) -> dict[str, Any]:
    _assert_current_unchanged(snapshot)
    code, first_status = _read_status(spec, runner)
    if code != 0:
        raise AcceptanceError(
            "ACCEPTANCE_RUNTIME_NOT_RUNNING", "current密封发布未由监管器运行"
        )
    _assert_running_identity(first_status, spec)
    supervisor = _supervisor_projection(first_status)
    status, body = http_get(f"http://127.0.0.1:{spec.backend_port}/health", 3.0)
    if status != 200 or len(body) > 1024 * 1024:
        raise AcceptanceError(
            "ACCEPTANCE_RUNTIME_HEALTH_UNAVAILABLE", "本地后端健康检查不可用"
        )
    try:
        health_payload = json.loads(body.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise AcceptanceError(
            "ACCEPTANCE_RUNTIME_HEALTH_INVALID", "后端健康响应不是有效JSON"
        ) from exc
    health = _backend_health_projection(
        health_payload,
        spec=spec,
        supervisor=supervisor,
    )
    ui_status, _ui_body = http_get(f"http://127.0.0.1:{spec.ui_port}/", 3.0)
    if not 200 <= ui_status < 400:
        raise AcceptanceError(
            "ACCEPTANCE_RUNTIME_UI_UNHEALTHY", "本地界面未通过健康检查"
        )
    final_code, final_status = _read_status(spec, runner)
    if final_code != 0:
        raise AcceptanceError(
            "ACCEPTANCE_RUNTIME_UNHEALTHY", "健康复验期间监管器停止"
        )
    _assert_running_identity(final_status, spec)
    if _supervisor_projection(final_status) != supervisor:
        raise AcceptanceError(
            "ACCEPTANCE_RUNTIME_CHANGED", "健康复验期间监管进程发生变化"
        )
    _assert_current_unchanged(snapshot)
    return {
        "system_id": spec.identity.system_id,
        "release_id": spec.identity.release_id,
        "manifest_digest": spec.identity.manifest_digest,
        "source_digest": spec.identity.source_digest,
        "runtime_digest": spec.identity.runtime_digest,
        "current_json_sha256": snapshot.raw_digest,
        "supervisor_state_sha256": canonical_digest(supervisor),
        "backend_health_sha256": canonical_digest(health),
        "release_root": str(spec.release_dir),
        "health_status": "verified_healthy",
        "supervisor_instance_id": str(supervisor["supervisor_instance_id"]),
        "supervisor_pid": int(supervisor["supervisor_pid"]),
        "backend_pid": int(supervisor["backend_pid"]),
        "ui_pid": int(supervisor["ui_pid"]),
    }


def _release_bundle(
    snapshot: CurrentSnapshot,
    spec: ReleaseSpec,
    *,
    runner: CommandRunner,
    http_get: HttpGetter,
) -> tuple[
    dict[str, Any],
    list[FileSnapshot],
    Callable[[], Mapping[str, Any]],
]:
    current_witness = read_regular_file_snapshot(snapshot.path)
    assert current_witness is not None
    if current_witness.sha256 != snapshot.raw_digest:
        raise AcceptanceError(
            "ACCEPTANCE_RELEASE_WITNESSES_INVALID", "current文件摘要与解析快照不一致"
        )
    identity = _attest_runtime(snapshot, spec, runner=runner, http_get=http_get)

    def validate() -> Mapping[str, Any]:
        current = load_current_snapshot(snapshot.path)
        if current.raw_digest != snapshot.raw_digest or current.raw_bytes != snapshot.raw_bytes:
            raise AcceptanceError(
                "ACCEPTANCE_RELEASE_CHANGED", "验收期间current发布发生变化"
            )
        current_spec = parse_release_spec(current, spec.base)
        preflight_release(current_spec)
        return _attest_runtime(
            current,
            current_spec,
            runner=runner,
            http_get=http_get,
        )

    return identity, [current_witness], validate


def _fixed_current_write_context_impl() -> dict[str, Any]:
    """Build the non-injectable production write authority from current runtime."""

    base = default_release_base()
    snapshot, spec = _sealed_release_context(base)
    identity, witnesses, validator = _release_bundle(
        snapshot,
        spec,
        runner=_default_runner,
        http_get=_default_http_get,
    )
    if len(witnesses) != 1 or not isinstance(witnesses[0], FileSnapshot):
        raise AcceptanceError(
            "ACCEPTANCE_RELEASE_WITNESSES_INVALID",
            "正式写入缺少唯一current文件见证",
        )
    current_witness = witnesses[0]
    data_root = base / "state" / "workspace" / "backend" / "data"
    registry_path = sealed_official_registry_path(spec.release_dir)
    authority_core = {
        "schema_version": "no-model-current-write-authority-v1",
        "release": identity,
        "current": {
            "path": str(current_witness.path),
            "sha256": current_witness.sha256,
            "size": current_witness.size,
            "device": current_witness.device,
            "inode": current_witness.inode,
            "mtime_ns": current_witness.mtime_ns,
        },
        "data_root": str(data_root),
        "registry_path": str(registry_path),
        "output_root": None,
        "python_executable": str(Path(sys.executable).resolve()),
        "cli_path": str(Path(__file__).resolve()),
    }
    return {
        "release_identity": identity,
        "current_witness": current_witness,
        "release_validator": validator,
        "data_root": data_root,
        "registry_path": registry_path,
        "authority_digest": canonical_digest(authority_core),
    }


def _execute_dry_run(
    args: argparse.Namespace,
    *,
    runner: CommandRunner = _default_runner,
    http_get: HttpGetter = _default_http_get,
) -> dict[str, Any]:
    default_base = default_release_base()
    release_base = args.release_base or default_base
    snapshot, spec = _sealed_release_context(release_base)
    data_root = Path(
        os.path.abspath(
            os.fspath(
                args.data_root
                or (spec.base / "state" / "workspace" / "backend" / "data")
            )
        )
    )
    output_root = (
        Path(os.path.abspath(os.fspath(args.output_root)))
        if args.output_root is not None
        else None
    )
    registry_path = sealed_official_registry_path(spec.release_dir)
    release_identity, release_witnesses, release_validator = _release_bundle(
        snapshot,
        spec,
        runner=runner,
        http_get=http_get,
    )
    return run_acceptance(
        project_id=args.project_id,
        data_root=data_root,
        registry_path=registry_path,
        release_identity=release_identity,
        release_witnesses=release_witnesses,
        release_validator=release_validator,
        write=False,
        output_root=output_root,
        run_id=args.run_id,
        source_job_id=args.source_job_id,
    )


def _execute(args: argparse.Namespace) -> dict[str, Any]:
    if not args.write:
        return _execute_dry_run(args)
    if (
        args.release_base is not None
        or args.data_root is not None
        or args.output_root is not None
    ):
        raise AcceptanceError(
            "ACCEPTANCE_WRITE_PATH_OVERRIDE_FORBIDDEN",
            "write模式只允许current默认发布、数据与回执路径",
        )
    if str(os.environ.get("ZF_COMPLIANCE_ROOT") or "").strip():
        raise AcceptanceError(
            "ACCEPTANCE_WRITE_REGISTRY_OVERRIDE_FORBIDDEN",
            "write模式禁止覆盖正式标准registry根目录",
        )
    return run_current_runtime_acceptance_write(
        project_id=args.project_id,
        run_id=args.run_id,
        source_job_id=args.source_job_id,
    )


def _failure_payload(code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "machine_code": code,
        "message": message,
        "model_calls": 0,
        "provider_probes": 0,
    }


def main(
    argv: Sequence[str] | None = None,
) -> int:
    try:
        args = _parser().parse_args(argv)
        result = _execute(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except SystemExit as exc:
        if exc.code in {None, 0}:
            return 0
        print(
            json.dumps(
                _failure_payload(
                    "ACCEPTANCE_ARGUMENTS_INVALID",
                    "验收命令参数无效，已安全停止且未发布回执",
                ),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    except KeyboardInterrupt:
        print(
            json.dumps(
                _failure_payload("ACCEPTANCE_INTERRUPTED", "验收被中断"),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 130
    except (AcceptanceError, LaunchError, SupervisorError, ReleaseBuildError) as exc:
        print(
            json.dumps(
                _failure_payload(exc.code, exc.message),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    except Exception:  # noqa: BLE001 - CLI boundary redacts all unexpected details
        print(
            json.dumps(
                _failure_payload(
                    "ACCEPTANCE_UNEXPECTED_FAILURE",
                    "验收发生未预期错误，已安全停止且未发布回执",
                ),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
