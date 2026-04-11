from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_scripts_directory_has_no_duplicate_copy_suffix_files() -> None:
    offenders = sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / "scripts").glob("* 2.sh")
    )
    assert offenders == []


def test_repo_root_has_no_stray_test_python_scripts() -> None:
    offenders = sorted(
        str(path.relative_to(ROOT))
        for path in ROOT.glob("test_*.py")
    )
    assert offenders == []
