from __future__ import annotations

from backend.zhifei_autoplan import generate_payload_service


def test_prepare_generate_payload_applies_stamp_before_signature():
    seen_for_signature: list[dict] = []

    def _prepare(raw_payload: dict):
        return {**raw_payload, "prepared": True}

    def _stamp(payload: dict):
        payload["_contract_stamp"] = {"request_contract_version": "v1"}

    def _signature(payload: dict) -> str:
        seen_for_signature.append(dict(payload))
        return "sig-1"

    out = generate_payload_service.prepare_generate_payload(
        raw_payload={"topic": "t-1"},
        prepare_runtime_payload_fn=_prepare,
        attach_contract_stamp_fn=_stamp,
        compute_job_signature_fn=_signature,
    )

    assert out.payload == {
        "topic": "t-1",
        "prepared": True,
        "_contract_stamp": {"request_contract_version": "v1"},
    }
    assert out.request_signature == "sig-1"
    assert seen_for_signature == [out.payload]
