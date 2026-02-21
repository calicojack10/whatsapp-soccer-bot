import requests

API_KEY = "YOUR_API_FOOTBALL_KEY"


def live_scores():
    url = "https://v3.football.api-sports.io/fixtures?live=all"

    headers = {
        "x-apisports-key": API_KEY
    }

    r = requests.get(url, headers=headers).json()

    games = []

    for match in r.get("response", [])[:10]:
        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]
        goals = match["goals"]
        minute = match["fixture"]["status"]["elapsed"]

        games.append(
            f"{home} {goals['home']}-{goals['away']} {away} ({minute}')"
        )

    if not games:
        return "⚽ No live matches right now."

    return "⚽ Live Matches\n\n" + "\n".join(games)