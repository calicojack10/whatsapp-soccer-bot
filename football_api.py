# football_api.py
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

FINISHED_KEYWORDS = (
    "finished",
    "match finished",
    "ft",
    "full time",
    "fulltime",
    "ended",
    "final",
)

SCHEDULED_KEYWORDS = (
    "not started",
    "scheduled",
    "fixture",
    "tbd",
)

IGNORED_STATUSES = (
    "postponed",
    "cancelled",
    "canceled",
    "abandoned",
    "suspended",
    "delayed",
)

# League code -> keywords to match TheSportsDB strLeague text
LEAGUE_MAP = {
    # Top 5 + Championship
    "epl": ["premier league", "english premier league"],
    "laliga": [ "laliga", "la liga", "la liga santander", "spanish laliga", "spanish la liga", "primera division", "primera división", "spain primera division", "spanish primera division",],
    "seriea": ["serie a", "italian serie a"],
    "bundesliga": ["bundesliga", "german bundesliga"],
    "ligue1": ["ligue 1", "french ligue 1"],
    "champ": ["championship", "english championship", "efl championship"],

    # UEFA
    "ucl": ["uefa champions league", "champions league"],
    "uel": ["uefa europa league", "europa league"],
    "uecl": ["uefa europa conference league", "europa conference league", "conference league"],

    # Defaults you asked to include
    "turkey": ["super lig", "süper lig", "turkish super lig", "turkish süper lig"],
    "portugal": ["primeira liga", "liga portugal", "portuguese primeira liga"],
    "switzerland": ["swiss super league", "super league (switzerland)"],
    "scotland": ["scottish premiership", "premiership (scotland)"],
    "austria": ["austrian bundesliga", "bundesliga (austria)"],
    "belgium": ["jupiler pro league", "belgian pro league", "pro league (belgium)"],
    "denmark": ["danish superliga", "3f superliga", "superliga (denmark)"],
}

# Default pack (used when user has no custom selection saved)
DEFAULT_LEAGUES = [
    "epl", "laliga", "seriea", "bundesliga", "ligue1",
    "champ",
    "ucl", "uel", "uecl",
    "turkey", "portugal", "switzerland", "scotland", "austria", "belgium", "denmark",
]


def available_leagues_text() -> str:
    return (
        "Available leagues (codes)\n\n"
        "epl, laliga, seriea, bundesliga, ligue1, champ\n"
        "ucl, uel, uecl\n"
        "turkey, portugal, switzerland, scotland, austria, belgium, denmark\n\n"
        "Use:\n"
        "add epl\n"
        "remove epl\n"
        "my leagues\n"
        "reset leagues"
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
    If selected_codes is empty => use DEFAULT_LEAGUES
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


def _fmt_live_line(e) -> str:
    home = e.get("strHomeTeam") or "Home"
    away = e.get("strAwayTeam") or "Away"
    hs = e.get("intHomeScore")
    a_s = e.get("intAwayScore")
    status_raw = (e.get("strStatus") or "").strip()

    score = ""
    if hs is not None and a_s is not None:
        score = f"{hs}-{a_s}"

    # ✅ Force a clean ending label when finished
    if _is_finished(e):
        return f"{home} {score} {away} — Finished".replace("  ", " ").strip()

    # otherwise, show whatever status we have (Live / 2nd Half / HT etc.)
    if status_raw:
        return f"{home} {score} {away} — {status_raw}".replace("  ", " ").strip()

    return f"{home} {score} {away}".replace("  ", " ").strip()


def _fmt_result_line(e) -> str:
    home = e.get("strHomeTeam") or "Home"
    away = e.get("strAwayTeam") or "Away"
    hs = e.get("intHomeScore")
    a_s = e.get("intAwayScore")
    score = ""
    if hs is not None and a_s is not None:
        score = f"{hs}-{a_s}"
    return f"{home} {score} {away}".replace("  ", " ").strip()


from zoneinfo import ZoneInfo
from datetime import datetime

NY_TZ = ZoneInfo("America/New_York")


def _format_kickoff_time(e) -> str:
    """
    Convert TheSportsDB UTC timestamp to New York time (America/New_York).
    Falls back safely if timestamp not present.
    """

    ts = e.get("strTimestamp")

    if ts:
        try:
            # Ensure UTC awareness
            ts_clean = ts.replace("Z", "+00:00")
            dt_utc = datetime.fromisoformat(ts_clean)

            # Convert to NYC timezone
            dt_ny = dt_utc.astimezone(NY_TZ)

            return dt_ny.strftime("%-I:%M %p ET")

        except Exception:
            pass

    # Fallback if timestamp missing
    t = (e.get("strTime") or "").strip()
    if t:
        try:
            dt = datetime.strptime(t, "%H:%M:%S")
            return dt.strftime("%-I:%M %p")
        except Exception:
            return t

    return "TBD"


def _is_scheduled(e) -> bool:
    status = (e.get("strStatus") or "").strip().lower()
    return status == "" or any(k in status for k in SCHEDULED_KEYWORDS)


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

    if any(k in status for k in LIVE_KEYWORDS):
        return True

    if _has_score(e):
        if any(k in status for k in SCHEDULED_KEYWORDS):
            return False
        if any(k in status for k in FINISHED_KEYWORDS):
            return False
        if any(k in status for k in IGNORED_STATUSES):
            return False
        return True

    return False


def _is_finished(e) -> bool:
    """STRICT: only finished keywords count as finished."""
    status = (e.get("strStatus") or "").strip().lower()
    return any(k in status for k in FINISHED_KEYWORDS)


def _group_by_league(lines_by_league: dict, header: str) -> str:
    if not lines_by_league:
        return ""

    out = [header, ""]
    for league in sorted(lines_by_league.keys()):
        out.append(league)
        for line in lines_by_league[league]:
            out.append(f"• {line}")   # <-- bullet added back
        out.append("")

    return "\n".join(out).strip()


def build_live_message(events, selected_codes=None, max_games: int = 12) -> str:
    selected_codes = selected_codes or []
    filtered = [e for e in events if _match_selected_leagues(e, selected_codes)]

    grouped = {}
    count = 0
    for e in filtered:
        if not _is_live(e):
            continue
        league = e.get("strLeague") or "Soccer"
        grouped.setdefault(league, []).append(_fmt_live_line(e))
        count += 1
        if count >= max_games:
            break

    if not grouped:
        return "No live matches right now for your selected leagues." if selected_codes else "No live matches right now."

    return _group_by_league(grouped, "LIVE")


def build_fixtures_message(events, selected_codes=None, max_games: int = 12) -> str:
    selected_codes = selected_codes or []
    filtered = [e for e in events if _match_selected_leagues(e, selected_codes)]

    grouped = {}
    count = 0

    for e in filtered:
        if not _is_scheduled(e):
            continue

        league = e.get("strLeague") or "Soccer"
        home = e.get("strHomeTeam") or "Home"
        away = e.get("strAwayTeam") or "Away"
        t = _format_kickoff_time(e)

        grouped.setdefault(league, []).append(f"• {t} — {home} vs {away}")

        count += 1
        if count >= max_games:
            break

    if not grouped:
        return (
            "No fixtures found for today for your selected leagues."
            if selected_codes
            else "No fixtures found for today."
        )

    lines = ["TODAY", ""]
    for league in sorted(grouped.keys()):
        lines.append(league)
        for line in grouped[league]:
            lines.append(f"  {line}")
        lines.append("")

    return "\n".join(lines).strip()


def build_results_message(events, selected_codes=None, max_games: int = 12) -> str:
    selected_codes = selected_codes or []
    filtered = [e for e in events if _match_selected_leagues(e, selected_codes)]

    grouped = {}
    count = 0
    for e in filtered:
        if not _is_finished(e):
            continue
        league = e.get("strLeague") or "Soccer"
        grouped.setdefault(league, []).append(_fmt_result_line(e))
        count += 1
        if count >= max_games:
            break

    if not grouped:
        return "No finished results yet today for your selected leagues." if selected_codes else "No finished results yet today."

    return _group_by_league(grouped, "RESULTS")





