"""
⛔ VACIADO (2026-06-11) — la implementación real del DCF vive en:

    tools/valuation_engine.py

Este fichero contenía una segunda implementación del DCF "lista para copiar"
(~950 líneas). Se vació deliberadamente: dos implementaciones de la misma
aritmética acaban divergiendo, y la duplicación del cálculo fue la causa de
las divergencias históricas que el rediseño eliminó (ver REDISENO.md).

Si necesitas la aritmética del DCF:
  - úsala:      from tools.valuation_engine import DCFAssumptions, run_dcf
  - verifícala: tools/finalize_thesis.py la ejecuta en cada finalización
                (+ sensibilidad WACC×TV y reverse-DCF informativos)
  - léela:      la metodología completa está en el SKILL.md de dcf-valuation
                y en el docstring de tools/valuation_engine.py

NO reimplementar el DCF aquí ni en ningún otro sitio.
"""
