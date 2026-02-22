import os
import requests

# API-Football key (api-sports)
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")

# League IDs (API-Football)
# Top 5 leagues + Championship + UEFA competitions
LEAGUES = {
    "EPL": 39,          # Premier League
    "LALIGA": 140,      # La Liga
    "SERIEA": 135,      # Serie A
    "BUNDESLIGA": 78,   # Bundesliga
    "LIGUE1": 61,       # Ligue 1
    "CHAMP": 40,        # Championship
    "UCL": 2,           # UEFA Champions League
    "UEL": 3,           # UEFA Europa League
    "UECL": 848,        # UEFA Europa Conference League
}


def live_scores(max_games: int = 12) -> str:
    """
    Returns a readable list of live scores across all competitions.
    """
    if not API_FOOTBALL_KEY:
        return "⚠️ Missing API_FOOTBALL_KEY. Add it in Render Env Vars."

    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_FOOTBALL_KEY}

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        payload = r.json()
    except Exception:
        return "⚠️ Could not reach the football API right now."

    matches = payload.get("response", []) or []

    # Optional: prioritize your target leagues by filtering to those league IDs first
    target_league_ids = set(LEAGUES.values())
    preferred = [m for m in matches if (m.get("league") or {}).get("id") in target_league_ids]
    others = [m for m in matches if (m.get("league") or {}).get("id") not in target_league_ids]
    ordered = preferred + others

    lines = []
    for m in ordered[:max_games]:
        league_name = (m.get("league") or {}).get("name", "League")
        home = (m.get("teams") or {}).get("home", {}).get("name", "Home")
        away = (m.get("teams") or {}).get("away", {}).get("name", "Away")
        goals = m.get("goals") or {}
        minute = (m.get("fixture") or {}).get("status", {}).get("elapsed")

        score_home = goals.get("home")
        score_away = goals.get("away")

        minute_txt = f"{minute}'" if minute is not None else ""
        lines.append(f"{league_name}: {home} {score_home}-{score_away} {away} {minute_txt}".strip())

    if not lines:
        return "⚽ No live matches right now."

    return "⚽ Live Matches\n\n" + "\n".join(lines)
