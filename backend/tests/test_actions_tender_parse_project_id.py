from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from starlette.datastructures import UploadFile


class _ParsedTender:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self):
        return dict(self._payload)


class _ParserStub:
    def __init__(self, payload):
        self._payload = payload

    async def parse(self, paths):
        return _ParsedTender(self._payload)


@pytest.mark.asyncio
async def test_actions_tender_parse_prefers_requested_project_id_over_parsed_code():
    from backend.app.routers.actions_bridge import actions_tender_parse

    file_obj = UploadFile(filename="招标文件.pdf", file=BytesIO(b"fake pdf bytes"))
    parser_payload = {
        "project_name": "合肥新桥机场海关业务用房改造项目",
        "project_code": "2026BFJGZ50048",
        "items": [],
        "style": {},
    }

    with patch("backend.app.routers.actions_bridge._auth_actions_key", return_value=None), \
         patch("backend.app.routers.actions_bridge._resolve_workspace_context", return_value={"workspace_dir": "ws"}), \
         patch("backend.app.routers.actions_bridge._save_upload", return_value="dummy.pdf"), \
         patch("backend.app.routers.actions_bridge.TenderParser", return_value=_ParserStub(parser_payload)), \
         patch("backend.app.routers.actions_bridge.build_bidding_format_config_from_style", return_value={}), \
         patch("backend.app.routers.actions_bridge.save_tender_matrix", return_value="ws/projects/release_reg_case/tender_matrix.json") as save_matrix, \
         patch("backend.app.routers.actions_bridge.save_bidding_format_config", return_value="ws/projects/release_reg_case/bidding_format_config.json") as save_format:
        result = await actions_tender_parse(
            files=[file_obj],
            project_id="release_reg_case",
            session_id="release_reg_case",
            workspace_dir=None,
            x_actions_key="test-key",
        )

    assert result["ok"] is True
    assert result["project_id"] == "release_reg_case"
    assert result["project_code"] == "2026BFJGZ50048"
    assert save_matrix.call_args.kwargs["project_id"] == "release_reg_case"
    assert save_format.call_args.kwargs["project_id"] == "release_reg_case"
