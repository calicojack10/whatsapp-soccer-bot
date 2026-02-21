import requests

ACCESS_TOKEN = "YOUR_WHATSAPP_ACCESS_TOKEN"
PHONE_ID = "YOUR_PHONE_NUMBER_ID"


def send_message(phone, text):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    }

    requests.post(url, json=payload, headers=headers)