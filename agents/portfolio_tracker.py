"""
Portfolio Tracker Agent — estado de cartera con Excel.
Python hace todo el cálculo; Claude solo genera el resumen legible.
"""
from agents.base import call_agent
from tools.excel_portfolio import (
    get_portfolio_summary, update_prices, update_manual_position,
    add_position, add_transaction, add_to_watchlist, create_portfolio_file,
)
from tools.financial_data import get_current_prices
from tools.formatters import format_portfolio_for_llm
from config.prompts import PORTFOLIO_TRACKER


def run_portfolio_tracker(action: str = "status", **kwargs) -> str:
    """
    Gestiona la cartera y devuelve un resumen legible.

    Acciones:
        "status"          → muestra estado actual de la cartera
        "update_prices"   → actualiza precios automáticos vía yfinance
        "add_stock"       → añade posición en acción (kwargs: ticker, name,
                            shares, avg_price, buy_date, target, stop_loss)
        "add_fund"        → añade fondo manual (kwargs: name, invested_amount,
                            current_value)
        "manual_update"   → actualiza valor de fondo manual (kwargs: name,
                            current_value)
        "add_transaction" → registra compra/venta (kwargs: ticker_or_name,
                            action, amount, price, fee)
        "watchlist_add"   → añade a watchlist (kwargs: ticker, name,
                            target_buy, notes)

    Returns:
        Texto legible generado por Claude con el estado/confirmación.
    """
    create_portfolio_file()

    # ── Acciones que modifican Excel ───────────────────────────────────────────
    if action == "update_prices":
        print("  [portfolio_tracker] Actualizando precios automáticos...")
        summary_data = get_portfolio_summary()
        auto_tickers = [
            p["name"] for p in summary_data["positions"]
            if p["source"] == "auto"
        ]
        if auto_tickers:
            prices = get_current_prices(auto_tickers)
            update_prices(prices)
            print(f"  [portfolio_tracker] Actualizados {len(prices)} precios.")

    elif action == "manual_update":
        name = kwargs["name"]
        value = float(kwargs["current_value"])
        print(f"  [portfolio_tracker] Actualizando {name} → {value:,.2f}")
        update_manual_position(name=name, current_value=value)

    elif action == "add_stock":
        print(f"  [portfolio_tracker] Añadiendo {kwargs.get('ticker')}...")
        add_position(
            source="auto",
            position_type="stock",
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
        print(f"  [portfolio_tracker] Añadiendo fondo {kwargs.get('name')}...")
        add_position(
            source="manual",
            position_type="fund",
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

    # ── Leer estado actualizado y pasar a Claude ───────────────────────────────
    print("  [portfolio_tracker] Generando resumen...")
    portfolio_data = get_portfolio_summary()
    formatted = format_portfolio_for_llm(portfolio_data["positions"])

    # Añadir alertas al contexto si las hay
    alerts = portfolio_data.get("alerts", [])
    if alerts:
        alert_lines = "\nALERTAS: " + " | ".join(
            f"{a['name']}: {a['alert']}" for a in alerts
        )
        formatted += alert_lines

    response = call_agent(
        system_prompt=PORTFOLIO_TRACKER,
        user_message=formatted,
        model_tier="quick",
        max_tokens=800,
        json_output=False,
        force_api=True,  # Portfolio tracker siempre usa API (automatización)
    )
    return response
