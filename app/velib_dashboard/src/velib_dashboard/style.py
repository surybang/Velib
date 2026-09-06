"""Palette et CSS aux couleurs Vélib'.

Vélib' : turquoise #5BC8C8, gris anthracite #3D3D3D, blanc cassé #F5F5F5.
Le CSS est injecté via st.markdown.
"""

VELIB_TEAL = "#5BC8C8"
VELIB_DARK = "#3D3D3D"
VELIB_LIGHT = "#F5F5F5"
VELIB_ORANGE = "#E8834A"  # ruptures / alertes
VELIB_BLUE = "#3D6B8C"  # stations pleines


def marker_color(occupancy: float | None) -> str:
    """Couleur d'un marqueur de carte selon le taux d'occupation."""
    if occupancy is None:
        return "#999999"
    if occupancy == 0:
        return VELIB_ORANGE  # vide
    if occupancy < 20:
        return "#F0A500"  # presque vide
    if occupancy > 90:
        return VELIB_BLUE  # presque plein
    return VELIB_TEAL  # ok


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    background-color: {VELIB_LIGHT};
}}

[data-testid="stSidebar"] {{
    background-color: {VELIB_DARK};
}}
[data-testid="stSidebar"] * {{
    color: white !important;
}}

h1 {{
    color: {VELIB_DARK};
    font-weight: 700;
    border-bottom: 3px solid {VELIB_TEAL};
    padding-bottom: 0.4rem;
}}
h2, h3 {{ color: {VELIB_DARK}; font-weight: 600; }}

.metric-card {{
    background: white;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    border-left: 4px solid {VELIB_TEAL};
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    margin-bottom: 0.5rem;
}}
.metric-card.alert {{ border-left-color: {VELIB_ORANGE}; }}
.metric-value {{
    font-size: 2rem;
    font-weight: 700;
    color: {VELIB_DARK};
    line-height: 1.1;
}}
.metric-label {{
    font-size: 0.78rem;
    color: #777;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.3rem;
}}

.meteo-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: white;
    border-radius: 20px;
    padding: 0.35rem 0.9rem;
    font-size: 0.85rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    margin-right: 0.5rem;
}}

.stButton > button {{
    background-color: {VELIB_TEAL};
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
}}
.stButton > button:hover {{ background-color: #4ab5b5; }}
</style>
"""


def metric_card(value: str, label: str, alert: bool = False) -> str:
    cls = "metric-card alert" if alert else "metric-card"
    return f"""
    <div class="{cls}">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """
