# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal, User
from whatsapp import send_message
from football_api import fetch_events_today, build_live_message, LEAGUE_MAP


def _parse_leagues(leagues_str: str):
    if not leagues_str:
        return []
    parts = [p.strip().lower() for p in leagues_str.split(",") if p.strip()]
    return [p for p in parts if p in LEAGUE_MAP]


def send_auto_updates():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.auto_updates == True).all()
        if not users:
            return

        # Fetch once per tick
        events = fetch_events_today()
        if not events:
            return

        for user in users:
            selected = _parse_leagues(user.leagues)
            msg = build_live_message(events, selected_codes=selected, max_games=10)
            send_message(user.phone, msg)

    finally:
        db.close()


scheduler = BackgroundScheduler()
# 10 minutes is safer for free APIs; change to 5 if you want later
scheduler.add_job(send_auto_updates, "interval", minutes=10, max_instances=1, coalesce=True)
scheduler.start()
