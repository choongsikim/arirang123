"""Step 6 (optional) – upload via the YouTube Data API v3 (OAuth, resumable)."""
from __future__ import annotations

from pathlib import Path

from .script import Script

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def upload(video: Path, script: Script, privacy: str = "private", secrets: str = "client_secret.json",
           token: str = "token.json") -> str:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials.from_authorized_user_file(token, SCOPES) if Path(token).exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(secrets, SCOPES).run_local_server(port=0)
        Path(token).write_text(creds.to_json())

    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {"title": script.title[:100], "description": script.description[:5000],
                    "tags": script.tags[:15], "categoryId": "22"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), chunksize=8 << 20, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return f"https://youtube.com/shorts/{resp['id']}"
