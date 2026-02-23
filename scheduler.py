import os
from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal, User
from whatsapp import send_message
from football_api import fetch_events_today, build_scores_message, LEAGUE_MAP


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
            msg = build_scores_message(events, selected_codes=selected, max_games=10)
            send_message(user.phone, msg)

    finally:
        db.close()


def start_scheduler():
    sched = BackgroundScheduler()
    sched.add_job(send_auto_updates, "interval", minutes=10, max_instances=1, coalesce=True)
    sched.start()
    return sched


# ✅ Only run scheduler when explicitly enabled
if os.getenv("ENABLE_SCHEDULER", "0") == "1":
    start_scheduler()
