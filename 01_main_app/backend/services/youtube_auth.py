"""
YouTube OAuth2 authentication service.

Handles:
- OAuth 2.0 flow with Google APIs (offline access, refresh token)
- Channel profile retrieval (subscriber count, video count, avatar)
- Credential caching in token.json
- Channel disconnection and revocation
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from backend.core.config import project_root

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

CLIENT_SECRET_FILE = project_root() / "client_secret.json"
TOKEN_FILE = project_root() / "token.json"


def get_client_secret_path() -> Path:
    return CLIENT_SECRET_FILE


def get_token_path() -> Path:
    return TOKEN_FILE


def is_authenticated() -> bool:
    """Check if valid or refreshable credentials exist."""
    if not TOKEN_FILE.exists():
        return False
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and creds.valid:
            return True
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
            return True
    except Exception as e:
        print(f"[YouTubeAuth] is_authenticated error: {e}")
        return False
    return False


def get_auth_url(redirect_uri: str) -> str:
    """Generate Google OAuth 2.0 authorization URL."""
    if not CLIENT_SECRET_FILE.exists():
        raise FileNotFoundError(
            f"Missing {CLIENT_SECRET_FILE.name}. Please ensure client_secret.json is in project root."
        )

    flow = Flow.from_client_secrets_file(
        str(CLIENT_SECRET_FILE),
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return auth_url


def handle_oauth_callback(code: str, redirect_uri: str) -> Credentials:
    """Exchange authorization code for tokens and save to token.json."""
    if not CLIENT_SECRET_FILE.exists():
        raise FileNotFoundError("Missing client_secret.json")

    flow = Flow.from_client_secrets_file(
        str(CLIENT_SECRET_FILE),
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    flow.fetch_token(code=code)
    creds = flow.credentials

    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def get_authenticated_service():
    """Build and return an authorized YouTube Resource object."""
    if not CLIENT_SECRET_FILE.exists():
        raise RuntimeError(
            f"Missing {CLIENT_SECRET_FILE.name}. Please place your Google OAuth client_secret.json in the project root."
        )

    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            print(f"[YouTubeAuth] Error loading token.json: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise PermissionError("YouTube account is not connected. Please connect via OAuth first.")

    return build("youtube", "v3", credentials=creds)


def get_channel_profile() -> Dict[str, Any]:
    """Fetch profile and statistics for the authenticated YouTube channel."""
    if not is_authenticated():
        return {
            "connected": False,
            "channel": None,
            "message": "YouTube account not connected."
        }

    try:
        youtube = get_authenticated_service()
        req = youtube.channels().list(
            part="snippet,statistics,contentDetails",
            mine=True
        )
        res = req.execute()
        items = res.get("items", [])
        if not items:
            return {
                "connected": True,
                "channel": None,
                "message": "No channel found for authenticated Google account."
            }

        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        thumbnails = snippet.get("thumbnails", {})
        avatar_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
            or ""
        )

        return {
            "connected": True,
            "channel": {
                "id": item.get("id"),
                "title": snippet.get("title", "YouTube Channel"),
                "custom_url": snippet.get("customUrl", ""),
                "description": snippet.get("description", ""),
                "avatar": avatar_url,
                "subscriber_count": int(stats.get("subscriberCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "view_count": int(stats.get("viewCount", 0)),
                "hidden_subscriber_count": stats.get("hiddenSubscriberCount", False),
            }
        }
    except Exception as e:
        return {
            "connected": False,
            "channel": None,
            "error": str(e)
        }


def disconnect_channel() -> Dict[str, Any]:
    """Revoke credentials and remove token.json."""
    if TOKEN_FILE.exists():
        try:
            TOKEN_FILE.unlink()
        except Exception as e:
            print(f"[YouTubeAuth] Error deleting token file: {e}")
    return {"success": True, "message": "YouTube channel disconnected successfully."}
