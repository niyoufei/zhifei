from backend.zhifei_autoplan.system_autonomy_permissions import (
    ApprovalLevel,
    GovernanceMode,
    PermissionDimension,
    PermissionRequest,
    check_permission_request,
)


def test_code_change_no_runtime_blocks_runtime_dimensions():
    result = check_permission_request(
        PermissionRequest(
            mode=GovernanceMode.CODE_CHANGE_NO_RUNTIME,
            approval_level=ApprovalLevel.A3_CODE_CHANGE,
            requested_dimensions=(
                PermissionDimension.CODE_MODIFY,
                PermissionDimension.SERVICE_START,
                PermissionDimension.ENDPOINT_ACCESS,
                PermissionDimension.OLLAMA,
                PermissionDimension.MODEL_INFERENCE,
                PermissionDimension.PROMPT_INPUT,
            ),
            evidence_refs=("SYSTEM-AUTONOMY-006",),
        )
    )

    assert result.allowed is False
    assert PermissionDimension.SERVICE_START in result.blocked_dimensions
    assert PermissionDimension.ENDPOINT_ACCESS in result.blocked_dimensions
    assert PermissionDimension.OLLAMA in result.blocked_dimensions
    assert PermissionDimension.MODEL_INFERENCE in result.blocked_dimensions
    assert PermissionDimension.PROMPT_INPUT in result.blocked_dimensions


def test_static_permission_requires_evidence_refs():
    result = check_permission_request(
        PermissionRequest(
            mode=GovernanceMode.CODE_CHANGE_NO_RUNTIME,
            approval_level=ApprovalLevel.A3_CODE_CHANGE,
            requested_dimensions=(PermissionDimension.CODE_MODIFY,),
        )
    )

    assert result.allowed is False
    assert result.missing_evidence == ("evidence_refs",)


def test_docs_only_does_not_allow_code_modify():
    result = check_permission_request(
        PermissionRequest(
            mode=GovernanceMode.DOCS_ONLY,
            approval_level=ApprovalLevel.A1_DOCS_WRITE,
            requested_dimensions=(PermissionDimension.CODE_MODIFY,),
            evidence_refs=("docs-only",),
        )
    )

    assert result.allowed is False
    assert PermissionDimension.CODE_MODIFY in result.blocked_dimensions
