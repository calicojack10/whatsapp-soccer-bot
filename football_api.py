import os
import requests

# API-Football key (api-sports)
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")


# simple in-memory cache (survives until Render restarts)
_LAST_GOOD_TEXT = None
_LAST_GOOD_TS = 0

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
    global _LAST_GOOD_TEXT, _LAST_GOOD_TS

    if not API_FOOTBALL_KEY:
        return "⚠️ Missing API_FOOTBALL_KEY. Add it in Render Env Vars."

    url = "https://v3.football.api-sports.io/fixtures?live=all"
    headers = {"x-apisports-key": API_FOOTBALL_KEY}

    try:
        r = requests.get(url, headers=headers, timeout=15)
        status = r.status_code
        payload = r.json() if r.content else {}
    except Exception as e:
        print(f"[API-Football] EXCEPTION: {e}")
        # If we have a recent cache, use it
        if _LAST_GOOD_TEXT and (time.time() - _LAST_GOOD_TS) < 600:
            return _LAST_GOOD_TEXT + "\n\n(Showing last known update)"
        return "⚠️ Could not reach the football API right now."

    results = payload.get("results")
    errors = payload.get("errors")
    response = payload.get("response") or []

    print(f"[API-Football] status={status} results={results} resp_len={len(response)} errors={errors}")

    # If API returns empty but we recently had data, show cached data instead of saying "no matches"
    if len(response) == 0:
        if _LAST_GOOD_TEXT and (time.time() - _LAST_GOOD_TS) < 600:
            return _LAST_GOOD_TEXT + "\n\n(Showing last known update)"
        return "⚽ No live matches right now."

    lines = []
    for m in response[:max_games]:
        league_name = (m.get("league") or {}).get("name", "League")
        home = (m.get("teams") or {}).get("home", {}).get("name", "Home")
        away = (m.get("teams") or {}).get("away", {}).get("name", "Away")
        goals = m.get("goals") or {}
        minute = (m.get("fixture") or {}).get("status", {}).get("elapsed")

        score_home = goals.get("home")
        score_away = goals.get("away")

        minute_txt = f"{minute}'" if minute is not None else ""
        lines.append(f"{league_name}: {home} {score_home}-{score_away} {away} {minute_txt}".strip())

    text = "⚽ Live Matches\n\n" + "\n".join(lines)

    # update cache
    _LAST_GOOD_TEXT = text
    _LAST_GOOD_TS = time.time()

    return text

