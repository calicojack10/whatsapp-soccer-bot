import requests

ACCESS_TOKEN = "EAA83CwyZBN9QBQxXNY6IoyeqTZCeuYqjZB96kdkbLLoWBpGdPZCnLY3HOqSLMLVJMgdeFBVUGnScfEwqUsGKxrhLqtkrPrE3tFu6fYAPn2XVGAXpNEWihnZAP45y5uQwBPZAAS2ZAVGyGtJmQNyzJtE1npePhbMZBdkJ77gt4ZBKrHe7eoQEvRhjFAg0Ob4gZB2blu4fwdFZATtRdEitK0ehPkVlmVAmA1SUt210Hljs544"
PHONE_ID = "1049528254903132"


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
