from __future__ import annotations

import subprocess
import time

from backend.zhifei_autoplan.job_store import _is_process_alive


def test_is_process_alive_treats_zombie_process_as_not_alive() -> None:
    proc = subprocess.Popen(["/bin/sh", "-c", "exit 0"])
    try:
        time.sleep(0.1)
        assert _is_process_alive(proc.pid) is False
    finally:
        proc.wait(timeout=1)
