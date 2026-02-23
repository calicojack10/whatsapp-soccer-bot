# football_api.py
import os
import re
import unicodedata
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SPORTSDB_KEY = os.getenv("SPORTSDB_KEY", "123")
NY_TZ = ZoneInfo("America/New_York")

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

LEAGUE_MAP = {
    "epl": ["premier league", "english premier league"],
    "laliga": [
        "laliga",
        "la liga",
        "laliga santander",
        "primera division",
        "spain primera division",
        "spanish primera division",
        "primera división",
    ],
    "seriea": ["serie a", "italian serie a"],
    "bundesliga": ["bundesliga", "german bundesliga"],
    "ligue1": ["ligue 1", "french ligue 1"],
    "champ": ["championship", "efl championship"],

    "ucl": ["champions league", "uefa champions league"],
    "uel": ["europa league", "uefa europa league"],
    "uecl": ["conference league", "uefa europa conference league"],

    "turkey": ["super lig", "süper lig", "turkish super lig", "turkish süper lig"],
    "portugal": [
        "liga portugal",
        "liga portugal betclic",
        "primeira liga",
        "portuguese primeira liga",
        "portugal primeira liga",
    ],
    "switzerland": ["swiss super league"],
    "scotland": ["scottish premiership"],
    "austria": ["austrian bundesliga"],
    "belgium": ["jupiler pro league", "belgian pro league"],
    "denmark": ["danish superliga", "3f superliga"],
}

DEFAULT_LEAGUES = list(LEAGUE_MAP.keys())


def available_leagues_text() -> str:
    return (
        "Available leagues (codes)\n\n"
        "Top leagues:\n"
        "• epl, laliga, seriea, bundesliga, ligue1, champ\n\n"
        "Europe:\n"
        "• ucl, uel, uecl\n\n"
        "More leagues:\n"
        "• turkey, portugal, switzerland, scotland, austria, belgium, denmark\n\n"
        "Commands:\n"
        "• add <code>\n"
        "• remove <code>\n"
        "• my leagues\n"
        "• reset leagues"
    )


def _norm_txt(s: str) -> str:
    s = (s or "").lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def fetch_events_today():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"https://www.thesportsdb.com/api/v1/json/{SPORTSDB_KEY}/eventsday.php"
    params = {"d": today, "s": "Soccer"}

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return (r.json() or {}).get("events") or []


def _match_selected_leagues(event, selected_codes):
    if not selected_codes:
        selected_codes = DEFAULT_LEAGUES

    league_text = _norm_txt(event.get("strLeague"))
    if not league_text:
        return False

    for code in selected_codes:
        for kw in LEAGUE_MAP.get(code, []):
            if _norm_txt(kw) in league_text:
                return True
    return False


def _is_finished(e):
    status = _norm_txt(e.get("strStatus"))
    return any(k in status for k in FINISHED_KEYWORDS)


def _is_scheduled(e):
    status = _norm_txt(e.get("strStatus"))
    return status == "" or any(k in status for k in SCHEDULED_KEYWORDS)


def _has_score(e) -> bool:
    return e.get("intHomeScore") is not None and e.get("intAwayScore") is not None


def _is_live(e):
    """
    Live if:
    - status contains live keywords, OR
    - it has a score AND it's not scheduled AND not finished/cancelled.
    """
    status = _norm_txt(e.get("strStatus"))

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


def _fmt_live_line(e):
    home = e.get("strHomeTeam") or "Home"
    away = e.get("strAwayTeam") or "Away"
    hs = e.get("intHomeScore")
    a_s = e.get("intAwayScore")
    score = f"{hs}-{a_s}" if hs is not None and a_s is not None else ""

    # Force clean finished label
    if _is_finished(e):
        return f"{home} {score} {away} — Finished".replace("  ", " ").strip()

    status_raw = (e.get("strStatus") or "").strip()
    if status_raw:
        return f"{home} {score} {away} — {status_raw}".replace("  ", " ").strip()

    return f"{home} {score} {away}".replace("  ", " ").strip()


def _fmt_result_line(e):
    home = e.get("strHomeTeam") or "Home"
    away = e.get("strAwayTeam") or "Away"
    hs = e.get("intHomeScore")
    a_s = e.get("intAwayScore")
    score = f"{hs}-{a_s}" if hs is not None and a_s is not None else ""
    return f"{home} {score} {away}".replace("  ", " ").strip()


def _format_kickoff_time(e):
    ts = e.get("strTimestamp")
    if ts:
        try:
            ts_clean = ts.replace("Z", "+00:00")
            dt_utc = datetime.fromisoformat(ts_clean)
            dt_ny = dt_utc.astimezone(NY_TZ)
            return dt_ny.strftime("%-I:%M %p ET")
        except Exception:
            pass

    t = (e.get("strTime") or "").strip()
    if t:
        try:
            dt = datetime.strptime(t, "%H:%M:%S")
            return dt.strftime("%-I:%M %p")
        except Exception:
            return t

    return "TBD"


def _group(header, grouped):
    if not grouped:
        return ""

    out = [header, ""]
    for league in sorted(grouped.keys()):
        out.append(league)
        for line in grouped[league]:
            out.append(f"• {line}")
        out.append("")
    return "\n".join(out).strip()


def build_live_message(events, selected_codes=None, max_games: int = 30):
    selected_codes = selected_codes or []
    grouped = {}
    count = 0

    for e in events:
        if count >= max_games:
            break
        if _match_selected_leagues(e, selected_codes) and _is_live(e):
            league = e.get("strLeague") or "Soccer"
            grouped.setdefault(league, []).append(_fmt_live_line(e))
            count += 1

    return _group("LIVE", grouped) or "No live matches right now for your selected leagues."


def build_results_message(events, selected_codes=None, max_games: int = 30):
    selected_codes = selected_codes or []
    grouped = {}
    count = 0

    for e in events:
        if count >= max_games:
            break
        if _match_selected_leagues(e, selected_codes) and _is_finished(e):
            league = e.get("strLeague") or "Soccer"
            grouped.setdefault(league, []).append(_fmt_result_line(e))
            count += 1

    return _group("RESULTS", grouped) or "No finished results yet today for your selected leagues."


def build_fixtures_message(events, selected_codes=None, max_games: int = 30):
    selected_codes = selected_codes or []
    grouped = {}
    count = 0

    for e in events:
        if count >= max_games:
            break
        if _match_selected_leagues(e, selected_codes) and _is_scheduled(e):
            league = e.get("strLeague") or "Soccer"
            time_str = _format_kickoff_time(e)
            home = e.get("strHomeTeam") or "Home"
            away = e.get("strAwayTeam") or "Away"
            grouped.setdefault(league, []).append(f"{time_str} — {home} vs {away}")
            count += 1

    return _group("TODAY", grouped) or "No fixtures found for today for your selected leagues."


def debug_league_names(events, limit: int = 60) -> str:
    names = sorted({(e.get("strLeague") or "").strip() for e in events if e.get("strLeague")})
    if not names:
        return "No league names found in today's feed."

    out = ["LEAGUES (from TheSportsDB today):", ""]
    for n in names[:limit]:
        out.append(f"• {n}")
    if len(names) > limit:
        out.append("")
        out.append(f"...and {len(names) - limit} more")
    return "\n".join(out)
