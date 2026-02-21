from apscheduler.schedulers.background import BackgroundScheduler
from database import Session, User
from football_api import live_scores
from whatsapp import send_message


def send_auto_updates():
    db = Session()

    users = db.query(User).filter(User.auto_updates == True).all()

    if not users:
        return

    scores = live_scores()

    for user in users:
        send_message(user.phone, scores)


scheduler = BackgroundScheduler()
scheduler.add_job(send_auto_updates, "interval", minutes=5)
scheduler.start()