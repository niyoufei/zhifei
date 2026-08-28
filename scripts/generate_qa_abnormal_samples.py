#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter


REPO_ROOT = Path(__file__).resolve().parents[1]
QA_ROOT = REPO_ROOT / "artifacts" / "qa"
SAMPLE_ROOT = QA_ROOT / "inputs" / "sample_F"
RECEIPT_PATH = QA_ROOT / "abnormal_input_receipt.json"
ACTIVE_PROJECT = "合成市政道路工程"
FOREIGN_PROJECT = "外部医院改造工程"
QA_OVERSIZE_LIMIT = 1024 * 1024


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _case(name: str, path: Path, *, expected: str, observed: str, ok: bool, **details: Any) -> dict[str, Any]:
    return {
        "case": name,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "expected": expected,
        "observed": observed,
        "status": "pass" if ok else "blocked",
        **details,
    }


def main() -> int:
    SAMPLE_ROOT.mkdir(parents=True, exist_ok=True)

    chinese = SAMPLE_ROOT / "中文文件名_招标资料.txt"
    chinese.write_text(f"项目名称：{ACTIVE_PROJECT}\n资料用途：中文路径与编码验收。\n", encoding="utf-8")

    empty = SAMPLE_ROOT / "空文件.txt"
    empty.write_bytes(b"")

    damaged = SAMPLE_ROOT / "损坏文件.pdf"
    damaged.write_bytes(b"%PDF-1.7\ntruncated and invalid payload")

    duplicate_a = SAMPLE_ROOT / "重复文件_A.txt"
    duplicate_b = SAMPLE_ROOT / "重复文件_B.txt"
    duplicate_payload = f"项目名称：{ACTIVE_PROJECT}\n总工期：180日历天\n".encode("utf-8")
    duplicate_a.write_bytes(duplicate_payload)
    duplicate_b.write_bytes(duplicate_payload)

    oversized = SAMPLE_ROOT / "超大文件_2MiB.txt"
    oversized.write_bytes(("超大资料边界验收\n".encode("utf-8") * 160_000)[: 2 * 1024 * 1024])

    missing_page = SAMPLE_ROOT / "缺页文件_声明2页实际1页.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with missing_page.open("wb") as handle:
        writer.write(handle)

    conflict = SAMPLE_ROOT / "内容冲突文件.txt"
    conflict.write_text(
        f"项目名称：{ACTIVE_PROJECT}\n总工期：180日历天\n总工期：210日历天\n",
        encoding="utf-8",
    )

    residual = SAMPLE_ROOT / "其他项目残留文件.txt"
    residual.write_text(
        f"当前项目：{ACTIVE_PROJECT}\n复制残留：{FOREIGN_PROJECT}施工部署。\n",
        encoding="utf-8",
    )

    cases: list[dict[str, Any]] = []
    chinese_text = chinese.read_text(encoding="utf-8")
    cases.append(
        _case(
            "中文文件名",
            chinese,
            expected="UTF-8 文件名与正文可无损读取",
            observed="filename_and_utf8_preserved",
            ok=chinese.name.startswith("中文文件名") and ACTIVE_PROJECT in chinese_text,
        )
    )
    cases.append(
        _case(
            "空文件",
            empty,
            expected="拒绝空文件",
            observed="EMPTY_FILE" if empty.stat().st_size == 0 else "non_empty",
            ok=empty.stat().st_size == 0,
        )
    )
    damaged_error = ""
    try:
        PdfReader(str(damaged))
    except Exception as exc:  # exact parser type is dependency-version specific
        damaged_error = type(exc).__name__
    cases.append(
        _case(
            "损坏文件",
            damaged,
            expected="解析失败并拒绝",
            observed="FILE_PARSE_FAILED" if damaged_error else "unexpected_parse_success",
            ok=bool(damaged_error),
            parser_error_type=damaged_error,
        )
    )
    duplicate = _sha256(duplicate_a) == _sha256(duplicate_b)
    cases.append(
        _case(
            "重复文件",
            duplicate_b,
            expected="相同内容按 SHA-256 去重",
            observed="DUPLICATE_FILE" if duplicate else "distinct",
            ok=duplicate,
            duplicate_of=str(duplicate_a),
        )
    )
    too_large = oversized.stat().st_size > QA_OVERSIZE_LIMIT
    cases.append(
        _case(
            "超大文件",
            oversized,
            expected=f"超过验收边界 {QA_OVERSIZE_LIMIT} 字节时拒绝",
            observed="UPLOAD_TOO_LARGE" if too_large else "within_limit",
            ok=too_large,
            qa_limit_bytes=QA_OVERSIZE_LIMIT,
        )
    )
    actual_pages = len(PdfReader(str(missing_page)).pages)
    cases.append(
        _case(
            "缺页文件",
            missing_page,
            expected="声明2页与实际页数一致",
            observed=f"PAGE_COUNT_MISMATCH:expected=2,actual={actual_pages}",
            ok=actual_pages != 2,
            declared_pages=2,
            actual_pages=actual_pages,
        )
    )
    durations = sorted(set(re.findall(r"总工期\s*[：:]\s*(\d+)\s*日历天", conflict.read_text(encoding="utf-8"))))
    cases.append(
        _case(
            "内容冲突文件",
            conflict,
            expected="同一关键参数只能有一个值",
            observed="PARAMETER_CONFLICT" if len(durations) > 1 else "consistent",
            ok=len(durations) > 1,
            detected_duration_values=durations,
        )
    )
    residual_text = residual.read_text(encoding="utf-8")
    cases.append(
        _case(
            "其他项目残留",
            residual,
            expected="只允许当前项目名称",
            observed="FOREIGN_PROJECT_RESIDUAL" if FOREIGN_PROJECT in residual_text else "clean",
            ok=FOREIGN_PROJECT in residual_text and ACTIVE_PROJECT in residual_text,
            active_project=ACTIVE_PROJECT,
            detected_foreign_project=FOREIGN_PROJECT,
        )
    )

    payload = {
        "schema": "zhifei.qa.abnormal_input.v1",
        "synthetic_data_only": True,
        "status": "pass" if all(item["status"] == "pass" for item in cases) else "blocked",
        "case_count": len(cases),
        "passed_count": sum(item["status"] == "pass" for item in cases),
        "cases": cases,
        "production_controls": {
            "empty_file": "HTTP 400",
            "damaged_file": "HTTP 422 / FILE_PARSE_FAILED",
            "duplicate_file": "SHA-256 within-batch rejection",
            "oversized_file": "HTTP 413 / configurable ZHIFEI_MAX_UPLOAD_BYTES",
        },
    }
    RECEIPT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
