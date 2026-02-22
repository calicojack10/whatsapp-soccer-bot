import os
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from database import SessionLocal, User
from whatsapp import send_message
from football_api import live_scores
import scheduler  # starts the scheduler on import

app = FastAPI()

# You create this token yourself; must match the "Verify Token" in Meta
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "live_ball")


@app.get("/health")
async def health():
    return {"status": "ok"}


# =========================
# WEBHOOK VERIFICATION (GET)
# Meta calls: /webhook?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
# =========================
@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge:
        # Must return the raw challenge as plain text
        return PlainTextResponse(challenge)

    return PlainTextResponse("Verification failed", status_code=403)


# =========================
# RECEIVE WHATSAPP EVENTS (POST)
# =========================
@app.post("/webhook")
async def webhook(req: Request):
    # Never crash on bad input
    try:
        data = await req.json()
    except Exception:
        return {"status": "no json"}

    # WhatsApp sends many event types; only some contain "messages"
    try:
        value = data["entry"][0]["changes"][0]["value"]
    except Exception:
        return {"status": "unrecognized payload"}

    # Ignore non-message events (e.g., statuses, template updates, etc.)
    if "messages" not in value:
        return {"status": "no message in event"}

    try:
        message_obj = value["messages"][0]
        phone = message_obj["from"]
        text = (message_obj.get("text") or {}).get("body", "").strip().lower()
    except Exception:
        return {"status": "could not parse message"}

    # If user sent something non-text (image, etc.)
    if not text:
        send_message(phone, "I can only read text right now. Type *menu*.")
        return {"status": "ok"}

    db = SessionLocal()
    try:
        user = db.get(User, phone)
        if not user:
            user = User(phone=phone, auto_updates=False)
            db.add(user)
            db.commit()

        # Commands
        if text == "menu":
            send_message(phone, menu(user.auto_updates))

        elif text == "scores":
            send_message(phone, live_scores())

        elif text in ("auto on", "autoon", "auto-on"):
            user.auto_updates = True
            db.commit()
            send_message(phone, "✅ Auto updates enabled. I'll send live scores every 5 minutes.")

        elif text in ("auto off", "autooff", "auto-off"):
            user.auto_updates = False
            db.commit()
            send_message(phone, "❌ Auto updates disabled. Use *scores* anytime.")

        else:
            send_message(phone, "Type *menu* to see commands.")

    finally:
        db.close()

    return {"status": "ok"}


def menu(auto_enabled: bool) -> str:
    auto_status = "ON ✅" if auto_enabled else "OFF ❌"
    return (
        "⚽ Soccer Bot\n\n"
        f"Auto updates: {auto_status}\n\n"
        "Commands:\n"
        "• menu — show this menu\n"
        "• scores — live matches now\n"
        "• auto on — get automatic updates\n"
        "• auto off — stop automatic updates\n"
    )
