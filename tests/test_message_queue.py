"""
Tests para tools/message_queue.py — la cola de Telegram (única vía de entrada de Kiko).

Verifica el roundtrip, que dos mensajes del mismo segundo no colisionan, que un
fichero corrupto avisa en vez de tragar en silencio, y que las escrituras dejan JSON
válido sin temporales residuales.
"""
import json

import pytest

from tools import message_queue as mq


@pytest.fixture
def queue(tmp_path, monkeypatch):
    """Redirige la cola a un directorio temporal."""
    monkeypatch.setattr(mq, "QUEUE_DIR", tmp_path)
    monkeypatch.setattr(mq, "INBOX_DIR", tmp_path / "inbox")
    monkeypatch.setattr(mq, "DONE_DIR", tmp_path / "done")
    return mq


def test_enqueue_get_pending_roundtrip(queue):
    mid = queue.enqueue_message("123", "Kiko", "tesis de AAPL")
    assert mid
    pending = queue.get_pending()
    assert len(pending) == 1
    assert pending[0]["text"] == "tesis de AAPL"
    assert pending[0]["status"] == "pending"


def test_mensajes_distintos_no_colisionan(queue):
    """Dos mensajes del mismo chat (aunque sea el mismo segundo) con texto distinto
    deben generar ids únicos y persistir ambos."""
    m1 = queue.enqueue_message("123", "Kiko", "mensaje uno")
    m2 = queue.enqueue_message("123", "Kiko", "mensaje dos")
    assert m1 != m2
    assert len(queue.get_pending()) == 2


def test_duplicado_se_bloquea(queue):
    """Mismo texto del mismo chat en la ventana de 30s = duplicado ignorado."""
    m1 = queue.enqueue_message("123", "Kiko", "idéntico")
    m2 = queue.enqueue_message("123", "Kiko", "idéntico")
    assert m1 is not None
    assert m2 is None
    assert len(queue.get_pending()) == 1


def test_fichero_corrupto_avisa_y_no_crashea(queue, capsys):
    """Un JSON truncado en inbox NO debe perderse en silencio ni tumbar get_pending."""
    queue.enqueue_message("123", "Kiko", "mensaje bueno")
    (queue.INBOX_DIR / "corrupto.json").write_text("{ truncado", encoding="utf-8")

    pending = queue.get_pending()
    assert len(pending) == 1  # el bueno se lee igual
    out = capsys.readouterr().out
    assert "AVISO" in out and "corrupto.json" in out


def test_save_response_deja_json_valido_sin_temporales(queue):
    mid = queue.enqueue_message("123", "Kiko", "pregunta")
    queue.save_response(mid, "respuesta", auto_send=True)

    msg = json.loads((queue.INBOX_DIR / f"{mid}.json").read_text(encoding="utf-8"))
    assert msg["response"] == "respuesta"
    assert msg["status"] == "sending"
    leftovers = [p for p in queue.INBOX_DIR.iterdir() if p.name.endswith(".tmp")]
    assert not leftovers
