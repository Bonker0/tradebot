"""
Bot Telegram de Trade Esportivo - Filtro de Jogos para Lay Placar Exato
"""
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters as tg_filters
import config
from api_football import APIFootball
from filters import TradeFilter
from formatter import (
    format_full_analysis, format_quick_summary, format_no_games_found,
    format_daily_header, format_loading_message, format_error_message,
    format_config_message, format_help_message,
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
api = APIFootball()
trade_filter = TradeFilter()
user_config = {
    "max_over25_marcados": config.FILTRO_MAX_OVER25_MARCADOS,
    "max_over25_sofridos": config.FILTRO_MAX_OVER25_SOFRIDOS,
    "min_jogos": config.FILTRO_MIN_JOGOS_DISPUTADOS,
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot de Trade Esportivo!\n\nCriterio: Over 2.5 <= 19%\nUse /help para comandos.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_help_message())


async def jogos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loading_msg = await update.message.reply_text(format_loading_message())
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        fixtures = await api.get_fixtures_today(today)
        if not fixtures:
            await loading_msg.edit_text("Nenhum jogo encontrado hoje.")
            return
        upcoming = [f for f in fixtures if f.get("fixture", {}).get("status", {}).get("short") == "NS"]
        if not upcoming:
            await loading_msg.edit_text("Nenhum jogo pendente hoje.")
            return
        max_analyze = min(len(upcoming), config.MAX_JOGOS_DIA)
        await loading_msg.edit_text("Analisando " + str(max_analyze) + " jogos...")
        approved_games = []
        analyzed_count = 0
        for fixture in upcoming[:max_analyze]:
            try:
                analysis = await trade_filter.analyze_fixture(fixture)
                if analysis:
                    analyzed_count += 1
                    filter_result = trade_filter.filter_fixtures(analysis)
                    if filter_result["any_approved"]:
                        approved_games.append(analysis)
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Erro: {e}")
                continue
        if not approved_games:
            header = format_daily_header(analyzed_count, 0)
            await loading_msg.edit_text(header + "\n" + format_no_games_found())
            return
        header = format_daily_header(analyzed_count, len(approved_games))
        await loading_msg.edit_text(header)
        for game in approved_games:
            await update.message.reply_text(format_quick_summary(game))
            await asyncio.sleep(0.5)
        await update.message.reply_text(str(len(approved_games)) + " jogos aprovados!\nUse /analisar Time x Time para detalhes.")
    except Exception as e:
        logger.error(f"Erro /jogos: {e}")
        await loading_msg.edit_text(format_error_message(str(e)))


async def analisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /analisar Time A x Time B")
        return
    text = " ".join(context.args)
    separator = None
    for sep in [" x ", " X ", " vs ", " VS "]:
        if sep in text:
            separator = sep
            break
    if not separator:
        await update.message.reply_text("Use x para separar. Ex: /analisar Sport x Athletic")
        return
    parts = text.split(separator)
    if len(parts) != 2:
        await update.message.reply_text("Formato invalido.")
        return
    team_a = parts[0].strip()
    team_b = parts[1].strip()
    loading_msg = await update.message.reply_text("Buscando: " + team_a + " x " + team_b + "...")
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        fixtures = await api.get_fixtures_today(today)
        target_fixture = None
        for fixture in fixtures:
            teams = fixture.get("teams", {})
            home_name = teams.get("home", {}).get("name", "").lower()
            away_name = teams.get("away", {}).get("name", "").lower()
            if (team_a.lower() in home_name or team_a.lower() in away_name or
                team_b.lower() in home_name or team_b.lower() in away_name):
                target_fixture = fixture
                break
        if not target_fixture:
            await loading_msg.edit_text("Jogo " + team_a + " x " + team_b + " nao encontrado hoje.")
            return
        analysis = await trade_filter.analyze_fixture(target_fixture)
        if not analysis:
            await loading_msg.edit_text("Sem dados suficientes para este jogo.")
            return
        full_analysis = format_full_analysis(analysis)
        if len(full_analysis) <= 4096:
            await loading_msg.edit_text(full_analysis)
        else:
            parts_msg = [full_analysis[i:i+4000] for i in range(0, len(full_analysis), 4000)]
            await loading_msg.edit_text(parts_msg[0])
            for part in parts_msg[1:]:
                await update.message.reply_text(part)
    except Exception as e:
        logger.error(f"Erro /analisar: {e}")
        await loading_msg.edit_text(format_error_message(str(e)))


async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_config_message(user_config["max_over25_marcados"], user_config["max_over25_sofridos"], user_config["min_jogos"]))


async def setfiltro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /setfiltro marcados 15")
        return
    tipo = context.args[0].lower()
    try:
        valor = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Valor deve ser numero.")
        return
    if tipo == "marcados":
        user_config["max_over25_marcados"] = valor
        trade_filter.max_over25_marcados = valor
        await update.message.reply_text("Over 2.5 marcados: <= " + str(valor) + "%")
    elif tipo == "sofridos":
        user_config["max_over25_sofridos"] = valor
        trade_filter.max_over25_sofridos = valor
        await update.message.reply_text("Over 2.5 sofridos: <= " + str(valor) + "%")
    elif tipo == "jogos":
        user_config["min_jogos"] = valor
        trade_filter.min_jogos = valor
        await update.message.reply_text("Min. jogos: " + str(valor))
    else:
        await update.message.reply_text("Use: marcados, sofridos ou jogos")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Comando nao reconhecido. Use /help")


def main():
    if not config.TELEGRAM_TOKEN:
        print("TELEGRAM_TOKEN nao configurado!")
        return
    if not config.API_FOOTBALL_KEY:
        print("API_FOOTBALL_KEY nao configurado!")
        return
    print("Iniciando Bot de Trade Esportivo...")
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("jogos", jogos))
    application.add_handler(CommandHandler("analisar", analisar))
    application.add_handler(CommandHandler("config", config_command))
    application.add_handler(CommandHandler("setfiltro", setfiltro))
    application.add_handler(MessageHandler(tg_filters.COMMAND, unknown))
    print("Bot iniciado!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
