"""TTS con ElevenLabs + envío como nota de voz por Telegram.

Estado de voz (on/off) se persiste por chat_id en config/voice_state.json.
Cuando está ON, las respuestas se mandan como voice message (OGG Opus).
Si la TTS falla, el caller debe hacer fallback a texto.
"""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import requests

_STATE_FILE = Path(__file__).parent.parent / "config" / "voice_state.json"
_STATE_FILE.parent.mkdir(exist_ok=True)

# Límite de caracteres para TTS (proteger cuota Starter: 30k/mes)
MAX_TTS_CHARS = 800


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def is_voice_on(chat_id: str) -> bool:
    return _load_state().get(str(chat_id), False)


def set_voice(chat_id: str, on: bool) -> None:
    state = _load_state()
    state[str(chat_id)] = on
    _save_state(state)


def _strip_for_tts(text: str) -> str:
    """Limpia texto para TTS: sin tags HTML ni markdown de tablas."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[`*_~]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def text_to_speech(text: str) -> bytes | None:
    """Llama a ElevenLabs TTS, devuelve bytes MP3 o None si falla."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    voice_id = os.environ.get("JARVIS_VOICE_ID", "851ejYcv2BoNPjrkw93G")
    model = os.environ.get("JARVIS_VOICE_MODEL", "eleven_turbo_v2_5")
    if not api_key:
        print("[ElevenLabs] ELEVENLABS_API_KEY no configurada.")
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    try:
        resp = requests.post(
            url,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={"text": text, "model_id": model},
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"[ElevenLabs] Error {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.content
    except Exception as e:
        print(f"[ElevenLabs] Excepción: {e}")
        return None


def _mp3_to_ogg_opus(mp3_bytes: bytes) -> bytes | None:
    """Convierte MP3 a OGG Opus con ffmpeg para que Telegram lo muestre como nota de voz."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_f:
            mp3_f.write(mp3_bytes)
            mp3_path = mp3_f.name
        ogg_path = mp3_path.replace(".mp3", ".ogg")
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus", "-b:a", "32k", ogg_path],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"[ffmpeg] Error: {result.stderr.decode()[:200]}")
            return None
        ogg_bytes = Path(ogg_path).read_bytes()
        Path(mp3_path).unlink(missing_ok=True)
        Path(ogg_path).unlink(missing_ok=True)
        return ogg_bytes
    except Exception as e:
        print(f"[ffmpeg] Excepción: {e}")
        return None


def send_voice(api_base: str, chat_id: str, text: str) -> bool:
    """Convierte texto a voz y lo manda como voice message.
    Trunca a MAX_TTS_CHARS para proteger cuota. Retorna False si falla (el caller
    debe hacer fallback a texto)."""
    clean = _strip_for_tts(text)
    truncated = False
    if len(clean) > MAX_TTS_CHARS:
        clean = clean[:MAX_TTS_CHARS].rsplit(" ", 1)[0] + "..."
        truncated = True

    mp3 = text_to_speech(clean)
    if not mp3:
        return False

    ogg = _mp3_to_ogg_opus(mp3)
    audio_bytes, filename, mime = (ogg, "jarvis.ogg", "audio/ogg") if ogg else (mp3, "jarvis.mp3", "audio/mpeg")

    try:
        resp = requests.post(
            f"{api_base}/sendVoice",
            data={"chat_id": chat_id},
            files={"voice": (filename, audio_bytes, mime)},
            timeout=30,
        )
        data = resp.json()
        if not data.get("ok"):
            print(f"[Telegram] sendVoice falló: {data.get('description')}")
            return False
        if truncated:
            requests.post(
                f"{api_base}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "(Respuesta larga truncada en audio. Escribe /voz off para ver el texto completo.)",
                },
            )
        return True
    except Exception as e:
        print(f"[Telegram] Error enviando voz: {e}")
        return False
