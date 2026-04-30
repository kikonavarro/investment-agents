"""
tools/leaps_scanner.py — Scanner de LEAPS calls ITM sobre universo USA.

Filosofía: Python identifica candidatos cuantitativamente (delta, IV, liquidez,
earnings); Claude interpreta y escribe la justificación.

Métricas calculadas:
  - Delta vía Black-Scholes (yfinance no lo da)
  - "IV percentile" aproximado vía HV percentile del subyacente (52w)
    (yfinance no da IV histórica del contrato — proxy razonable)
  - Liquidez: open interest, bid-ask spread relativo
  - Filtro earnings: excluye tickers con earnings <14 días (IV inflada)

Uso:
    from tools.leaps_scanner import scan_universe, scan_ticker
    candidates = scan_universe()           # top 10-15 ranked
    candidate = scan_ticker("NKE")         # un ticker on-demand
"""
from __future__ import annotations

import math
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf
import yaml

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "leaps_universe.yaml"
RISK_FREE_RATE = 0.045  # 10Y treasury approx; aceptable para BS de LEAPS

# ─── Black-Scholes delta (call) ─────────────────────────────────────────────────

def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_delta_call(spot: float, strike: float, t_years: float,
                  rfr: float, iv: float) -> Optional[float]:
    """Delta de un call europeo bajo Black-Scholes. None si inputs inválidos."""
    if not (spot > 0 and strike > 0 and t_years > 0 and iv > 0):
        return None
    d1 = (math.log(spot / strike) + (rfr + 0.5 * iv * iv) * t_years) / (iv * math.sqrt(t_years))
    return _norm_cdf(d1)


# ─── Volatilidad histórica del subyacente ───────────────────────────────────────

def hv_percentile(ticker: yf.Ticker, window: int = 30) -> Optional[dict]:
    """
    HV anualizada del subyacente: ventana de 30d, percentil sobre 252d.
    Proxy de "IV percentile" (yfinance no expone IV histórica del contrato).
    """
    try:
        hist = ticker.history(period="1y", auto_adjust=True)
        if len(hist) < 60:
            return None
        rets = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
        rolling_vol = rets.rolling(window).std() * math.sqrt(252)
        rolling_vol = rolling_vol.dropna()
        if len(rolling_vol) < 30:
            return None
        current = float(rolling_vol.iloc[-1])
        pct = float((rolling_vol < current).sum() / len(rolling_vol) * 100)
        return {
            "hv_current": round(current, 4),
            "hv_percentile": round(pct, 1),  # 0=mínimo año, 100=máximo año
            "hv_min": round(float(rolling_vol.min()), 4),
            "hv_max": round(float(rolling_vol.max()), 4),
        }
    except Exception as e:
        log.debug(f"hv_percentile error: {e}")
        return None


# ─── Earnings filter ────────────────────────────────────────────────────────────

def days_to_next_earnings(ticker: yf.Ticker) -> Optional[int]:
    """Días al próximo earnings (None si desconocido). Best-effort con yfinance."""
    try:
        cal = ticker.calendar
        if cal is None:
            return None
        # yfinance puede devolver dict o DataFrame según versión
        if isinstance(cal, dict):
            edate = cal.get("Earnings Date")
            if isinstance(edate, list) and edate:
                edate = edate[0]
        else:
            try:
                edate = cal.loc["Earnings Date"][0]
            except Exception:
                return None
        if edate is None:
            return None
        if hasattr(edate, "date"):
            edate = edate.date()
        elif isinstance(edate, str):
            edate = datetime.fromisoformat(edate[:10]).date()
        return (edate - date.today()).days
    except Exception:
        return None


# ─── Pullback / momentum signal ─────────────────────────────────────────────────

def pullback_metrics(ticker: yf.Ticker) -> Optional[dict]:
    """Distancia al máximo 52w y al mínimo 52w + retorno 6m."""
    try:
        hist = ticker.history(period="1y", auto_adjust=True)
        if len(hist) < 60:
            return None
        close = float(hist["Close"].iloc[-1])
        high_52w = float(hist["High"].max())
        low_52w = float(hist["Low"].min())
        ret_6m = float(hist["Close"].iloc[-1] / hist["Close"].iloc[-126] - 1) if len(hist) >= 126 else None
        return {
            "price": round(close, 2),
            "high_52w": round(high_52w, 2),
            "low_52w": round(low_52w, 2),
            "from_high_pct": round((close / high_52w - 1) * 100, 1),
            "ret_6m_pct": round(ret_6m * 100, 1) if ret_6m is not None else None,
        }
    except Exception:
        return None


# ─── Selección del LEAP óptimo ──────────────────────────────────────────────────

def find_best_leap(ticker_obj: yf.Ticker, spot: float, cfg: dict) -> Optional[dict]:
    """
    Busca el mejor call ITM con delta 0.60-0.80 y vencimiento >12 meses.
    Mejor = delta más cercano a 0.70 entre los que pasan filtros de liquidez.
    """
    try:
        expiries = ticker_obj.options
    except Exception:
        return None
    if not expiries:
        return None

    today = date.today()
    min_dte = cfg["leap_criteria"]["min_dte"]
    max_dte = cfg["leap_criteria"]["max_dte"]
    dmin = cfg["leap_criteria"]["delta_min"]
    dmax = cfg["leap_criteria"]["delta_max"]
    min_oi = cfg["liquidity"]["min_open_interest"]
    max_spread = cfg["liquidity"]["max_spread_pct"]

    candidates = []
    for exp_str in expiries:
        try:
            exp_date = datetime.fromisoformat(exp_str).date()
        except Exception:
            continue
        dte = (exp_date - today).days
        if dte < min_dte or dte > max_dte:
            continue
        try:
            chain = ticker_obj.option_chain(exp_str)
            calls = chain.calls
        except Exception:
            continue
        if calls is None or len(calls) == 0:
            continue

        t_years = dte / 365.0
        for _, row in calls.iterrows():
            strike = float(row["strike"])
            if strike >= spot:  # solo ITM
                continue
            iv = float(row.get("impliedVolatility", 0) or 0)
            if iv <= 0:
                continue
            delta = bs_delta_call(spot, strike, t_years, RISK_FREE_RATE, iv)
            if delta is None or delta < dmin or delta > dmax:
                continue
            bid = float(row.get("bid", 0) or 0)
            ask = float(row.get("ask", 0) or 0)
            oi = int(row.get("openInterest", 0) or 0)
            if oi < min_oi:
                continue
            mid = (bid + ask) / 2 if (bid > 0 and ask > 0) else 0
            if mid <= 0:
                continue
            spread_pct = (ask - bid) / mid if mid > 0 else 1
            if spread_pct > max_spread:
                continue

            candidates.append({
                "expiry": exp_str,
                "dte": dte,
                "strike": strike,
                "delta": round(delta, 3),
                "iv": round(iv, 3),
                "bid": round(bid, 2),
                "ask": round(ask, 2),
                "mid": round(mid, 2),
                "spread_pct": round(spread_pct * 100, 2),
                "open_interest": oi,
                "volume": int(row.get("volume", 0) or 0),
                "break_even": round(strike + mid, 2),
            })

    if not candidates:
        return None

    # Mejor = delta más cercano a 0.70
    candidates.sort(key=lambda c: abs(c["delta"] - 0.70))
    return candidates[0]


# ─── Scan de un ticker individual ───────────────────────────────────────────────

def scan_ticker(ticker: str, cfg: Optional[dict] = None) -> dict:
    """Evalúa un ticker para LEAP. Devuelve dict con resultado o motivo de descarte."""
    if cfg is None:
        cfg = yaml.safe_load(CONFIG_PATH.read_text())

    result = {"ticker": ticker, "ok": False, "reason": None}
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        spot = info.get("regularMarketPrice") or info.get("currentPrice")
        if not spot:
            hist = t.history(period="5d")
            spot = float(hist["Close"].iloc[-1]) if len(hist) else None
        if not spot:
            result["reason"] = "no_price"
            return result

        # Filtro earnings
        dte_earn = days_to_next_earnings(t)
        if dte_earn is not None and 0 <= dte_earn <= cfg["earnings_exclusion_days"]:
            result["reason"] = f"earnings_in_{dte_earn}d"
            result["earnings_days"] = dte_earn
            return result

        leap = find_best_leap(t, float(spot), cfg)
        if leap is None:
            result["reason"] = "no_leap_match"
            return result

        hv = hv_percentile(t)
        pb = pullback_metrics(t)

        result.update({
            "ok": True,
            "spot": round(float(spot), 2),
            "company_name": info.get("longName") or info.get("shortName") or ticker,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "leap": leap,
            "hv": hv,
            "pullback": pb,
            "earnings_days": dte_earn,
        })
        return result
    except Exception as e:
        result["reason"] = f"error: {str(e)[:100]}"
        return result


# ─── Scan del universo completo ─────────────────────────────────────────────────

def scan_universe(top_n: int = 15) -> dict:
    """
    Escanea universo y devuelve top_n candidatos rankeados.
    Ranking: HV percentile bajo (LEAPS baratas) + pullback (from_high negativo).
    """
    cfg = yaml.safe_load(CONFIG_PATH.read_text())
    universe = cfg["universe"]

    log.info(f"Scan LEAPS: {len(universe)} tickers")
    valid = []
    discarded = {}

    for i, tk in enumerate(universe, 1):
        if i % 20 == 0:
            log.info(f"  {i}/{len(universe)}...")
        r = scan_ticker(tk, cfg)
        if r["ok"]:
            valid.append(r)
        else:
            discarded[tk] = r.get("reason", "unknown")

    # Score: HV percentile bajo (cheaper IV) + pullback desde máximos
    for r in valid:
        hv_pct = (r.get("hv") or {}).get("hv_percentile", 50)
        from_high = (r.get("pullback") or {}).get("from_high_pct", 0)
        # Lower hv_pct = better. More negative from_high = better (recent pullback).
        r["_score"] = (100 - hv_pct) + max(0, -from_high)

    valid.sort(key=lambda x: x["_score"], reverse=True)
    top = valid[:top_n]
    for r in top:
        r.pop("_score", None)

    return {
        "scan_date": datetime.now().isoformat(),
        "universe_size": len(universe),
        "valid_count": len(valid),
        "discarded_count": len(discarded),
        "top_candidates": top,
        "discarded_summary": _summarize_discarded(discarded),
    }


def _summarize_discarded(discarded: dict) -> dict:
    """Cuenta razones de descarte."""
    out = {}
    for reason in discarded.values():
        key = reason.split(":")[0] if ":" in reason else reason
        if key.startswith("earnings_in_"):
            key = "earnings_soon"
        out[key] = out.get(key, 0) + 1
    return out


# ─── Persistencia ───────────────────────────────────────────────────────────────

def save_scan(result: dict, out_dir: Optional[Path] = None) -> Path:
    """Guarda el scan en data/leaps/ con timestamp."""
    if out_dir is None:
        out_dir = Path(__file__).parent.parent / "data" / "leaps"
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    fpath = out_dir / fname
    fpath.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return fpath


# ─── Formatter para mensaje de Telegram al inbox ────────────────────────────────

def format_scan_for_inbox(scan: dict, n: int = 5) -> str:
    """Formato compacto para encolar como [SCHEDULER] LEAPS."""
    lines = [f"[SCHEDULER] LEAPS scan {scan['scan_date'][:10]} — {scan['valid_count']}/{scan['universe_size']} válidos. Top {n} candidatos:\n"]
    for r in scan["top_candidates"][:n]:
        leap = r["leap"]
        hv = r.get("hv") or {}
        pb = r.get("pullback") or {}
        lines.append(
            f"{r['ticker']} ({r['company_name']}) — {r.get('sector') or 'n/a'}\n"
            f"  Spot ${r['spot']} | LEAP {leap['expiry']} ${leap['strike']} "
            f"Δ{leap['delta']:.2f} | Prima ${leap['mid']} | BE ${leap['break_even']}\n"
            f"  IV{leap['iv']:.0%} | HV pctil {hv.get('hv_percentile', 'n/a')} | "
            f"from_high {pb.get('from_high_pct', 'n/a')}% | OI {leap['open_interest']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if len(sys.argv) > 1:
        # Modo on-demand: python -m tools.leaps_scanner NKE
        tk = sys.argv[1].upper()
        r = scan_ticker(tk)
        print(json.dumps(r, indent=2, default=str))
    else:
        # Modo universo: python -m tools.leaps_scanner
        scan = scan_universe()
        path = save_scan(scan)
        print(f"Guardado: {path}")
        print(format_scan_for_inbox(scan))
