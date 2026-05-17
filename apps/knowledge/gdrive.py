import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def refresh_gdrive_token(config):
    """Refresh expired Google Drive access token using refresh token."""
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": config.refresh_token,
            "grant_type": "refresh_token",
        },
    )
    data = response.json()
    if "access_token" in data:
        config.access_token = data["access_token"]
        config.save(update_fields=["access_token"])
    return config.access_token


def list_gdrive_files(bot):
    """List files in connected Google Drive (PDFs, DOCX, TXT)."""
    from apps.knowledge.models import GoogleDriveConfig
    config = GoogleDriveConfig.objects.get(bot=bot)

    headers = {"Authorization": f"Bearer {config.access_token}"}
    params = {
        "q": "mimeType='application/pdf' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document' or mimeType='text/plain'",
        "fields": "files(id, name, mimeType, size, modifiedTime)",
        "pageSize": 100,
    }
    response = requests.get(
        "https://www.googleapis.com/drive/v3/files",
        headers=headers,
        params=params,
    )

    if response.status_code == 401:
        # token expired, refresh and retry
        token = refresh_gdrive_token(config)
        headers["Authorization"] = f"Bearer {token}"
        response = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params=params,
        )

    response.raise_for_status()
    return response.json().get("files", [])


def download_gdrive_file(bot, file_id: str) -> tuple[bytes, str]:
    """
    Download a file from Google Drive.
    Returns (file_bytes, mime_type).
    """
    from apps.knowledge.models import GoogleDriveConfig
    config = GoogleDriveConfig.objects.get(bot=bot)

    headers = {"Authorization": f"Bearer {config.access_token}"}

    # get file metadata first
    meta_resp = requests.get(
        f"https://www.googleapis.com/drive/v3/files/{file_id}",
        headers=headers,
        params={"fields": "id,name,mimeType"},
    )
    if meta_resp.status_code == 401:
        token = refresh_gdrive_token(config)
        headers["Authorization"] = f"Bearer {token}"
        meta_resp = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers=headers,
            params={"fields": "id,name,mimeType"},
        )
    meta_resp.raise_for_status()
    mime_type = meta_resp.json().get("mimeType", "")

    # download content
    download_resp = requests.get(
        f"https://www.googleapis.com/drive/v3/files/{file_id}",
        headers=headers,
        params={"alt": "media"},
    )
    download_resp.raise_for_status()
    return download_resp.content, mime_type


def get_gdrive_oauth_url() -> str:
    """Generate Google OAuth URL for connecting Drive."""
    from urllib.parse import urlencode
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive.readonly",
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def exchange_gdrive_code(code: str, bot) -> None:
    """Exchange OAuth code for tokens and save to GoogleDriveConfig."""
    from apps.knowledge.models import GoogleDriveConfig

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )
    response.raise_for_status()
    tokens = response.json()

    GoogleDriveConfig.objects.update_or_create(
        bot=bot,
        defaults={
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token", ""),
        },
    )
