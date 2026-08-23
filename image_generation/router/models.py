"""Static model and route types for local image generation planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ImageTaskType(str, Enum):
    """Supported image task classes for construction document generation."""

    TECHNICAL_BID_ILLUSTRATION = "technical_bid_illustration"
    REALISTIC_CONSTRUCTION_SCENE = "realistic_construction_scene"
    SITE_PHOTO_EDIT = "site_photo_edit"
    SAFETY_CIVILIZATION_SCENE = "safety_civilization_scene"
    TEMPORARY_FACILITY_LAYOUT = "temporary_facility_layout"
    MACHINERY_OPERATION_SCENE = "machinery_operation_scene"
    MATERIAL_YARD_SCENE = "material_yard_scene"
    CONSTRUCTION_PROCESS_DIAGRAM = "construction_process_diagram"
    BIRDSEYE_RENDER = "birdseye_render"
    COVER_IMAGE = "cover_image"
    CHINESE_SIGNAGE_SCENE = "chinese_signage_scene"


class ModelRole(str, Enum):
    """Local model roles known by the static router."""

    QWEN_IMAGE_PRIMARY = "qwen_image_primary"
    QWEN_IMAGE_EDIT = "qwen_image_edit"
    FLUX_REALISTIC = "flux_realistic"
    QWEN_IMAGE_EDIT_LATEST_CANDIDATE = "qwen_image_edit_latest_candidate"
    DISABLED_VIDEO = "disabled_video"


@dataclass(frozen=True)
class ImageModelConfig:
    """Static configuration for one local image model role."""

    role: str
    repo_id: str
    local_cache_status: str
    runtime_status: str
    primary_use: list[str]
    supports_chinese_text: bool
    supports_photo_edit: bool
    supports_realistic_render: bool
    supports_controlnet: bool
    is_active: bool
    notes: str


@dataclass(frozen=True)
class ImageRouteDecision:
    """Static routing decision for an image task."""

    task_type: str
    selected_role: str
    selected_repo_id: str
    fallback_role: str
    prompt_template_key: str
    workflow_key: str
    reasons: list[str]
    warnings: list[str]
