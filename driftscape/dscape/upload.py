"""Optional - upload to YouTube via the Data API v3. NEVER runs without explicit confirmation.

Safety rails:
  * requires the --i-confirm flag AND typing the video title at an interactive prompt
  * uploads as the privacy in metadata.json (default 'private'); 'public' needs a second confirmation
  * --dry-run prints exactly what would be sent and stops
Setup (one time): see README "YouTube upload".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .config import Project

CONFIG_DIR = Path.home() / ".driftscape"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _body(md: dict) -> dict:
    return {
        "snippet": {"title": md["title"], "description": md["description"], "tags": md["tags"],
                    "categoryId": md["category_id"], "defaultLanguage": md["default_language"]},
        "status": {"privacyStatus": md["privacy"], "selfDeclaredMadeForKids": md["made_for_kids"],
                   "containsSyntheticMedia": md["contains_synthetic_media"]},
    }


def run(proj: Project, confirm: bool, dry_run: bool, thumb: str | None) -> None:
    md = proj.load_json("out/metadata.json")
    fj = proj.load_json("work/final.json")
    video = Path(fj["file"])
    if md.get("validation_errors"):
        raise SystemExit("Fix metadata errors first: " + "; ".join(md["validation_errors"]))
    qc = proj.root / "out" / "reports" / "qc_final.json"
    if not qc.exists():
        raise SystemExit("Run `./ds qc <project> --final` before uploading.")
    if not json.loads(qc.read_text()).get("pass"):
        print("  ! final QC did not pass - read out/reports/qc_final.md before continuing.")
    thumbs = sorted((proj.out / "thumbnails").glob("thumb_*.jpg"))
    tpath = Path(thumb) if thumb else (thumbs[0] if thumbs else None)
    body = _body(md)
    print(json.dumps({"file": str(video), "thumbnail": str(tpath) if tpath else None, "body": body}, indent=2))
    if dry_run:
        print("\n  dry run - nothing was uploaded.")
        return
    if not confirm:
        raise SystemExit("Refusing to upload without --i-confirm (review the request above first).")
    if not sys.stdin.isatty():
        raise SystemExit("Upload needs an interactive terminal for the confirmation prompt.")
    typed = input(f"\nType the exact title to upload as {md['privacy'].upper()}:\n> ")
    if typed.strip() != md["title"]:
        raise SystemExit("Title did not match - upload cancelled.")
    if md["privacy"] == "public" and input("This will be PUBLIC immediately. Type PUBLISH: ").strip() != "PUBLISH":
        raise SystemExit("Cancelled.")
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        raise SystemExit("Install upload extras first: pip install -r requirements-upload.txt")
    secret = CONFIG_DIR / "client_secret.json"
    token = CONFIG_DIR / "youtube_token.json"
    if not secret.exists():
        raise SystemExit(f"Missing {secret} (OAuth desktop client from Google Cloud Console).")
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES).run_local_server(port=0)
        token.write_text(creds.to_json())
        token.chmod(0o600)
    yt = build("youtube", "v3", credentials=creds)
    media = MediaFileUpload(str(video), chunksize=64 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"  uploaded {status.progress() * 100:.1f}%", end="\r")
    vid = resp["id"]
    print(f"\n  uploaded: https://youtu.be/{vid} ({md['privacy']})")
    if tpath:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(tpath))).execute()
        print(f"  thumbnail set: {tpath.name}")
    proj.save_json("out/upload.json", {"video_id": vid, "privacy": md["privacy"]})
