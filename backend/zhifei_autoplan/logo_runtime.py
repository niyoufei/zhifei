from __future__ import annotations

import hashlib
import json
import ipaddress
import re
import socket
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from urllib.parse import urlparse, urljoin


ASSET_DIR = Path("backend/data/autoplan/assets")
ASSET_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(s: str, limit: int = 80) -> str:
    out = re.sub(r"[^A-Za-z0-9_\\-\\.]+", "_", (s or "").strip())
    return out[:limit] or "asset"


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def find_latest_ingested_logo(project_id: str | None = None) -> Optional[str]:
    """
    Best-effort: find the latest uploaded logo from ingest audit records.
    Convention: filename contains 'logo/标志/标识/徽标' and ingest tags include 'logo'.
    """
    audit_path = Path("backend/data/audit/ingest.jsonl")
    if not audit_path.exists():
        return None
    try:
        lines = audit_path.read_text(encoding="utf-8", errors="ignore").splitlines()[::-1]
    except Exception:
        return None

    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    for ln in lines[:400]:
        try:
            rec = json.loads(ln)
        except Exception:
            continue
        if pid is not None and str(rec.get("project_id") or "").strip() != pid:
            continue
        tags = rec.get("tags") or []
        if "logo" not in tags:
            continue
        p = rec.get("preview_saved_as") or rec.get("saved_as")
        if not isinstance(p, str) or not p.strip():
            continue
        path = Path(p)
        if path.exists() and path.is_file():
            return str(path)
    return None


def _load_locked_logo(project_id: str | None) -> Optional[str]:
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    if not pid:
        return None
    try:
        from backend.zhifei_autoplan.branding_store import load_branding

        rec = load_branding(pid) or {}
        for key in ("logo_path", "logo_embed_path", "logo_raw_path"):
            p = rec.get(key)
            if isinstance(p, str) and p.strip():
                path = Path(p)
                if path.exists() and path.is_file():
                    return str(path)
    except Exception:
        return None
    return None


def _lock_logo(project_id: str | None, logo_path: str, *, source: str, bidder_company: str | None = None, bidder_domain: str | None = None, logo_url: str | None = None) -> None:
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    if not pid:
        return
    try:
        from backend.zhifei_autoplan.branding_store import update_branding

        update_branding(
            pid,
            {
                "bidder_company": bidder_company,
                "bidder_domain": bidder_domain,
                "logo_url": logo_url,
                "logo_raw_path": str(logo_path),
                "logo_path": str(logo_path),
                "logo_source": str(source),
            },
            merge=True,
        )
    except Exception:
        return


def _host_is_public(host: str) -> bool:
    h = (host or "").strip()
    if not h:
        return False
    low = h.lower()
    if low in {"localhost"} or low.endswith(".local"):
        return False
    # If host is an IP literal
    try:
        ip = ipaddress.ip_address(h)
        return bool(getattr(ip, "is_global", False))
    except Exception:
        pass
    try:
        infos = socket.getaddrinfo(h, None)
        ips = {info[4][0] for info in infos if info and info[4]}
        if not ips:
            return False
        for ip_str in ips:
            try:
                ip = ipaddress.ip_address(ip_str)
                if not getattr(ip, "is_global", False):
                    return False
            except Exception:
                return False
        return True
    except Exception:
        return False


def _safe_fetch(url: str, timeout: int = 20, max_bytes: int = 2_000_000, max_redirects: int = 3) -> tuple[bytes, str] | None:
    """
    Safe HTTP fetch for external images:
    - http/https only
    - block private/loopback/link-local hosts (basic SSRF guard)
    - size limit
    - manual redirects with re-check
    """
    u = (url or "").strip()
    if not u:
        return None
    for _ in range(max(0, int(max_redirects)) + 1):
        parsed = urlparse(u)
        if parsed.scheme not in {"http", "https"}:
            return None
        host = parsed.hostname or ""
        if not _host_is_public(host):
            return None
        try:
            r = requests.get(
                u,
                timeout=timeout,
                headers={"User-Agent": "autoplan/0.1"},
                stream=True,
                allow_redirects=False,
            )
        except Exception:
            return None
        if r.status_code in {301, 302, 303, 307, 308}:
            loc = r.headers.get("Location")
            if not loc:
                return None
            u = urljoin(u, loc)
            continue
        if r.status_code != 200:
            return None
        ctype = (r.headers.get("Content-Type") or "").lower()
        chunks = []
        total = 0
        try:
            for ch in r.iter_content(chunk_size=64 * 1024):
                if not ch:
                    continue
                chunks.append(ch)
                total += len(ch)
                if total > max_bytes:
                    return None
        finally:
            try:
                r.close()
            except Exception:
                pass
        return b"".join(chunks), ctype
    return None


def download_logo_from_url(url: str, timeout: int = 20) -> Optional[str]:
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        fetched = _safe_fetch(url.strip(), timeout=timeout)
        if not fetched:
            return None
        data, ctype = fetched
        if "image" not in ctype and not re.search(r"\\.(png|jpg|jpeg|webp|gif|svg)(\\?|$)", url, re.I):
            return None
        if len(data) < 200:
            return None
        digest = _sha256(data)[:10]
        ext = "png"
        if "svg" in ctype or url.lower().endswith(".svg"):
            ext = "svg"
        elif "icon" in ctype or url.lower().endswith(".ico"):
            ext = "ico"
        elif "webp" in ctype or url.lower().endswith(".webp"):
            ext = "webp"
        elif "jpeg" in ctype or url.lower().endswith(".jpg") or url.lower().endswith(".jpeg"):
            ext = "jpg"
        out = ASSET_DIR / f"logo_{digest}.{ext}"
        out.write_bytes(data)
        return str(out)
    except Exception:
        return None


def prepare_logo_for_embedding(path: str) -> Optional[str]:
    """
    Convert logo into a docx-friendly raster format when possible.
    - python-docx does not support svg; ico/webp/gif may fail depending on version.
    Returns a PNG/JPG path or None.
    """
    try:
        p = Path(str(path))
        if not p.exists() or not p.is_file():
            return None
        suf = p.suffix.lower()
        if suf in {".png", ".jpg", ".jpeg"}:
            return str(p)
        # Try PIL rasterization/conversion (works for ico/webp/gif; svg not supported).
        from PIL import Image

        with Image.open(p) as im:
            im = im.convert("RGBA")
            out = ASSET_DIR / f"{p.stem}_embed.png"
            im.save(out, format="PNG")
        return str(out)
    except Exception:
        return None


def resolve_logo_from_domain(domain: str) -> Optional[str]:
    d = (domain or "").strip()
    if not d:
        return None
    d = d.replace("https://", "").replace("http://", "").strip().strip("/")
    # Basic: Clearbit
    p = download_logo_from_url(f"https://logo.clearbit.com/{d}", timeout=15)
    if p:
        return p
    # Favicon fallback
    for path in ("/favicon.ico", "/apple-touch-icon.png"):
        p = download_logo_from_url(f"https://{d}{path}", timeout=15)
        if p:
            return p
    return None


def _wiki_api(lang: str) -> str:
    l = (lang or "zh").strip().lower()
    host = "zh.wikipedia.org" if l.startswith("zh") else "en.wikipedia.org"
    return f"https://{host}/w/api.php"


def _wiki_opensearch(company: str, lang: str) -> Optional[str]:
    try:
        api = _wiki_api(lang)
        params = {"action": "opensearch", "search": company, "limit": 1, "namespace": 0, "format": "json"}
        r = requests.get(api, params=params, timeout=12, headers={"User-Agent": "autoplan/0.1"})
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list) and data[1]:
            title = str(data[1][0]).strip()
            return title or None
    except Exception:
        return None
    return None


def _wiki_page_image(title: str, lang: str) -> Optional[str]:
    try:
        api = _wiki_api(lang)
        params = {
            "action": "query",
            "titles": title,
            "prop": "pageimages",
            "pithumbsize": 480,
            "format": "json",
        }
        r = requests.get(api, params=params, timeout=12, headers={"User-Agent": "autoplan/0.1"})
        if r.status_code != 200:
            return None
        data: Dict[str, Any] = r.json() if isinstance(r.json(), dict) else {}
        pages = (data.get("query") or {}).get("pages") or {}
        if not isinstance(pages, dict):
            return None
        for _, page in pages.items():
            if not isinstance(page, dict):
                continue
            thumb = page.get("thumbnail") or {}
            if isinstance(thumb, dict):
                src = thumb.get("source")
                if isinstance(src, str) and src.strip():
                    return src.strip()
    except Exception:
        return None
    return None


def resolve_logo_from_wikipedia(company_name: str) -> Optional[str]:
    """
    Best-effort public source. Not guaranteed "official standard", but often good enough as a starting point.
    """
    company = (company_name or "").strip()
    if not company:
        return None

    # Try zh, then en.
    for lang in ("zh", "en"):
        title = _wiki_opensearch(company, lang=lang)
        if not title:
            continue
        img_url = _wiki_page_image(title, lang=lang)
        if not img_url:
            continue
        p = download_logo_from_url(img_url)
        if p:
            return p
    return None


def resolve_logo(
    bidder_company: str | None = None,
    logo_url: str | None = None,
    bidder_domain: str | None = None,
    project_id: str | None = None,
) -> Optional[str]:
    """
    Resolution order:
    1) direct URL (user provided)
    1.5) locked branding (project-level)
    2) latest ingested logo asset
    3) domain (clearbit/favicon) best-effort
    4) wikipedia best-effort (requires company name)
    """
    if isinstance(logo_url, str) and logo_url.strip():
        p = download_logo_from_url(logo_url.strip())
        if p:
            _lock_logo(project_id, p, source="url", bidder_company=bidder_company, bidder_domain=bidder_domain, logo_url=logo_url)
            return p
    locked = _load_locked_logo(project_id)
    if locked:
        return locked
    p = find_latest_ingested_logo(project_id=project_id)
    if p:
        _lock_logo(project_id, p, source="ingest", bidder_company=bidder_company, bidder_domain=bidder_domain, logo_url=logo_url)
        return p
    if isinstance(bidder_domain, str) and bidder_domain.strip():
        p = resolve_logo_from_domain(bidder_domain.strip())
        if p:
            _lock_logo(project_id, p, source="domain", bidder_company=bidder_company, bidder_domain=bidder_domain, logo_url=logo_url)
            return p
    if isinstance(bidder_company, str) and bidder_company.strip():
        p = resolve_logo_from_wikipedia(bidder_company.strip())
        if p:
            _lock_logo(project_id, p, source="wikipedia", bidder_company=bidder_company, bidder_domain=bidder_domain, logo_url=logo_url)
            return p
    return None
