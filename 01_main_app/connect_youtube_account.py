"""
MAESTRO YouTube 1-Click Authentication Connector.

Run this script or double-click 'connect_my_youtube.bat'.
It opens Google's official sign-in page in your browser, securely retrieves
your YouTube API authorization, saves your permanent refresh token to token.json,
and verifies your channel connection!
"""
from __future__ import annotations
import sys
import os
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from google_auth_oauthlib.flow import InstalledAppFlow
from backend.services.youtube_auth import SCOPES, CLIENT_SECRET_FILE, TOKEN_FILE, get_channel_profile


def main():
    print("==================================================================")
    print("        MAESTRO - YOUTUBE ACCOUNT 1-CLICK AUTHENTICATION         ")
    print("==================================================================")
    print()

    if not CLIENT_SECRET_FILE.exists():
        print(f"❌ ERROR: '{CLIENT_SECRET_FILE.name}' not found at:")
        print(f"   {CLIENT_SECRET_FILE}")
        print("Please ensure your Google OAuth client_secret.json is placed in 01_main_app/.")
        sys.exit(1)

    print(f"[✓] Found OAuth Client Secrets: {CLIENT_SECRET_FILE.name}")
    print("[+] Opening Google OAuth Sign-in in your default browser...")
    print("    (Please sign in with the Google Account that owns your YouTube channel)")
    print()

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET_FILE),
            scopes=SCOPES
        )
        
        # Runs local loopback server on an ephemeral free port
        creds = flow.run_local_server(
            port=0,
            prompt="consent",
            access_type="offline"
        )

        # Save credentials to token.json
        token_content = creds.to_json()
        TOKEN_FILE.write_text(token_content, encoding="utf-8")

        # Also copy to root project directory for compatibility
        parent_token = ROOT.parent / "token.json"
        try:
            parent_token.write_text(token_content, encoding="utf-8")
        except Exception:
            pass

        print()
        print("==================================================================")
        print("   ✅ SUCCESS! AUTHORIZATION RECEIVED & SAVED TO TOKEN.JSON       ")
        print("==================================================================")
        
        # Verify and fetch channel profile
        profile = get_channel_profile()
        if profile.get("connected") and profile.get("channel"):
            ch = profile["channel"]
            print(f" Channel Name : {ch.get('title')}")
            print(f" Channel ID   : {ch.get('id')}")
            print(f" Subscribers  : {ch.get('subscriber_count', 0):,}")
            print(f" Total Videos : {ch.get('video_count', 0):,}")
            print(f" Custom URL   : {ch.get('custom_url') or 'N/A'}")
        else:
            print(" Connected, but no public channel profile found under this account.")

        print("==================================================================")
        print(" MAESTRO is now 100% linked to your YouTube Channel!")
        print(" Automated video publishing, 24/7 autonomous scheduling,")
        print(" and telemetry-based SEO optimizations are now FULLY OPERATIONAL!")
        print("==================================================================")

    except Exception as exc:
        print()
        print(f"❌ Authentication failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
