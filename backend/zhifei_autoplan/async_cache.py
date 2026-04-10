from __future__ import annotations

import asyncio
import copy
from typing import Any, Callable


class AsyncThreadCache:
    """
    Deduplicate identical to_thread calls inside one orchestration run.

    Completed results are cached in ``items``.
    In-flight identical requests share the same task and do not fan out.
    """

    def __init__(
        self,
        *,
        items: dict[str, Any] | None = None,
        stats: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> None:
        self.enabled = bool(enabled)
        self.items = items if isinstance(items, dict) else {}
        self.stats = stats if isinstance(stats, dict) else {}
        self.stats.setdefault("hits", 0)
        self.stats.setdefault("misses", 0)
        self.stats.setdefault("stores", 0)
        self.stats.setdefault("coalesced", 0)
        self._lock = asyncio.Lock()
        self._inflight: dict[str, asyncio.Task] = {}

    async def get_or_run(
        self,
        key: str,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if not self.enabled:
            return await asyncio.to_thread(fn, *args, **kwargs)

        key = str(key or "").strip()
        owner = False
        task: asyncio.Task | None = None

        async with self._lock:
            if key in self.items:
                self.stats["hits"] = int(self.stats.get("hits") or 0) + 1
                return copy.deepcopy(self.items[key])

            task = self._inflight.get(key)
            if task is None:
                self.stats["misses"] = int(self.stats.get("misses") or 0) + 1
                task = asyncio.create_task(asyncio.to_thread(fn, *args, **kwargs))
                self._inflight[key] = task
                owner = True
            else:
                self.stats["coalesced"] = int(self.stats.get("coalesced") or 0) + 1

        try:
            result = await task
        except Exception:
            if owner:
                async with self._lock:
                    if self._inflight.get(key) is task:
                        self._inflight.pop(key, None)
            raise

        async with self._lock:
            if owner:
                if key not in self.items:
                    self.items[key] = copy.deepcopy(result)
                    self.stats["stores"] = int(self.stats.get("stores") or 0) + 1
                if self._inflight.get(key) is task:
                    self._inflight.pop(key, None)
            elif key in self.items:
                self.stats["hits"] = int(self.stats.get("hits") or 0) + 1
                return copy.deepcopy(self.items[key])

        return copy.deepcopy(result)
