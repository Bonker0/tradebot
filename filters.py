"""
Modulo de filtros para Trade Esportivo.
"""
from typing import Optional
import config
from api_football import APIFootball, parse_team_stats, calculate_over25_from_fixtures


class TradeFilter:
    def __init__(self):
        self.api = APIFootball()
        self.max_over25_marcados = config.FILTRO_MAX_OVER25_MARCADOS
        self.max_over25_sofridos = config.FILTRO_MAX_OVER25_SOFRIDOS
        self.min_jogos = config.FILTRO_MIN_JOGOS_DISPUTADOS

    async def analyze_fixture(self, fixture):
        teams = fixture.get("teams", {})
        league = fixture.get("league", {})
        fixture_info = fixture.get("fixture", {})
        home_team = teams.get("home", {})
        away_team = teams.get("away", {})
        home_id = home_team.get("id")
        away_id = away_team.get("id")
        league_id = league.get("id")
        season = league.get("season")
        if not all([home_id, away_id, league_id, season]):
            return None
        home_stats_raw = await self.api.get_team_statistics(home_id, league_id, season)
        away_stats_raw = await self.api.get_team_statistics(away_id, league_id, season)
        if not home_stats_raw or not away_stats_raw:
            return None
        home_stats = parse_team_stats(home_stats_raw)
        away_stats = parse_team_stats(away_stats_raw)
        if (home_stats["played"]["home"] < self.min_jogos or
                away_stats["played"]["away"] < self.min_jogos):
            return None
        home_fixtures = await self.api.get_fixtures_by_team(league_id, season, home_id, last=10)
        away_fixtures = await self.api.get_fixtures_by_team(league_id, season, away_id, last=10)
        away_over25_scored = calculate_over25_from_fixtures(away_fixtures, away_id, is_home=False, mode="scored")
        home_over25_conceded = calculate_over25_from_fixtures(home_fixtures, home_id, is_home=True, mode="conceded")
        home_over25_scored = calculate_over25_from_fixtures(home_fixtures, home_id, is_home=True, mode="scored")
        away_over25_conceded = calculate_over25_from_fixtures(away_fixtures, away_id, is_home=False, mode="conceded")
        h2h = await self.api.get_head_to_head(home_id, away_id, last=5)
        home_clean_sheet_pct = round(
            (home_stats["clean_sheet"]["home"] / home_stats["played"]["home"]) * 100, 1
        ) if home_stats["played"]["home"] > 0 else 0
        away_failed_to_score_pct = round(
            (away_stats["failed_to_score"]["away"] / away_stats["played"]["away"]) * 100, 1
        ) if away_stats["played"]["away"] > 0 else 0
        lay_0x3 = self._analyze_lay_0x3(away_over25_scored, home_over25_conceded, away_stats, away_failed_to_score_pct)
        lay_3x0 = self._analyze_lay_3x0(home_over25_scored, away_over25_conceded, home_stats)
        home_avg_scored = home_stats["goals_for"]["avg_home"]
        away_avg_scored = away_stats["goals_for"]["avg_away"]

        # Calcular BTTS (ambas marcam) dos ultimos jogos
        home_btts_pct = self._calculate_btts(home_fixtures, home_id, is_home=True)
        away_btts_pct = self._calculate_btts(away_fixtures, away_id, is_home=False)

        # Decisao de mercado usando BTTS (70%+) e media de gols do time a favor
        # Lay 0x3: time a favor = mandante. Se BTTS >= 70% -> placar exato (ambas marcam, goleada limpa rara)
        if home_btts_pct >= 70 or home_avg_scored >= 1.2:
            market_suggestion_0x3 = "LAY PLACAR EXATO (BTTS: " + str(home_btts_pct) + "%)"
        else:
            market_suggestion_0x3 = "LAY GOLEADA (BTTS: " + str(home_btts_pct) + "%)"

        # Lay 3x0: time a favor = visitante. Se BTTS >= 70% -> placar exato
        if away_btts_pct >= 70 or away_avg_scored >= 1.2:
            market_suggestion_3x0 = "LAY PLACAR EXATO (BTTS: " + str(away_btts_pct) + "%)"
        else:
            market_suggestion_3x0 = "LAY GOLEADA (BTTS: " + str(away_btts_pct) + "%)"
        return {
            "fixture": fixture_info, "league": league,
            "home": {"info": home_team, "stats": home_stats, "over25_scored_home": home_over25_scored, "over25_conceded_home": home_over25_conceded, "clean_sheet_pct": home_clean_sheet_pct},
            "away": {"info": away_team, "stats": away_stats, "over25_scored_away": away_over25_scored, "over25_conceded_away": away_over25_conceded, "failed_to_score_pct": away_failed_to_score_pct},
            "h2h": h2h,
            "analysis": {"lay_0x3": lay_0x3, "lay_3x0": lay_3x0, "market_suggestion_0x3": market_suggestion_0x3, "market_suggestion_3x0": market_suggestion_3x0}
        }

    def _analyze_lay_0x3(self, away_over25_scored, home_over25_conceded, away_stats, away_failed_to_score_pct):
        passes_filter = (away_over25_scored <= self.max_over25_marcados and home_over25_conceded <= self.max_over25_sofridos)
        risk = self._calculate_risk(away_over25_scored, home_over25_conceded)
        away_goals_0_15 = away_stats.get("goals_for_minute", {}).get("0-15", {}).get("percentage", "0%")
        away_goals_0_15_pct = float(str(away_goals_0_15).replace("%", "").replace("None", "0") or "0")
        wait_15min = away_goals_0_15_pct >= 20
        return {"passes_filter": passes_filter, "away_over25_scored": away_over25_scored, "home_over25_conceded": home_over25_conceded, "risk": risk, "wait_15min": wait_15min, "away_goals_0_15_pct": away_goals_0_15_pct, "away_failed_to_score_pct": away_failed_to_score_pct, "entry_type": "ESPERAR 15 MIN" if wait_15min else "ENTRADA DIRETA"}

    def _analyze_lay_3x0(self, home_over25_scored, away_over25_conceded, home_stats):
        passes_filter = (home_over25_scored <= self.max_over25_marcados and away_over25_conceded <= self.max_over25_sofridos)
        risk = self._calculate_risk(home_over25_scored, away_over25_conceded)
        home_goals_0_15 = home_stats.get("goals_for_minute", {}).get("0-15", {}).get("percentage", "0%")
        home_goals_0_15_pct = float(str(home_goals_0_15).replace("%", "").replace("None", "0") or "0")
        wait_15min = home_goals_0_15_pct >= 20
        return {"passes_filter": passes_filter, "home_over25_scored": home_over25_scored, "away_over25_conceded": away_over25_conceded, "risk": risk, "wait_15min": wait_15min, "home_goals_0_15_pct": home_goals_0_15_pct, "entry_type": "ESPERAR 15 MIN" if wait_15min else "ENTRADA DIRETA"}

    def _calculate_btts(self, fixtures, team_id, is_home):
        """Calcula % de jogos onde ambas as equipes marcaram."""
        if not fixtures:
            return 0.0
        relevant_games = 0
        btts_count = 0
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
                game_is_home = True
            elif away_team.get("id") == team_id:
                game_is_home = False
            else:
                continue
            if is_home is not None and game_is_home != is_home:
                continue
            relevant_games += 1
            if home_goals >= 1 and away_goals >= 1:
                btts_count += 1
        if relevant_games == 0:
            return 0.0
        return round((btts_count / relevant_games) * 100, 1)

    def _calculate_risk(self, over25_a, over25_b):
        avg = (over25_a + over25_b) / 2
        if avg <= 5: return 1
        elif avg <= 10: return 2
        elif avg <= 15: return 3
        elif avg <= 19: return 4
        else: return 5

    def filter_fixtures(self, analysis):
        lay_0x3 = analysis["analysis"]["lay_0x3"]
        lay_3x0 = analysis["analysis"]["lay_3x0"]
        return {"lay_0x3_approved": lay_0x3["passes_filter"], "lay_3x0_approved": lay_3x0["passes_filter"], "any_approved": lay_0x3["passes_filter"] or lay_3x0["passes_filter"]}
