"""
Portfolio Tracker — estado de cartera con Excel.
Python hace todo el cálculo. Claude Code interpreta si necesitas análisis.
"""
from tools.excel_portfolio import (
    get_portfolio_summary, update_prices, update_manual_position,
    add_position, add_transaction, add_to_watchlist, create_portfolio_file,
)
from tools.financial_data import get_current_prices
from tools.formatters import format_portfolio_for_llm


def run_portfolio_tracker(action: str = "status", **kwargs) -> str:
    """
    Gestiona la cartera y devuelve un resumen formateado.

    Acciones:
        "status"          → muestra estado actual
        "update_prices"   → actualiza precios vía Yahoo Finance
        "add_stock"       → añade posición (kwargs: ticker, name, shares, avg_price, ...)
        "add_fund"        → añade fondo manual (kwargs: name, invested_amount, current_value)
        "manual_update"   → actualiza valor de fondo (kwargs: name, current_value)
        "add_transaction" → registra compra/venta
        "watchlist_add"   → añade a watchlist
    """
    create_portfolio_file()

    if action == "update_prices":
        print("  [portfolio] Actualizando precios...")
        summary_data = get_portfolio_summary()
        auto_tickers = [
            p["name"] for p in summary_data["positions"]
            if p["source"] == "auto"
        ]
        if auto_tickers:
            prices = get_current_prices(auto_tickers)
            update_prices(prices)
            print(f"  [portfolio] Actualizados {len(prices)} precios.")

    elif action == "manual_update":
        name = kwargs["name"]
        value = float(kwargs["current_value"])
        update_manual_position(name=name, current_value=value)

    elif action == "add_stock":
        add_position(
            source="auto", position_type="stock",
            ticker=kwargs["ticker"],
            name=kwargs.get("name", kwargs["ticker"]),
            shares=float(kwargs["shares"]),
            avg_price=float(kwargs["avg_price"]),
            buy_date=kwargs.get("buy_date"),
            current_price=kwargs.get("current_price"),
            target=kwargs.get("target"),
            stop_loss=kwargs.get("stop_loss"),
            notes=kwargs.get("notes"),
        )

    elif action == "add_fund":
        add_position(
            source="manual", position_type="fund",
            name=kwargs["name"],
            invested_amount=float(kwargs["invested_amount"]),
            current_value=float(kwargs.get("current_value", kwargs["invested_amount"])),
            notes=kwargs.get("notes"),
        )

    elif action == "add_transaction":
        add_transaction(
            ticker_or_name=kwargs["ticker_or_name"],
            action=kwargs["action"],
            amount=float(kwargs["amount"]),
            price=float(kwargs.get("price", 0)),
            fee=float(kwargs.get("fee", 0)),
            notes=kwargs.get("notes"),
        )

    elif action == "watchlist_add":
        add_to_watchlist(
            ticker=kwargs["ticker"],
            name=kwargs.get("name", kwargs["ticker"]),
            target_buy=kwargs.get("target_buy"),
            notes=kwargs.get("notes"),
        )

    # Devolver resumen formateado
    portfolio_data = get_portfolio_summary()
    formatted = format_portfolio_for_llm(portfolio_data["positions"])

    alerts = portfolio_data.get("alerts", [])
    if alerts:
        alert_lines = "\nALERTAS: " + " | ".join(
            f"{a['name']}: {a['alert']}" for a in alerts
        )
        formatted += alert_lines

    return formatted
