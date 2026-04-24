import streamlit as st
import plotly.graph_objects as go
import json
import pandas as pd
from asset_classes import *
from utils import get_current_weather
st.set_page_config(page_title="My Apartment Status", page_icon="🏢", layout="wide")


@st.cache_data(ttl=600, show_spinner=False)
def _get_outside_weather(location: tuple):
    return get_current_weather(location)


OUTSIDE_LOCATION = (45.6486, 25.6061)

st.markdown("""
    <style>
        .block-container { padding-top: 2rem; }
        h3 { font-size: 1.1rem !important; color: #333; font-weight: 600 !important; }
        p { margin-bottom: 0px !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOAD DATA
# ==========================================
with open("dummydata.json", "r") as file:
    data = json.load(file)

# ==========================================
# 3. HEADER
# ==========================================
st.title("Apartment Status")
st.write("")
tab1, tab2 = st.tabs(["📊 Current Status", "📈 Historical Data"])


## ==========================================
# TAB 1
# ==========================================

with tab1:
    # ==========================================
    # 4. DASHBOARD GRID
    # ==========================================
    # Top Row
    col1, col2 = st.columns(2)

    # --- CARD 1: LIGHT LEVEL ---
    with col1:
        with st.container(border=True):
            st.markdown("### ☀️ LIGHT LEVEL")
            
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = data["light"],
                number = {'suffix': " LUX", 'font': {'size': 40, 'color': "#bbbbbb", 'weight': 'bold'}},
                gauge = {
                    'axis': {'range': [None, 1000], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': "#cbd5e1"},
                    'bgcolor': "white",
                    'borderwidth': 0,
                    'steps': [
                        {'range': [0, data["light"]], 'color': '#a3e635'}
                    ],
                }
            ))
            
            fig.update_layout(height=220, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
            

            # if data["light"] < 100:
            #     st.markdown("<p style='text-align: center; color: #666;'>Dim, artificial light</p>", unsafe_allow_html=True)
            # else:
            #     st.markdown("<p style='text-align: center; color: #666;'>Bright, natural</p>", unsafe_allow_html=True)

    # --- CARD 2: AIR QUALITY ---
    with col2:
        with st.container(border=True):
            st.markdown("### ☁️ Gases in Room")
            aqi = data["gas"]
            
            if aqi <= 400:
                status, color, desc = "EXCELLENT", "#22c55e", "Fresh air, low particulates"
            elif aqi <= 800:
                status, color, desc = "MODERATE", "#eab308", "Acceptable air quality"
            elif aqi <= 1400:
                status, color, desc = "UNHEALTHY", "#f97316", "Noticeable pollution"
            else:
                status, color, desc = "HAZARDOUS", "#ef4444", "Emergency conditions!."

            custom_progress_bar(
                current = aqi,
                min_val = 200,
                max_val = 2200,
                color = color,
                height = "30px"
            )
            
            st.markdown(f"""
                <div style="display: flex; align-items: center; height: 165px; justify-content: center; flex-direction: column;">
                    <h1 style="color: {color}; font-size: 2.5rem; margin: 0;text-align: center">{status}</h1>
                    <p style="font-size: 1.2rem; color: #555; font-weight: bold; text-align: center">AQI {aqi}</p>
                </div>
                <p style="text-align: center; color: #666;">{desc}</p>
            """, unsafe_allow_html=True)

    st.write("")

    # Bottom Row
    col3, col4 = st.columns(2)

    with col3:
        with st.container(border=True):
            st.markdown("### 🌡️ TEMPERATURE")

            outside_temp_c = None
            try:
                outside_weather = _get_outside_weather(OUTSIDE_LOCATION)
                if outside_weather is not None:
                    outside_temp_c = outside_weather[0]
            except Exception:
                outside_temp_c = None
            if outside_temp_c is not None:
                temp_diff = data["temp"] - outside_temp_c
            
                if temp_diff >= 0:
                    outside_temp_html = f'<p style="text-align: center; color: #666; font-size: 1.1rem; margin: 0;">{temp_diff:.1f}° warmer than outside ({outside_temp_c}°C)</p>'
                else:
                    outside_temp_html = f'<p style="text-align: center; color: #666; font-size: 1.1rem; margin: 0;">{abs(temp_diff):.1f}° colder than outside ({outside_temp_c}°C)</p>'
            
            st.markdown(f"""
                <div style="height: 180px; display: flex; align-items: center; justify-content: center;">
                    <h1 style="font-size: 4.5rem; margin: 0; color: #333;">{data["temp"]} °C</h1>
                </div>
                {outside_temp_html}
                <p style="text-align: center; color: #666;">Stable in the last hour</p>
            """, unsafe_allow_html=True)

    # --- CARD 4: DOOR STATUS ---
    with col4:
        with st.container(border=True):
            st.markdown("### 🪟 WINDOW STATUS")
            
            is_open = data["window_open"]
            
            if is_open:
                icon = "🪟"
                bg_color = "#70f16c"
                text = "OPEN"
                desc = "Main window open."
            else:
                icon = "🪟"
                bg_color = "#eb5353"
                text = "CLOSED"
                desc = "Main window closed."
                
            st.markdown(f"""
                <div style="display: flex; align-items: center; justify-content: center; height: 180px; gap: 20px;">
                    <span style="font-size: 5rem;">{icon}</span>
                    <span style="background-color: {bg_color}; color: white; padding: 10px 25px; border-radius: 25px; font-weight: bold; font-size: 1.5rem; letter-spacing: 1px;">
                        {text}
                    </span>
                </div>
                <p style="text-align: center; color: #666;">{desc}</p>
            """, unsafe_allow_html=True)

with tab2:
    st.write("tab 2 yippie")

    with open("dummy_temp_history.json", "r") as file:
        temp_history_data = json.load(file)

    df = pd.DataFrame(temp_history_data)

    st.subheader("Raw Data Preview")
    st.dataframe(df) 

    display_historical_graph(
        df = df,
        date_column = "timestamp",
        metric_column = "temperature",
        title = "Historical Temp Data",
        line_color = "#f97316",
        fill_area = True,
        y_range=[0, 50]
    )