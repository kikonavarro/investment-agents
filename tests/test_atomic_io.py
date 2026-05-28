"""Tests para tools/atomic_io.py — escritura atómica."""
from tools.atomic_io import atomic_write_text


def test_crea_fichero_y_directorios(tmp_path):
    p = tmp_path / "sub" / "dir" / "f.json"
    atomic_write_text(p, '{"a": 1}')
    assert p.read_text(encoding="utf-8") == '{"a": 1}'


def test_sobrescribe_contenido_previo(tmp_path):
    p = tmp_path / "f.txt"
    atomic_write_text(p, "viejo")
    atomic_write_text(p, "nuevo")
    assert p.read_text(encoding="utf-8") == "nuevo"


def test_no_deja_temporales(tmp_path):
    p = tmp_path / "f.txt"
    atomic_write_text(p, "contenido")
    leftovers = [q for q in tmp_path.iterdir() if q.name.endswith(".tmp")]
    assert not leftovers


def test_acentos_y_unicode(tmp_path):
    p = tmp_path / "f.txt"
    atomic_write_text(p, "análisis de petróleo en el año señalado")
    assert "petróleo" in p.read_text(encoding="utf-8")
