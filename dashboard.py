import streamlit as st
import plotly.graph_objects as go
import json
import time
from json import JSONDecodeError
from pathlib import Path
import pandas as pd
from asset_classes import *
from utils import get_current_weather
st.set_page_config(page_title="RoomSense", page_icon="🏢", layout="wide")


REFRESH_INTERVAL_MS = 3000
CURRENT_DATA_PATH = Path(__file__).with_name("current_data.json")
HISTORICAL_DATA_PATH = Path(__file__).with_name("historical_data.json")
DOOR_CURRENT_PATH = Path(__file__).with_name("door_current.json")
DOOR_EVENTS_PATH = Path(__file__).with_name("door_events.json")


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    raw = hex_color.strip().lstrip("#")
    if len(raw) != 6:
        raise ValueError(f"Expected 6-digit hex color, got: {hex_color!r}")
    return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _value_to_gradient_color(
    value: float,
    min_val: float,
    max_val: float,
    start_hex: str,
    end_hex: str,
) -> str:
    if max_val == min_val:
        return end_hex
    t = (value - min_val) / (max_val - min_val)
    t = _clamp(t, 0.0, 1.0)
    sr, sg, sb = _hex_to_rgb(start_hex)
    er, eg, eb = _hex_to_rgb(end_hex)
    rgb = (
        int(round(_lerp(sr, er, t))),
        int(round(_lerp(sg, eg, t))),
        int(round(_lerp(sb, eb, t))),
    )
    return _rgb_to_hex(rgb)


def _temperature_to_color(temp_c: float) -> str:
    """Map temperature (°C) to a readable color.

    Cold -> blue, comfortable -> green, hot -> red.
    """
    cold = 16.0
    comfy = 22.0
    hot = 30.0
    if temp_c <= comfy:
        return _value_to_gradient_color(temp_c, cold, comfy, "#3b82f6", "#22c55e")
    return _value_to_gradient_color(temp_c, comfy, hot, "#22c55e", "#ef4444")


def _build_notifications(
    *,
    current_data: dict,
    door_data: dict,
    outside_temp_c: float | None,
    outside_is_raining: bool | None,
    historical_data: dict | None,
) -> list[tuple[str, str]]:
    notifications: list[tuple[str, str]] = []

    def _num(value, default: float | None = None) -> float | None:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    gas = _num(current_data.get("gas"))
    oxygenation = _num(current_data.get("oxygenation"))
    light_lux = _num(current_data.get("light"))

    is_window_open = bool(door_data.get("window_open", current_data.get("window_open", False)))

    # 0) Close window if it's open and it's raining outside.
    if is_window_open and outside_is_raining is True:
        notifications.append(("error", "It's raining / It will rain outside and the window is open. It is recommended you close the window."))

    # 1) Close window if it's open and it's cold outside.
    if is_window_open and outside_temp_c is not None and outside_temp_c < 18:
        notifications.append(("warning", "Outside is under 18°C. Consider closing the window to not decrease room temperature."))

    # 2) Open window if it's closed and oxygenation drops.
    if (not is_window_open) and oxygenation is not None and oxygenation < 30:
        notifications.append(("warning", "Oxygenation is below 30. Open the window for better focus."))

    # 3-4) Open window if it's closed and gas is high.
    if (not is_window_open) and gas is not None:
        if gas > 50:
            notifications.append(("error", "Gas is over 50. Open the window immediately."))
        elif gas > 30:
            notifications.append(("warning", "Gas is over 30. Open the window."))

    # 5) Suggest turning off lights after 10pm when lux is high.
    if light_lux is not None and light_lux > 100 and time.localtime().tm_hour >= 22:
        notifications.append(("info", "It's after 10pm and the room is bright. Consider turning off the lights to avoid bad sleep quality."))

    return notifications


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
    # historical_data.json can be larger and is rewritten; give it a bit more time.
    data = _load_json_safely(HISTORICAL_DATA_PATH, retries=25, delay_s=0.05)
    if data is not None:
        st.session_state["_last_good_historical_data"] = data
        return data

    return st.session_state.get("_last_good_historical_data")


def _get_latest_door_current_data() -> dict | None:
    data = _load_json_safely(DOOR_CURRENT_PATH)
    if data is not None:
        st.session_state["_last_good_door_current"] = data
        return data
    return st.session_state.get("_last_good_door_current")


def _get_latest_door_events_data() -> dict | None:
    data = _load_json_safely(DOOR_EVENTS_PATH, retries=25, delay_s=0.05)
    if data is not None:
        st.session_state["_last_good_door_events"] = data
        return data
    return st.session_state.get("_last_good_door_events")


@st.cache_data(ttl=600, show_spinner=False)
def _get_outside_weather(location: tuple):
    return get_current_weather(location)


OUTSIDE_LOCATION = (45.6486, 25.6061)
#OUTSIDE_LOCATION = (4.6243, -74.0636) raining for testing

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
st.title("Room Status")
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

        door_data = _get_latest_door_current_data() or {}

        outside_temp_c: float | None = None
        outside_is_raining: bool | None = None
        try:
            outside_weather = _get_outside_weather(OUTSIDE_LOCATION)
            if outside_weather is not None:
                outside_temp_c = outside_weather[0]
                outside_is_raining = outside_weather[1]
        except Exception:
            outside_temp_c = None
            outside_is_raining = None

        historical_data = _get_latest_historical_data()

        with st.container(border=True):
            st.markdown("### 🔔 Notifications")
            notifications = _build_notifications(
                current_data=data,
                door_data=door_data,
                outside_temp_c=outside_temp_c,
                outside_is_raining=outside_is_raining,
                historical_data=historical_data,
            )

            for kind, message in notifications:
                if kind == "error":
                    st.error(message)
                elif kind == "warning":
                    st.warning(message)
                elif kind == "success":
                    st.success(message)
                else:
                    st.info(message)

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
                if outside_temp_c is not None:
                    temp_diff = data["temp"] - outside_temp_c
                
                    if temp_diff >= 0:
                        outside_temp_html = f'<p style="text-align: center; color: #666; font-size: 1.1rem; margin: 0;">{temp_diff:.1f}° warmer than outside ({outside_temp_c:.1f}°C)</p>'
                    else:
                        outside_temp_html = f'<p style="text-align: center; color: #666; font-size: 1.1rem; margin: 0;">{abs(temp_diff):.1f}° colder than outside ({outside_temp_c:.1f}°C)</p>'

                if outside_is_raining is True:
                    outside_rain_html = '<p style="text-align: center; color: #666; font-size: 1.0rem; margin: 0;">🌧️ Raining outside</p>'
                elif outside_is_raining is False:
                    outside_rain_html = '<p style="text-align: center; color: #666; font-size: 1.0rem; margin: 0;">☁️ No rain outside</p>'
                else:
                    outside_rain_html = '<p style="text-align: center; color: #666; font-size: 1.0rem; margin: 0;">☔ Rain status unavailable</p>'
                
                try:
                    temp_value = float(data["temp"])
                except (TypeError, ValueError):
                    temp_value = 0.0
                temp_color = _temperature_to_color(temp_value)

                st.markdown(f"""
                    <div style="height: 180px; display: flex; align-items: center; justify-content: center;">
                        <h1 style="font-size: 4.5rem; margin: 0; color: {temp_color};">{data["temp"]} °C</h1>
                    </div>
                    {outside_temp_html}
                    {outside_rain_html}
                """, unsafe_allow_html=True)

        # --- CARD 4: DOOR STATUS ---
        with col4:
            with st.container(border=True):
                st.markdown("### 🪟 WINDOW STATUS")

                # Door/window tracking is stored separately (door_current.json),
                # but keep a soft fallback for older files.
                is_open = bool(door_data.get("window_open", data.get("window_open", False)))
                oxygenation = data.get("oxygenation")
                if oxygenation is None:
                    oxygenation = 100 if is_open else 0
                
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
                """, unsafe_allow_html=True)

                st.caption("Oxygenation")

                oxygen_color = _value_to_gradient_color(
                    float(oxygenation),
                    0.0,
                    100.0,
                    "#ef4444",
                    "#22c55e",
                )
                custom_progress_bar(
                    current=oxygenation,
                    min_val=0,
                    max_val=100,
                    color=oxygen_color,
                    height="30px",
                )

                st.markdown(f"<p style=\"text-align: center; color: #666;\">{desc}</p>", unsafe_allow_html=True)

    _render_current_status()

with tab2:
    if hasattr(st, "fragment"):
        render_hist_decorator = st.fragment(run_every=f"{REFRESH_INTERVAL_MS}ms")
    else:
        try:
            from streamlit_autorefresh import st_autorefresh  # type: ignore

            st_autorefresh(interval=REFRESH_INTERVAL_MS, key="historical_data_autorefresh")
        except Exception:
            pass

        def render_hist_decorator(fn):
            return fn

    @render_hist_decorator
    def _render_historical_data() -> None:
        historical_data = _get_latest_historical_data()
        if not historical_data:
            st.info("No readable historical data yet (historical_data.json may still be updating).")
            return

        df = pd.DataFrame.from_dict(historical_data, orient="index")
        df.index.name = "timestamp"
        df = df.reset_index()

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

        door_events = _get_latest_door_events_data() or {}
        if isinstance(door_events, dict) and len(door_events) > 0:
            door_df = pd.DataFrame.from_dict(door_events, orient="index")
            door_df.index.name = "timestamp"
            door_df = door_df.reset_index()
            door_df["timestamp"] = pd.to_datetime(door_df["timestamp"], errors="coerce")
            door_df = door_df.dropna(subset=["timestamp"]).sort_values("timestamp")

            if "window_open" not in door_df.columns and "closed" in door_df.columns:
                door_df["window_open"] = ~door_df["closed"].astype(bool)

            if "window_open" in door_df.columns:
                door_df["window_open"] = door_df["window_open"].astype(bool)
                door_df = door_df.rename(columns={"window_open": "window_open_event"})
                df = pd.merge_asof(
                    df.sort_values("timestamp"),
                    door_df[["timestamp", "window_open_event"]].sort_values("timestamp"),
                    on="timestamp",
                    direction="backward",
                )

                if "window_open" in df.columns:
                    df["window_open"] = df["window_open_event"].combine_first(df["window_open"])
                else:
                    df["window_open"] = df["window_open_event"]

                df = df.drop(columns=["window_open_event"])

        if "window_open" in df.columns:
            df["window_open"] = df["window_open"].astype(int)

        metric_specs: list[tuple[str, str, str, bool]] = [
            ("temp", "🌡️ Temperature", "#f97316", True),
            ("humidity", "💧 Humidity", "#3b82f6", True),
            ("gas", "☁️ Gas", "#a855f7", True),
            ("light", "☀️ Light", "#eab308", True),
            ("oxygenation", "🫁 Oxygenation", "#22c55e", True),
        ]

        available_specs = [spec for spec in metric_specs if spec[0] in df.columns]
        if not available_specs:
            st.warning("historical_data.json has no recognized measurement columns.")
            return

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

    _render_historical_data()