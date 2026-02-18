from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr

from backend.auth_store import create_user, verify_user, get_user_by_id, update_balance, get_user_by_email, list_charges, list_charges_by_user, update_daily_limit, list_users

router = APIRouter(prefix="/auth", tags=["Auth"])

JWT_SECRET = os.environ.get("ZF_JWT_SECRET", "change-me")
JWT_ALG = "HS256"
ADMIN_KEY = os.environ.get("ZF_ADMIN_KEY", "")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TopupRequest(BaseModel):
    email: EmailStr
    amount: int


class DailyLimitRequest(BaseModel):
    email: EmailStr
    limit: int


def _issue_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _get_user_from_token(auth_header: Optional[str]):
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = auth_header.split(" ", 1)[1].strip()
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = int(data.get("sub"))
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="invalid user")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")


@router.post("/register")
def register(req: RegisterRequest):
    if get_user_by_email(req.email):
        raise HTTPException(status_code=400, detail="email already exists")
    user = create_user(req.email, req.password)
    token = _issue_token(user["id"])
    return {"ok": True, "user": {"id": user["id"], "email": user["email"], "balance": user["balance"]}, "token": token}


@router.post("/login")
def login(req: LoginRequest):
    user = verify_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = _issue_token(user["id"])
    return {"ok": True, "user": {"id": user["id"], "email": user["email"], "balance": user["balance"]}, "token": token}


@router.get("/me")
def me(authorization: Optional[str] = Header(default=None)):
    user = _get_user_from_token(authorization)
    return {
        "ok": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "balance": user["balance"],
            "daily_limit": user.get("daily_limit"),
        },
    }


@router.post("/topup")
def topup(req: TopupRequest, authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    balance = update_balance(user["id"], req.amount)
    return {"ok": True, "email": req.email, "balance": balance}


@router.post("/set_daily_limit")
def set_daily_limit(req: DailyLimitRequest, authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    limit = update_daily_limit(user["id"], req.limit)
    return {"ok": True, "email": req.email, "daily_limit": limit}


@router.get("/charges")
def charges(authorization: Optional[str] = Header(default=None), limit: int = 100):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    return {"ok": True, "items": list_charges(limit=limit)}


@router.get("/my_charges")
def my_charges(authorization: Optional[str] = Header(default=None), limit: int = 100):
    user = _get_user_from_token(authorization)
    return {"ok": True, "items": list_charges_by_user(user["id"], limit=limit)}


@router.get("/charge_summary")
def charge_summary(authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    items = list_charges(limit=10000)
    total = sum(int(i.get("cost") or 0) for i in items)
    by_action = {}
    for it in items:
        act = it.get("action") or "unknown"
        by_action[act] = by_action.get(act, 0) + int(it.get("cost") or 0)
    return {"ok": True, "total": total, "by_action": by_action}


@router.get("/usage_summary")
def usage_summary(authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    items = list_charges(limit=20000)
    by_user = {}
    by_action = {}
    for it in items:
        uid = it.get("user_id")
        act = it.get("action") or "unknown"
        by_user[uid] = by_user.get(uid, 0) + 1
        by_action[act] = by_action.get(act, 0) + 1
    return {"ok": True, "by_user": by_user, "by_action": by_action, "total_events": len(items)}


@router.get("/active_summary")
def active_summary(authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    items = list_charges(limit=20000)
    now = datetime.utcnow().timestamp()
    day7 = now - 7 * 24 * 3600
    day30 = now - 30 * 24 * 3600
    u7 = set()
    u30 = set()
    for it in items:
        ts = it.get("ts")
        try:
            # ts is sqlite datetime string
            from datetime import datetime as _dt
            t = _dt.fromisoformat(ts).timestamp()
        except Exception:
            t = None
        if t is None:
            continue
        if t >= day7:
            u7.add(it.get("user_id"))
        if t >= day30:
            u30.add(it.get("user_id"))
    return {"ok": True, "active_7d": len(u7), "active_30d": len(u30)}


@router.get("/users")
def users(authorization: Optional[str] = Header(default=None), limit: int = 100):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    return {"ok": True, "items": list_users(limit=limit)}


@router.get("/export_csv")
def export_csv(authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    users_data = list_users(limit=10000)
    charges = list_charges(limit=20000)
    from pathlib import Path
    import csv
    out_dir = Path("backend/data/auth")
    out_dir.mkdir(parents=True, exist_ok=True)
    users_csv = out_dir / "users_export.csv"
    charges_csv = out_dir / "charges_export.csv"

    with users_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "email", "balance", "daily_limit"])
        w.writeheader()
        for u in users_data:
            w.writerow(u)

    with charges_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "user_id", "action", "cost", "ts"])
        w.writeheader()
        for c in charges:
            w.writerow(c)

    return {"ok": True, "users_csv": str(users_csv), "charges_csv": str(charges_csv)}


@router.post("/set_default_model")
def set_default_model(authorization: Optional[str] = Header(default=None), provider: str = "", model: str = ""):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    if not provider or not model:
        raise HTTPException(status_code=400, detail="provider and model required")
    # 写入到本地配置文件（避免直接改系统环境变量）
    from pathlib import Path
    import json
    cfg_path = Path("backend/data/autoplan/config.json")
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    cfg["default_provider"] = provider
    cfg["default_model"] = model
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "default_provider": provider, "default_model": model, "config_path": str(cfg_path)}


@router.post("/set_agent_roles")
def set_agent_roles(authorization: Optional[str] = Header(default=None), payload: dict = None):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    if not payload:
        raise HTTPException(status_code=400, detail="payload required")
    # 配置校验：必须包含 default + rules(list)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be object")
    if "default" not in payload or "rules" not in payload:
        raise HTTPException(status_code=400, detail="payload must include default and rules")
    if not isinstance(payload.get("rules"), list):
        raise HTTPException(status_code=400, detail="rules must be list")
    for r in payload.get("rules", []):
        if not isinstance(r, dict):
            raise HTTPException(status_code=400, detail="each rule must be object")
        if "match" not in r or "role" not in r:
            raise HTTPException(status_code=400, detail="each rule must include match and role")
        if not isinstance(r.get("match"), list) or not all(isinstance(x, str) for x in r.get("match")):
            raise HTTPException(status_code=400, detail="match must be list of strings")
        if not isinstance(r.get("role"), str) or not r.get("role"):
            raise HTTPException(status_code=400, detail="role must be non-empty string")
    from pathlib import Path
    import json
    cfg_path = Path("backend/data/autoplan/agent_roles.json")
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "config_path": str(cfg_path)}


@router.get("/get_agent_roles")
def get_agent_roles(authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    from pathlib import Path
    import json
    cfg_path = Path("backend/data/autoplan/agent_roles.json")
    if not cfg_path.exists():
        return {"ok": True, "config": None}
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        cfg = None
    return {"ok": True, "config": cfg}
