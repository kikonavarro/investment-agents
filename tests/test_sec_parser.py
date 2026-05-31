"""
Tests para tools/sec_parser.py — normalización de escala y signo del XBRL.

Protege contra el bug del atributo `scale`: una empresa que reporta en miles
(scale=3) se parseaba como millones, inflando todo 1000x y generando alertas
'critical' falsas (HIMS daba 99.900% de diferencia vs Yahoo). También verifica
que se respeta el atributo `sign` (una pérdida no debe convertirse en beneficio).
"""

from tools.sec_parser import parse_10k, cross_reference


def _write_xbrl(tmp_path, facts):
    """Escribe un iXBRL mínimo. `facts` = lista de (tag, valor_texto, attrs_extra)."""
    lines = []
    for tag, value, extra in facts:
        lines.append(
            f'<ix:nonFraction name="us-gaap:{tag}" contextRef="c1" '
            f'unitRef="usd" {extra}>{value}</ix:nonFraction>'
        )
    html = "<html><body>\n" + "\n".join(lines) + "\n</body></html>"
    p = tmp_path / "10K_test.htm"
    p.write_text(html)
    return str(p)


def test_escala_miles_se_normaliza_a_millones(tmp_path):
    """scale=3 (miles): 2.347.637 mil = 2.347,6 millones."""
    path = _write_xbrl(tmp_path, [
        ("Revenues", "2,347,637", 'scale="3"'),
        ("NetIncomeLoss", "128,365", 'scale="3"'),
    ])
    result = parse_10k(path)
    assert result["revenue"] == 2347.637
    assert result["net_income"] == 128.365


def test_escala_millones(tmp_path):
    """scale=6 (millones): el texto ya está en millones."""
    path = _write_xbrl(tmp_path, [("Revenues", "416161", 'scale="6"')])
    result = parse_10k(path)
    assert result["revenue"] == 416161.0


def test_sin_escala_son_unidades(tmp_path):
    """Sin scale: el valor está en unidades, se divide entre 1e6."""
    path = _write_xbrl(tmp_path, [("Revenues", "35934000000", "")])
    result = parse_10k(path)
    assert result["revenue"] == 35934.0


def test_signo_negativo_se_respeta(tmp_path):
    """sign='-' convierte el valor en negativo: una pérdida sigue siendo pérdida."""
    path = _write_xbrl(tmp_path, [("NetIncomeLoss", "2,000,000", 'scale="3" sign="-"')])
    result = parse_10k(path)
    assert result["net_income"] == -2000.0  # pérdida de 2.000M, no +2.000M


def test_max_por_magnitud_conserva_signo(tmp_path):
    """Con varios contextos, se toma el de mayor magnitud conservando el signo
    (el full-year), no el simple max numérico."""
    path = _write_xbrl(tmp_path, [
        ("NetIncomeLoss", "500,000", 'scale="3" sign="-"'),   # full year: -500M
        ("NetIncomeLoss", "120,000", 'scale="3"'),            # un trimestre: +120M
    ])
    result = parse_10k(path)
    assert result["net_income"] == -500.0


def test_cross_reference_no_emite_critical(tmp_path):
    """Aunque haya una diferencia enorme, el cruce automático nunca emite 'critical'
    (puede ser desajuste de período/segmento; lo confirma Opus contra el 10-K)."""
    path = _write_xbrl(tmp_path, [("Revenues", "100", 'scale="6"')])
    sec = parse_10k(path)
    # Yahoo dice 10x más → diferencia del 900%, antes habría sido 'critical'
    out = cross_reference(sec, {"revenue": 1000e6}, "TEST")
    assert out["alerts"], "debería haber alerta por la diferencia"
    assert all(a["level"] != "critical" for a in out["alerts"])


def test_empresa_en_miles_cuadra_con_yahoo(tmp_path):
    """Regresión HIMS: una empresa que reporta en miles ahora CUADRA con Yahoo
    (mismo orden de magnitud) en vez de dar 99.900% de diferencia."""
    path = _write_xbrl(tmp_path, [
        ("Revenues", "2,347,637", 'scale="3"'),
        ("NetIncomeLoss", "128,365", 'scale="3"'),
    ])
    sec = parse_10k(path)
    out = cross_reference(sec, {"revenue": 2348e6, "net_income": 128e6}, "HIMS")
    assert out["confidence"] == "HIGH"
    assert not out["alerts"]
