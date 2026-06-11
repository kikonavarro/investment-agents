"""
Configuración global del sistema multi-agente.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VALUATIONS_DIR = DATA_DIR / "valuations"

# NOTA: aquí vivían DCF_DEFAULTS y WACC_DEFAULTS (risk-free/ERP por divisa).
# Se eliminaron (2026-06-11): ningún código de producción los leía y unos números
# "oficiales" que el sistema ignora son una fuente de divergencia futura. El WACC
# lo decide Opus en cada tesis (skill dcf-valuation) con datos actuales, y el motor
# (tools/valuation_engine.calculate_wacc_capm) recibe los valores como argumentos.

# --- Portfolio ---
PORTFOLIO_FILE = DATA_DIR / "mi_cartera.xlsx"

# --- Caché de datos financieros ---
CACHE_DIR = DATA_DIR / "cache"
CACHE_TTL_DAYS = 7        # Limpiar caché de más de 7 días
FORCE_FRESH = False       # --fresh para forzar descarga nueva

# --- Telegram Bot ---
TELEGRAM_POLL_INTERVAL = 60     # Segundos entre polls
TELEGRAM_MESSAGE_TIMEOUT = 180  # Max segundos procesando un mensaje

# --- Scheduler ---
TWEETS_DIR = DATA_DIR / "tweets"
DB_PATH = DATA_DIR / "scheduler_state.db"
