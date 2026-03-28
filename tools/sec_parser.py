"""
SEC 10-K Parser — extrae datos financieros clave de filings XBRL/HTML.
Cruza con datos de Yahoo Finance para detectar discrepancias.
"""
import re
from pathlib import Path
from collections import defaultdict


# Mapeo de tags XBRL a métricas financieras
XBRL_TAGS = {
    # Income Statement
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "cost_of_revenue": [
        "CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold",
    ],
    "gross_profit": [
        "GrossProfit",
    ],
    "operating_expenses": [
        "OperatingExpenses",
    ],
    "operating_income": [
        "OperatingIncomeLoss",
    ],
    "net_income": [
        "NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic",
    ],
    "income_tax": [
        "IncomeTaxExpenseBenefit",
    ],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",
    ],
    # Balance Sheet
    "total_assets": [
        "Assets",
    ],
    "total_equity": [
        "StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue", "Cash",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "long_term_debt": [
        "LongTermDebt", "LongTermDebtNoncurrent",
    ],
    "total_debt": [
        "DebtInstrumentCarryingAmount", "LongTermDebt",
    ],
    "current_assets": [
        "AssetsCurrent",
    ],
    "current_liabilities": [
        "LiabilitiesCurrent",
    ],
    # Cash Flow
    "operating_cashflow": [
        "NetCashProvidedByUsedInOperatingActivities",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
    ],
    "depreciation": [
        "DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
    ],
    "share_buybacks": [
        "PaymentsForRepurchaseOfCommonStock",
    ],
    "dividends_paid": [
        "PaymentsOfDividends", "PaymentsOfDividendsCommonStock",
    ],
    "sbc": [
        "ShareBasedCompensation",
    ],
}


def parse_10k(filepath: str) -> dict:
    """
    Parsea un 10-K XBRL/HTML y extrae métricas financieras clave.

    Returns:
        dict con las métricas encontradas. Valores en millones.
        Incluye 'raw_tags' con todos los tags XBRL encontrados.
    """
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    with open(path, 'r', errors='ignore') as f:
        content = f.read()

    # Extraer todos los valores numéricos XBRL
    pattern = r'<ix:nonFraction[^>]*name="([^"]*)"[^>]*>([^<]+)</ix:nonFraction>'
    matches = re.findall(pattern, content)

    if not matches:
        return {"error": "No XBRL data found in file"}

    # Agrupar por tag
    raw_tags = defaultdict(list)
    for name, value in matches:
        tag_name = name.split(':')[-1]  # Remove namespace prefix
        clean_val = value.strip().replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
        try:
            num = float(clean_val)
            raw_tags[tag_name].append(num)
        except ValueError:
            pass

    # Extraer métricas mapeadas
    result = {"_source": str(filepath), "_total_tags": len(raw_tags)}

    for metric, tag_names in XBRL_TAGS.items():
        for tag in tag_names:
            if tag in raw_tags:
                values = raw_tags[tag]
                # Tomar el valor más grande (generalmente el full-year)
                # Para métricas de balance, tomar el primer valor (más reciente)
                if metric in ("total_assets", "total_equity", "cash", "long_term_debt",
                              "total_debt", "current_assets", "current_liabilities"):
                    result[metric] = values[0]  # Most recent
                else:
                    result[metric] = max(values)  # Full year (largest)
                break

    # Calcular métricas derivadas
    if "revenue" in result and "cost_of_revenue" in result:
        result["gross_margin_10k"] = (result["revenue"] - result["cost_of_revenue"]) / result["revenue"]
    if "revenue" in result and "operating_income" in result:
        result["operating_margin_10k"] = result["operating_income"] / result["revenue"]
    if "revenue" in result and "net_income" in result:
        result["net_margin_10k"] = result["net_income"] / result["revenue"]
    if "operating_cashflow" in result and "capex" in result:
        result["fcf_10k"] = result["operating_cashflow"] - abs(result.get("capex", 0))

    return result


def cross_reference(sec_data: dict, yahoo_data: dict, ticker: str) -> dict:
    """
    Cruza datos del 10-K con datos de Yahoo Finance.
    Detecta discrepancias significativas.

    Args:
        sec_data: dict de parse_10k()
        yahoo_data: dict latest_financials del JSON de valoración

    Returns:
        dict con comparación y alertas
    """
    if "error" in sec_data:
        return {"error": sec_data["error"], "alerts": []}

    comparisons = []
    alerts = []

    # Mapeo SEC -> Yahoo
    checks = [
        ("revenue", "revenue", "Revenue"),
        ("net_income", "net_income", "Net Income"),
        ("operating_income", None, "Operating Income"),  # Yahoo no tiene este campo directo en latest_financials
        ("cash", "cash", "Cash"),
        ("total_equity", "total_equity", "Total Equity"),
    ]

    for sec_key, yahoo_key, label in checks:
        sec_val = sec_data.get(sec_key)
        yahoo_val = yahoo_data.get(yahoo_key, 0) / 1e6 if yahoo_key and yahoo_data.get(yahoo_key) else None

        if sec_val is not None and yahoo_val is not None:
            # SEC values are already in millions for most tags
            # Yahoo values need /1e6
            diff_pct = abs(sec_val - yahoo_val) / yahoo_val * 100 if yahoo_val != 0 else 0

            comp = {
                "metric": label,
                "sec_10k": sec_val,
                "yahoo": yahoo_val,
                "diff_pct": diff_pct,
                "match": diff_pct < 5,  # <5% difference = match
            }
            comparisons.append(comp)

            if diff_pct >= 5:
                alerts.append({
                    "level": "warning" if diff_pct < 15 else "critical",
                    "metric": label,
                    "message": f"{label}: SEC 10-K = {sec_val:,.0f}M vs Yahoo = {yahoo_val:,.0f}M ({diff_pct:.1f}% diff)"
                })

    # Check for EBITDA (Yahoo reports it, SEC doesn't directly)
    if "operating_income" in sec_data and "depreciation" in sec_data:
        ebitda_10k = sec_data["operating_income"] + sec_data["depreciation"]
        ebitda_yahoo = yahoo_data.get("ebitda", 0) / 1e6
        if ebitda_yahoo:
            diff = abs(ebitda_10k - ebitda_yahoo) / ebitda_yahoo * 100
            comparisons.append({
                "metric": "EBITDA (calculated)",
                "sec_10k": ebitda_10k,
                "yahoo": ebitda_yahoo,
                "diff_pct": diff,
                "match": diff < 10,
            })
            if diff >= 10:
                alerts.append({
                    "level": "warning",
                    "metric": "EBITDA",
                    "message": f"EBITDA: SEC calc = {ebitda_10k:,.0f}M vs Yahoo = {ebitda_yahoo:,.0f}M ({diff:.1f}% diff). "
                               f"Puede indicar ajustes IFRS16 o items no recurrentes."
                })

    # Check gross margin
    if "gross_margin_10k" in sec_data:
        gm_yahoo = yahoo_data.get("gross_margin", 0)
        gm_10k = sec_data["gross_margin_10k"]
        if gm_yahoo and abs(gm_10k - gm_yahoo) > 0.02:
            alerts.append({
                "level": "warning",
                "metric": "Gross Margin",
                "message": f"Gross Margin: SEC = {gm_10k:.1%} vs Yahoo = {gm_yahoo:.1%}"
            })

    return {
        "ticker": ticker,
        "comparisons": comparisons,
        "alerts": alerts,
        "sec_data": sec_data,
        "confidence": "HIGH" if not alerts else ("MEDIUM" if len(alerts) <= 2 else "LOW"),
    }


def audit_company(ticker: str, valuation_dir: str = None) -> dict:
    """
    Auditoría completa: parsea 10-K y cruza con Yahoo.

    Args:
        ticker: Ticker de la empresa
        valuation_dir: Directorio de valoración (default: data/valuations/{TICKER}/)

    Returns:
        dict con resultados de auditoría
    """
    import json

    if valuation_dir is None:
        folder = ticker.replace(".", "_")
        valuation_dir = Path(__file__).parent.parent / "data" / "valuations" / folder
    else:
        valuation_dir = Path(valuation_dir)

    # Cargar JSON de Yahoo
    json_path = valuation_dir / f"{ticker.replace('.', '_')}_valuation.json"
    if not json_path.exists():
        return {"error": f"No valuation JSON found: {json_path}"}

    with open(json_path) as f:
        valuation = json.load(f)

    yahoo_data = valuation.get("latest_financials", {})

    # Buscar 10-K más reciente
    sec_dir = valuation_dir / "SEC_filings"
    if not sec_dir.exists():
        return {
            "ticker": ticker,
            "has_10k": False,
            "message": "No SEC filings directory. International company — use IR presentation instead.",
            "alerts": [],
        }

    # Buscar el 10-K más reciente
    ten_k_files = sorted(sec_dir.glob("10K_*.htm"), reverse=True)
    if not ten_k_files:
        return {
            "ticker": ticker,
            "has_10k": False,
            "message": "No 10-K files found in SEC_filings/",
            "alerts": [],
        }

    latest_10k = ten_k_files[0]

    # Parsear 10-K
    sec_data = parse_10k(str(latest_10k))

    # Cruzar con Yahoo
    result = cross_reference(sec_data, yahoo_data, ticker)
    result["has_10k"] = True
    result["filing"] = str(latest_10k)

    return result


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python sec_parser.py TICKER")
        sys.exit(1)

    ticker = sys.argv[1]
    result = audit_company(ticker)

    print(f"\n{'='*60}")
    print(f"  SEC 10-K Audit: {ticker}")
    print(f"{'='*60}")

    if "error" in result:
        print(f"  Error: {result['error']}")
        sys.exit(1)

    if not result.get("has_10k"):
        print(f"  {result.get('message', 'No 10-K available')}")
        sys.exit(0)

    print(f"  Filing: {result.get('filing', 'N/A')}")
    print(f"  Confidence: {result.get('confidence', 'N/A')}")

    if result.get("comparisons"):
        print(f"\n  {'Metric':<20} {'SEC 10-K':>12} {'Yahoo':>12} {'Diff':>8} {'Match':>6}")
        print(f"  {'-'*60}")
        for c in result["comparisons"]:
            icon = "OK" if c["match"] else "XX"
            print(f"  {c['metric']:<20} {c['sec_10k']:>12,.0f} {c['yahoo']:>12,.0f} {c['diff_pct']:>7.1f}% [{icon}]")

    if result.get("alerts"):
        print(f"\n  Alerts:")
        for a in result["alerts"]:
            print(f"    [{a['level'].upper()}] {a['message']}")
    else:
        print(f"\n  No alerts — Yahoo data matches SEC 10-K.")
