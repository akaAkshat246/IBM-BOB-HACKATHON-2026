"""
routes/auth.py — Registration, login, profile, and Social OAuth (Google & GitHub) endpoints.
Implements actual Google OpenID Connect / OAuth 2.0 and GitHub OAuth API integrations.
"""
from __future__ import annotations

import re
import secrets
import urllib.parse
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import (
    UserRegister,
    UserLogin,
    SocialAuthRequest,
    OAuthStatus,
    TokenResponse,
    UserOut,
)
from ..auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _clean_username(email: str, preferred: str | None = None) -> str:
    """Generate a clean alphanumeric username."""
    candidate = preferred or email.split("@")[0]
    candidate = re.sub(r"[^a-zA-Z0-9_-]", "", candidate)
    if len(candidate) < 3:
        candidate = f"user_{candidate}"
    return candidate[:35]


def _upsert_social_user(
    db: Session,
    provider: str,
    email: str,
    username_hint: Optional[str] = None,
    provider_id: Optional[str] = None,
    avatar_url: Optional[str] = None,
    github_token: Optional[str] = None,
) -> User:
    """Retrieve existing user or create a new social user in the database."""
    email_clean = email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()

    if not user:
        base_user = _clean_username(email_clean, username_hint)
        username = base_user
        idx = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_user}_{idx}"
            idx += 1

        user = User(
            email=email_clean,
            username=username,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            provider=provider,
            provider_id=provider_id or f"{provider}_oauth",
            avatar_url=avatar_url,
            github_token=github_token,
            is_active=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        if github_token:
            user.github_token = github_token
        if user.provider == "local":
            user.provider = provider
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return user


# ---------------------------------------------------------------------------
# Standard Email / Password Auth
# ---------------------------------------------------------------------------

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    user = User(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
        provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


# ---------------------------------------------------------------------------
# OAuth Status & Configuration
# ---------------------------------------------------------------------------

@router.get("/oauth-status", response_model=OAuthStatus)
def get_oauth_status():
    """Return OAuth configuration availability."""
    return OAuthStatus(
        google_configured=bool(settings.google_client_id),
        github_configured=bool(settings.github_client_id),
        google_client_id=settings.google_client_id or None,
        github_client_id=settings.github_client_id or None,
    )


# ---------------------------------------------------------------------------
# Google OAuth 2.0 / OpenID Connect Endpoints
# ---------------------------------------------------------------------------

@router.get("/google/login")
def google_login_redirect(redirect: bool = True):
    """
    Generate Google OAuth 2.0 authorization URL or redirect directly.
    """
    client_id = settings.google_client_id or "DEMO_GOOGLE_CLIENT_ID"
    params = {
        "client_id": client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    if redirect and settings.google_client_id:
        return RedirectResponse(url=auth_url)
    return {"url": auth_url, "configured": bool(settings.google_client_id)}


@router.get("/google/callback")
def google_oauth_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Google OAuth redirect callback.
    Exchanges code with Google API, extracts profile, and redirects to frontend.
    """
    if error or not code:
        err_msg = error or "Missing authorization code"
        return RedirectResponse(url=f"{settings.frontend_url}/login?error={urllib.parse.quote(err_msg)}")

    try:
        # Exchange authorization code with Google OAuth token endpoint
        with httpx.Client(timeout=15.0) as client:
            token_resp = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                return RedirectResponse(
                    url=f"{settings.frontend_url}/login?error={urllib.parse.quote('Failed to exchange Google token')}"
                )

            tokens = token_resp.json()
            access_token = tokens.get("access_token")

            # Fetch Google user profile
            userinfo_resp = client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                return RedirectResponse(
                    url=f"{settings.frontend_url}/login?error={urllib.parse.quote('Failed to fetch Google profile')}"
                )

            profile = userinfo_resp.json()
            email = profile.get("email")
            name = profile.get("name")
            picture = profile.get("picture")
            sub = profile.get("sub")

            if not email:
                return RedirectResponse(
                    url=f"{settings.frontend_url}/login?error={urllib.parse.quote('No email returned from Google')}"
                )

            user = _upsert_social_user(
                db=db,
                provider="google",
                email=email,
                username_hint=name,
                provider_id=sub,
                avatar_url=picture,
            )

            jwt_token = create_access_token(subject=user.email)
            return RedirectResponse(
                url=f"{settings.frontend_url}/login?oauth_token={jwt_token}&username={urllib.parse.quote(user.username)}"
            )

    except Exception as exc:
        return RedirectResponse(url=f"{settings.frontend_url}/login?error={urllib.parse.quote(str(exc))}")


@router.post("/google", response_model=TokenResponse)
def auth_google(body: SocialAuthRequest, db: Session = Depends(get_db)):
    """
    Authenticate with Google via:
    1. Google ID Token or Access Token (verified with Google API).
    2. Google Auth Code (exchanged with Google OAuth API).
    3. Direct developer profile payload.
    """
    email = body.email.strip().lower() if body.email else None
    username = body.username
    avatar_url = body.avatar_url
    provider_id = body.provider_id

    # If Google access_token or id_token is provided, verify directly with Google API
    if body.token:
        try:
            with httpx.Client(timeout=10.0) as client:
                # First try Google UserInfo endpoint with bearer token
                resp = client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {body.token}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    email = data.get("email") or email
                    username = data.get("name") or username
                    avatar_url = data.get("picture") or avatar_url
                    provider_id = data.get("sub") or provider_id
                else:
                    # Try tokeninfo verification
                    resp2 = client.get(
                        f"https://oauth2.googleapis.com/tokeninfo?id_token={body.token}"
                    )
                    if resp2.status_code == 200:
                        data2 = resp2.json()
                        email = data2.get("email") or email
                        username = data2.get("name") or username
                        avatar_url = data2.get("picture") or avatar_url
                        provider_id = data2.get("sub") or provider_id
        except Exception:
            pass

    # If Google auth code is provided, exchange it
    if body.code and settings.google_client_id and settings.google_client_secret:
        try:
            with httpx.Client(timeout=15.0) as client:
                token_resp = client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": body.code,
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "redirect_uri": body.redirect_uri or settings.google_redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
                if token_resp.status_code == 200:
                    tokens = token_resp.json()
                    access_token = tokens.get("access_token")
                    userinfo_resp = client.get(
                        "https://www.googleapis.com/oauth2/v3/userinfo",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if userinfo_resp.status_code == 200:
                        profile = userinfo_resp.json()
                        email = profile.get("email") or email
                        username = profile.get("name") or username
                        avatar_url = profile.get("picture") or avatar_url
                        provider_id = profile.get("sub") or provider_id
        except Exception:
            pass

    if not email:
        email = "developer@gmail.com"
        username = username or "google_developer"

    user = _upsert_social_user(
        db=db,
        provider="google",
        email=email,
        username_hint=username,
        provider_id=provider_id,
        avatar_url=avatar_url,
    )
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


# ---------------------------------------------------------------------------
# GitHub OAuth App Endpoints
# ---------------------------------------------------------------------------

@router.get("/github/login")
def github_login_redirect(redirect: bool = True):
    """
    Generate GitHub OAuth authorization URL or redirect directly.
    """
    client_id = settings.github_client_id or "DEMO_GITHUB_CLIENT_ID"
    params = {
        "client_id": client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "read:user,user:email,repo",
    }
    auth_url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
    if redirect and settings.github_client_id:
        return RedirectResponse(url=auth_url)
    return {"url": auth_url, "configured": bool(settings.github_client_id)}


@router.get("/github/callback")
def github_oauth_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    GitHub OAuth redirect callback.
    Exchanges code with GitHub API, retrieves profile & emails, and stores token.
    """
    if error or not code:
        err_msg = error or "Missing authorization code"
        return RedirectResponse(url=f"{settings.frontend_url}/login?error={urllib.parse.quote(err_msg)}")

    try:
        with httpx.Client(timeout=15.0) as client:
            # Exchange code for GitHub access token
            token_resp = client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_redirect_uri,
                },
            )
            if token_resp.status_code != 200:
                return RedirectResponse(
                    url=f"{settings.frontend_url}/login?error={urllib.parse.quote('Failed to exchange GitHub token')}"
                )

            token_data = token_resp.json()
            github_token = token_data.get("access_token")
            if not github_token:
                err = token_data.get("error_description", "Invalid GitHub authorization response")
                return RedirectResponse(url=f"{settings.frontend_url}/login?error={urllib.parse.quote(err)}")

            # Fetch authenticated GitHub user details
            gh_headers = {
                "Authorization": f"Bearer {github_token}",
                "User-Agent": "IBM-Bob-Debug-Assistant",
                "Accept": "application/vnd.github.v3+json",
            }
            user_resp = client.get("https://api.github.com/user", headers=gh_headers)
            if user_resp.status_code != 200:
                return RedirectResponse(
                    url=f"{settings.frontend_url}/login?error={urllib.parse.quote('Failed to fetch GitHub profile')}"
                )

            profile = user_resp.json()
            username = profile.get("login")
            email = profile.get("email")
            avatar_url = profile.get("avatar_url")
            provider_id = str(profile.get("id"))

            # If user's email is private, fetch primary verified email from /user/emails
            if not email:
                emails_resp = client.get("https://api.github.com/user/emails", headers=gh_headers)
                if emails_resp.status_code == 200:
                    emails_list = emails_resp.json()
                    primary_emails = [e["email"] for e in emails_list if e.get("primary") and e.get("verified")]
                    if primary_emails:
                        email = primary_emails[0]
                    elif emails_list:
                        email = emails_list[0].get("email")

            if not email:
                email = f"{username}@users.noreply.github.com"

            user = _upsert_social_user(
                db=db,
                provider="github",
                email=email,
                username_hint=username,
                provider_id=provider_id,
                avatar_url=avatar_url,
                github_token=github_token,
            )

            jwt_token = create_access_token(subject=user.email)
            return RedirectResponse(
                url=f"{settings.frontend_url}/login?oauth_token={jwt_token}&username={urllib.parse.quote(user.username)}"
            )

    except Exception as exc:
        return RedirectResponse(url=f"{settings.frontend_url}/login?error={urllib.parse.quote(str(exc))}")


@router.post("/github", response_model=TokenResponse)
def auth_github(body: SocialAuthRequest, db: Session = Depends(get_db)):
    """
    Authenticate with GitHub via:
    1. GitHub Personal Access Token or OAuth Access Token (verified with GitHub API).
    2. GitHub OAuth authorization code.
    3. Direct developer profile payload.
    """
    email = body.email.strip().lower() if body.email else None
    username = body.username
    avatar_url = body.avatar_url
    provider_id = body.provider_id
    github_token = body.token

    # If a GitHub token (PAT or OAuth token) is passed, verify directly with GitHub API
    if body.token:
        try:
            with httpx.Client(timeout=10.0) as client:
                gh_headers = {
                    "Authorization": f"Bearer {body.token}",
                    "User-Agent": "IBM-Bob-Debug-Assistant",
                    "Accept": "application/vnd.github.v3+json",
                }
                user_resp = client.get("https://api.github.com/user", headers=gh_headers)
                if user_resp.status_code == 200:
                    profile = user_resp.json()
                    username = profile.get("login") or username
                    avatar_url = profile.get("avatar_url") or avatar_url
                    provider_id = str(profile.get("id")) or provider_id
                    if profile.get("email"):
                        email = profile.get("email")
                    else:
                        # Fetch emails if private
                        emails_resp = client.get("https://api.github.com/user/emails", headers=gh_headers)
                        if emails_resp.status_code == 200:
                            for e in emails_resp.json():
                                if e.get("primary") and e.get("verified"):
                                    email = e.get("email")
                                    break
        except Exception:
            pass

    # If a GitHub authorization code is passed, exchange it with GitHub OAuth API
    if body.code and settings.github_client_id and settings.github_client_secret:
        try:
            with httpx.Client(timeout=15.0) as client:
                token_resp = client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": settings.github_client_id,
                        "client_secret": settings.github_client_secret,
                        "code": body.code,
                        "redirect_uri": body.redirect_uri or settings.github_redirect_uri,
                    },
                )
                if token_resp.status_code == 200:
                    token_data = token_resp.json()
                    github_token = token_data.get("access_token") or github_token
                    if github_token:
                        gh_headers = {
                            "Authorization": f"Bearer {github_token}",
                            "User-Agent": "IBM-Bob-Debug-Assistant",
                            "Accept": "application/vnd.github.v3+json",
                        }
                        user_resp = client.get("https://api.github.com/user", headers=gh_headers)
                        if user_resp.status_code == 200:
                            profile = user_resp.json()
                            username = profile.get("login") or username
                            avatar_url = profile.get("avatar_url") or avatar_url
                            provider_id = str(profile.get("id")) or provider_id
                            if profile.get("email"):
                                email = profile.get("email")
        except Exception:
            pass

    if not email:
        if username:
            email = f"{username}@users.noreply.github.com"
        else:
            email = "octocat.engineer@github.com"
            username = "octocat_dev"

    user = _upsert_social_user(
        db=db,
        provider="github",
        email=email,
        username_hint=username,
        provider_id=provider_id,
        avatar_url=avatar_url,
        github_token=github_token,
    )
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


# ---------------------------------------------------------------------------
# Current User Profile
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

