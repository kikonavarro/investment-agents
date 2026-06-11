# ServiceNow, Inc. (NOW) — Tesis de inversión

**Fecha:** 11 de junio de 2026
**Precio actual:** $103.84 · **Market cap:** $107.1 B · **Acciones:** 1.031 M (post-split ~5:1)
**Sector:** Software empresarial (workflow / plataforma) · **Beta:** 0.93

> *Nota sobre cifras: todas las magnitudes por acción están ajustadas al split de acciones ~5:1 efectivo en 2026 (el 10-K reexpresa retroactivamente las series). El análisis financiero se hace sobre cifras absolutas (revenue, FCF, RPO), inmunes al split.*

---

## 1. Resumen ejecutivo

ServiceNow es, por calidad de franquicia, uno de los mejores negocios de software del mundo: plataforma de workflow con **tasa de renovación del 98%**, **$28.2 B de RPO** (2.1× los ingresos anuales) y un margen de FCF del 34%. Y, sin embargo, la acción **ha caído ~45-52% en seis meses** (-37% en el año) hasta $103.84. No es un problema de números —Q1 FY2026 batió y la guía se **subió**— sino de **narrativa**: el mercado teme que los agentes de IA destruyan el modelo de licencia por asiento ("seat compression"). El selloff arrancó cuando Anthropic lanzó plug-ins agénticos en febrero y se llevó por delante ~17% del índice de software en seis sesiones.

La pregunta de inversión no es si ServiceNow es un gran negocio (lo es), sino **cuánto vale una vez que descuento honestamente el coste real del stock-based compensation (SBC) y que la IA podría ser tanto viento de cola como de cara.**

Mi valoración DCF (descontando el SBC como coste real, no como FCF gratis):

- 🔴 **Bear ($78.81, -24%):** la "SaaS-pocalypse" es real. Los agentes comprimen asientos, el crecimiento se desacelera al 8-9%, el margen bruto sigue erosionándose por el coste de compute de IA y el múltiplo normaliza a 19× EBITDA. *Duele de verdad: la tesis estaría equivocada.*
- ⚪ **Base ($118.34, +14%):** la desaceleración es ordenada (22%→12%), ServiceNow se convierte en la **capa de orquestación** de los agentes de IA (no en su víctima), el margen operativo se expande hacia el 21% y el múltiplo terminal se asienta en 22× EBITDA.
- 🟢 **Bull ($151.72, +46%):** Now Assist y el pricing por consumo **reaceleran** el ACV; los productos de IA superan los $1.500 M de McDermott, el crecimiento se mantiene ~20% y el margen avanza al 23-24%.

**Fair value ponderado (40/40/20): $109.20 · Margen de seguridad: +4.9% → ⚪ VALOR JUSTO (sesgo ligeramente positivo).**

**Conclusión rápida:** negocio excepcional a precio razonable, no a precio de ganga. La diferencia entre mi $109 y el consenso de $141.86 **no es un desacuerdo sobre el negocio: es metodológico** —yo expenso el SBC como lo que es (dilución real); la calle valora sobre FCF reportado. A $104 hay calidad pero el margen de seguridad es fino. Es una posición para **iniciar pequeño y ampliar por debajo de ~$90**, no para cargar de golpe.

---

## 2. El negocio

### Modelo de negocio (cómo gana dinero)

ServiceNow vende **suscripciones plurianuales (típicamente 3 años) a una plataforma cloud única** sobre la que corren todos sus productos: gestión de servicios de IT (ITSM, su origen y aún su corazón), IT operations, gestión de riesgo, seguridad (SecOps), customer service, RRHH, workflows de empleado, y ahora una capa de IA (Now Assist) y datos (Workflow Data Fabric, RaptorDB). El 97% de los ingresos son **suscripción recurrente**; el resto, servicios profesionales.

La mecánica de las "unit economics" es la mejor del SaaS empresarial:

- **Land & expand.** Entra por un departamento (normalmente IT) y se expande a RRHH, legal, finanzas, atención al cliente. Cada workflow nuevo reutiliza la misma plataforma → coste marginal de venta bajísimo y net expansion alto.
- **Facturación por adelantado.** Cobra el año por anticipado y reconoce el ingreso de forma lineal. Eso genera **deferred revenue** (float de clientes que financia el crecimiento) y explica por qué el FCF (34% de margen) supera con creces al beneficio GAAP.
- **Visibilidad extrema.** $28.2 B de RPO (+27% YoY) son ingresos ya contratados aún no reconocidos: **2.1 años de ingresos vendidos de antemano**. El cRPO ($13.0 B, +25%) es lo que entra en los próximos 12 meses. Pocos negocios del mundo tienen esta predictibilidad.

### Moat — **Wide moat** (calificación: Amplio)

Cuatro de las cinco fuentes de ventaja de Morningstar están presentes, de forma robusta:

1. **Costes de cambio (la fuente dominante).** ServiceNow se incrusta en los procesos operativos críticos de la empresa. Migrar significa reescribir flujos de trabajo, reentrenar a miles de empleados y arriesgar la operativa diaria. El **98% de renovación, sostenido tres años seguidos**, es la prueba cuantitativa del moat. Es un número que solo exhiben las mejores franquicias de software del planeta.
2. **Efecto de red / plataforma.** Cuantos más módulos adopta un cliente, más datos y procesos viven en la "single system of record", y más valioso (y pegajoso) se vuelve. La extensión hacia el App Engine y el ecosistema de partners refuerza el efecto.
3. **Intangibles.** Dos décadas entendiendo cómo fluye el trabajo entre silos. El propio 10-K lo expresa con precisión: el valor está en *"controlar y gestionar lo que ocurre después de que la información se genera"* —exactamente la capa de orquestación que la IA necesita.
4. **Escala/coste.** I+D de >$3 B anuales que un competidor de nicho no puede replicar.

El debate de 2026 es si la IA **erosiona** este moat (menos asientos humanos = menos licencias) o lo **refuerza** (alguien tiene que orquestar, gobernar y auditar a los agentes, y esa es justo la plataforma de ServiceNow). Mi base case se inclina por lo segundo, pero el bear es plausible y por eso pesa el 40%.

---

## 3. Análisis financiero

| Año | Revenue ($M) | YoY | Op. income ($M) | Op. margin (GAAP) | Net income ($M) | FCF ($M) | FCF margin |
|------|--------------|--------|------------------|--------------------|------------------|-----------|------------|
| 2022 | 7,245 | — | 355 | 4.9% | 325 | 2,173 | 30.0% |
| 2023 | 8,971 | +23.8% | 762 | 8.5% | 1,731 | 2,701 | 30.1% |
| 2024 | 10,984 | +22.4% | 1,364 | 12.4% | 1,425 | 3,375 | 30.7% |
| 2025 | 13,278 | +20.9% | 1,824 | 13.7% | 1,748 | 4,533 | 34.1% |

**Lo que cuenta esta tabla:**

- **Crecimiento de élite y duradero:** +22.4% CAGR a 3 años partiendo ya de una base de >$7 B. Q1 FY2026 mantuvo el ritmo (+22% en suscripción) y la dirección **subió** la guía FY26 a $15.74-15.78 B (+20.5-21%).
- **Apalancamiento operativo real:** el margen operativo GAAP casi se triplica (4.9% → 13.7%) en tres años. La operación escala.
- **El "puzzle" del SBC.** Aquí está la clave de toda la valoración. El **FCF ($4.533 B) cuadruplica el beneficio neto GAAP ($1.748 B)**. La diferencia es, sobre todo, el **stock-based compensation** (no-cash, pero **dilución muy real** para el accionista) y el deferred revenue. Un value investor honesto **no puede tratar el SBC como FCF gratis.** Mi DCF lo descuenta como coste (vía margen EBIT GAAP), y de ahí que mi fair value quede por debajo del consenso, que valora sobre FCF reportado. *El gap entre mi $109 y los $142 de la calle es, casi exactamente, el SBC capitalizado.*
- **Erosión de margen bruto a vigilar:** el margen bruto de suscripción bajó de 82% (2024) a **80% (2025)** y el 10-K anticipa otra ligera caída en 2026, por el **coste de compute de IA de terceros** y la amortización de intangibles de adquisiciones (Armis). No es trivial: el pivote de licencia-por-asiento a pricing-por-consumo de IA traslada coste de compute al P&L. Es el principal argumento del bear sobre márgenes.

### Capital allocation

- **ROIC muy por encima del WACC.** Con $1.8 B de op. income GAAP (y ~$4 B no-GAAP) sobre una base de capital invertido modesta —es un negocio asset-light—, el retorno sobre capital incremental es de doble dígito alto, holgadamente por encima de un WACC del 10%. Crea valor cada dólar que reinvierte.
- **Sin dividendo, reinversión + recompra.** ServiceNow reinvierte agresivamente en I+D y go-to-market (lo correcto a estas tasas de retorno) y usa recompras **principalmente para neutralizar la dilución del SBC**, no para reducir significativamente el share count. El inversor debe entender que la recompra aquí es más "tapar el agujero del SBC" que retorno neto de caja.
- **M&A disciplinada y estratégica:** Armis (seguridad/visibilidad de activos) y la colaboración con Cohesity encajan en la narrativa de plataforma + IA + datos. Balance impecable: **caja neta** (~$2.75 B), deuda/equity de 0.02. Sin riesgo financiero.

---

## 4. Valoración DCF

### Metodología y parámetros

Valoro por DCF unlevered a 5 años con valor terminal sobre EV/EBITDA. **Decisión metodológica central: uso EBIT GAAP** (que ya descuenta el SBC como gasto) en lugar de partir del FCF reportado. Esto trata el SBC como coste real del accionista —la postura value correcta— y produce un "owner earnings" más conservador que el FCF de $4.5 B. WACC vía CAPM: risk-free 4% + beta 0.93 × ERP 5.5% ≈ 9.1%, elevado al suelo value del 10% en base.

| Parámetro | 🔴 Bear | ⚪ Base | 🟢 Bull |
|------------|---------|---------|---------|
| Crecimiento ingresos Y1-Y5 | 19/15/12/10/9% | 22/19/16/14/12% | 23/21/19/16/14% |
| CAGR 5 años implícito | ~12.8% | ~16.6% | ~18.6% |
| Margen bruto | 75% | 77% | 78% |
| SG&A % / I+D % | 36% / 21% | 35% / 21% | 34% / 21% |
| **Margen EBIT resultante** | **18%** | **21%** | **23%** |
| D&A % / CapEx % | 5.5% / 3.0% | 5.5% / 3.0% | 5.5% / 3.0% |
| Tasa impositiva | 21% | 20% | 19% |
| WACC | 10.5% | 10.0% | 9.5% |
| Múltiplo terminal (EV/EBITDA) | 19× | 22× | 24× |
| **Fair value / acción** | **$78.81** | **$118.34** | **$151.72** |
| Upside vs $103.84 | -24.1% | +14.0% | +46.1% |

**Fair value ponderado (40% / 40% / 20%) = $109.20**

> Justificación de los múltiplos terminales: ServiceNow cotiza hoy a 34.5× EV/EBITDA (sobre EBITDA reportado). Un grower de calidad que en el año 5 aún crece ~12-14% con 26%+ de margen EBITDA merece 20-25× (rango SaaS premium). El bear (19×) asume de-rating hacia software maduro; el bull (24×) asume que conserva la prima de compounder.

### Tabla de sensibilidad (base case: FV/acción)

| WACC \ EV/EBITDA | 18× | 20× | 22× | 24× | 26× |
|-------------------|------|------|------|------|------|
| **9.0%** | $104 | $114 | $123 | $133 | $143 |
| **9.5%** | $102 | $112 | $121 | $130 | $140 |
| **10.0%** | $100 | $109 | **$118** | $127 | $137 |
| **10.5%** | $98 | $107 | $116 | $125 | $134 |
| **11.0%** | $96 | $105 | $113 | $122 | $131 |
| **11.5%** | $94 | $103 | $111 | $120 | $128 |

### Análisis de impacto: ¿qué mueve el precio?

La variable más sensible es, con diferencia, **el múltiplo terminal**: cada 2× de EV/EBITDA mueve el fair value ~$9-10/acción (≈9% del precio). El WACC es secundario (±0.5% mueve ~$2-3). Esto **no es casualidad**: el valor terminal pesa el **~87% del EV** en todos los escenarios —típico de un compounder de alto crecimiento—. La implicación incómoda: **estoy valorando, en gran parte, la persistencia del múltiplo premium de ServiceNow.**

### Reverse DCF: ¿qué descuenta el precio?

Invirtiendo el modelo, **a $103.84 el mercado descuenta solo ~13.8% de crecimiento anual** (5 años) con mis márgenes, WACC y múltiplo base. Mi base asume **16.6%** —2.8 puntos por encima—, y **ahí vive el margen de seguridad**. ¿Está justificado ese exceso? La dirección **guía FY26 a +20.5-21%** en suscripción, el CAGR histórico a 3 años es **22.4%**, y el RPO de $28.2 B (+27%) da visibilidad a 2 años. Es decir: **el mercado está extrapolando una desaceleración brusca (hacia ~14%) que ni la guía ni el backlog respaldan todavía.** Si ServiceNow simplemente cumple su propia guía y desacelera de forma ordenada, bate el crecimiento implícito en el precio. Ese es, en una frase, el caso alcista: *no necesitas que la IA sea un milagro, solo que el miedo a la "seat compression" esté exagerando la desaceleración.*

### Sanity checks (y la advertencia honesta)

1. ✅ **Bull/Bear ratio = 1.93×** (dentro de 1.5-2.0×).
2. ⚠️ **Bear a -24%** (fuera del ±15% de la regla). Justificado: en un valor de múltiplo alto el bear debe doler de verdad, y aquí el riesgo de seat compression por IA es estructural, no cíclico. Mantengo el bear "duro" deliberadamente.
3. ⚠️ **TV = ~87% del EV.** Validación Gordon Growth (g=3%): el valor terminal por Gordon sería ~45% inferior al de exit-multiple. **Con un terminal Gordon, el base case caería a ~$67** (cerca del bear). Esto es el corazón del riesgo: si ServiceNow **no** retiene una prima de múltiplo —porque la IA lo convierte en software "commodity"— el valor real está más cerca de $70-80 que de $118. El exit-multiple de 22× es defendible *solo si* uno cree que en el año 5 todavía crece doble dígito con moat intacto.
4. ✅ **Crecimiento base (Y1 22%) = guía de la dirección**; CAGR 5 años (16.6%) por debajo del histórico (22.4%) → conservador.
5. ⚠️ **P/E implícito elevado** (~40-45× sobre owner earnings normalizados). Alto, pero coherente con un compounder de calidad superior.
6. **Consenso: $141.86** (high $236, low $85). Mi ponderado ($109) queda un 23% por debajo —por la metodología SBC—. Cómodo dentro del rango; no es un outlier.

---

## 5. Riesgos principales

| # | Riesgo | Severidad | Probabilidad | Comentario |
|---|--------|-----------|--------------|------------|
| 1 | **Seat compression por IA agéntica** | Alta | Media | El núcleo de la tesis bajista. Si los agentes reducen los asientos humanos, el modelo per-seat se erosiona antes de que el pricing-por-consumo lo compense. Es un riesgo de *transición*, no necesariamente terminal, pero puede comprimir crecimiento **y** múltiplo a la vez. |
| 2 | **Compresión de múltiplo / de-rating** | Alta | Media-Alta | El 87% del valor es terminal. El mercado ya pasó de "premium perpetuo" a dudar. Si el de-rating de SaaS continúa, el dolor llega vía múltiplo aunque los fundamentales aguanten. |
| 3 | **Erosión de margen bruto por compute de IA** | Media | Alta (ya ocurriendo) | GM de suscripción 82%→80% y bajando. El compute de IA de terceros traslada coste al P&L; el pricing-por-consumo aún no compensa del todo. |
| 4 | **SBC y dilución** | Media | Alta (estructural) | ~14-16% de los ingresos en SBC. El "FCF" reportado sobreestima el owner earnings; la recompra apenas tapa la dilución. Riesgo de que el mercado "despierte" a esto en un entorno risk-off. |
| 5 | **Valoración aún exigente** | Media | Media | Incluso tras el -50%, a 23× P/FCF y 34× EV/EBITDA reportado no es barata en absoluto; cualquier miss de guía castiga con fuerza (ya pasó: -14% post-Q1 pese al beat). |

---

## 6. Catalizadores (12-24 meses)

**Positivos:**
- **Now Assist supera los $1.500 M de ACV de IA en 2026** (guía de McDermott, +50% sobre la previsión anterior). Los clientes Now Assist >$1 M ACV **crecieron +130% YoY** —evidencia temprana de que ServiceNow *monetiza* la IA en vez de ser desplazado por ella.
- **Prueba de que la IA expande, no comprime:** si el ACV por cliente sube con agentes (más workflows orquestados), se invalida el bear y el múltiplo se recupera.
- Integración de Armis (seguridad) y datos (Workflow Data Fabric) ampliando TAM.
- Un simple cambio de sentimiento macro/risk-on en software re-califica al líder de calidad primero.

**Negativos:**
- Cualquier recorte de guía o desaceleración de cRPO por debajo del ~20% confirmaría el bear y dispararía más de-rating.
- Nuevos lanzamientos de competidores de IA (Microsoft Copilot, Salesforce Agentforce, hyperscalers) que erosionen el caso de uso.
- Continuación del selloff de software por miedo agéntico (riesgo de "value trap" temporal).

---

## 7. Conclusión y plan de acción

ServiceNow es **un negocio de calidad excepcional** —98% de renovación, $28 B de RPO, plataforma con wide moat— que el mercado está vendiendo por un **miedo legítimo pero posiblemente exagerado**: que la IA agéntica destruya el modelo per-seat. La evidencia temprana (Q1 beat, guía subida, Now Assist +130%) apunta a que ServiceNow es más probablemente **el orquestador de los agentes que su víctima**. Pero el riesgo es real y bidireccional, y por eso el rango bear-bull es ancho.

**Mi número honesto, descontando el SBC como coste real, es $109 — apenas un 5% sobre los $104 de hoy.** En términos de Graham, el margen de seguridad es demasiado fino para una compra agresiva. La brecha con el consenso ($142) es metodológica, no de tesis: si uno acepta valorar sobre FCF reportado, la acción parece un 25-35% infravalorada; si uno expensa el SBC (mi postura), está en valor justo.

**Señal: ⚪ VALOR JUSTO (sesgo ligeramente positivo).**

**Plan de acción:**
- **Iniciar posición pequeña (1/3 del tamaño objetivo) a precio actual** para tener exposición a una de las mejores franquicias de software a su valoración más barata en años.
- **Ampliar agresivamente por debajo de ~$90** (donde el margen de seguridad supera el 20% incluso descontando SBC), y **cargar fuerte hacia $78-80** (zona bear), donde se compraría calidad de primer nivel a precio de software maduro.
- **No perseguir hacia arriba de $120** sin nueva evidencia de que la IA reacelera el ACV (catalizador #1).
- **Tesis se invalida si:** el cRPO desacelera por debajo del 18% dos trimestres seguidos, o el margen bruto de suscripción cae por debajo del 76% sin compensación en crecimiento → el bear se materializaría y el suelo estaría más cerca de $70.

> Negocio de 10. Precio de 6. Paciencia: esta es de las que el mercado, tarde o temprano, vuelve a pagar a múltiplo premium —pero hay que comprarla con margen, no con fe.

---

### Fuentes

- ServiceNow 10-K FY2025 (SEC, filing 2026): renovación 98%, RPO $28.2 B, GM suscripción 80%, reexpresión por split.
- ServiceNow 8-K Q1 FY2026 (22-abr-2026): suscripción $3,671 M (+22%), guía FY26 subida a $15.74-15.78 B.
- SEC audit interno: discrepancia EBITDA (SEC calc $2,562 M vs Yahoo $3,022 M, +15.2%) por tratamiento de ajustes/SBC.
- Fortune, CNBC, Motley Fool, Seeking Alpha, TIKR (abr-may 2026): selloff de software, narrativa anti-SaaS / seat compression, -45/52% en 6 meses, Now Assist +130% YoY, guía de $1.500 M en IA.
- Datos de mercado: `data/valuations/NOW/NOW_valuation.json` (11-jun-2026).

*Documento de análisis de inversión. No es recomendación personalizada. Elaborado para uso propio.*
