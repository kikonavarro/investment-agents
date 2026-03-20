"""Fixtures compartidos para tests."""
import pytest


@pytest.fixture
def good_valuation():
    """Valoración válida con datos completos."""
    return {
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "currency": "$",
        "date": "2026-03-20",
        "current_price": 185.50,
        "shares_outstanding": 15_500_000_000,
        "market_cap": 2_870_000_000_000,
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "historical_years": [2021, 2022, 2023, 2024, 2025],
        "latest_financials": {
            "revenue": 394_000_000_000,
            "net_income": 97_000_000_000,
            "ebitda": 130_000_000_000,
            "free_cashflow": 99_000_000_000,
            "gross_margin": 0.44,
            "operating_margin": 0.30,
            "net_margin": 0.25,
            "total_debt": 120_000_000_000,
            "cash": 60_000_000_000,
            "total_equity": 65_000_000_000,
        },
        "scenarios": {
            "bear": {
                "revenue_growth_y1": 0.02,
                "revenue_growth_y5": 0.01,
                "gross_margin": 0.42,
                "wacc": 0.12,
                "terminal_multiple": 13,
            },
            "base": {
                "revenue_growth_y1": 0.07,
                "revenue_growth_y5": 0.04,
                "gross_margin": 0.44,
                "wacc": 0.10,
                "terminal_multiple": 15,
            },
            "bull": {
                "revenue_growth_y1": 0.12,
                "revenue_growth_y5": 0.07,
                "gross_margin": 0.46,
                "wacc": 0.09,
                "terminal_multiple": 18,
            },
        },
        "segments": [
            {"name": "iPhone", "revenues": {2024: 200e9, 2025: 210e9}},
            {"name": "Services", "revenues": {2024: 85e9, 2025: 95e9}},
        ],
        "historical_data": {
            "2023": {"revenue": 383e9, "net_income": 94e9, "ebitda": 125e9, "fcf": 93e9, "operating_income": 114e9},
            "2024": {"revenue": 390e9, "net_income": 95e9, "ebitda": 128e9, "fcf": 96e9, "operating_income": 115e9},
            "2025": {"revenue": 394e9, "net_income": 97e9, "ebitda": 130e9, "fcf": 99e9, "operating_income": 118e9},
        },
        "news": [],
        "files": {"excel": "/tmp/test.xlsx", "sec_filings": []},
    }


@pytest.fixture
def bad_valuation():
    """Valoración con datos problemáticos."""
    return {
        "ticker": "BAD",
        "company": "Bad Corp",
        "currency": "$",
        "date": "2026-03-20",
        "current_price": 0,
        "shares_outstanding": 0,
        "market_cap": 0,
        "sector": "",
        "historical_years": [2025],
        "latest_financials": {
            "revenue": -100,
            "net_income": 0,
            "ebitda": 0,
            "free_cashflow": 0,
            "gross_margin": -0.5,
            "operating_margin": -0.8,
            "net_margin": 0,
            "total_debt": 10_000_000,
            "cash": 0,
            "total_equity": -500_000,
        },
        "scenarios": {
            "bear": {"wacc": 0.30, "terminal_multiple": 50, "revenue_growth_y1": -0.1},
            "base": {"wacc": 0.30, "terminal_multiple": 50, "revenue_growth_y1": -0.05},
            "bull": {"wacc": 0.25, "terminal_multiple": 45, "revenue_growth_y1": 0.0},
        },
        "segments": [],
        "historical_data": {},
        "news": [],
        "files": {},
    }
