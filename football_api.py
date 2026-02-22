# football_api.py
import os
import requests
from datetime import datetime, timezone

# TheSportsDB API key (yours is 123). Best practice: keep it in Render Env Vars as SPORTSDB_KEY
SPORTSDB_KEY = os.getenv("SPORTSDB_KEY", "123")

# Keywords TheSportsDB may use to indicate a match is currently in progress
LIVE_KEYWORDS = (
    "live",
    "in play",
    "inplay",
    "half time",
    "halftime",
    "1st half",
    "2nd half",
    "playing",
)

def live_scores(max_games: int = 12) -> str:
    """
    TheSportsDB integration:
    - Fetches today's soccer events (UTC date)
    - Tries to detect LIVE matches using strStatus
    - If none detected, returns today's matches with status
    """

    # TheSportsDB expects date in YYYY-MM-DD
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    url = f"https://www.thesportsdb.com/api/v1/json/{SPORTSDB_KEY}/eventsday.php"
    params = {"d": today, "s": "Soccer"}

    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        payload = r.json() or {}
    except Exception:
        return "⚠️ Could not reach TheSportsDB right now."

    events = payload.get("events") or []
    if not events:
        return "⚽ No matches found for today."

    def fmt_event(e, include_status: bool = True) -> str:
        league = e.get("strLeague") or "Soccer"
        home = e.get("strHomeTeam") or "Home"
        away = e.get("strAwayTeam") or "Away"
        hs = e.get("intHomeScore")
        a_s = e.get("intAwayScore")
        status = (e.get("strStatus") or "Scheduled").strip()

        score = ""
        if hs is not None and a_s is not None:
            score = f"{hs}-{a_s}"

        if include_status:
            return f"{league}: {home} {score} {away} ({status})".replace("  ", " ").strip()
        return f"{league}: {home} {score} {away}".replace("  ", " ").strip()

    # Try to detect live matches
    live = []
    for e in events:
        status = (e.get("strStatus") or "").strip().lower()
        if any(k in status for k in LIVE_KEYWORDS):
            live.append(fmt_event(e, include_status=True))

    if live:
        return "⚽ Live Matches\n\n" + "\n".join(live[:max_games])

    # No live detected — show today's list with statuses
    lines = [fmt_event(e, include_status=True) for e in events[:max_games]]
    return "⚽ Today’s Matches (no live detected)\n\n" + "\n".join(lines)
