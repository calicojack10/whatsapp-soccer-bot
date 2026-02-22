from fastapi import FastAPI, Request
from database import Session, User
from whatsapp import send_message
from football_api import live_scores
import scheduler
import os

app = FastAPI()

VERIFY_TOKEN = "live_ball"  # must match Meta dashboard


# =========================
# WEBHOOK VERIFICATION (GET)
# =========================
@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = None,
    hub_challenge: str = None,
    hub_verify_token: str = None,
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)
    return {"error": "Verification failed"}


# =========================
# RECEIVE WHATSAPP MESSAGES
# =========================
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        phone = message["from"]
        text = message["text"]["body"].lower()
    except:
        return {"status": "no message"}

    db = Session()
    user = db.get(User, phone)

    if not user:
        user = User(phone=phone)
        db.add(user)
        db.commit()

    # COMMANDS
    if text == "menu":
        send_message(phone, menu())

    elif text == "scores":
        send_message(phone, live_scores())

    elif text == "auto on":
        user.auto_updates = True
        db.commit()
        send_message(phone, "✅ Auto updates enabled.")

    elif text == "auto off":
        user.auto_updates = False
        db.commit()
        send_message(phone, "❌ Auto updates disabled.")

    else:
        send_message(phone, "Type *menu* to see options.")

    return {"status": "ok"}


def menu():
    return """
⚽ Soccer Bot

Commands:

menu - show menu
scores - live matches
auto on - automatic updates
auto off - stop updates

"""
