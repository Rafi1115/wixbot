import requests
import logging

logger = logging.getLogger(__name__)

META_GRAPH_URL = "https://graph.facebook.com/v19.0"


def send_whatsapp_message(to: str, message: str, phone_number_id: str, access_token: str) -> bool:
    """
    Send a WhatsApp message via Meta Cloud API.
    Args:
        to: recipient phone number in international format (e.g. 966501234567)
        message: text to send
        phone_number_id: your WhatsApp Business phone number ID from Meta
        access_token: WhatsApp access token
    """
    url = f"{META_GRAPH_URL}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"WhatsApp send failed: {response.status_code} {response.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"WhatsApp send exception: {e}")
        return False


def mark_whatsapp_read(message_id: str, phone_number_id: str, access_token: str):
    """Mark an incoming WhatsApp message as read (shows double blue tick)."""
    url = f"{META_GRAPH_URL}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        requests.post(url, json=payload, headers=headers, timeout=5)
    except Exception:
        pass
