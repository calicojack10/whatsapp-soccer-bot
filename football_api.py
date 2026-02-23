# football_api.py
import os
import requests
from datetime import datetime, timezone

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

# Finished detection keywords (status wording can vary)
FINISHED_KEYWORDS = (
    "finished",
    "match finished",
    "ft",
    "full time",
    "fulltime",
    "ended",
    "final",
)

# Scheduled/not-started keywords
SCHEDULED_KEYWORDS = (
    "not started",
    "scheduled",
    "fixture",
    "tbd",
)

# Ignore these in finished detection
IGNORED_STATUSES = (
    "postponed",
    "cancelled",
    "canceled",
    "abandoned",
    "suspended",
    "delayed",
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
    """Fetch today's Soccer events (UTC date) from TheSportsDB."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"https://www.thesportsdb.com/api/v1/json/{SPORTSDB_KEY}/eventsday.php"
    params = {"d": today, "s": "Soccer"}

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    payload = r.json() or {}
    return payload.get("events") or []


def _match_selected_leagues(event, selected_codes):
    """If selected_codes is empty => ALL leagues allowed."""
    if not selected_codes:
        return True

    league_text = (event.get("strLeague") or "").strip().lower()
    if not league_text:
        return False

    for code in selected_codes:
        for kw in LEAGUE_MAP.get(code, []):
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


def _has_score(e) -> bool:
    return e.get("intHomeScore") is not None and e.get("intAwayScore") is not None


def _is_live(e) -> bool:
    status = (e.get("strStatus") or "").strip().lower()
    return any(k in status for k in LIVE_KEYWORDS)


def _is_scheduled(e) -> bool:
    status = (e.get("strStatus") or "").strip().lower()
    # Some feeds return blank status for scheduled matches; treat that as scheduled
    return status == "" or any(k in status for k in SCHEDULED_KEYWORDS)


def _is_finished(e) -> bool:
    """
    Robust finished detection:
    - If status contains finished keywords -> finished
    - Else if it has a score AND isn't live/scheduled/cancelled/etc -> treat as finished
    """
    status = (e.get("strStatus") or "").strip().lower()

    if any(k in status for k in FINISHED_KEYWORDS):
        return True

    if _has_score(e):
        if any(k in status for k in LIVE_KEYWORDS):
            return False
        if any(k in status for k in SCHEDULED_KEYWORDS):
            return False
        if any(k in status for k in IGNORED_STATUSES):
            return False
        return True

    return False


def build_live_message(events, selected_codes=None, max_games: int = 12) -> str:
    """Only live/in-play matches."""
    selected_codes = selected_codes or []
    filtered = [e for e in events if _match_selected_leagues(e, selected_codes)]

    live = [_fmt_event(e, include_status=True) for e in filtered if _is_live(e)]

    if not live:
        return (
            "🔴 No live matches right now for your selected leagues."
            if selected_codes
            else "🔴 No live matches right now."
        )

    return "🔴 Live Now\n\n" + "\n".join(live[:max_games])


def build_fixtures_message(events, selected_codes=None, max_games: int = 12) -> str:
    """Only scheduled/not-started matches for today."""
    selected_codes = selected_codes or []
    filtered = [e for e in events if _match_selected_leagues(e, selected_codes)]

    fixtures = [_fmt_event(e, include_status=True) for e in filtered if _is_scheduled(e)]

    if not fixtures:
        return (
            "📅 No fixtures found for today for your selected leagues."
            if selected_codes
            else "📅 No fixtures found for today."
        )

    return "📅 Today’s Fixtures\n\n" + "\n".join(fixtures[:max_games])


def build_results_message(events, selected_codes=None, max_games: int = 12) -> str:
    """Only finished results for today."""
    selected_codes = selected_codes or []
    filtered = [e for e in events if _match_selected_leagues(e, selected_codes)]

    finished = [_fmt_event(e, include_status=False) for e in filtered if _is_finished(e)]

    if not finished:
        return (
            "🏁 No finished results found yet today for your selected leagues."
            if selected_codes
            else "🏁 No finished results found yet today."
        )

    return "🏁 Today’s Results\n\n" + "\n".join(finished[:max_games])
