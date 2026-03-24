"""
Wrapper central para llamadas a la API de Claude.
Todos los agentes usan call_agent(). Una sola función, sin clases.

En modo DATA_ONLY_MODE, las llamadas se interceptan y no consumen API.
Esto permite usar Claude Code (suscripción Max) para la interpretación.

Incluye: reintentos con backoff exponencial, timeouts por tier,
fallback de modelo, manejo de errores transitorios,
y tracking de costes/tokens por llamada.
"""
import json
import time
from datetime import datetime
import anthropic
from config import settings
from config.settings import MODELS

client = anthropic.Anthropic()

# --- Circuit breaker ---
_circuit_breaker = {
    "failures": 0,
    "open": False,
    "opened_at": 0.0,
    "cooldown_s": 60,
    "threshold": 3,
}


def _circuit_check():
    """Verifica si el circuit breaker permite la llamada. Raise si está abierto."""
    cb = _circuit_breaker
    if not cb["open"]:
        return
    elapsed = time.time() - cb["opened_at"]
    if elapsed >= cb["cooldown_s"]:
        # Half-open: permitir un intento
        cb["open"] = False
        cb["failures"] = 0
        print(f"  [circuit-breaker] Half-open tras {cb['cooldown_s']}s de cooldown")
        return
    raise AgentError(
        f"Circuit breaker abierto ({cb['failures']} fallos consecutivos). "
        f"Reintento en {cb['cooldown_s'] - elapsed:.0f}s.",
        tier="", partial=False,
    )


def _circuit_record_success():
    """Registra éxito → resetea contador."""
    _circuit_breaker["failures"] = 0
    _circuit_breaker["open"] = False


def _circuit_record_failure():
    """Registra fallo → abre circuit si supera threshold."""
    cb = _circuit_breaker
    cb["failures"] += 1
    if cb["failures"] >= cb["threshold"]:
        cb["open"] = True
        cb["opened_at"] = time.time()
        print(f"  [circuit-breaker] ABIERTO tras {cb['failures']} fallos consecutivos. "
              f"Cooldown: {cb['cooldown_s']}s")


# Timeouts, costes y reintentos — desde settings.py
TIMEOUTS = settings.API_TIMEOUTS
COST_PER_M_TOKENS = settings.API_COST_PER_M_TOKENS

# --- Tracker de costes ---
_call_log: list[dict] = []


def reset_tracker():
    """Limpia el log de llamadas. Llamar al inicio de cada pipeline."""
    _call_log.clear()


def _log_call(tier: str, model: str, input_tokens: int, output_tokens: int,
              duration_s: float, agent_name: str = ""):
    """Registra una llamada a la API."""
    cost_in, cost_out = COST_PER_M_TOKENS.get(tier, (3.0, 15.0))
    cost = (input_tokens * cost_in + output_tokens * cost_out) / 1_000_000
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "agent": agent_name,
        "model": model,
        "tier": tier,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
        "duration_s": round(duration_s, 2),
    }
    _call_log.append(entry)


def get_tracker_summary() -> dict:
    """Devuelve resumen agregado del pipeline actual."""
    if not _call_log:
        return {"calls": 0, "total_tokens": 0, "total_cost_usd": 0, "total_duration_s": 0}
    total_in = sum(e["input_tokens"] for e in _call_log)
    total_out = sum(e["output_tokens"] for e in _call_log)
    total_cost = sum(e["cost_usd"] for e in _call_log)
    total_dur = sum(e["duration_s"] for e in _call_log)
    return {
        "calls": len(_call_log),
        "input_tokens": total_in,
        "output_tokens": total_out,
        "total_tokens": total_in + total_out,
        "total_cost_usd": round(total_cost, 6),
        "total_duration_s": round(total_dur, 2),
        "detail": list(_call_log),
    }


def print_tracker_summary():
    """Imprime resumen de costes del pipeline."""
    s = get_tracker_summary()
    if s["calls"] == 0:
        return
    print(f"\n{'='*50}")
    print(f"  API: {s['calls']} llamada(s) | "
          f"{s['total_tokens']:,} tokens | "
          f"${s['total_cost_usd']:.4f} | "
          f"{s['total_duration_s']:.1f}s")
    if len(_call_log) > 1:
        for e in _call_log:
            label = e['agent'] or e['tier']
            print(f"    {label:20s} {e['input_tokens']:>6,}+{e['output_tokens']:>6,} tok  "
                  f"${e['cost_usd']:.4f}  {e['duration_s']:.1f}s  ({e['model']})")
    print(f"{'='*50}")

# Cadena de fallback: si un tier falla, intentar con el siguiente
FALLBACK_CHAIN = {
    "deep": "standard",
    "standard": "quick",
    "quick": None,
}

# Errores HTTP que justifican reintento
_RETRYABLE_STATUS = {429, 500, 502, 503, 529}

MAX_RETRIES = settings.API_MAX_RETRIES
INITIAL_BACKOFF = settings.API_INITIAL_BACKOFF


class AgentError(Exception):
    """Error de agente con contexto para resultados parciales."""
    def __init__(self, message: str, agent_name: str = "", tier: str = "", partial: bool = False):
        super().__init__(message)
        self.agent_name = agent_name
        self.tier = tier
        self.partial = partial


def _is_permanent_error(error: Exception) -> bool:
    """True para errores que no tiene sentido reintentar (auth, bad request)."""
    if isinstance(error, anthropic.AuthenticationError):
        return True
    if isinstance(error, anthropic.BadRequestError):
        return True
    if isinstance(error, anthropic.PermissionDeniedError):
        return True
    if isinstance(error, anthropic.NotFoundError):
        return True
    return False


def _should_retry(error: Exception) -> bool:
    """Determina si un error es transitorio y merece reintento."""
    if _is_permanent_error(error):
        return False
    if isinstance(error, anthropic.RateLimitError):
        return True
    if isinstance(error, anthropic.APIStatusError):
        return error.status_code in _RETRYABLE_STATUS
    if isinstance(error, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
        return True
    return False


def _call_with_retry(model: str, system_prompt: str, user_message: str,
                     max_tokens: int, tier: str,
                     tools: list | None = None) -> anthropic.types.Message:
    """Llama a la API con reintentos y backoff exponencial."""
    timeout = TIMEOUTS.get(tier, 60)
    last_error = None

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
        "timeout": timeout,
    }
    if tools:
        kwargs["tools"] = tools

    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(**kwargs)
            return response
        except Exception as e:
            last_error = e
            if not _should_retry(e):
                raise
            wait = INITIAL_BACKOFF * (2 ** attempt)
            print(f"  [retry] Intento {attempt + 1}/{MAX_RETRIES} fallido "
                  f"({type(e).__name__}). Reintentando en {wait}s...")
            time.sleep(wait)

    raise last_error


def _extract_text(response: anthropic.types.Message) -> str:
    """Extrae el texto de una respuesta que puede tener múltiples content blocks."""
    text_parts = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
    return "\n".join(text_parts) if text_parts else ""


def call_agent(
    system_prompt: str,
    user_message: str,
    model_tier: str = "standard",
    max_tokens: int = 2000,
    json_output: bool = False,
    force_api: bool = False,
    allow_fallback: bool = True,
    agent_name: str = "",
    web_search: bool = False,
) -> str:
    """
    Llamada genérica a Claude con reintentos y fallback.

    Args:
        system_prompt: Instrucciones del agente (mantener corto).
        user_message: Datos/instrucción específica (solo lo necesario).
        model_tier: "quick" (Haiku), "standard" (Sonnet), "deep" (Opus).
        max_tokens: Límite de respuesta.
        json_output: Si True, fuerza respuesta JSON.
        force_api: Si True, usa la API aunque DATA_ONLY_MODE esté activo.
        allow_fallback: Si True, intenta modelo inferior si el principal falla.
        agent_name: Nombre del agente (para tracking de costes).
        web_search: Si True, habilita búsqueda web en la llamada.

    Returns:
        Texto de respuesta de Claude.
    """
    if json_output:
        system_prompt += "\n\nResponde ÚNICAMENTE con JSON válido. Sin texto adicional."

    # Modo data-only: no llamar a la API (salvo force_api)
    if settings.DATA_ONLY_MODE and not force_api:
        return "[DATA_ONLY]"

    # Circuit breaker: fail fast si hay muchos fallos consecutivos
    _circuit_check()

    tools = [{"type": "web_search_20250305"}] if web_search else None

    current_tier = model_tier
    while current_tier is not None:
        model = MODELS[current_tier]
        try:
            t0 = time.time()
            response = _call_with_retry(model, system_prompt, user_message,
                                        max_tokens, current_tier, tools=tools)
            duration = time.time() - t0
            # Éxito: resetear circuit breaker
            _circuit_record_success()
            # Registrar uso de tokens
            usage = response.usage
            _log_call(
                tier=current_tier,
                model=model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                duration_s=duration,
                agent_name=agent_name,
            )
            if current_tier != model_tier:
                print(f"  [fallback] Respuesta obtenida con {current_tier} "
                      f"(modelo original: {model_tier})")
            return _extract_text(response)
        except Exception as e:
            # Errores permanentes: no reintentar ni hacer fallback
            if _is_permanent_error(e):
                _circuit_record_failure()
                raise AgentError(
                    f"Error permanente ({type(e).__name__}): {e}",
                    tier=model_tier,
                )
            if allow_fallback and FALLBACK_CHAIN.get(current_tier):
                fallback = FALLBACK_CHAIN[current_tier]
                print(f"  [fallback] {current_tier} agotó reintentos "
                      f"({type(e).__name__}). Bajando a {fallback}...")
                current_tier = fallback
            else:
                _circuit_record_failure()
                raise AgentError(
                    f"API falló tras {MAX_RETRIES} reintentos: {e}",
                    tier=model_tier,
                )


def call_agent_json(
    system_prompt: str,
    user_message: str,
    model_tier: str = "standard",
    max_tokens: int = 2000,
    force_api: bool = False,
    allow_fallback: bool = True,
    agent_name: str = "",
    web_search: bool = False,
) -> dict:
    """Wrapper que llama a call_agent y parsea el JSON de respuesta."""
    # Modo data-only: devolver sentinel sin llamar a la API
    if settings.DATA_ONLY_MODE and not force_api:
        return {"_data_only": True}

    raw = call_agent(
        system_prompt=system_prompt,
        user_message=user_message,
        model_tier=model_tier,
        max_tokens=max_tokens,
        json_output=True,
        allow_fallback=allow_fallback,
        agent_name=agent_name,
        web_search=web_search,
    )
    # Limpiar posibles backticks markdown
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)
