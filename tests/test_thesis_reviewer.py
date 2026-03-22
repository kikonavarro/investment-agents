"""Tests para thesis_reviewer.py."""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.thesis_reviewer import review_thesis, _extract_fair_values, _get_ev_ebitda


# --- Fixtures ---

GOOD_VALUATION = {
    "ticker": "AAPL",
    "current_price": 200.0,
    "shares_outstanding": 15_000_000_000,
    "market_cap": 3_000_000_000_000,
    "latest_financials": {
        "revenue": 400_000_000_000,
        "ebitda": 140_000_000_000,
        "total_debt": 100_000_000_000,
        "cash": 60_000_000_000,
        "total_equity": 70_000_000_000,
    },
    "scenarios": {
        "base": {"terminal_multiple": 18, "wacc": 0.10},
    },
}

EXTREME_VALUATION = {
    "ticker": "TSLA",
    "current_price": 368.0,
    "shares_outstanding": 3_750_000_000,
    "market_cap": 1_380_000_000_000,
    "latest_financials": {
        "revenue": 95_000_000_000,
        "ebitda": 12_000_000_000,
        "total_debt": 15_000_000_000,
        "cash": 16_500_000_000,
        "total_equity": 83_000_000_000,
    },
    "scenarios": {
        "base": {"terminal_multiple": 12, "wacc": 0.15},
    },
}

GOOD_THESIS = """
## AAPL — Apple Inc. | INFRAVALORADA

### Resumen ejecutivo
Precio actual de **$200.00**, fair value ponderado **$235.00**.

### El negocio
Apple es líder en tecnología de consumo.

### Análisis financiero
| Año | Revenue |
|-----|---------|
| 2024 | $400B |

### Valoración DCF
| Escenario | WACC | TV | Precio |
|-----------|------|-----|--------|
| **Bear** | 11% | 16x | **$185.00** |
| **Base** | 10% | 18x | **$235.00** |
| **Bull** | 9% | 20x | **$295.00** |

**Fair value ponderado (40/40/20): $227.00**

### Tabla sensibilidad
| WACC \\ TV | 14x | 16x | 18x | 20x | 22x |
|-----------|-----|-----|-----|-----|-----|
| 9% | $220 | $250 | $280 | $310 | $340 |
| 10% | $200 | $225 | $250 | $275 | $300 |

### Riesgos principales
- Competencia en smartphones.

### Catalizadores
- Vision Pro y servicios.

### Conclusión y plan de acción
Recomendación: COMPRAR por debajo de $200.

---
*No es consejo de inversión.*
"""

TESLA_BAD_THESIS = """
## TSLA — Tesla, Inc. | SOBREVALORADA

### Resumen ejecutivo
Precio actual de **$367.96**, fair value ponderado **$28.87**.

### El negocio
Tesla fabrica EVs.

### Análisis financiero
Revenue estancado.

### Valoración DCF
| Escenario | WACC | TV | Precio |
|-----------|------|-----|--------|
| **Bear** | 16% | 10x | **$18.53** |
| **Base** | 15% | 12x | **$28.39** |
| **Bull** | 14% | 14x | **$40.15** |

### Riesgos principales
Márgenes cayendo.

### Catalizadores
FSD y robotaxi.

### Conclusión y plan de acción
Señal: SOBREVALORADA. No comprar.
"""

MISSING_SECTIONS_THESIS = """
## TEST — Test Corp | VALOR_JUSTO

### Resumen ejecutivo
Precio actual de **$100.00**.

### Valoración DCF
| Escenario | Precio |
|-----------|--------|
| **Bear** | **$85.00** |
| **Base** | **$110.00** |
| **Bull** | **$140.00** |

### Conclusión y plan de acción
Mantener.
"""


# --- Tests ---

class TestExtractFairValues:
    def test_extracts_three_scenarios(self):
        fv = _extract_fair_values(GOOD_THESIS)
        assert "bear" in fv
        assert "base" in fv
        assert "bull" in fv
        assert fv["bear"] == 185.00
        assert fv["base"] == 235.00
        assert fv["bull"] == 295.00

    def test_extracts_tesla_values(self):
        fv = _extract_fair_values(TESLA_BAD_THESIS)
        assert fv["bear"] == 18.53
        assert fv["base"] == 28.39
        assert fv["bull"] == 40.15


class TestGetEvEbitda:
    def test_normal_company(self):
        ev_ebitda = _get_ev_ebitda(GOOD_VALUATION)
        # EV = 3T + 100B - 60B = 3.04T, EBITDA = 140B → ~21.7x
        assert 20 < ev_ebitda < 23

    def test_extreme_company(self):
        ev_ebitda = _get_ev_ebitda(EXTREME_VALUATION)
        # EV = 1.38T + 15B - 16.5B ≈ 1.379T, EBITDA = 12B → ~115x
        assert ev_ebitda > 100


class TestReviewThesis:
    def test_good_thesis_passes(self):
        result = review_thesis("AAPL", GOOD_THESIS, GOOD_VALUATION)
        assert result["verdict"] == "PASS"
        assert len(result["critical"]) == 0

    def test_tesla_bad_thesis_fails(self):
        """La tesis original de Tesla con $29 debe FAIL."""
        result = review_thesis("TSLA", TESLA_BAD_THESIS, EXTREME_VALUATION)
        assert result["verdict"] == "FAIL"
        checks = [i["check"] for i in result["critical"]]
        assert "multiplos_auto_extrema" in checks

    def test_missing_sections_warns(self):
        """Tesis sin secciones obligatorias debe dar REVIEW."""
        valuation = {
            "current_price": 100.0,
            "shares_outstanding": 1_000_000_000,
            "latest_financials": {
                "ebitda": 10_000_000_000,
                "total_debt": 5_000_000_000,
                "cash": 3_000_000_000,
            },
            "scenarios": {"base": {"terminal_multiple": 15, "wacc": 0.10}},
        }
        result = review_thesis("TEST", MISSING_SECTIONS_THESIS, valuation)
        assert result["verdict"] == "REVIEW"
        missing = [i for i in result["warnings"] if i["check"] == "seccion_faltante"]
        # Faltan: El negocio, Análisis financiero, Riesgos, Catalizadores
        assert len(missing) >= 3

    def test_missing_sensitivity_table(self):
        """Tesis sin tabla de sensibilidad debe warning."""
        valuation = {
            "current_price": 100.0,
            "shares_outstanding": 1_000_000_000,
            "latest_financials": {
                "ebitda": 10_000_000_000,
                "total_debt": 5_000_000_000,
                "cash": 3_000_000_000,
            },
            "scenarios": {"base": {"terminal_multiple": 15, "wacc": 0.10}},
        }
        result = review_thesis("TEST", MISSING_SECTIONS_THESIS, valuation)
        checks = [i["check"] for i in result["warnings"]]
        assert "tabla_sensibilidad" in checks

    def test_bull_below_price_with_buy_signal_fails(self):
        """Bull < precio + recomienda comprar = FAIL."""
        thesis = GOOD_THESIS.replace("$295.00", "$150.00").replace(
            "INFRAVALORADA", "INFRAVALORADA"
        )
        valuation = dict(GOOD_VALUATION)
        result = review_thesis("AAPL", thesis, valuation)
        checks = [i["check"] for i in result["critical"]]
        assert "bull_vs_recomendacion" in checks

    def test_scenario_spread_too_wide(self):
        """Ratio bull/bear > 3.5x debe warning."""
        thesis = GOOD_THESIS.replace("$185.00", "$50.00").replace("$295.00", "$400.00")
        result = review_thesis("AAPL", thesis, GOOD_VALUATION)
        checks = [i["check"] for i in result["warnings"]]
        assert "spread_amplio" in checks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
