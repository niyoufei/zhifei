"""Report formatting helpers for the R5B static ComfyUI precheck scaffold."""

from __future__ import annotations

from image_generation.precheck.comfyui_precheck_models import (
    PrecheckReport,
    PrecheckStatus,
)


def report_to_dict(report: PrecheckReport) -> dict:
    """Return the machine-readable report dict."""

    return report.as_dict()


def blocked_items(report: PrecheckReport) -> list[dict]:
    """Return failed or blocked static items."""

    return [
        result.as_dict()
        for result in report.results
        if result.status in {PrecheckStatus.FAIL, PrecheckStatus.BLOCKED}
    ]


def next_authorization_required(report: PrecheckReport) -> list[dict]:
    """Return future actions that need explicit user authorization."""

    return [item.as_dict() for item in report.explicit_authorizations_required]


def human_readable_summary(report: PrecheckReport) -> str:
    """Format a concise static report without executing runtime checks."""

    blocked = blocked_items(report)
    auth = next_authorization_required(report)
    lines = [
        f"Node: {report.node}",
        f"Status: {report.status.value}",
        "Scope: R5B static scaffold only.",
        "Runtime: ComfyUI is not started; localhost is not accessed; ports are not checked.",
        "Models: model weights, .env, and ~/.ollama/models are not read.",
        "Generation: no workflow dry run, inference, image generation, or video deployment.",
        "Next: R5C may review static PR scope; later explicit authorization is required for environment checks.",
        "R6: controlled single-image generation is a later explicit authorization boundary.",
        f"Blocked items: {len(blocked)}",
        f"Next authorizations required: {len(auth)}",
    ]
    if blocked:
        lines.append("Blocked detail:")
        lines.extend(f"- {item['check_id']}: {item['message']}" for item in blocked)
    return "\n".join(lines)
