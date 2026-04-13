from __future__ import annotations

from backend.zhifei_autoplan import generate_sync_postprocess_service


def test_postprocess_generate_sync_results_skips_single_variant():
    calls: list[str] = []
    generate_sync_postprocess_service.postprocess_generate_sync_results(
        payload={},
        results=[{"sections": []}],
        load_params_fn=lambda: calls.append("params") or {},
        rebuild_postprocessed_fn=lambda *args, **kwargs: calls.append("rebuild"),
        workspace_dir_from_payload_fn=lambda payload: "/tmp/ws",
        compute_variant_similarity_fn=lambda *args, **kwargs: calls.append("similarity") or {},
        apply_diversity_autofix_fn=lambda *args, **kwargs: False,
    )
    assert calls == []


def test_postprocess_generate_sync_results_applies_autofix_and_rebuilds():
    rebuilt: list[dict] = []
    reports = [
        {"ok": False, "flagged": [{"title": "施工部署", "pair": "v1_v2"}]},
        {"ok": True, "flagged": []},
    ]
    similarity_calls = {"count": 0}

    def _compute(results, **kwargs):
        idx = similarity_calls["count"]
        similarity_calls["count"] += 1
        return reports[idx]

    def _apply(sec, **kwargs):
        sec["auto_remediated"] = "diversity_autofix"
        return True

    generate_sync_postprocess_service.postprocess_generate_sync_results(
        payload={"params_override": {"variant_diversity": {"auto_fix_rounds": 1}}},
        results=[
            {"sections": [{"title": "施工部署", "content": "第一版"}]},
            {"sections": [{"title": "施工部署", "content": "第二版"}]},
        ],
        load_params_fn=lambda: {"variant_diversity": {"auto_fix_rounds": 1}},
        rebuild_postprocessed_fn=lambda results, **kwargs: rebuilt.append({"results": results, "kwargs": kwargs}),
        workspace_dir_from_payload_fn=lambda payload: "/tmp/ws",
        compute_variant_similarity_fn=_compute,
        apply_diversity_autofix_fn=_apply,
    )

    assert similarity_calls["count"] == 2
    assert rebuilt[0]["kwargs"]["report"] == {"ok": True, "flagged": []}
    assert rebuilt[0]["kwargs"]["workspace_dir"] == "/tmp/ws"
    assert rebuilt[0]["results"][1]["sections"][0]["auto_remediated"] == "diversity_autofix"


def test_postprocess_generate_sync_results_swallows_similarity_failures():
    calls: list[str] = []
    generate_sync_postprocess_service.postprocess_generate_sync_results(
        payload={},
        results=[{"sections": []}, {"sections": []}],
        load_params_fn=lambda: {},
        rebuild_postprocessed_fn=lambda *args, **kwargs: calls.append("rebuild"),
        workspace_dir_from_payload_fn=lambda payload: "/tmp/ws",
        compute_variant_similarity_fn=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        apply_diversity_autofix_fn=lambda *args, **kwargs: False,
    )
    assert calls == []

