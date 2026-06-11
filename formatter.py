"""
Modulo de formatacao das mensagens do Telegram.
"""
from datetime import datetime


def format_risk_stars(risk):
    stars = {1: "[*] MUITO BAIXO", 2: "[**] BAIXO", 3: "[***] MEDIO", 4: "[****] ELEVADO", 5: "[*****] ALTO"}
    return stars.get(risk, "?")


def format_form(form):
    if not form:
        return "N/D"
    result = ""
    for char in form:
        if char == "W":
            result += "[V]"
        elif char == "D":
            result += "[E]"
        elif char == "L":
            result += "[D]"
    return result


def format_minute_data(minute_data):
    lines = []
    for period in ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90"]:
        data = minute_data.get(period, {})
        pct = data.get("percentage", "0%")
        total = data.get("total", 0)
        lines.append(f"  {period}: {pct} ({total} gols)")
    return "\n".join(lines)


def format_h2h(h2h_data):
    if not h2h_data:
        return "  Sem dados de H2H"
    lines = []
    for match in h2h_data[:5]:
        teams = match.get("teams", {})
        goals = match.get("goals", {})
        fixture = match.get("fixture", {})
        home = teams.get("home", {})
        away = teams.get("away", {})
        hg = goals.get("home", 0) or 0
        ag = goals.get("away", 0) or 0
        date = fixture.get("date", "")
        try:
            dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
            date_str = dt.strftime("%d/%m/%y")
        except Exception:
            date_str = "?"
        lines.append(f"  {home.get('name', '?')} {hg}x{ag} {away.get('name', '?')} ({date_str})")
    return "\n".join(lines)


def format_full_analysis(analysis):
    fixture = analysis["fixture"]
    league = analysis["league"]
    home = analysis["home"]
    away = analysis["away"]
    h2h = analysis["h2h"]
    lay_0x3 = analysis["analysis"]["lay_0x3"]
    lay_3x0 = analysis["analysis"]["lay_3x0"]
    mkt_0x3 = analysis["analysis"]["market_suggestion_0x3"]
    mkt_3x0 = analysis["analysis"]["market_suggestion_3x0"]
    home_name = home["info"].get("name", "?")
    away_name = away["info"].get("name", "?")
    league_name = league.get("name", "?")
    country = league.get("country", "?")
    date_str = fixture.get("date", "")
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M")
    except Exception:
        time_str = "?"
    h_stats = home["stats"]
    a_stats = away["stats"]
    h_goals_against_min = format_minute_data(h_stats.get("goals_against_minute", {}))
    a_goals_for_min = format_minute_data(a_stats.get("goals_for_minute", {}))
    h_goals_for_min = format_minute_data(h_stats.get("goals_for_minute", {}))
    a_goals_against_min = format_minute_data(a_stats.get("goals_against_minute", {}))
    h2h_formatted = format_h2h(h2h)
    verdicts = []
    if lay_0x3["passes_filter"]:
        verdicts.append("[APROVADO] LAY 0x3\n" + f"  Visitante Over 2.5 fora: {lay_0x3['away_over25_scored']:.1f}%\n" + f"  Mandante sofre Over 2.5 casa: {lay_0x3['home_over25_conceded']:.1f}%\n" + f"  Entrada: {lay_0x3['entry_type']}\n" + f"  Mercado sugerido: {mkt_0x3}\n" + f"  Risco: {format_risk_stars(lay_0x3['risk'])}")
    else:
        verdicts.append(f"[REPROVADO] LAY 0x3\n  Vis. O2.5: {lay_0x3['away_over25_scored']:.1f}% | Mand. sofre: {lay_0x3['home_over25_conceded']:.1f}%")
    if lay_3x0["passes_filter"]:
        verdicts.append("[APROVADO] LAY 3x0\n" + f"  Mandante Over 2.5 casa: {lay_3x0['home_over25_scored']:.1f}%\n" + f"  Visitante sofre Over 2.5 fora: {lay_3x0['away_over25_conceded']:.1f}%\n" + f"  Entrada: {lay_3x0['entry_type']}\n" + f"  Mercado sugerido: {mkt_3x0}\n" + f"  Risco: {format_risk_stars(lay_3x0['risk'])}")
    else:
        verdicts.append(f"[REPROVADO] LAY 3x0\n  Mand. O2.5: {lay_3x0['home_over25_scored']:.1f}% | Vis. sofre: {lay_3x0['away_over25_conceded']:.1f}%")
    verdicts_text = "\n\n".join(verdicts)
    msg = ("========================\n" + f"{home_name} x {away_name}\n" + f"{league_name} ({country}) | {time_str}\n" + "========================\n\n" + f"[CASA] {home_name}\n" + f"  Forma: {format_form(h_stats.get('form', ''))}\n" + f"  Marca: {h_stats['goals_for']['avg_home']} gol/jogo\n" + f"  Sofre: {h_stats['goals_against']['avg_home']} gol/jogo\n" + f"  Over 2.5 marcados: {home['over25_scored_home']:.1f}%\n" + f"  Over 2.5 sofridos: {home['over25_conceded_home']:.1f}%\n" + f"  Clean sheet: {home['clean_sheet_pct']:.1f}%\n" + f"  MINUTAGEM GOLS SOFRIDOS:\n{h_goals_against_min}\n" + f"  MINUTAGEM GOLS MARCADOS:\n{h_goals_for_min}\n\n" + f"[FORA] {away_name}\n" + f"  Forma: {format_form(a_stats.get('form', ''))}\n" + f"  Marca: {a_stats['goals_for']['avg_away']} gol/jogo\n" + f"  Sofre: {a_stats['goals_against']['avg_away']} gol/jogo\n" + f"  Over 2.5 marcados: {away['over25_scored_away']:.1f}%\n" + f"  Over 2.5 sofridos: {away['over25_conceded_away']:.1f}%\n" + f"  Nao marca: {away['failed_to_score_pct']:.1f}%\n" + f"  MINUTAGEM GOLS MARCADOS:\n{a_goals_for_min}\n" + f"  MINUTAGEM GOLS SOFRIDOS:\n{a_goals_against_min}\n\n" + f"H2H (ultimos 5):\n{h2h_formatted}\n\n" + f"VEREDICTO:\n{verdicts_text}\n" + "========================")
    return msg


def format_quick_summary(analysis):
    fixture = analysis["fixture"]
    league = analysis["league"]
    home = analysis["home"]
    away = analysis["away"]
    lay_0x3 = analysis["analysis"]["lay_0x3"]
    lay_3x0 = analysis["analysis"]["lay_3x0"]
    mkt_0x3 = analysis["analysis"]["market_suggestion_0x3"]
    mkt_3x0 = analysis["analysis"]["market_suggestion_3x0"]
    home_name = home["info"].get("name", "?")
    away_name = away["info"].get("name", "?")
    league_name = league.get("name", "?")
    date_str = fixture.get("date", "")
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M")
    except Exception:
        time_str = "?"
    lines = [f"-- {home_name} x {away_name}", f"   {league_name} | {time_str}"]
    if lay_0x3["passes_filter"]:
        lines.append(f"   [OK] Lay 0x3 | {lay_0x3['entry_type']} | {mkt_0x3}\n   Vis. O2.5: {lay_0x3['away_over25_scored']:.0f}% | Mand. sofre: {lay_0x3['home_over25_conceded']:.0f}%\n   Risco: {format_risk_stars(lay_0x3['risk'])}")
    if lay_3x0["passes_filter"]:
        lines.append(f"   [OK] Lay 3x0 | {lay_3x0['entry_type']} | {mkt_3x0}\n   Mand. O2.5: {lay_3x0['home_over25_scored']:.0f}% | Vis. sofre: {lay_3x0['away_over25_conceded']:.0f}%\n   Risco: {format_risk_stars(lay_3x0['risk'])}")
    return "\n".join(lines)


def format_no_games_found():
    return "Nenhum jogo passou nos filtros hoje.\nCriterio: Over 2.5 <= 19%\nUse /analisar Time x Time para analise manual."


def format_daily_header(total_analyzed, total_approved):
    today = datetime.now().strftime("%d/%m/%Y")
    return f"FILTRO DE JOGOS - {today}\n========================\nAnalisados: {total_analyzed}\nAprovados: {total_approved}\nCriterio: Over 2.5 <= 19%\n========================\n"


def format_loading_message():
    return "Buscando e analisando jogos...\nIsso pode levar 1-2 minutos."


def format_error_message(error):
    return f"Erro: {error}\nTente novamente."


def format_config_message(max_marcados, max_sofridos, min_jogos):
    return f"CONFIGURACOES\n========================\n\nOver 2.5 marcados: <= {max_marcados}%\nOver 2.5 sofridos: <= {max_sofridos}%\nMin. jogos: {min_jogos}\n\nAlterar: /setfiltro marcados 15"


def format_help_message():
    return "BOT DE TRADE ESPORTIVO\n========================\n\n/jogos - Filtrar jogos do dia (1a leva de 30)\n/jogos2 - Analisar proximos 30 jogos\n/jogos3 - Analisar mais 30 jogos\n/lista - Ver TODOS os jogos analisados\n/analisar Time A x Time B - Analise detalhada\n/config - Ver configuracoes dos filtros\n/setfiltro marcados 15 - Alterar filtro\n/setfiltro sofridos 15 - Alterar filtro\n/setfiltro jogos 8 - Alterar minimo de jogos\n/help - Esta mensagem\n\n========================\nEstrategia: Lay Placar Exato / Lay Goleada\nCriterio: Over 2.5 <= 19%\nBTTS >= 70% = Lay Placar Exato\nBTTS < 70% = Lay Goleada"
