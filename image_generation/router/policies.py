"""Static safety policy flags for local image generation routing."""

LOCAL_ONLY = True
VIDEO_GENERATION_ENABLED = False
ALLOW_AUTO_INFERENCE = False
ALLOW_AUTO_COMFYUI_START = False
ALLOW_REMOTE_API_MODELS = False


def assert_static_policy() -> dict:
    """Return the enforced static policy surface for callers and checks."""

    return {
        "LOCAL_ONLY": LOCAL_ONLY,
        "VIDEO_GENERATION_ENABLED": VIDEO_GENERATION_ENABLED,
        "ALLOW_AUTO_INFERENCE": ALLOW_AUTO_INFERENCE,
        "ALLOW_AUTO_COMFYUI_START": ALLOW_AUTO_COMFYUI_START,
        "ALLOW_REMOTE_API_MODELS": ALLOW_REMOTE_API_MODELS,
    }
