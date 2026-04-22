"""Simple shared-password auth for the internal dashboard."""

import hashlib
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

router = APIRouter()

_RAW_PASSWORD = os.getenv("INTERNAL_DASHBOARD_PASSWORD", "vendoroo2026")
_PASSWORD_HASH = hashlib.sha256(_RAW_PASSWORD.encode()).hexdigest()
_TOKEN_SECRET = os.getenv("INTERNAL_TOKEN_SECRET", secrets.token_hex(32))


def _make_token() -> str:
    return hashlib.sha256(f"{_PASSWORD_HASH}:{_TOKEN_SECRET}".encode()).hexdigest()


def verify_internal_token(request: Request) -> bool:
    token = request.cookies.get("vendoroo_internal_token")
    if not token or token != _make_token():
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def internal_login(body: LoginRequest, response: Response):
    if hashlib.sha256(body.password.encode()).hexdigest() != _PASSWORD_HASH:
        raise HTTPException(status_code=401, detail="Wrong password")
    response.set_cookie(
        key="vendoroo_internal_token",
        value=_make_token(),
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return {"ok": True}


@router.post("/logout")
async def internal_logout(response: Response):
    response.delete_cookie("vendoroo_internal_token")
    return {"ok": True}


@router.get("/check")
async def check_auth(authed: bool = Depends(verify_internal_token)):
    return {"ok": True}
