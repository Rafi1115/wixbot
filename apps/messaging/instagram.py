import requests
import logging

logger = logging.getLogger(__name__)

META_GRAPH_URL = "https://graph.facebook.com/v19.0"


def send_instagram_message(recipient_id: str, message: str, page_access_token: str) -> bool:
    """
    Send an Instagram Direct Message.
    Uses the same Messenger API endpoint — Instagram DMs go through the Pages Messaging API.
    Args:
        recipient_id: Instagram-scoped user ID
        message: text to send
        page_access_token: Facebook Page access token linked to the Instagram account
    """
    url = f"{META_GRAPH_URL}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message},
        "messaging_type": "RESPONSE",
    }
    params = {"access_token": page_access_token}
    try:
        response = requests.post(url, json=payload, params=params, timeout=10)
        if response.status_code != 200:
            logger.error(f"Instagram send failed: {response.status_code} {response.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"Instagram send exception: {e}")
        return False
