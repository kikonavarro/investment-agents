"""
Generador de informes PDF para análisis de screening multi-empresa.
Usa fpdf2 con soporte Unicode (DejaVu).
"""
import os
import tempfile
from datetime import datetime
from fpdf import FPDF

# Colores del tema
C_PRIMARY = (39, 58, 79)       # Azul oscuro
C_ACCENT = (0, 102, 204)       # Azul
C_POSITIVE = (46, 125, 50)     # Verde
C_NEGATIVE = (198, 40, 40)     # Rojo
C_NEUTRAL = (117, 117, 117)    # Gris
C_BG_LIGHT = (245, 245, 245)   # Gris claro
C_WHITE = (255, 255, 255)
C_DARK = (50, 50, 50)
C_WARN = (255, 152, 0)         # Naranja


def _s(text: str) -> str:
    """Sanitiza texto para latin-1."""
    if not text:
        return ""
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u2022": "-",
        "\u2192": "->", "\u2190": "<-", "\u2191": "^", "\u2193": "v",
        "\u2264": "<=", "\u2265": ">=", "\u2260": "!=",
        "\u2605": "*", "\u2606": "*",
        "\u2714": "[OK]", "\u2718": "[X]",
        "\u26a0": "[!]", "\u2139": "[i]",
        "\U0001f4ca": "", "\U0001f4b5": "$", "\U0001f4b0": "$",
        "\U0001f3af": "", "\U0001f4c8": "", "\U0001f4c9": "",
        "\U0001f4cb": "", "\U0001f3e2": "", "\U0001f6a8": "",
        "\U0001f680": "", "\U0001f4aa": "", "\U0001f3c6": "",
        "\u2b50": "*", "\u26a1": "!", "\u2699": "",
        "\U0001f534": "[!]", "\U0001f7e1": "[!]",
        "\U0001f43b": "[Bear]", "\U0001f402": "[Bull]",
        "\u2694": "", "\U0001f464": "", "\U0001f3e6": "",
        "\u2611": "[v]", "\u2b06": "^", "\u2b07": "v",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('latin-1', 'replace').decode('latin-1')


class ScreeningReportPDF(FPDF):
    """PDF para informes de screening multi-empresa."""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.report_title = title
        self.report_subtitle = subtitle
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(*C_NEUTRAL)
            self.cell(0, 10, _s(self.report_title), align="L")
            self.cell(0, 10, f"Pag. {self.page_no()}", align="R")
            self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*C_NEUTRAL)
        self.cell(0, 10,
                  f"Generado {datetime.now().strftime('%d/%m/%Y')} | "
                  f"Investment Agents - Analisis automatizado",
                  align="C")

    def cover_page(self, title, subtitle, date_str, extra_lines=None):
        self.add_page()
        self.ln(50)
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*C_PRIMARY)
        self.cell(0, 15, _s(title), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        self.set_font("Helvetica", "", 16)
        self.set_text_color(*C_ACCENT)
        self.cell(0, 10, _s(subtitle), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(15)
        self.set_font("Helvetica", "", 12)
        self.set_text_color(*C_DARK)
        self.cell(0, 8, _s(date_str), align="C", new_x="LMARGIN", new_y="NEXT")
        if extra_lines:
            self.ln(5)
            for line in extra_lines:
                self.cell(0, 7, _s(line), align="C", new_x="LMARGIN", new_y="NEXT")

    def section_title(self, title, level=1):
        self.ln(3)
        if level == 1:
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(*C_PRIMARY)
            self.cell(0, 10, _s(title), new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(*C_PRIMARY)
            self.set_line_width(0.5)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(4)
        elif level == 2:
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*C_ACCENT)
            self.cell(0, 8, _s(title), new_x="LMARGIN", new_y="NEXT")
            self.ln(2)
        else:
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*C_DARK)
            self.cell(0, 7, _s(title), new_x="LMARGIN", new_y="NEXT")
            self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*C_DARK)
        self.multi_cell(0, 5, _s(text))
        self.ln(2)

    def bullet(self, text, indent=5):
        x = self.get_x()
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*C_DARK)
        self.cell(indent, 5, "")
        self.cell(4, 5, "-")
        self.multi_cell(0, 5, _s(text))
        self.ln(1)

    def key_value(self, key, value, bold_value=False):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_DARK)
        self.cell(55, 6, _s(f"{key}:"))
        self.set_font("Helvetica", "B" if bold_value else "", 10)
        self.cell(0, 6, _s(str(value)), new_x="LMARGIN", new_y="NEXT")

    def metrics_table(self, headers, rows, col_widths=None):
        """Tabla generica con headers y filas."""
        if col_widths is None:
            col_widths = [190 / len(headers)] * len(headers)

        # Header
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*C_PRIMARY)
        self.set_text_color(*C_WHITE)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, _s(h), border=1, fill=True,
                      align="C" if i > 0 else "L")
        self.ln()

        # Rows
        self.set_font("Helvetica", "", 8)
        for row_idx, row in enumerate(rows):
            bg = C_BG_LIGHT if row_idx % 2 == 0 else C_WHITE
            self.set_fill_color(*bg)
            self.set_text_color(*C_DARK)
            for i, cell in enumerate(row):
                align = "C" if i > 0 else "L"
                self.cell(col_widths[i], 6, _s(str(cell)), border=1,
                          fill=True, align=align)
            self.ln()
        self.ln(3)

    def rating_box(self, ticker, company, rating, color):
        """Box coloreado con rating de conviccion."""
        self.set_fill_color(*color)
        self.set_text_color(*C_WHITE)
        self.set_font("Helvetica", "B", 11)
        stars = "*" * rating
        self.cell(0, 8,
                  f"  {_s(ticker)} - {_s(company)}   [{stars}]",
                  fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*C_DARK)
        self.ln(2)

    def verdict_box(self, text, box_type="info"):
        """Box con fondo coloreado para veredictos."""
        colors = {
            "positive": (232, 245, 233),
            "negative": (255, 235, 238),
            "warning": (255, 243, 224),
            "info": (227, 242, 253),
        }
        bg = colors.get(box_type, colors["info"])
        self.set_fill_color(*bg)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*C_DARK)
        self.multi_cell(0, 6, _s(text), fill=True)
        self.ln(3)


def generate_screening_report(output_path: str = None) -> str:
    """Genera el informe PDF de screening de 18 empresas con contexto Iran."""

    if output_path is None:
        output_path = "data/Informe_Screening_Iran_Mar2026.pdf"

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    pdf = ScreeningReportPDF(
        title="Screening de Oportunidades - Conflicto Iran",
        subtitle="Analisis de 18 empresas"
    )

    # ===== PORTADA =====
    pdf.cover_page(
        title="Screening de Oportunidades",
        subtitle="Conflicto Iran - Marzo 2026",
        date_str=datetime.now().strftime("%d de marzo de 2026"),
        extra_lines=[
            "Analisis de 18 empresas: energia, mineria, fintech",
            "Contexto: guerra de Iran y prima de riesgo geopolitico",
        ]
    )

    # ===== CONTEXTO MACRO =====
    pdf.add_page()
    pdf.section_title("1. Contexto Macro: Guerra de Iran")
    pdf.body_text(
        "El conflicto con Iran genera multiples efectos en los mercados financieros "
        "que afectan directamente a las empresas analizadas:"
    )
    pdf.bullet("Prima de riesgo en petroleo: el Estrecho de Ormuz canaliza el 20% "
               "del crudo mundial. Cualquier disruption dispara el precio del barril.")
    pdf.bullet("Huida a activos refugio: oro, uranio y metales preciosos se benefician "
               "de la incertidumbre geopolitica.")
    pdf.bullet("Demanda de seguridad energetica: carbon, GNL y energia nuclear ganan "
               "relevancia como alternativas de suministro fiable.")
    pdf.bullet("Presion alcista en metales criticos: disruption de cadenas de suministro "
               "eleva precios de estanyo, cobre y otros minerales industriales.")
    pdf.bullet("Gasto militar creciente: mayor demanda de cobre, aluminio y materiales "
               "de defensa.")
    pdf.ln(3)
    pdf.body_text(
        "Las empresas analizadas se agrupan en: petroleo/gas (WCP, MAU, SOIL, PBR, KOS), "
        "carbon (YAL, WHC), GNL (GLNG), mineria (REG, DNG, AFM, MLX, IVN), "
        "uranio (U-UN), fintech (KSPI), financieras (CGEO, GGAL) y tecnologia (ASTS)."
    )

    # ===== TABLA RESUMEN =====
    pdf.add_page()
    pdf.section_title("2. Tabla Resumen - 18 Empresas")

    headers = ["Ticker", "Empresa", "Sector", "P/E", "EV/EBITDA", "Div%", "Precio", "Target"]
    widths = [18, 42, 30, 16, 20, 14, 20, 20]

    rows = [
        ["CGEO.L", "Georgia Capital", "Financiero", "2.3x", "N/A", "-", "3450p", "3655p"],
        ["ASTS", "AST SpaceMobile", "Tech/Space", "N/A", "N/A", "-", "$88.2", "$88.5"],
        ["REG.V", "Regulus Resources", "Mineria", "N/A", "N/A", "-", "C$3.26", "C$6.00"],
        ["DNG.TO", "Dynacor Group", "Oro", "9.7x", "7.2x", "3.2%", "C$4.94", "C$8.90"],
        ["U-UN.TO", "Sprott Uranium", "Uranio", "N/A", "N/A", "-", "N/A", "N/A"],
        ["WCP.TO", "Whitecap Resources", "Oil&Gas", "15.1x", "6.7x", "4.9%", "C$14.91", "C$15.30"],
        ["MAU.PA", "Maurel et Prom", "Oil&Gas", "6.1x", "N/A", "2.9%", "10.93E", "9.63E"],
        ["SOIL.TO", "Saturn Oil & Gas", "Oil&Gas", "6.6x", "3.0x", "-", "C$5.37", "C$4.79"],
        ["KSPI", "Kaspi.kz", "Fintech", "6.3x", "N/A", "10.0%", "$73.0", "$99.3"],
        ["YAL.AX", "Yancoal", "Carbon", "25.2x", "6.6x", "2.2%", "A$8.31", "N/A"],
        ["WHC.AX", "Whitehaven Coal", "Carbon", "11.8x", "3.5x", "0.9%", "A$9.30", "A$8.49"],
        ["PBR-A", "Petrobras (Pref)", "Oil&Gas", "5.4x", "2.7x", "8.1%", "$16.99", "$16.51"],
        ["GLNG", "Golar LNG", "GNL", "81.1x", "47.3x", "2.0%", "$52.7", "$52.1"],
        ["AFM.V", "Alphamin Resources", "Estanyo", "6.7x", "4.5x", "9.9%", "C$1.07", "N/A"],
        ["GGAL", "Grupo Fin. Galicia", "Banca", "49.2x*", "N/A", "3.3%", "$43.3", "$68.1"],
        ["MLX.AX", "Metals X", "Estanyo", "9.8x", "5.1x", "-", "A$1.18", "A$1.55"],
        ["KOS", "Kosmos Energy", "Oil&Gas", "N/A", "9.6x", "-", "$2.88", "$2.51"],
        ["IVN.TO", "Ivanhoe Mines", "Cobre", "41.5x*", "N/A", "-", "C$10.8", "C$19.2"],
    ]
    pdf.metrics_table(headers, rows, widths)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*C_NEUTRAL)
    pdf.cell(0, 5, "* P/E trailing elevado pero Forward P/E mucho menor (GGAL Fwd 5.4x, IVN Fwd 11.9x)",
             new_x="LMARGIN", new_y="NEXT")

    # ===== TOP OPORTUNIDADES =====
    pdf.add_page()
    pdf.section_title("3. Top Oportunidades (ordenadas por conviccion)")

    # --- AFM.V ---
    pdf.rating_box("AFM.V", "Alphamin Resources - Estanyo (RDC)", 5, C_POSITIVE)
    pdf.body_text(
        "El estanyo es mineral critico (semiconductores, soldadura electronica). "
        "Alphamin es el mayor productor de estanyo del mundo desde una sola mina "
        "(Bisie, RDC). Margenes brutales, casi sin deuda, dividendo del 10%, y "
        "cotiza un 33% por debajo de maximos."
    )
    headers_m = ["Metrica", "Valor"]
    rows_m = [
        ["P/E", "6.7x"], ["EV/EBITDA", "4.5x"], ["ROE", "43%"],
        ["Margen operativo", "49%"], ["Dividendo", "9.9%"],
        ["Deuda/Equity", "9.9 (baja)"], ["vs 52w High", "-33%"],
    ]
    pdf.metrics_table(headers_m, rows_m, [60, 40])
    pdf.verdict_box(
        "Catalizador Iran: la disrupcion de cadenas de suministro eleva precios de "
        "minerales criticos. Riesgo: concentracion en una sola mina en RDC.",
        "positive"
    )

    # --- SOIL.TO ---
    pdf.add_page()
    pdf.rating_box("SOIL.TO", "Saturn Oil & Gas - Petroleo (Canada)", 5, C_POSITIVE)
    pdf.body_text(
        "La petrolera mas barata de la lista. Forward P/E de 3.3x es absurdo para "
        "una empresa con 19% ROE. Produccion 100% canadiense (alejada de Ormuz, "
        "sin riesgo de sanciones). El petroleo canadiense se beneficia directamente "
        "del conflicto con Iran."
    )
    rows_m = [
        ["P/E Forward", "3.3x"], ["EV/EBITDA", "3.0x"], ["ROE", "19%"],
        ["Margen operativo", "24%"], ["Deuda/Equity", "87 (alta)"],
        ["Consenso", "Buy"],
    ]
    pdf.metrics_table(headers_m, rows_m, [60, 40])
    pdf.verdict_box(
        "Catalizador Iran: beneficiario directo del petroleo caro. "
        "Riesgo: deuda elevada (D/E 87). Si el petroleo cae, el apalancamiento pesa.",
        "positive"
    )

    # --- DNG.TO ---
    pdf.rating_box("DNG.TO", "Dynacor Group - Oro (Peru)", 4, C_POSITIVE)
    pdf.body_text(
        "Procesador de oro artesanal en Peru. El oro es EL activo refugio por "
        "excelencia en guerras. Cotiza un 30% debajo de maximos con un 80% de "
        "upside segun analistas. Negocio muy defensivo: compra mineral, lo procesa, "
        "vende oro -- no tiene riesgo de exploracion. Deuda practicamente cero."
    )
    rows_m = [
        ["P/E", "9.7x (Fwd 6.5x)"], ["Dividendo", "3.2%"],
        ["Deuda total", "$688K (casi cero)"], ["Target analistas", "C$8.90 (+80%)"],
    ]
    pdf.metrics_table(headers_m, rows_m, [60, 40])
    pdf.verdict_box(
        "Catalizador Iran: el oro es activo refugio clasico en conflictos. "
        "Riesgo: dependencia del precio del oro (pero ese es justamente el catalizador).",
        "positive"
    )

    # --- PBR-A ---
    pdf.add_page()
    pdf.rating_box("PBR-A", "Petrobras - Petroleo (Brasil)", 4, C_POSITIVE)
    pdf.body_text(
        "La major de petroleo mas barata del mundo. EV/EBITDA de 2.7x es de "
        "liquidacion. Brasil esta geograficamente aislado del conflicto de Iran, "
        "y Petrobras tiene el pre-sal (uno de los activos petroleros mas valiosos "
        "del planeta). Cobras 8% de dividendo mientras esperas."
    )
    rows_m = [
        ["P/E", "5.4x"], ["EV/EBITDA", "2.7x"], ["ROE", "28%"],
        ["Dividendo", "8.1%"], ["Deuda/Equity", "92"],
    ]
    pdf.metrics_table(headers_m, rows_m, [60, 40])
    pdf.verdict_box(
        "Catalizador Iran: petroleo caro + aislamiento geografico. "
        "Riesgo: riesgo politico brasilenyo (Lula, interferencia estatal). "
        "Siempre ha sido el motivo del descuento.",
        "positive"
    )

    # --- MAU.PA ---
    pdf.rating_box("MAU.PA", "Maurel et Prom - Petroleo (Francia/Africa)", 4, C_POSITIVE)
    pdf.body_text(
        "Petrolera francesa con produccion en Gabon y Angola (Africa Occidental, "
        "lejos de Ormuz). Margen neto del 71% es extraordinario. P/E de 6x con "
        "beta de 0.33 -- es casi una 'utility petrolera'."
    )
    rows_m = [
        ["P/E", "6.1x"], ["Margen neto", "71%"],
        ["Dividendo", "2.9%"], ["Beta", "0.33"],
    ]
    pdf.metrics_table(headers_m, rows_m, [60, 40])

    # --- IVN.TO ---
    pdf.add_page()
    pdf.rating_box("IVN.TO", "Ivanhoe Mines - Cobre (RDC)", 4, C_ACCENT)
    pdf.body_text(
        "Kamoa-Kakula es una de las mejores minas de cobre del mundo. Cotiza un "
        "47% debajo de maximos. El cobre es esencial para defensa, electrificacion "
        "y la transicion energetica. El conflicto con Iran acelera el gasto militar "
        "(mas cobre). Target de consenso implica casi duplicar."
    )
    rows_m = [
        ["P/E Forward", "11.9x"], ["Precio actual", "C$10.78"],
        ["52w High", "C$20.34 (-47%)"], ["Target", "C$19.23 (+78%)"],
    ]
    pdf.metrics_table(headers_m, rows_m, [60, 40])

    # --- KSPI ---
    pdf.rating_box("KSPI", "Kaspi.kz - Fintech (Kazajistan)", 3, C_ACCENT)
    pdf.body_text(
        "Super-app kazaja (pagos + marketplace + fintech). ROE del 51% a P/E 6.3x "
        "es absurdamente barato. Dividendo del 10%. El negocio es fantastico -- "
        "el descuento es puramente geopolitico (proximidad a Rusia/Iran)."
    )
    rows_m = [
        ["P/E", "6.3x"], ["ROE", "51%"],
        ["Dividendo", "10%"], ["Target", "$99.3 (+36%)"],
    ]
    pdf.metrics_table(headers_m, rows_m, [60, 40])
    pdf.verdict_box(
        "Riesgo: Kazajistan comparte frontera maritima (Caspio) con Iran. "
        "Escalada del conflicto podria impactar mas.",
        "warning"
    )

    # ===== OPORTUNIDADES MODERADAS =====
    pdf.add_page()
    pdf.section_title("4. Oportunidades Moderadas")

    moderate = [
        ("MLX.AX - Metals X (Estanyo)",
         "P/E 10, net cash ($294M cash vs $3M deuda), Strong Buy. "
         "Misma tesis que Alphamin pero mas cara y menor margen."),
        ("WHC.AX - Whitehaven Coal (Carbon)",
         "EV/EBITDA 3.5, FCF $1.7B. Seguridad energetica. "
         "Pero near 52w high y carbon tiene estigma ESG."),
        ("YAL.AX - Yancoal (Carbon)",
         "Net cash masivo ($2.1B vs $84M deuda). Fwd P/E 8.2. "
         "Seguro pero crecimiento limitado."),
        ("CGEO.L - Georgia Capital (Conglomerado)",
         "P/E 2.3x, ROE 43%. Conglomerado georgiano. "
         "Baratisimo pero iliquido y riesgo geopolitico (frontera Rusia)."),
        ("GGAL - Grupo Financiero Galicia (Banca Argentina)",
         "Argentina reform play, Fwd P/E 5.4, target +57%. "
         "Pero no tiene relacion directa con Iran. Es una apuesta a Milei."),
        ("U-UN.TO - Sprott Physical Uranium",
         "Trust fisico de uranio. El conflicto refuerza la tesis nuclear como "
         "energia segura de base. Bueno como cobertura."),
        ("WCP.TO - Whitecap Resources (Oil&Gas)",
         "P/E 15, Strong Buy, Div 4.9%. Solido pero ya cotiza near 52w high. "
         "Menos upside que SOIL o PBR."),
    ]

    for title, desc in moderate:
        pdf.section_title(title, level=3)
        pdf.body_text(desc)

    # ===== EVITAR =====
    pdf.add_page()
    pdf.section_title("5. Empresas a Evitar")

    avoid = [
        ("ASTS - AST SpaceMobile", "EVITAR",
         "Pre-revenue, market cap $33B sobre $71M de ingresos. Sin beneficios. "
         "Pura especulacion sin relacion con el conflicto Iran."),
        ("GLNG - Golar LNG", "EVITAR",
         "P/E 81x, EV/EBITDA 47x, FCF negativo (-$901M). Carisimo. "
         "Strong buy de analistas pero los numeros no cuadran con value investing."),
        ("KOS - Kosmos Energy", "EVITAR",
         "Deuda/Equity de 580x. Margenes negativos (-54% neto). "
         "Una bomba de relojeria financiera."),
        ("REG.V - Regulus Resources", "ESPECULATIVO",
         "Explorador sin ingresos. Target $6 pero es un solo analista. "
         "Puro venture capital, no value investing."),
    ]

    for title, label, desc in avoid:
        pdf.rating_box(title, label, 0, C_NEGATIVE)
        pdf.body_text(desc)

    # ===== CONCLUSION =====
    pdf.add_page()
    pdf.section_title("6. Conclusion y Top 3")

    pdf.body_text(
        "Las tres mejores oportunidades combinando valuacion de deep value "
        "con catalizador directo del conflicto Iran son:"
    )
    pdf.ln(3)

    pdf.section_title("1. AFM.V (Alphamin Resources)", level=2)
    pdf.body_text(
        "Mejor ratio calidad/precio absoluto de la lista. ROE 43%, dividendo 10%, "
        "P/E 6.7x. Mineral critico con disruption de supply chain como catalizador."
    )

    pdf.section_title("2. SOIL.TO (Saturn Oil & Gas)", level=2)
    pdf.body_text(
        "El mas barato (Fwd P/E 3.3x) y beneficiario directo del petroleo caro. "
        "Produccion canadiense aislada de riesgos de Ormuz."
    )

    pdf.section_title("3. DNG.TO (Dynacor Group)", level=2)
    pdf.body_text(
        "Oro + margen de seguridad del 80% + deuda cero. El activo refugio clasico "
        "en entorno de conflicto belico, con negocio defensivo de procesamiento."
    )

    # ===== DISCLAIMER =====
    pdf.ln(10)
    pdf.set_draw_color(*C_NEUTRAL)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*C_NEUTRAL)
    pdf.multi_cell(0, 4,
        "DISCLAIMER: Este informe ha sido generado automaticamente con fines "
        "educativos e informativos. No constituye consejo de inversion. "
        "Las valoraciones y opiniones se basan en datos publicos disponibles "
        "a fecha de generacion. Consulte con un asesor financiero antes de "
        "tomar decisiones de inversion. Datos de Yahoo Finance via yahooquery."
    )

    # Guardar
    pdf.output(output_path)
    print(f"PDF generado: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_screening_report()
