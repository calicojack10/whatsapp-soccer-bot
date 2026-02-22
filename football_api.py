import os
import requests
from datetime import datetime, timezone

SPORTSDB_KEY = os.getenv("SPORTSDB_KEY", "123")

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

# User-facing league codes -> keywords to match TheSportsDB strLeague text
LEAGUE_MAP = {
    "epl": ["premier league", "english premier league"],
    "laliga": ["la liga", "spanish la liga"],
    "seriea": ["serie a", "italian serie a"],
    "bundesliga": ["bundesliga", "german bundesliga"],
    "ligue1": ["ligue 1", "french ligue 1"],
    "champ": ["championship", "english championship", "efl championship"],
    "ucl": ["uefa champions league", "champions league"],
    "uel": ["uefa europa league", "europa league"],
    "uecl": ["uefa europa conference league", "europa conference league", "conference league"],
}

def available_leagues_text() -> str:
    return (
        "🏆 Available leagues (codes)\n\n"
        "epl, laliga, seriea, bundesliga, ligue1, champ,\n"
        "ucl, uel, uecl\n\n"
        "Use:\n"
        "• add epl\n"
        "• remove epl\n"
        "• my leagues\n"
        "• reset leagues"
    )

def fetch_events_today():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"https://www.thesportsdb.com/api/v1/json/{SPORTSDB_KEY}/eventsday.php"
    params = {"d": today, "s": "Soccer"}

    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    payload = r.json() or {}
    return payload.get("events") or []

def _match_selected_leagues(event, selected_codes):
    """
    If selected_codes is empty => ALL leagues allowed.
    Otherwise match TheSportsDB strLeague text to our code keywords.
    """
    if not selected_codes:
        return True

    league_text = (event.get("strLeague") or "").strip().lower()
    if not league_text:
        return False

    for code in selected_codes:
        keywords = LEAGUE_MAP.get(code, [])
        for kw in keywords:
            if kw in league_text:
                return True
    return False

def _fmt_event(e, include_status=True) -> str:
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

def build_scores_message(events, selected_codes=None, max_games: int = 12) -> str:
    selected_codes = selected_codes or []

    # filter by selected leagues
    filtered = [e for e in events if _match_selected_leagues(e, selected_codes)]

    if not filtered:
        if selected_codes:
            return "⚽ No matches found for your selected leagues today."
        return "⚽ No matches found for today."

    # find live-ish
    live = []
    for e in filtered:
        status = (e.get("strStatus") or "").strip().lower()
        if any(k in status for k in LIVE_KEYWORDS):
            live.append(_fmt_event(e, include_status=True))

    if live:
        return "⚽ Live Matches\n\n" + "\n".join(live[:max_games])

    # otherwise show today's matches for those leagues
    lines = [_fmt_event(e, include_status=True) for e in filtered[:max_games]]
    return "⚽ Today’s Matches (no live detected)\n\n" + "\n".join(lines)
