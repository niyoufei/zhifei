from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PrecheckContext:
    repo_path: str
    branch: str
    head: str
    origin_head: str
    head_tree: str
    origin_tree: str
    working_tree_clean: bool
    expected_head: str
    expected_tree: str
    expected_tag: str
    local_tag_target: str
    remote_tag_target: str
    ports: dict[str, str] = field(default_factory=dict)
    processes: dict[str, bool] = field(default_factory=dict)
    runtime_locks: dict[str, bool] = field(default_factory=dict)
    allow_conditional_cleanup: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PrecheckContext":
        return cls(
            repo_path=str(data.get("repo_path", "")),
            branch=str(data.get("branch", "")),
            head=str(data.get("head", "")),
            origin_head=str(data.get("origin_head", "")),
            head_tree=str(data.get("head_tree", "")),
            origin_tree=str(data.get("origin_tree", "")),
            working_tree_clean=bool(data.get("working_tree_clean", False)),
            expected_head=str(data.get("expected_head", "")),
            expected_tree=str(data.get("expected_tree", "")),
            expected_tag=str(data.get("expected_tag", "")),
            local_tag_target=str(data.get("local_tag_target", "")),
            remote_tag_target=str(data.get("remote_tag_target", "")),
            ports={str(key): str(value) for key, value in dict(data.get("ports") or {}).items()},
            processes={str(key): bool(value) for key, value in dict(data.get("processes") or {}).items()},
            runtime_locks={str(key): bool(value) for key, value in dict(data.get("runtime_locks") or {}).items()},
            allow_conditional_cleanup=bool(data.get("allow_conditional_cleanup", False)),
        )
