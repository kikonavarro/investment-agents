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

# --- API ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# --- Modelos por tipo de tarea (optimización de coste) ---
MODELS = {
    "quick": "claude-haiku-4-5-20251001",       # Clasificar, formatear, extraer
    "standard": "claude-sonnet-4-6",             # Análisis, redacción
    "deep": "claude-opus-4-6",                   # Razonamiento complejo (usar poco)
}

# --- DCF defaults (referencia, reales en tools/financial_data.py) ---
DCF_DEFAULTS = {
    "projection_years": 5,
    "risk_free_rate": 0.045,
    "equity_risk_premium": 0.055,
}

# --- WACC por mercado/divisa ---
WACC_DEFAULTS = {
    "risk_free_rates": {
        "USD": 0.045, "EUR": 0.035, "GBP": 0.04, "CAD": 0.04,
        "AUD": 0.045, "CHF": 0.02, "JPY": 0.01, "HKD": 0.045,
        "SEK": 0.03, "NOK": 0.035, "DKK": 0.03,
        "INR": 0.07, "BRL": 0.10, "MXN": 0.09, "ZAR": 0.08,
        "KRW": 0.035, "SGD": 0.03, "TWD": 0.02,
        "default": 0.045,
    },
    "equity_risk_premiums": {
        "USD": 0.055, "EUR": 0.06, "GBP": 0.055, "CAD": 0.055,
        "AUD": 0.06, "CHF": 0.05, "JPY": 0.06,
        "INR": 0.08, "BRL": 0.08, "MXN": 0.07,
        "default": 0.055,
    },
    "credit_spread": 0.02,  # 200bps sobre risk-free para coste de deuda
}

# --- Portfolio ---
PORTFOLIO_FILE = DATA_DIR / "mi_cartera.xlsx"

# --- Caché de datos financieros ---
CACHE_DIR = DATA_DIR / "cache"
CACHE_TTL_DAYS = 7        # Limpiar caché de más de 7 días
FORCE_FRESH = False       # --fresh para forzar descarga nueva

# --- Telegram Bot ---
TELEGRAM_POLL_INTERVAL = 60     # Segundos entre polls
TELEGRAM_MESSAGE_TIMEOUT = 180  # Max segundos procesando un mensaje

# --- API call config ---
API_TIMEOUTS = {"quick": 30, "standard": 60, "deep": 120}
API_MAX_RETRIES = 3
API_INITIAL_BACKOFF = 2  # Segundos
API_COST_PER_M_TOKENS = {
    "quick":    (1.00,  5.00),   # Haiku (input, output)
    "standard": (3.00, 15.00),   # Sonnet
    "deep":    (15.00, 75.00),   # Opus
}

# --- Scheduler ---
TWEETS_DIR = DATA_DIR / "tweets"
DB_PATH = DATA_DIR / "scheduler_state.db"
