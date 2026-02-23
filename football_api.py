# football_api.py
import os
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

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
    # Top 5 + extras you already had
    "epl": ["premier league", "english premier league"],
    "laliga": ["la liga", "spanish la liga"],
    "seriea": ["serie a", "italian serie a"],
    "bundesliga": ["bundesliga", "german bundesliga"],
    "ligue1": ["ligue 1", "french ligue 1"],
    "champ": ["championship", "english championship", "efl championship"],

    # UEFA competitions
    "ucl": ["uefa champions league", "champions league"],
    "uel": ["uefa europa league", "europa league"],
    "uecl": ["uefa europa conference league", "europa conference league", "conference league"],

    # New leagues you requested
    "turkey": ["super lig", "süper lig", "turkish super lig", "turkish süper lig"],
    "portugal": ["primeira liga", "liga portugal", "portuguese primeira liga"],
    "switzerland": ["swiss super league", "super league (switzerland)", "credit suisse super league"],
    "scotland": ["scottish premiership", "premiership (scotland)"],
    "austria": ["austrian bundesliga", "bundesliga (austria)"],
    "belgium": ["jupiler pro league", "belgian pro league", "pro league (belgium)"],
    "denmark": ["danish superliga", "3f superliga", "superliga (denmark)"],
}

DEFAULT_LEAGUES = [
    "epl", "laliga", "seriea", "bundesliga", "ligue1",
    "champ",
    "ucl", "uel", "uecl",
    "turkey", "portugal", "switzerland", "scotland", "austria", "belgium", "denmark",
]

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
    """
    If selected_codes is empty => use DEFAULT_LEAGUES.
    Otherwise match TheSportsDB strLeague text to our code keywords.
    """
    if not selected_codes:
        selected_codes = DEFAULT_LEAGUES

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
    """
    Live if:
    - status contains live keywords, OR
    - it has a score AND it's not scheduled AND not finished/cancelled.
    This catches games where TheSportsDB doesn't label status as 'Live' but score updates.
    """
    status = (e.get("strStatus") or "").strip().lower()

    # obvious live statuses
    if any(k in status for k in LIVE_KEYWORDS):
        return True

    # score present can indicate match in progress on TheSportsDB free feeds
    if _has_score(e):
        if any(k in status for k in SCHEDULED_KEYWORDS):
            return False
        if any(k in status for k in FINISHED_KEYWORDS):
            return False
        if any(k in status for k in IGNORED_STATUSES):
            return False
        return True

    return False

def _is_scheduled(e) -> bool:
    status = (e.get("strStatus") or "").strip().lower()
    # Some feeds return blank status for scheduled matches; treat that as scheduled
    return status == "" or any(k in status for k in SCHEDULED_KEYWORDS)


def _is_finished(e) -> bool:
    """
    STRICT finished detection:
    Only treat as finished if status clearly says so.
    This prevents in-progress games with scores from appearing as results.
    """
    status = (e.get("strStatus") or "").strip().lower()
    return any(k in status for k in FINISHED_KEYWORDS)


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
    """
    Only scheduled/not-started matches for today.
    Output grouped by league, includes kickoff time, uses 'vs', no status text.
    """
    selected_codes = selected_codes or []
    filtered = [e for e in events if _match_selected_leagues(e, selected_codes)]

    # Collect fixtures and group by league
    by_league = {}
    count = 0

    for e in filtered:
        if not _is_scheduled(e):
            continue

        league = e.get("strLeague") or "Soccer"
        home = e.get("strHomeTeam") or "Home"
        away = e.get("strAwayTeam") or "Away"
        time_txt = _format_kickoff_time(e)

        by_league.setdefault(league, []).append(f"{time_txt} — {home} vs {away}")
        count += 1
        if count >= max_games:
            break

    if not by_league:
        return (
            "No fixtures found for today for your selected leagues."
            if selected_codes
            else "No fixtures found for today."
        )

    # Build nicely formatted message
    lines = ["Today’s Fixtures", ""]
    for league in sorted(by_league.keys()):
        lines.append(league)
        for item in by_league[league]:
            lines.append(f"• {item}")
        lines.append("")

    return "\n".join(lines).strip()

def _format_kickoff_time(e) -> str:
    """
    Best-effort kickoff time:
    - If strTimestamp exists (often ISO like '2026-02-23T20:00:00+00:00'), convert to ET
    - Else fallback to (strTime) as-is
    """
    # 1) Try timestamp -> ET
    ts = e.get("strTimestamp")
    if ts:
        try:
            # Handle 'Z' if present
            ts_clean = ts.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_clean)
            dt_et = dt.astimezone(ZoneInfo("America/New_York"))
            return dt_et.strftime("%-I:%M %p ET")  # e.g. 3:00 PM ET
        except Exception:
            pass

    # 2) Fallback to strTime (TheSportsDB often provides HH:MM:SS)
    t = (e.get("strTime") or "").strip()
    if t:
        try:
            # convert 20:00:00 -> 8:00 PM (no timezone guarantee)
            dt = datetime.strptime(t, "%H:%M:%S")
            return dt.strftime("%-I:%M %p")
        except Exception:
            return t

    return "TBD"
    
def build_results_message(events, selected_codes=None, max_games: int = 12) -> str:
    """Only finished results for today."""
    selected_codes = selected_codes or []
    filtered = [e for e in events if _match_selected_leagues(e, selected_codes)]

    finished = [_fmt_event(e, include_status=False) for e in filtered if _is_finished(e)]

    if not finished:
        return (
            "🏁 No finished results yet today for your selected leagues."
            if selected_codes
            else "🏁 No finished results yet today."
        )

    return "🏁 Today’s Results\n\n" + "\n".join(finished[:max_games])


