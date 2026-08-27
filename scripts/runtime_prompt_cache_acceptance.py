#!/usr/bin/env python3
from __future__ import annotations

"""Run a minimal, privacy-safe Anthropic prompt-cache acceptance.

The synthetic prefix is just over the provider's cache minimum and the two
dynamic requests ask for only a tiny acknowledgement.  Credentials are loaded
locally, never printed, and the JSON report contains usage/cost metadata only.
"""

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.zhifei_autoplan.local_env import load_local_env
from backend.zhifei_autoplan.providers.anthropic_provider import AnthropicProvider


def _safe_result(result: dict[str, Any]) -> dict[str, Any]:
    usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
    cache = result.get("cache") if isinstance(result.get("cache"), dict) else {}
    return {
        "model": str(result.get("model") or ""),
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "cache_creation_input_tokens": int(
            usage.get("cache_creation_input_tokens") or 0
        ),
        "cache_read_input_tokens": int(usage.get("cache_read_input_tokens") or 0),
        "cache_hit_ratio": float(usage.get("cache_hit_ratio") or 0.0),
        "prewarm_cache_creation_input_tokens": int(
            cache.get("prewarm_cache_creation_input_tokens") or 0
        ),
        "prewarm_cache_read_input_tokens": int(
            cache.get("prewarm_cache_read_input_tokens") or 0
        ),
        "prewarm_effective": bool(cache.get("prewarm_effective")),
        "request_duration_ms": int(result.get("request_duration_ms") or 0),
        "estimated_cost_usd": float(result.get("estimated_cost_usd") or 0.0),
        "estimated_no_cache_cost_usd": float(
            result.get("estimated_no_cache_cost_usd") or 0.0
        ),
        "estimated_savings_ratio": float(
            result.get("estimated_savings_ratio") or 0.0
        ),
        "ok": bool(str(result.get("text") or "").strip()) and not result.get("error"),
        "error": str(result.get("error") or "") or None,
    }


async def _run(env_file: Path, output: Path) -> dict[str, Any]:
    load_local_env(env_file)
    api_key = str(os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    model = str(
        os.environ.get("ANTHROPIC_TEXT_MODEL_DRAFT") or "claude-sonnet-5"
    ).strip()
    if not api_key:
        raise RuntimeError("anthropic_credential_not_configured")

    output.parent.mkdir(parents=True, exist_ok=True)
    os.environ["ZHIFEI_CLAUDE_USAGE_LOG"] = str(output.with_suffix(".events.jsonl"))
    nonce = uuid.uuid4().hex[:12]
    stable_lines = [
        (
            f"Synthetic construction rule {index:04d}: use verified facts only; "
            "protect privacy; keep scoring, Word layout, and graphics constraints stable."
        )
        # 28 lines are intentionally only a little above Sonnet 5's current
        # 1,024-token cache minimum, keeping the paid acceptance tiny.
        for index in range(28)
    ]
    stable = "\n".join(stable_lines) + f"\nAcceptance nonce: {nonce}"
    shared = (
        "Synthetic project context: no real location, organization, person, tender, "
        "drawing, bill of quantities, or historical chapter content is included."
    )
    provider = AnthropicProvider(api_key=api_key, model=model)
    common = {
        "stable_system_prompt": stable,
        "shared_context_prompt": shared,
        "cache_mode": "section",
        "project_id": "prompt-cache-minimal-acceptance",
        "task_type": "prompt_cache_minimal_acceptance",
        "timeout": 60.0,
        "max_tokens": 8,
    }
    first = await provider.complete("Reply only: OK-A", **common)
    second = await provider.complete("Reply only: OK-B", **common)
    report = {
        "schema_version": "prompt-cache-minimal-acceptance-v1",
        "credentials_exposed": False,
        "contains_project_material": False,
        "first": _safe_result(first),
        "second": _safe_result(second),
    }
    report["passed"] = bool(
        report["first"]["ok"]
        and report["second"]["ok"]
        and report["first"]["prewarm_cache_creation_input_tokens"] > 0
        and report["second"]["cache_read_input_tokens"] > 0
    )
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output.chmod(0o600)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="极小 Claude Prompt Cache 真实验收")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = asyncio.run(_run(args.env_file.resolve(), args.output.resolve()))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "credentials_exposed": False,
                    "error_type": type(exc).__name__,
                },
                ensure_ascii=False,
            )
        )
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
