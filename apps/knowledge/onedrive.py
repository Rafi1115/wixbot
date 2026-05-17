import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def refresh_onedrive_token(config):
    """Refresh expired OneDrive access token."""
    response = requests.post(
        f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0/token",
        data={
            "client_id": settings.AZURE_CLIENT_ID,
            "client_secret": settings.AZURE_CLIENT_SECRET,
            "refresh_token": config.refresh_token,
            "grant_type": "refresh_token",
            "scope": "Files.Read.All offline_access",
        },
    )
    data = response.json()
    if "access_token" in data:
        config.access_token = data["access_token"]
        config.save(update_fields=["access_token"])
    return config.access_token


def list_onedrive_files(bot):
    """List files in connected OneDrive."""
    from apps.knowledge.models import OneDriveConfig
    config = OneDriveConfig.objects.get(bot=bot)

    headers = {"Authorization": f"Bearer {config.access_token}"}
    response = requests.get(
        "https://graph.microsoft.com/v1.0/me/drive/root/children",
        headers=headers,
        params={"$select": "id,name,file,size,lastModifiedDateTime"},
    )

    if response.status_code == 401:
        token = refresh_onedrive_token(config)
        headers["Authorization"] = f"Bearer {token}"
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me/drive/root/children",
            headers=headers,
        )

    response.raise_for_status()
    items = response.json().get("value", [])
    # filter to supported file types
    supported = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    return [
        item for item in items
        if item.get("file", {}).get("mimeType") in supported
    ]


def download_onedrive_file(bot, file_id: str) -> tuple[bytes, str]:
    """
    Download a file from OneDrive.
    Returns (file_bytes, mime_type).
    """
    from apps.knowledge.models import OneDriveConfig
    config = OneDriveConfig.objects.get(bot=bot)

    headers = {"Authorization": f"Bearer {config.access_token}"}

    # get download URL
    meta_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}",
        headers=headers,
        params={"$select": "id,name,file,@microsoft.graph.downloadUrl"},
    )
    if meta_resp.status_code == 401:
        token = refresh_onedrive_token(config)
        headers["Authorization"] = f"Bearer {token}"
        meta_resp = requests.get(
            f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}",
            headers=headers,
        )
    meta_resp.raise_for_status()
    data = meta_resp.json()
    mime_type = data.get("file", {}).get("mimeType", "")
    download_url = data.get("@microsoft.graph.downloadUrl", "")

    file_resp = requests.get(download_url)
    file_resp.raise_for_status()
    return file_resp.content, mime_type


def get_onedrive_oauth_url() -> str:
    from urllib.parse import urlencode
    params = {
        "client_id": settings.AZURE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.AZURE_REDIRECT_URI,
        "scope": "Files.Read.All offline_access",
        "response_mode": "query",
    }
    return f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0/authorize?{urlencode(params)}"


def exchange_onedrive_code(code: str, bot) -> None:
    from apps.knowledge.models import OneDriveConfig
    response = requests.post(
        f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0/token",
        data={
            "client_id": settings.AZURE_CLIENT_ID,
            "client_secret": settings.AZURE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.AZURE_REDIRECT_URI,
            "grant_type": "authorization_code",
            "scope": "Files.Read.All offline_access",
        },
    )
    response.raise_for_status()
    tokens = response.json()
    OneDriveConfig.objects.update_or_create(
        bot=bot,
        defaults={
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token", ""),
        },
    )
