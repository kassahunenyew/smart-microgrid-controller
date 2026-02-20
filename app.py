import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="AI Smart Microgrid Controller",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0a1628;
    color: #e8edf5;
}

.stApp { background: #0a1628; }

section[data-testid="stSidebar"] {
    background: #0d1f3c;
    border-right: 1px solid #1a3a6b;
}

/* Sidebar text */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] div {
    color: #c8d8f0 !important;
}

/* Title */
h1 { color: #f0c040 !important; font-weight: 700 !important; }
h2, h3 { color: #f0c040 !important; }

/* Metric labels and values */
[data-testid="stMetricLabel"] { color: #8aaad0 !important; font-size: 0.8rem !important; }
[data-testid="stMetricValue"] { color: #f0c040 !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] { color: #4ecf8a !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #0d1f3c;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #8aaad0;
    border-radius: 8px;
    font-weight: 500;
    font-size: 0.85rem;
    padding: 8px 20px;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1a3a6b, #0d2a52) !important;
    color: #f0c040 !important;
    border-bottom: 2px solid #f0c040 !important;
}

/* Sidebar success */
.stSuccess {
    background: rgba(78, 207, 138, 0.1) !important;
    border: 1px solid #4ecf8a !important;
    color: #4ecf8a !important;
}

/* Dataframe */
.stDataFrame { border: 1px solid #1a3a6b !important; border-radius: 10px; }

/* Divider */
hr { border-color: #1a3a6b !important; }

/* Slider track and thumb */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: #f0c040 !important;
    border-color: #f0c040 !important;
}

.stSlider [data-baseweb="slider"] div[data-testid="stSlider"] {
    color: #f0c040 !important;
}

div[data-baseweb="slider"] > div > div > div {
    background: linear-gradient(90deg, #f0c040, #d4a017) !important;
}

div[data-baseweb="slider"] > div > div > div:last-child {
    background: #1a3a6b !important;
}

div[data-baseweb="slider"] [role="slider"] {
    background: #f0c040 !important;
    border: 3px solid #d4a017 !important;
    box-shadow: 0 0 8px rgba(240,192,64,0.5) !important;
}

/* Selectbox */
.stSelectbox div[data-baseweb="select"] > div {
    background: #0d2a52 !important;
    border-color: #1a3a6b !important;
    color: #e8edf5 !important;
}

#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────
BATTERY_CAPACITY = 10.0
PANEL_AREA       = 20.0
EFFICIENCY       = 0.20
ETA              = 0.95
P_MAX            = 2.0

NAVY    = "#0d2a52"
GOLD    = "#f0c040"
GOLD2   = "#d4a017"
BLUE1   = "#1a5fa8"
BLUE2   = "#2979c8"
GREEN   = "#4ecf8a"
RED     = "#e05555"
SILVER  = "#8aaad0"

def get_tou_price(hour):
    if hour >= 23 or hour < 7:  return 0.15
    elif 7 <= hour < 17:        return 0.25
    else:                       return 0.45

def radiation_to_kw(r):
    return max((r * PANEL_AREA * EFFICIENCY) / 1000, 0.0)

def rule_based_action(battery, solar_kw, demand):
    if solar_kw > demand and battery < BATTERY_CAPACITY * 0.9: return 2
    elif battery > BATTERY_CAPACITY * 0.2 and demand > 1.5:   return 4
    return 0

def simulate_week(df, start_idx, controller="Rule-Based", battery_init=5.0):
    battery = battery_init
    records = []
    total_cost = 0.0
    for i in range(168):
        row       = df.iloc[start_idx + i]
        solar_rad = float(row["shortwave_radiation"])
        demand    = float(row["Global_active_power"])
        hour      = int(row["hour"])
        price     = get_tou_price(hour)
        solar_kw  = radiation_to_kw(solar_rad)
        solar_used = min(solar_kw, demand)
        remaining  = demand - solar_used
        surplus    = solar_kw - solar_used
        action = rule_based_action(battery, solar_kw, demand) if controller == "Rule-Based" else 0
        grid_import=export=soc_change=charge_from_solar=0.0
        if action == 0:
            grid_import=remaining; export=surplus
        elif action in [1,2]:
            power=1.0 if action==1 else P_MAX
            space_soc=BATTERY_CAPACITY-battery
            charge_in=max(min(power,space_soc/ETA),0.0)
            soc_change=charge_in*ETA; battery+=soc_change
            charge_from_solar=min(surplus,charge_in)
            grid_import=remaining+max(charge_in-charge_from_solar,0.0)
            export=surplus-charge_from_solar
        elif action in [3,4]:
            power=1.0 if action==3 else P_MAX
            soc_drop=max(min(min(power,remaining)/ETA,battery),0.0)
            soc_change=soc_drop; battery-=soc_drop
            grid_import=max(remaining-soc_drop*ETA,0.0); export=surplus
        battery=np.clip(battery,0,BATTERY_CAPACITY)
        cost=grid_import*price - export*0.10 + 0.01*soc_change
        total_cost+=cost
        records.append({"hour":i,"solar_kw":round(solar_kw,3),
                        "demand_kw":round(demand,3),"battery_soc":round(battery,3),
                        "grid_import":round(grid_import,3),"export":round(export,3),
                        "price":price,"cost":round(cost,4),"action":action})
    return pd.DataFrame(records), round(total_cost, 2)

@st.cache_data
def load_data():
    import requests, zipfile, io
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {"latitude":40.71,"longitude":-74.01,"start_date":"2023-01-01",
              "end_date":"2023-12-31",
              "hourly":["shortwave_radiation","temperature_2m","cloudcover","windspeed_10m"]}
    df_solar = pd.DataFrame(requests.get(url,params=params).json()["hourly"])
    df_solar["time"] = pd.to_datetime(df_solar["time"])
    df_solar.set_index("time", inplace=True)
    url2 = "https://archive.ics.uci.edu/ml/machine-learning-databases/00235/household_power_consumption.zip"
    with zipfile.ZipFile(io.BytesIO(requests.get(url2).content)) as z:
        with z.open("household_power_consumption.txt") as f:
            df_e = pd.read_csv(f,sep=";",na_values="?",
                               parse_dates={"datetime":["Date","Time"]},dayfirst=True)
    df_e.set_index("datetime", inplace=True)
    df_e = df_e[["Global_active_power"]].dropna().resample("h").mean()
    df_e = df_e[~((df_e.index.month==2)&(df_e.index.day==29))]
    df_e.index = df_e.index.map(lambda x: x.replace(year=2023))
    df_e = df_e[~df_e.index.duplicated(keep="first")]
    df = df_solar.join(df_e,how="inner").dropna()
    df["hour"]=df.index.hour; df["day_of_week"]=df.index.dayofweek
    df["month"]=df.index.month; df["is_weekend"]=df["day_of_week"].isin([5,6]).astype(int)
    df["energy_lag_1h"]=df["Global_active_power"].shift(1)
    df["energy_lag_24h"]=df["Global_active_power"].shift(24)
    df["energy_rolling_24h"]=df["Global_active_power"].rolling(24).mean()
    return df.dropna().reset_index(drop=True)

# ── Plotly base theme ─────────────────────────────────────────────
def base_layout(title="", height=500):
    return dict(
        height=height, title=dict(text=title, font=dict(color=GOLD, size=14)),
        paper_bgcolor="#0a1628", plot_bgcolor="#0d1f3c",
        font=dict(family="Inter", color=SILVER, size=11),
        legend=dict(bgcolor="rgba(13,31,60,0.8)", bordercolor="#1a3a6b",
                    borderwidth=1, font=dict(color=SILVER)),
        margin=dict(l=10,r=10,t=50,b=10),
        hovermode="x unified",
        xaxis=dict(gridcolor="#1a3a6b", linecolor="#1a3a6b", zeroline=False),
        yaxis=dict(gridcolor="#1a3a6b", linecolor="#1a3a6b", zeroline=False),
    )

def style_fig(fig, title="", height=500):
    fig.update_layout(**base_layout(title, height))
    fig.update_xaxes(gridcolor="#1a3a6b", linecolor="#1a3a6b", zeroline=False)
    fig.update_yaxes(gridcolor="#1a3a6b", linecolor="#1a3a6b", zeroline=False)
    for ann in fig.layout.annotations:
        ann.font.color  = GOLD
        ann.font.size   = 12
        ann.font.family = "Inter"
    return fig

# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
st.sidebar.header("⚙️ Configuration")
st.sidebar.markdown("---")

with st.spinner("📡 Loading energy data..."):
    df = load_data()

st.sidebar.success(f"✅ Data loaded: {len(df):,} hours")

max_start    = len(df) - 168 - 1
week_start   = st.sidebar.slider("Select Week Start (hour)", 0, max_start, 1000, 168)
controller   = st.sidebar.selectbox("Controller", ["Rule-Based", "No Battery"])
battery_init = st.sidebar.slider("Initial Battery (kWh)", 0.0, 10.0, 5.0, 0.5)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Results Summary")

# ── Simulate ──────────────────────────────────────────────────────
df_sim, cost    = simulate_week(df, week_start, controller, battery_init)
df_nb,  cost_nb = simulate_week(df, week_start, "No Battery", battery_init)
savings     = cost_nb - cost
savings_pct = (savings / cost_nb * 100) if cost_nb > 0 else 0
grid_red    = ((df_nb.grid_import.sum()-df_sim.grid_import.sum()) /
                df_nb.grid_import.sum()*100) if df_nb.grid_import.sum()>0 else 0

st.sidebar.metric("Weekly Cost",     f"${cost:.2f}",  f"-${savings:.2f} vs No Battery")
st.sidebar.metric("Grid Import",     f"{df_sim.grid_import.sum():.1f} kWh")
st.sidebar.metric("Solar Generated", f"{df_sim.solar_kw.sum():.1f} kWh")
st.sidebar.metric("Energy Exported", f"{df_sim.export.sum():.1f} kWh")

# ══════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════
st.title("⚡ AI-Powered Smart Microgrid Controller")
st.markdown(
    f'<p style="color:{SILVER}; font-size:1rem; margin-top:-10px">'
    'Reinforcement Learning for optimal battery dispatch and energy cost reduction</p>',
    unsafe_allow_html=True)

# ── KPI row ───────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Weekly Cost",     f"${cost:.2f}",
            f"{savings_pct:.1f}% better than No Battery")
col2.metric("🔋 Avg Battery SoC", f"{df_sim.battery_soc.mean():.1f} kWh",
            f"Max {df_sim.battery_soc.max():.1f} kWh")
col3.metric("☀️ Solar Generated", f"{df_sim.solar_kw.sum():.1f} kWh")
col4.metric("🔌 Grid Import",     f"{df_sim.grid_import.sum():.1f} kWh",
            f"{grid_red:.1f}% vs No Battery")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "⚡ Energy Flow", "🔋 Battery", "💰 Cost", "📊 Comparison"
])

with tab1:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=("Solar Generation vs Demand (kW)",
                                        "Grid Import & Export (kWh)"),
                        vertical_spacing=0.12)
    fig.add_trace(go.Scatter(x=df_sim.hour, y=df_sim.solar_kw, name="☀️ Solar",
                             fill="tozeroy", fillcolor="rgba(240,192,64,0.15)",
                             line=dict(color=GOLD, width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_sim.hour, y=df_sim.demand_kw, name="🏠 Demand",
                             line=dict(color=BLUE2, width=2.5)), row=1, col=1)
    fig.add_trace(go.Bar(x=df_sim.hour, y=df_sim.grid_import, name="🔴 Grid Import",
                         marker_color=RED, opacity=0.8), row=2, col=1)
    fig.add_trace(go.Bar(x=df_sim.hour, y=df_sim.export, name="🟢 Export",
                         marker_color=GREEN, opacity=0.8), row=2, col=1)
    fig.update_layout(barmode="group")
    style_fig(fig, "Energy Flow — Selected Week", 500)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                         subplot_titles=("Battery State of Charge (kWh)",
                                         "TOU Electricity Price ($/kWh)"),
                         vertical_spacing=0.12)
    fig2.add_trace(go.Scatter(x=df_sim.hour, y=df_sim.battery_soc, name="🔋 SoC",
                              fill="tozeroy", fillcolor="rgba(26,95,168,0.2)",
                              line=dict(color=BLUE1, width=2.5)), row=1, col=1)
    fig2.add_hline(y=BATTERY_CAPACITY, line_dash="dash", line_color=RED,
                   annotation_text="Max Capacity",
                   annotation_font_color=RED, annotation_font_size=10,
                   row=1, col=1)
    # Color TOU bars by price tier
    price_colors = df_sim.price.map({0.15: GREEN, 0.25: GOLD, 0.45: RED})
    fig2.add_trace(go.Bar(x=df_sim.hour, y=df_sim.price, name="💲 TOU Price",
                          marker_color=price_colors, opacity=0.85), row=2, col=1)
    style_fig(fig2, "Battery SoC vs TOU Pricing", 500)
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    fig3 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                         subplot_titles=("Hourly Cost ($)",
                                         "Cumulative Cost — Controller vs No Battery ($)"),
                         vertical_spacing=0.12)
    fig3.add_trace(go.Bar(x=df_sim.hour, y=df_sim.cost, name="Hourly Cost",
                          marker_color=GOLD2, opacity=0.85), row=1, col=1)
    fig3.add_trace(go.Scatter(x=df_sim.hour, y=df_sim.cost.cumsum(),
                              name=f"🟡 {controller}", fill="tozeroy",
                              fillcolor="rgba(240,192,64,0.1)",
                              line=dict(color=GOLD, width=2.5)), row=2, col=1)
    fig3.add_trace(go.Scatter(x=df_nb.hour, y=df_nb.cost.cumsum(),
                              name="🔴 No Battery",
                              line=dict(color=RED, width=2, dash="dash")), row=2, col=1)
    style_fig(fig3, "Cost Analysis", 500)
    st.plotly_chart(fig3, use_container_width=True)

with tab4:
    controllers_list = ["No Battery", "Rule-Based"]
    costs_list = [cost_nb, cost]
    grid_list  = [df_nb.grid_import.sum(), df_sim.grid_import.sum()]

    fig4 = make_subplots(rows=1, cols=2,
                         subplot_titles=("Weekly Cost ($)", "Grid Import (kWh)"))
    fig4.add_trace(go.Bar(x=controllers_list, y=costs_list,
                          marker_color=[RED, GOLD],
                          text=[f"${c:.2f}" for c in costs_list],
                          textposition="outside",
                          textfont=dict(color=SILVER)), row=1, col=1)
    fig4.add_trace(go.Bar(x=controllers_list, y=grid_list,
                          marker_color=[RED, GOLD],
                          text=[f"{g:.1f}" for g in grid_list],
                          textposition="outside",
                          textfont=dict(color=SILVER)), row=1, col=2)
    fig4.update_layout(showlegend=False)
    style_fig(fig4, "Controller Comparison", 420)
    st.plotly_chart(fig4, use_container_width=True)

    st.markdown(
        f'<h3 style="color:{GOLD}">📋 Research Results — 10 Week Evaluation</h3>',
        unsafe_allow_html=True)
    results_data = {
        "Controller":    ["No Battery", "Rule-Based", "DQN (Best)"],
        "Avg Cost ($)":  [34.75,         31.76,        28.09],
        "Grid (kWh)":    [145.06,        131.58,       135.33],
        "Throughput":    [0.00,          59.36,        101.15],
        "vs Rule-Based": ["—",           "Baseline",   "✅ -11.5%"],
    }
    st.dataframe(pd.DataFrame(results_data), use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f'<p style="color:#2a4a6a; text-align:center; font-size:0.75rem">'
    'Built with · Python · Stable-Baselines3 DQN · OpenAI Gymnasium · '
    'Streamlit · Plotly · Open-Meteo API · UCI Energy Dataset</p>',
    unsafe_allow_html=True)