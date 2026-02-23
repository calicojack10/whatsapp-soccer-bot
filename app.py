# app.py
import os
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from database import SessionLocal, User
from whatsapp import send_message
from football_api import (
    fetch_events_today,
    build_live_message,
    build_fixtures_message,
    build_results_message,
    available_leagues_text,
    DEFAULT_LEAGUES,
    debug_league_names,
)

app = FastAPI()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "live_ball")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return PlainTextResponse(params.get("hub.challenge"))
    return PlainTextResponse("Verification failed", status_code=403)


@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()

    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        phone = msg["from"]
        text = msg.get("text", {}).get("body", "").strip().lower()
    except Exception:
        return {"status": "ignored"}

    db = SessionLocal()
    user = db.get(User, phone)
    if not user:
        user = User(phone=phone, auto_updates=False, leagues="")
        db.add(user)
        db.commit()

    selected = user.leagues.split(",") if user.leagues else DEFAULT_LEAGUES

    if text in ("live", "scores"):
        events = fetch_events_today()
        send_message(phone, build_live_message(events, selected))

    elif text in ("fixtures", "today"):
        events = fetch_events_today()
        send_message(phone, build_fixtures_message(events, selected))

    elif text == "results":
        events = fetch_events_today()
        send_message(phone, build_results_message(events, selected))

    elif text == "debug leagues":
        events = fetch_events_today()
        send_message(phone, debug_league_names(events))

    elif text == "menu":
        send_message(
            phone,
            "Soccer Bot\n\n"
            "Commands:\n"
            "• live\n"
            "• fixtures\n"
            "• results\n"
            "• debug leagues\n",
        )

    db.close()
    return {"status": "ok"}
