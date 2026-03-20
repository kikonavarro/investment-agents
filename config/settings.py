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
ANALYSES_DIR = DATA_DIR / "analyses"
REPORTS_DIR = DATA_DIR / "reports"
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

# --- Portfolio ---
PORTFOLIO_FILE = DATA_DIR / "mi_cartera.xlsx"

# --- Modo data-only (sin llamadas API, para usar desde Claude Code) ---
DATA_ONLY_MODE = False

# --- Caché de datos financieros ---
CACHE_DIR = DATA_DIR / "cache"
CACHE_TTL_DAYS = 7        # Limpiar caché de más de 7 días
FORCE_FRESH = False       # --fresh para forzar descarga nueva

# --- Scheduler ---
TWEETS_DIR = DATA_DIR / "tweets"
DB_PATH = DATA_DIR / "scheduler_state.db"
