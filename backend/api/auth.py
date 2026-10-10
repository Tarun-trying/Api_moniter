"""
Authentication API endpoints for PulseMonitor.

Routes
------
POST /api/auth/register       — Email + password registration
POST /api/auth/login          — Email + password login
GET  /api/auth/google         — Redirect to Google OAuth consent screen
GET  /api/auth/google/callback — Handle Google OAuth callback
GET  /api/auth/me             — Get current user info
POST /api/auth/logout         — Informational logout (client drops JWT)
"""
import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
import httpx

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback"
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ---------------------------------------------------------------------------
# Helper: create user document
# ---------------------------------------------------------------------------
async def _create_user(
    db,
    *,
    name: str,
    email: str,
    hashed_password: Optional[str] = None,
    google_id: Optional[str] = None,
    avatar: Optional[str] = None,
) -> dict:
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "_id_str": user_id,
        "name": name,
        "email": email,
        "hashed_password": hashed_password,
        "google_id": google_id,
        "avatar": avatar,
        "created_at": now,
        "updated_at": now,
    }
    await db.users.insert_one(doc)
    doc.pop("_id", None)
    doc.pop("hashed_password", None)
    return doc


def _safe_user(user: dict) -> dict:
    u = dict(user)
    u.pop("_id", None)
    u.pop("hashed_password", None)
    return u


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    db = get_db()

    existing = await db.users.find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    user = await _create_user(
        db,
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
    )

    token = create_access_token({"sub": user["_id_str"]})
    return {"access_token": token, "token_type": "bearer", "user": _safe_user(user)}


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    db = get_db()

    user = await db.users.find_one({"email": body.email})
    if not user or not user.get("hashed_password"):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user["_id_str"]})
    return {"access_token": token, "token_type": "bearer", "user": _safe_user(user)}


# ---------------------------------------------------------------------------
# Google OAuth — step 1: redirect to Google
# ---------------------------------------------------------------------------
@router.get("/google")
async def google_oauth_redirect():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured")

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")


# ---------------------------------------------------------------------------
# Google OAuth — step 2: callback
# ---------------------------------------------------------------------------
@router.get("/google/callback")
async def google_oauth_callback(code: Optional[str] = None, error: Optional[str] = None):
    if error or not code:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=google_denied")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            logger.error("Google token exchange failed: %s", token_resp.text)
            return RedirectResponse(f"{FRONTEND_URL}/login?error=google_failed")

        token_data = token_resp.json()
        access_token_google = token_data.get("access_token")

        # Fetch user info from Google
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token_google}"},
        )
        if userinfo_resp.status_code != 200:
            return RedirectResponse(f"{FRONTEND_URL}/login?error=google_userinfo")

        ginfo = userinfo_resp.json()

    google_id = ginfo.get("id")
    email = ginfo.get("email")
    name = ginfo.get("name", email)
    avatar = ginfo.get("picture")

    db = get_db()

    # Find existing user by google_id or email
    user = await db.users.find_one({"$or": [{"google_id": google_id}, {"email": email}]})

    if user is None:
        user = await _create_user(
            db,
            name=name,
            email=email,
            google_id=google_id,
            avatar=avatar,
        )
    else:
        # Update google_id / avatar if missing
        updates = {"updated_at": datetime.now(timezone.utc)}
        if not user.get("google_id"):
            updates["google_id"] = google_id
        if not user.get("avatar") and avatar:
            updates["avatar"] = avatar
        await db.users.update_one({"_id_str": user["_id_str"]}, {"$set": updates})
        user = await db.users.find_one({"_id_str": user["_id_str"]})
        user.pop("_id", None)

    jwt_token = create_access_token({"sub": user["_id_str"]})

    # Redirect to frontend with token as query param (frontend will store it)
    return RedirectResponse(
        f"{FRONTEND_URL}/auth/callback?token={jwt_token}"
    )


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------
@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# Logout (client-side — just acknowledges)
# ---------------------------------------------------------------------------
@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}
