import streamlit as st
import plotly.graph_objects as go
import json
from asset_classes import *
st.set_page_config(page_title="My Apartment Status", page_icon="🏢", layout="wide")

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
            st.markdown("### ☁️ AIR QUALITY")
            aqi = data["air"]
            
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
            
            st.markdown(f"""
                <div style="height: 180px; display: flex; align-items: center; justify-content: center;">
                    <h1 style="font-size: 4.5rem; margin: 0; color: #ffffff;">{data["temp"]} °C</h1>
                </div>
                <p style="text-align: center; color: ##ffffff;">Stable in the last hour</p>
            """, unsafe_allow_html=True)

    # --- CARD 4: DOOR STATUS ---
    with col4:
        with st.container(border=True):
            st.markdown("### 🚪 DOOR STATUS")
            
            is_open = data["door_open"]
            
            if is_open:
                icon = "🚪"
                bg_color = "#f97316"
                text = "OPEN"
                desc = "Main entrance, currently open!"
            else:
                icon = "🚪"
                bg_color = "#22c55e"
                text = "CLOSED"
                desc = "Main entrance, securely closed."
                
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

    dates = pd.date_range(end=pd.Timestamp.today(), periods=30, freq='D')
    mock_df = pd.DataFrame({
        "Date": dates,
        "Temperature (°C)": np.random.normal(loc=22, scale=2, size=30),
        "Air Quality (AQI)": np.random.normal(loc=120, scale=30, size=30)
    })

    display_historical_graph(
        df=mock_df,
        date_column="Date",
        metric_column="Air Quality (AQI)",
        title="30-Day AQI Trend",
        line_color="#3b82f6", 
        fill_area=True
    )