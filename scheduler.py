# scheduler.py
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal, User, MatchState
from whatsapp import send_message
from football_api import (
    fetch_events_today,
    DEFAULT_LEAGUES,
    LEAGUE_MAP,
    _match_selected_leagues,   # yes, underscore, but OK for internal use
    _is_live,
    _is_finished,
    _fmt_live_line,
    _fmt_result_line,
)

# ✅ Prevent multiple scheduler instances unless you explicitly enable it
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "1") == "1"


def _parse_user_leagues(leagues_str: str):
    if not leagues_str:
        return DEFAULT_LEAGUES
    parts = [p.strip().lower() for p in leagues_str.split(",") if p.strip()]
    cleaned = [p for p in parts if p in LEAGUE_MAP]
    return cleaned if cleaned else DEFAULT_LEAGUES


def _safe_int(v):
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


def _state_key(phone: str, event_id: str) -> str:
    return f"{phone}:{event_id}"


def send_auto_updates():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.auto_updates == True).all()
        if not users:
            return

        # Fetch once per tick
        try:
            events = fetch_events_today()
        except Exception:
            return

        if not events:
            return

        # Optional cleanup of old match states (keeps DB small)
        cutoff = datetime.utcnow() - timedelta(days=2)
        db.query(MatchState).filter(MatchState.updated_at < cutoff).delete()
        db.commit()

        for user in users:
            phone = user.phone
            selected_codes = _parse_user_leagues(user.leagues)

            # Filter events for this user's leagues
            filtered = [e for e in events if _match_selected_leagues(e, selected_codes)]

            for e in filtered:
                event_id = str(e.get("idEvent") or "").strip()
                if not event_id:
                    continue

                is_live_now = _is_live(e)
                is_finished_now = _is_finished(e)

                # We only care about live + finished for alerts
                if not is_live_now and not is_finished_now:
                    continue

                home = e.get("strHomeTeam") or "Home"
                away = e.get("strAwayTeam") or "Away"
                status = (e.get("strStatus") or "").strip()

                hs = _safe_int(e.get("intHomeScore"))
                a_s = _safe_int(e.get("intAwayScore"))

                key = _state_key(phone, event_id)
                state = db.get(MatchState, key)

                # First time we see the match for this user
                if not state:
                    state = MatchState(
                        key=key,
                        phone=phone,
                        event_id=event_id,
                        home=home,
                        away=away,
                        home_score=hs,
                        away_score=a_s,
                        status=status,
                        updated_at=datetime.utcnow(),
                    )
                    db.add(state)
                    db.commit()

                    # Kickoff alert if it's live
                    if is_live_now:
                        # Example: "KICKOFF\nFiorentina 0-0 Pisa — Live"
                        send_message(phone, "KICKOFF\n" + _fmt_live_line(e))
                    # If it’s already finished when we first see it, don’t spam a FT alert.
                    continue

                # Existing state: detect changes
                prev_hs = state.home_score
                prev_as = state.away_score
                prev_status = (state.status or "").strip()

                # Goal/change detection (score changed while live)
                score_changed = (hs is not None and a_s is not None) and (hs != prev_hs or a_s != prev_as)

                # Finished transition
                finished_now = is_finished_now and not any(k in prev_status.lower() for k in ("finished", "ft", "full time", "final", "ended"))

                # Kickoff transition (was not live before, now live)
                was_live_before = "live" in (prev_status.lower())
                kickoff_now = is_live_now and not was_live_before and not is_finished_now

                # Send alerts in priority order
                if finished_now:
                    # FULL TIME
                    send_message(phone, "FULL TIME\n" + _fmt_result_line(e))

                elif score_changed and is_live_now:
                    # GOAL (or just score update)
                    send_message(phone, "GOAL\n" + _fmt_live_line(e))

                elif kickoff_now:
                    send_message(phone, "KICKOFF\n" + _fmt_live_line(e))

                # Update stored state
                state.home = home
                state.away = away
                state.home_score = hs
                state.away_score = a_s
                state.status = status
                state.updated_at = datetime.utcnow()
                db.commit()

    finally:
        db.close()


def start_scheduler():
    sched = BackgroundScheduler()
    # 2 minutes is a good "FlashScore feel" without hammering the API too hard
    sched.add_job(send_auto_updates, "interval", minutes=2, max_instances=1, coalesce=True)
    sched.start()
    return sched


if ENABLE_SCHEDULER:
    start_scheduler()
