"""
Modulo de integracao com API-Football (api-sports.io)
"""
import aiohttp
from datetime import datetime
from typing import Optional
import config


class APIFootball:
    def __init__(self):
        self.base_url = config.API_FOOTBALL_BASE_URL
        self.headers = {"x-apisports-key": config.API_FOOTBALL_KEY}

    async def _request(self, endpoint, params):
        url = f"{self.base_url}/{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Erro API: {response.status}")
                        return None
        except Exception as e:
            print(f"Erro na requisicao: {e}")
            return None

    async def get_fixtures_today(self, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        data = await self._request("fixtures", {"date": date})
        if data and "response" in data:
            return data["response"]
        return []

    async def get_team_statistics(self, team_id, league_id, season):
        params = {"team": team_id, "league": league_id, "season": season}
        data = await self._request("teams/statistics", params)
        if data and "response" in data:
            return data["response"]
        return None

    async def get_fixtures_by_team(self, league_id, season, team_id, last=10):
        params = {"league": league_id, "season": season, "team": team_id, "last": last}
        data = await self._request("fixtures", params)
        if data and "response" in data:
            return data["response"]
        return []

    async def get_head_to_head(self, team_id_1, team_id_2, last=5):
        params = {"h2h": f"{team_id_1}-{team_id_2}", "last": last}
        data = await self._request("fixtures/headtohead", params)
        if data and "response" in data:
            return data["response"]
        return []


def parse_team_stats(stats):
    if not stats:
        return {}
    goals_for = stats.get("goals", {}).get("for", {})
    goals_against = stats.get("goals", {}).get("against", {})
    goals_for_minute = goals_for.get("minute", {})
    goals_against_minute = goals_against.get("minute", {})
    fixtures = stats.get("fixtures", {})
    played_home = fixtures.get("played", {}).get("home", 0) or 0
    played_away = fixtures.get("played", {}).get("away", 0) or 0
    played_total = fixtures.get("played", {}).get("total", 0) or 0
    wins = fixtures.get("wins", {})
    draws = fixtures.get("draws", {})
    losses = fixtures.get("losses", {})
    clean_sheet = stats.get("clean_sheet", {})
    failed_to_score = stats.get("failed_to_score", {})
    goals_for_home = goals_for.get("total", {}).get("home", 0) or 0
    goals_for_away = goals_for.get("total", {}).get("away", 0) or 0
    goals_against_home = goals_against.get("total", {}).get("home", 0) or 0
    goals_against_away = goals_against.get("total", {}).get("away", 0) or 0
    avg_gf_home = round(goals_for_home / played_home, 2) if played_home > 0 else 0
    avg_gf_away = round(goals_for_away / played_away, 2) if played_away > 0 else 0
    avg_ga_home = round(goals_against_home / played_home, 2) if played_home > 0 else 0
    avg_ga_away = round(goals_against_away / played_away, 2) if played_away > 0 else 0
    form = stats.get("form", "")
    form_last5 = form[-5:] if form else ""

    def parse_minute_data(minute_data):
        periods = {}
        for period in ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "91-105", "106-120"]:
            data = minute_data.get(period, {}) if minute_data else {}
            periods[period] = {
                "total": (data.get("total") or 0) if data else 0,
                "percentage": (data.get("percentage") or "0%") if data else "0%"
            }
        return periods

    return {
        "played": {"home": played_home, "away": played_away, "total": played_total},
        "wins": {"home": wins.get("home", 0) or 0, "away": wins.get("away", 0) or 0, "total": wins.get("total", 0) or 0},
        "draws": {"home": draws.get("home", 0) or 0, "away": draws.get("away", 0) or 0, "total": draws.get("total", 0) or 0},
        "losses": {"home": losses.get("home", 0) or 0, "away": losses.get("away", 0) or 0, "total": losses.get("total", 0) or 0},
        "goals_for": {"home": goals_for_home, "away": goals_for_away, "avg_home": avg_gf_home, "avg_away": avg_gf_away},
        "goals_against": {"home": goals_against_home, "away": goals_against_away, "avg_home": avg_ga_home, "avg_away": avg_ga_away},
        "clean_sheet": {"home": clean_sheet.get("home", 0) or 0, "away": clean_sheet.get("away", 0) or 0, "total": clean_sheet.get("total", 0) or 0},
        "failed_to_score": {"home": failed_to_score.get("home", 0) or 0, "away": failed_to_score.get("away", 0) or 0, "total": failed_to_score.get("total", 0) or 0},
        "form": form_last5,
        "goals_for_minute": parse_minute_data(goals_for_minute),
        "goals_against_minute": parse_minute_data(goals_against_minute),
    }


def calculate_over25_from_fixtures(fixtures, team_id, is_home, mode="scored"):
    if not fixtures:
        return 0.0
    relevant_games = 0
    over25_count = 0
    for fixture in fixtures:
        teams = fixture.get("teams", {})
        goals = fixture.get("goals", {})
        home_team = teams.get("home", {})
        away_team = teams.get("away", {})
        home_goals = goals.get("home")
        away_goals = goals.get("away")
        if home_goals is None or away_goals is None:
            continue
        if home_team.get("id") == team_id:
            team_scored = home_goals
            team_conceded = away_goals
            game_is_home = True
        elif away_team.get("id") == team_id:
            team_scored = away_goals
            team_conceded = home_goals
            game_is_home = False
        else:
            continue
        if is_home is not None and game_is_home != is_home:
            continue
        relevant_games += 1
        if mode == "scored" and team_scored >= 3:
            over25_count += 1
        elif mode == "conceded" and team_conceded >= 3:
            over25_count += 1
    if relevant_games == 0:
        return 0.0
    return round((over25_count / relevant_games) * 100, 1)
