"""
Señal de inversión a partir del margen de seguridad (MoS = (fair_value - precio) / fair_value).

Única fuente de verdad de las bandas value (Graham/Buffett): las usa el dashboard,
el escáner de watchlist y la skill `thesis-writer`. Si cambian las bandas, cambian aquí.
"""


def classify_signal(margin_of_safety: float) -> tuple:
    """MoS en % → (emoji, etiqueta, css_class). El css_class lo usa el dashboard."""
    if margin_of_safety >= 40:
        return ('🟢', 'MUY INFRAVALORADA', 'signal-strong-buy')
    elif margin_of_safety >= 25:
        return ('🟢', 'INFRAVALORADA', 'signal-buy')
    elif margin_of_safety >= 10:
        return ('🟡', 'LIGERAMENTE INFRAVALORADA', 'signal-watchlist')
    elif margin_of_safety >= -10:
        return ('⚪', 'VALOR JUSTO', 'signal-fair')
    elif margin_of_safety >= -25:
        return ('🟠', 'SOBREVALORADA', 'signal-overvalued')
    else:
        return ('🔴', 'MUY SOBREVALORADA', 'signal-avoid')
