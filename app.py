from fastapi import FastAPI, Request
from database import Session, User
from whatsapp import send_message
from football_api import live_scores
from fastapi.responses import PlainTextResponse
import scheduler
import os

app = FastAPI()

VERIFY_TOKEN = "live_ball"  # must match Meta dashboard


# =========================
# WEBHOOK VERIFICATION (GET)
# =========================

@app.get("/webhook")
async def verify_webhook(request: Request):

    params = request.query_params

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)

    return PlainTextResponse("Verification failed", status_code=403)


# =========================
# RECEIVE WHATSAPP MESSAGES
# =========================
@app.post("/webhook")
async def webhook(req: Request):

    try:
        data = await req.json()
    except:
        return {"status": "no json"}

    # ✅ Ignore non-message events safely
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        phone = message["from"]
        text = message["text"]["body"].lower()
    except (KeyError, IndexError, TypeError):
        return {"status": "no message event"}

    db = Session()
    user = db.get(User, phone)

    if not user:
        user = User(phone=phone)
        db.add(user)
        db.commit()

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




