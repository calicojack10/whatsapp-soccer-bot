import os
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from database import SessionLocal, User
from whatsapp import send_message
from football_api import (
    fetch_events_today,
    build_scores_message,
    available_leagues_text,
    LEAGUE_MAP,
)
import scheduler  # starts scheduler on import

app = FastAPI()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "live_ball")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge:
        return PlainTextResponse(challenge)

    return PlainTextResponse("Verification failed", status_code=403)


@app.post("/webhook")
async def webhook(req: Request):
    try:
        data = await req.json()
    except Exception:
        return {"status": "no json"}

    try:
        value = data["entry"][0]["changes"][0]["value"]
    except Exception:
        return {"status": "unrecognized payload"}

    if "messages" not in value:
        return {"status": "no message in event"}

    try:
        msg = value["messages"][0]
        phone = msg["from"]
        text = (msg.get("text") or {}).get("body", "").strip().lower()
    except Exception:
        return {"status": "could not parse message"}

    if not text:
        send_message(phone, "I can only read text right now. Type *menu*.")
        return {"status": "ok"}

    db = SessionLocal()
    try:
        user = db.get(User, phone)
        if not user:
            user = User(phone=phone, auto_updates=False, leagues="")
            db.add(user)
            db.commit()

        selected = parse_user_leagues(user.leagues)

        if text == "menu":
            send_message(phone, menu(user.auto_updates, selected))

        elif text == "leagues":
            send_message(phone, available_leagues_text())

        elif text == "my leagues":
            send_message(phone, my_leagues_text(selected))

        elif text.startswith("add "):
            code = text.replace("add ", "").strip()
            msg_out = add_league(user, code, db)
            send_message(phone, msg_out)

        elif text.startswith("remove "):
            code = text.replace("remove ", "").strip()
            msg_out = remove_league(user, code, db)
            send_message(phone, msg_out)

        elif text == "reset leagues":
            user.leagues = ""
            db.commit()
            send_message(phone, "✅ Reset complete. You will now receive *ALL* leagues.")

        elif text == "scores":
            try:
                events = fetch_events_today()
                send_message(phone, build_scores_message(events, selected_codes=selected))
            except Exception:
                send_message(phone, "⚠️ Could not fetch scores right now. Try again in a minute.")

        elif text in ("auto on", "autoon", "auto-on"):
            user.auto_updates = True
            db.commit()
            send_message(phone, "✅ Auto updates enabled. I’ll send updates for your selected leagues.")

        elif text in ("auto off", "autooff", "auto-off"):
            user.auto_updates = False
            db.commit()
            send_message(phone, "❌ Auto updates disabled.")

        else:
            send_message(phone, "Type *menu* to see commands.")

    finally:
        db.close()

    return {"status": "ok"}


def parse_user_leagues(leagues_str: str):
    if not leagues_str:
        return []
    parts = [p.strip().lower() for p in leagues_str.split(",") if p.strip()]
    # keep only valid codes
    return [p for p in parts if p in LEAGUE_MAP]


def my_leagues_text(selected_codes):
    if not selected_codes:
        return "🌍 You’re set to *ALL* leagues.\n\nUse `add epl` etc. to filter."
    return "✅ Your leagues:\n\n" + ", ".join(selected_codes)


def add_league(user: User, code: str, db):
    code = code.lower()
    if code not in LEAGUE_MAP:
        return "❌ Unknown league code. Type *leagues* to see valid options."

    current = set(parse_user_leagues(user.leagues))
    current.add(code)
    user.leagues = ",".join(sorted(current))
    db.commit()
    return f"✅ Added *{code}*. Type *my leagues* to view."


def remove_league(user: User, code: str, db):
    code = code.lower()
    current = set(parse_user_leagues(user.leagues))
    if code not in current:
        return f"ℹ️ *{code}* wasn’t in your list. Type *my leagues*."

    current.remove(code)
    user.leagues = ",".join(sorted(current))
    db.commit()

    if not current:
        return "✅ Removed. Your list is empty so you’re back to *ALL* leagues."
    return f"✅ Removed *{code}*. Type *my leagues* to view."


def menu(auto_enabled: bool, selected_codes) -> str:
    auto_status = "ON ✅" if auto_enabled else "OFF ❌"
    leagues_status = "ALL 🌍" if not selected_codes else ", ".join(selected_codes)

    return (
        "⚽ Soccer Bot\n\n"
        f"Auto updates: {auto_status}\n"
        f"Leagues: {leagues_status}\n\n"
        "Commands:\n"
        "• scores — live/today matches\n"
        "• auto on / auto off\n"
        "• leagues — list options\n"
        "• add <code> — subscribe\n"
        "• remove <code> — unsubscribe\n"
        "• my leagues — show your list\n"
        "• reset leagues — back to ALL\n"
    )
