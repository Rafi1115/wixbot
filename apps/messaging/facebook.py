import requests
import logging

logger = logging.getLogger(__name__)

META_GRAPH_URL = "https://graph.facebook.com/v19.0"


def send_facebook_message(recipient_id: str, message: str, page_access_token: str) -> bool:
    """
    Send a Facebook Messenger message.
    Args:
        recipient_id: Facebook Page-Scoped User ID (PSID)
        message: text to send
        page_access_token: Facebook Page access token
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
            logger.error(f"Facebook send failed: {response.status_code} {response.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"Facebook send exception: {e}")
        return False


def set_facebook_typing(recipient_id: str, page_access_token: str, on: bool = True):
    """Show/hide typing indicator in Messenger."""
    url = f"{META_GRAPH_URL}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "sender_action": "typing_on" if on else "typing_off",
    }
    try:
        requests.post(url, json=payload, params={"access_token": page_access_token}, timeout=5)
    except Exception:
        pass
