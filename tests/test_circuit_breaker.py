"""Tests para circuit breaker y clasificación de errores (Fases 3F, 4C)."""
import anthropic
from agents.base import (
    _circuit_breaker,
    _circuit_check,
    _circuit_record_success,
    _circuit_record_failure,
    _is_permanent_error,
    _should_retry,
    AgentError,
)


def _reset_circuit():
    _circuit_breaker["failures"] = 0
    _circuit_breaker["open"] = False
    _circuit_breaker["opened_at"] = 0.0


# --- Circuit breaker ---

def test_circuit_closed_by_default():
    _reset_circuit()
    # No debe lanzar excepción
    _circuit_check()


def test_circuit_opens_after_threshold():
    _reset_circuit()
    for _ in range(_circuit_breaker["threshold"]):
        _circuit_record_failure()
    assert _circuit_breaker["open"] is True


def test_circuit_open_rejects_calls():
    _reset_circuit()
    import time
    for _ in range(_circuit_breaker["threshold"]):
        _circuit_record_failure()
    _circuit_breaker["opened_at"] = time.time()  # Just opened
    try:
        _circuit_check()
        assert False, "Debería haber lanzado AgentError"
    except AgentError as e:
        assert "Circuit breaker" in str(e)


def test_circuit_resets_on_success():
    _reset_circuit()
    _circuit_record_failure()
    _circuit_record_failure()
    assert _circuit_breaker["failures"] == 2
    _circuit_record_success()
    assert _circuit_breaker["failures"] == 0
    assert _circuit_breaker["open"] is False


def test_circuit_half_open_after_cooldown():
    _reset_circuit()
    for _ in range(_circuit_breaker["threshold"]):
        _circuit_record_failure()
    # Simular que pasó el cooldown
    _circuit_breaker["opened_at"] = 0.0  # Epoch = mucho tiempo atrás
    _circuit_check()  # No debe lanzar (half-open)
    assert _circuit_breaker["open"] is False


# --- Error classification ---

def test_auth_error_is_permanent():
    e = anthropic.AuthenticationError(
        message="Invalid API key",
        response=_mock_response(401),
        body={"error": {"message": "Invalid API key"}},
    )
    assert _is_permanent_error(e) is True
    assert _should_retry(e) is False


def test_bad_request_is_permanent():
    e = anthropic.BadRequestError(
        message="Bad request",
        response=_mock_response(400),
        body={"error": {"message": "Bad request"}},
    )
    assert _is_permanent_error(e) is True
    assert _should_retry(e) is False


def test_rate_limit_is_retryable():
    e = anthropic.RateLimitError(
        message="Rate limited",
        response=_mock_response(429),
        body={"error": {"message": "Rate limited"}},
    )
    assert _is_permanent_error(e) is False
    assert _should_retry(e) is True


def test_connection_error_is_retryable():
    e = anthropic.APIConnectionError(request=None)
    assert _is_permanent_error(e) is False
    assert _should_retry(e) is True


def test_timeout_error_is_retryable():
    e = anthropic.APITimeoutError(request=None)
    assert _is_permanent_error(e) is False
    assert _should_retry(e) is True


# --- Helper ---

class _mock_response:
    """Mock minimal de httpx.Response para crear errores de Anthropic."""
    def __init__(self, status_code):
        self.status_code = status_code
        self.headers = {}
        self.request = None
