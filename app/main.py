"""
Compatibility app entrypoint.

Canonical backend service now lives at `backend.app.main:app`.
This module keeps `app.main:app` usable for older scripts/tools.
"""

from backend.app.main import app  # re-export canonical FastAPI app
