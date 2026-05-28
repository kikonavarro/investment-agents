"""
Escritura atómica de ficheros.

Escribe a un temporal en el mismo directorio y hace os.replace (atómico dentro del
mismo filesystem). Así un lector nunca ve un fichero a medio escribir: o el contenido
viejo completo, o el nuevo completo. Evita el JSON truncado que dejaría un crash a
mitad de un write_text, que luego los lectores tragan en silencio perdiendo datos.
"""
import os
import tempfile
from pathlib import Path


def atomic_write_text(path, text: str, encoding: str = "utf-8"):
    """Escribe `text` en `path` de forma atómica."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # El temporal va en el MISMO directorio para que os.replace no cruce filesystem.
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
