import streamlit as st
import plotly.graph_objects as go
import json
import time
from json import JSONDecodeError
from pathlib import Path
import pandas as pd
from asset_classes import *
from utils import get_current_weather
st.set_page_config(page_title="My Apartment Status", page_icon="🏢", layout="wide")


REFRESH_INTERVAL_MS = 3000
CURRENT_DATA_PATH = Path(__file__).with_name("current_data.json")
HISTORICAL_DATA_PATH = Path(__file__).with_name("historical_data.json")


def _load_json_safely(path: Path, *, retries: int = 5, delay_s: float = 0.05) -> dict | None:
    """Read JSON that may be rewritten frequently (avoid crashes on partial writes)."""
    for attempt in range(retries):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, JSONDecodeError):
            if attempt == retries - 1:
                return None
            time.sleep(delay_s)


def _get_latest_current_data() -> dict | None:
    """Return the latest readable current data, falling back to last good value."""
    data = _load_json_safely(CURRENT_DATA_PATH)
    if data is not None:
        st.session_state["_last_good_current_data"] = data
        return data

    return st.session_state.get("_last_good_current_data")


def _get_latest_historical_data() -> dict | None:
    """Return the latest readable historical data, falling back to last good value."""
    data = _load_json_safely(HISTORICAL_DATA_PATH)
    if data is not None:
        st.session_state["_last_good_historical_data"] = data
        return data

    return st.session_state.get("_last_good_historical_data")


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
# 3. HEADER
# ==========================================
st.title("Apartment Status")
st.write("")
tab1, tab2 = st.tabs(["📊 Current Status", "📈 Historical Data"])


## ==========================================
# TAB 1
# ==========================================

with tab1:
    if hasattr(st, "fragment"):
        render_decorator = st.fragment(run_every=f"{REFRESH_INTERVAL_MS}ms")
    else:
        try:
            from streamlit_autorefresh import st_autorefresh  # type: ignore

            st_autorefresh(interval=REFRESH_INTERVAL_MS, key="current_status_autorefresh")
        except Exception:
            pass

        def render_decorator(fn):
            return fn

    @render_decorator
    def _render_current_status() -> None:
        data = _get_latest_current_data()
        if data is None:
            st.info("Waiting for readable current data (current_data.json is updating).")
            return

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
                        'axis': {'range': [0, 500], 'tickwidth': 1, 'tickcolor': "darkblue"},
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
                
                if aqi <= 10:
                    status, color, desc = "EXCELLENT", "#22c55e", "Fresh air, low particulates"
                elif aqi <= 30:
                    status, color, desc = "MODERATE", "#eab308", "Acceptable air quality"
                elif aqi <= 50:
                    status, color, desc = "UNHEALTHY", "#f97316", "Noticeable pollution"
                else:
                    status, color, desc = "HAZARDOUS", "#ef4444", "Emergency conditions!."

                custom_progress_bar(
                    current = aqi,
                    min_val = 0,
                    max_val = 100,
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

                outside_temp_html = ""
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

    _render_current_status()

with tab2:
    historical_data = _get_latest_historical_data()
    if not historical_data:
        st.info("No readable historical data yet (historical_data.json may still be updating).")
    else:
        df = pd.DataFrame.from_dict(historical_data, orient="index")
        df.index.name = "timestamp"
        df = df.reset_index()

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

        if "window_open" in df.columns:
            df["window_open"] = df["window_open"].astype(int)

        metric_specs: list[tuple[str, str, str, bool]] = [
            ("temp", "🌡️ Temperature", "#f97316", True),
            ("humidity", "💧 Humidity", "#3b82f6", True),
            ("gas", "☁️ Gas", "#a855f7", True),
            ("light", "☀️ Light", "#eab308", True),
            ("window_open", "🪟 Window Open (0/1)", "#22c55e", False),
        ]

        # Only render metrics that are present in the file.
        available_specs = [spec for spec in metric_specs if spec[0] in df.columns]
        if not available_specs:
            st.warning("historical_data.json has no recognized measurement columns.")
        else:
            col_left, col_right = st.columns(2)
            for idx, (metric_col, title, color, fill_area) in enumerate(available_specs):
                target_col = col_left if idx % 2 == 0 else col_right
                with target_col:
                    with st.container(border=True):
                        display_historical_graph(
                            df=df,
                            date_column="timestamp",
                            metric_column=metric_col,
                            title=title,
                            line_color=color,
                            fill_area=fill_area,
                        )

            with st.expander("Raw historical data"):
                st.dataframe(df, use_container_width=True)