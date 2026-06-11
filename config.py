"""
Configuracoes do Bot de Trade Esportivo
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_HOST = "v3.football.api-sports.io"
API_FOOTBALL_BASE_URL = f"https://{API_FOOTBALL_HOST}"
FILTRO_MAX_OVER25_MARCADOS = int(os.getenv("FILTRO_MAX_OVER25_MARCADOS", "19"))
FILTRO_MAX_OVER25_SOFRIDOS = int(os.getenv("FILTRO_MAX_OVER25_SOFRIDOS", "19"))
FILTRO_MIN_JOGOS_DISPUTADOS = int(os.getenv("FILTRO_MIN_JOGOS", "5"))
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")
MAX_JOGOS_DIA = int(os.getenv("MAX_JOGOS_DIA", "50"))
