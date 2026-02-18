from __future__ import annotations

from typing import Dict, Any


class BaseProvider:
    name: str = "base"

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError
