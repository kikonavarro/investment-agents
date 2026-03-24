"""
Dashboard — visualización de valoraciones, portfolio y historial.
Ejecutar: streamlit run dashboard.py
"""
import json
import sys
from pathlib import Path

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import VALUATIONS_DIR, PORTFOLIO_FILE
from agents.analyst import load_history

# --- Config ---
st.set_page_config(page_title="Investment Agents", page_icon="📊", layout="wide")


# --- Data loading ---

@st.cache_data(ttl=60)
def load_all_valuations() -> list[dict]:
    """Carga todas las valoraciones existentes."""
    valuations = []
    if not VALUATIONS_DIR.exists():
        return valuations
    for folder in sorted(VALUATIONS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        json_files = list(folder.glob("*_valuation.json"))
        if not json_files:
            continue
        # Tomar el archivo sin timestamp (el "actual")
        main = [f for f in json_files if not any(c.isdigit() and len(c) == 8 for c in f.stem.split("_"))]
        path = main[0] if main else json_files[0]
        try:
            with open(path, encoding="utf-8") as f:
                v = json.load(f)
                if v.get("ticker") and v.get("current_price"):
                    valuations.append(v)
        except (json.JSONDecodeError, Exception):
            continue
    return valuations


@st.cache_data(ttl=60)
def load_portfolio() -> list[dict]:
    """Carga posiciones del portfolio Excel."""
    if not PORTFOLIO_FILE.exists():
        return []
    try:
        from tools.excel_portfolio import read_portfolio
        return read_portfolio()
    except Exception:
        return []


def classify_signal(v: dict) -> str:
    """Clasifica señal basada en precio vs escenarios."""
    price = v.get("current_price", 0)
    base_wacc = v.get("scenarios", {}).get("base", {}).get("wacc", 0)
    bear_wacc = v.get("scenarios", {}).get("bear", {}).get("wacc", 0)
    # Sin precio objetivo calculado en el JSON, usamos analyst_targets
    target = v.get("analyst_targets", {}).get("mean", 0)
    if target and price:
        ratio = price / target
        if ratio < 0.85:
            return "INFRAVALORADA"
        elif ratio > 1.15:
            return "SOBREVALORADA"
    return "VALOR_JUSTO"


# --- Pages ---

def page_valuations():
    st.header("📊 Valoraciones activas")

    valuations = load_all_valuations()
    if not valuations:
        st.warning("No hay valoraciones. Ejecuta: `python main.py --analyst TICKER`")
        return

    # Tabla resumen
    rows = []
    for v in valuations:
        signal = classify_signal(v)
        latest = v.get("latest_financials", {})
        base = v.get("scenarios", {}).get("base", {})
        rows.append({
            "Ticker": v.get("ticker", "?"),
            "Empresa": v.get("company", "")[:30],
            "Precio": v.get("current_price", 0),
            "Moneda": v.get("currency", "$"),
            "Sector": v.get("sector", "")[:20],
            "Señal": signal,
            "Margen bruto": latest.get("gross_margin", 0),
            "Margen neto": latest.get("net_margin", 0),
            "Growth Y1": base.get("revenue_growth_y1", 0),
            "WACC": base.get("wacc", 0),
            "TV": base.get("terminal_multiple", 0),
            "Fecha": v.get("date", ""),
        })

    df = pd.DataFrame(rows)

    # Semáforo con colores
    def color_signal(val):
        if val == "INFRAVALORADA":
            return "background-color: #1a472a; color: #4ade80"
        elif val == "SOBREVALORADA":
            return "background-color: #4a1a1a; color: #f87171"
        return "background-color: #4a3f1a; color: #fbbf24"

    # Formatear columnas
    styled = df.style.applymap(color_signal, subset=["Señal"])
    styled = styled.format({
        "Precio": "{:,.2f}",
        "Margen bruto": "{:.1%}",
        "Margen neto": "{:.1%}",
        "Growth Y1": "{:.1%}",
        "WACC": "{:.1%}",
        "TV": "{:.0f}x",
    })

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Filtros
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        signal_filter = st.multiselect("Filtrar por señal", ["INFRAVALORADA", "VALOR_JUSTO", "SOBREVALORADA"])
    with col2:
        sectors = sorted(set(v.get("sector", "") for v in valuations if v.get("sector")))
        sector_filter = st.multiselect("Filtrar por sector", sectors)

    if signal_filter:
        df = df[df["Señal"].isin(signal_filter)]
    if sector_filter:
        df = df[df["Sector"].isin(sector_filter)]

    if signal_filter or sector_filter:
        st.dataframe(df, use_container_width=True, hide_index=True)


def page_detail():
    st.header("🔍 Detalle de valoración")

    valuations = load_all_valuations()
    tickers = [v["ticker"] for v in valuations]

    if not tickers:
        st.warning("No hay valoraciones disponibles.")
        return

    selected = st.selectbox("Selecciona ticker", tickers)
    v = next((x for x in valuations if x["ticker"] == selected), None)
    if not v:
        return

    # Header
    signal = classify_signal(v)
    signal_color = {"INFRAVALORADA": "🟢", "SOBREVALORADA": "🔴"}.get(signal, "🟡")
    st.subheader(f"{signal_color} {v['ticker']} — {v.get('company', '')} | {signal}")

    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Precio", f"{v.get('currency', '$')}{v.get('current_price', 0):,.2f}")
    col2.metric("Sector", v.get("sector", "N/A"))
    latest = v.get("latest_financials", {})
    col3.metric("Margen bruto", f"{latest.get('gross_margin', 0):.1%}")
    col4.metric("Margen neto", f"{latest.get('net_margin', 0):.1%}")

    # Escenarios
    st.subheader("Escenarios DCF")
    scenarios = v.get("scenarios", {})
    if scenarios:
        sc_rows = []
        for name in ["bear", "base", "bull"]:
            sc = scenarios.get(name, {})
            sc_rows.append({
                "Escenario": name.capitalize(),
                "Growth Y1": sc.get("revenue_growth_y1", 0),
                "Growth Y5": sc.get("revenue_growth_y5", 0),
                "Margen bruto": sc.get("gross_margin", 0),
                "WACC": sc.get("wacc", 0),
                "TV múltiplo": sc.get("terminal_multiple", 0),
            })
        sc_df = pd.DataFrame(sc_rows)
        st.dataframe(
            sc_df.style.format({
                "Growth Y1": "{:.1%}", "Growth Y5": "{:.1%}",
                "Margen bruto": "{:.1%}", "WACC": "{:.1%}",
                "TV múltiplo": "{:.0f}x",
            }),
            use_container_width=True, hide_index=True,
        )

    # Historial de revenue
    st.subheader("Evolución financiera")
    hist = v.get("historical_data", {})
    if hist:
        years = sorted(hist.keys())
        hist_df = pd.DataFrame({
            "Año": years,
            "Revenue": [hist[y].get("revenue", 0) / 1e9 for y in years],
            "Net Income": [hist[y].get("net_income", 0) / 1e9 for y in years],
            "FCF": [hist[y].get("fcf", 0) / 1e9 for y in years],
        })
        st.bar_chart(hist_df.set_index("Año"), height=300)

    # Historial de valoraciones (3.7)
    history = load_history(selected)
    if history and len(history) > 1:
        st.subheader("Historial de valoraciones")
        h_df = pd.DataFrame(history)
        h_df["date"] = pd.to_datetime(h_df["date"])
        col1, col2 = st.columns(2)
        with col1:
            st.line_chart(h_df.set_index("date")["current_price"], height=250)
            st.caption("Evolución del precio")
        with col2:
            if "growth_y1_base" in h_df.columns:
                st.line_chart(h_df.set_index("date")["growth_y1_base"], height=250)
                st.caption("Growth Y1 (base)")

    # Segmentos
    segments = v.get("segments", [])
    if segments and len(segments) > 1:
        st.subheader("Segmentos de negocio")
        seg_data = []
        for s in segments:
            revs = s.get("revenues", {})
            if revs:
                latest_rev = list(revs.values())[-1] if revs else 0
                seg_data.append({"Segmento": s["name"], "Revenue": latest_rev / 1e9})
        if seg_data:
            seg_df = pd.DataFrame(seg_data)
            st.bar_chart(seg_df.set_index("Segmento"), height=250)



def page_portfolio():
    st.header("💼 Portfolio")

    positions = load_portfolio()
    if not positions:
        st.info("No hay portfolio. Crea uno con: `python main.py --portfolio status`")
        return

    # Calcular totales
    total_value = sum(p.get("current", 0) for p in positions)
    total_invested = sum(p.get("invested", 0) for p in positions)
    total_pnl = ((total_value - total_invested) / total_invested * 100) if total_invested else 0

    # Métricas globales
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Valor total", f"${total_value:,.2f}")
    col2.metric("Invertido", f"${total_invested:,.2f}")
    col3.metric("P&L", f"${total_value - total_invested:,.2f}", delta=f"{total_pnl:+.1f}%")
    col4.metric("Posiciones", len(positions))

    # Tabla de posiciones
    rows = []
    for p in positions:
        rows.append({
            "Nombre": p.get("name", "?"),
            "Ticker": p.get("ticker", ""),
            "Tipo": p.get("type", ""),
            "Invertido": p.get("invested", 0),
            "Valor actual": p.get("current", 0),
            "P&L %": p.get("pnl_pct", 0),
            "Peso %": (p.get("current", 0) / total_value * 100) if total_value else 0,
            "Fuente": p.get("source", ""),
        })

    df = pd.DataFrame(rows)

    def color_pnl(val):
        if isinstance(val, (int, float)):
            if val > 0:
                return "color: #4ade80"
            elif val < 0:
                return "color: #f87171"
        return ""

    styled = df.style.applymap(color_pnl, subset=["P&L %"])
    styled = styled.format({
        "Invertido": "${:,.2f}",
        "Valor actual": "${:,.2f}",
        "P&L %": "{:+.1f}%",
        "Peso %": "{:.1f}%",
    })

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Gráfico de peso
    if rows:
        weight_df = pd.DataFrame(rows)[["Nombre", "Peso %"]].set_index("Nombre")
        st.bar_chart(weight_df, height=250)


# --- Main ---

def main():
    st.sidebar.title("📊 Investment Agents")
    page = st.sidebar.radio("Navegación", ["Valoraciones", "Detalle", "Portfolio"])

    if page == "Valoraciones":
        page_valuations()
    elif page == "Detalle":
        page_detail()
    elif page == "Portfolio":
        page_portfolio()

    # Footer
    st.sidebar.divider()
    st.sidebar.caption("Investment Agents v2")
    st.sidebar.caption(f"Valoraciones: {len(load_all_valuations())}")


if __name__ == "__main__":
    main()
