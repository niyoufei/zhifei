from __future__ import annotations

from backend.zhifei_autoplan import logo_runtime


def test_logo_resolution_is_external_io_free_by_default(monkeypatch):
    monkeypatch.delenv("ZF_EXTERNAL_LOGO_FETCH_ENABLED", raising=False)
    monkeypatch.setattr(logo_runtime, "_load_locked_logo", lambda project_id: None)
    monkeypatch.setattr(
        logo_runtime, "find_latest_ingested_logo", lambda project_id=None: None
    )
    calls: list[str] = []
    monkeypatch.setattr(
        logo_runtime,
        "download_logo_from_url",
        lambda url, timeout=20: calls.append(f"url:{url}"),
    )
    monkeypatch.setattr(
        logo_runtime,
        "resolve_logo_from_domain",
        lambda domain: calls.append(f"domain:{domain}"),
    )
    monkeypatch.setattr(
        logo_runtime,
        "resolve_logo_from_wikipedia",
        lambda company: calls.append(f"wiki:{company}"),
    )

    result = logo_runtime.resolve_logo(
        bidder_company="示例公司",
        bidder_domain="example.com",
        logo_url="https://example.com/logo.png",
        project_id="project-1",
    )

    assert result is None
    assert calls == []


def test_locked_local_logo_precedes_external_sources(monkeypatch, tmp_path):
    monkeypatch.delenv("ZF_EXTERNAL_LOGO_FETCH_ENABLED", raising=False)
    local_logo = tmp_path / "logo.png"
    local_logo.write_bytes(b"local-logo")
    monkeypatch.setattr(
        logo_runtime, "_load_locked_logo", lambda project_id: str(local_logo)
    )
    monkeypatch.setattr(
        logo_runtime,
        "download_logo_from_url",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("external logo fetch must not run")
        ),
    )

    assert (
        logo_runtime.resolve_logo(
            logo_url="https://example.com/logo.png", project_id="project-1"
        )
        == str(local_logo)
    )


def test_external_logo_fetch_requires_explicit_server_opt_in(monkeypatch):
    monkeypatch.setenv("ZF_EXTERNAL_LOGO_FETCH_ENABLED", "1")
    monkeypatch.setattr(logo_runtime, "_load_locked_logo", lambda project_id: None)
    monkeypatch.setattr(
        logo_runtime, "find_latest_ingested_logo", lambda project_id=None: None
    )
    monkeypatch.setattr(
        logo_runtime,
        "download_logo_from_url",
        lambda url, timeout=20: "/tmp/admitted-logo.png",
    )
    locks: list[dict[str, object]] = []
    monkeypatch.setattr(
        logo_runtime,
        "_lock_logo",
        lambda project_id, logo_path, **kwargs: locks.append(
            {"project_id": project_id, "logo_path": logo_path, **kwargs}
        ),
    )

    result = logo_runtime.resolve_logo(
        logo_url="https://example.com/logo.png", project_id="project-1"
    )

    assert result == "/tmp/admitted-logo.png"
    assert locks[0]["source"] == "url"
