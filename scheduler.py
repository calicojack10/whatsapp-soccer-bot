from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal, User
from football_api import live_scores
from whatsapp import send_message


def send_auto_updates():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.auto_updates == True).all()
        if not users:
            return

        scores_text = live_scores()

        for user in users:
            send_message(user.phone, scores_text)

    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(send_auto_updates, "interval", minutes=5, max_instances=1)
scheduler.start()
