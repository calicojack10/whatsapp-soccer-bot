import os
import requests

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "EAA83CwyZBN9QBQxXNY6IoyeqTZCeuYqjZB96kdkbLLoWBpGdPZCnLY3HOqSLMLVJMgdeFBVUGnScfEwqUsGKxrhLqtkrPrE3tFu6fYAPn2XVGAXpNEWihnZAP45y5uQwBPZAAS2ZAVGyGtJmQNyzJtE1npePhbMZBdkJ77gt4ZBKrHe7eoQEvRhjFAg0Ob4gZB2blu4fwdFZATtRdEitK0ehPkVlmVAmA1SUt210Hljs544")
PHONE_ID = os.getenv("PHONE_ID", "1049528254903132")

# Meta Graph API version can be updated if needed
GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v19.0")


def send_message(to_phone: str, text: str) -> None:
    """
    Sends a WhatsApp text message using the Cloud API.
    """
    if not ACCESS_TOKEN or not PHONE_ID:
        # Avoid crashing; just do nothing (Render logs will show your missing env vars if you print)
        return

    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text},
    }

    try:
        requests.post(url, headers=headers, json=payload, timeout=15)
    except Exception:
        # Never crash webhook path
        pass
