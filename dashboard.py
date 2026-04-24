import streamlit as st
import plotly.graph_objects as go
import json
import time
import math
import os
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
OXYGEN_OVERRIDE_PATH = Path(__file__).with_name("oxygen_override.json")


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


def _predict_room_temp_after_minutes(
    *,
    inside_temp_c: float | None,
    outside_temp_c: float | None,
    wind_speed_m_s: float | None,
    t_minutes: float,
    volume_m3: float = 30.0,
    window_open_area_m2: float = 0.5,
    discharge_coeff: float = 0.6,
    thermal_mass_factor: float = 20.0,  # Slows down cooling to account for walls/furniture
) -> float | None:
    """Predict inside temperature after t_minutes with window open.

    Uses a simple exponential approach-to-outside model:
        T(t) = T_out + (T_in - T_out) * exp(-k * t)
        k = ((A * v * C_d) / V) / thermal_mass_factor

    Assumptions:
    - wind_speed_m_s in m/s
    - t_minutes in minutes
    - volume in m^3, window area in m^2
    """
    if inside_temp_c is None or outside_temp_c is None or wind_speed_m_s is None:
        return None

    try:
        inside = float(inside_temp_c)
        outside = float(outside_temp_c)
        wind = float(wind_speed_m_s)
    except (TypeError, ValueError):
        return None

    if volume_m3 <= 0 or window_open_area_m2 <= 0 or discharge_coeff <= 0 or t_minutes < 0:
        return None
    if wind < 0:
        return None

    if thermal_mass_factor <= 0:
        return None

    t_seconds = t_minutes * 60.0

    # Calculate the raw air exchange rate
    raw_k = (window_open_area_m2 * wind * discharge_coeff) / volume_m3

    # Dampen the rate to account for the room's thermal mass
    realistic_k = raw_k / thermal_mass_factor

    return outside + (inside - outside) * math.exp(-realistic_k * t_seconds)


def _time_to_reach_target_temp_minutes(
    *,
    inside_temp_c: float | None,
    outside_temp_c: float | None,
    wind_speed_m_s: float | None,
    target_temp_c: float,
    volume_m3: float = 30.0,
    window_open_area_m2: float = 0.5,
    discharge_coeff: float = 0.6,
    thermal_mass_factor: float = 20.0,
) -> float | None:
    """Return minutes to reach target_temp_c while window is open.

    Uses the same model as `_predict_room_temp_after_minutes`.
    Returns None if the target is not reachable (asymptotic/outside conditions) or inputs missing.
    """
    if inside_temp_c is None or outside_temp_c is None or wind_speed_m_s is None:
        return None

    try:
        inside = float(inside_temp_c)
        outside = float(outside_temp_c)
        wind = float(wind_speed_m_s)
        target = float(target_temp_c)
    except (TypeError, ValueError):
        return None

    if volume_m3 <= 0 or window_open_area_m2 <= 0 or discharge_coeff <= 0:
        return None
    if wind < 0 or thermal_mass_factor <= 0:
        return None

    delta0 = inside - outside
    if abs(delta0) < 1e-9:
        # No temperature evolution in this model (already at outside temp).
        return None

    raw_k = (window_open_area_m2 * wind * discharge_coeff) / volume_m3
    realistic_k = raw_k / thermal_mass_factor
    if realistic_k <= 0:
        return None

    ratio = (target - outside) / delta0
    # If already at target (within tolerance), return 0.
    if abs(target - inside) <= 0.05:
        return 0.0

    # Target must be between current temp and outside temp to be reachable.
    # ratio in (0, 1) => reachable in finite time.
    if ratio <= 0.0 or ratio >= 1.0:
        return None

    t_seconds = -math.log(ratio) / realistic_k
    if t_seconds < 0:
        return None
    return t_seconds / 60.0


def _format_minutes_duration(minutes: float) -> str:
    if minutes < 0:
        return "—"
    if minutes < 60:
        return f"{minutes:.0f} min"
    return f"{minutes / 60.0:.1f} h"


def _format_temp_delta_html(delta_c: float | None, *, font_size: str = "1.2rem") -> str:
    """Return a colored (↑/↓) delta snippet like '(↓ 1.2°)'."""
    if delta_c is None:
        return ""
    try:
        delta = float(delta_c)
    except (TypeError, ValueError):
        return ""

    if abs(delta) < 0.1:
        return ""

    if delta < 0:
        arrow = "↓"
        color = "#3b82f6"  # cooling
    else:
        arrow = "↑"
        color = "#ef4444"  # warming

    return (
        f'<span style="color: {color}; font-size: {font_size}; margin-left: 0.35rem;">'
        f'({arrow} {abs(delta):.1f}°)'
        f"</span>"
    )


def _recent_trend_delta(
    historical_data: dict | None,
    *,
    metric_key: str,
    points_back: int = 5,
) -> float | None:
    """Estimate recent trend using last value vs a few points back."""
    if not historical_data or not isinstance(historical_data, dict):
        return None

    series: list[float] = []
    # Keys are ISO timestamps; lexicographic sort works.
    for ts in sorted(historical_data.keys()):
        row = historical_data.get(ts)
        if not isinstance(row, dict):
            continue
        val = row.get(metric_key)
        try:
            if val is None:
                continue
            series.append(float(val))
        except (TypeError, ValueError):
            continue

    if len(series) < 2:
        return None

    idx = max(0, len(series) - 1 - max(1, min(points_back, len(series) - 1)))
    return series[-1] - series[idx]


def _light_context_icon(light_lux: float | None, *, hour_24: int) -> str:
    if light_lux is None:
        return ""
    try:
        lux = float(light_lux)
    except (TypeError, ValueError):
        return ""

    is_night = hour_24 >= 20 or hour_24 < 6
    is_high = lux >= 150
    if lux < 100:
        return "🌙"
    if is_high and is_night:
        return "💡"
    if is_high and (not is_night):
        return "☀️"
    # Mid-range: treat as low for scanability.
    return "🌙"


def _render_notification_banner(kind: str, html_message: str) -> None:
    styles = {
        "error": ("#fee2e2", "#991b1b", "#fecaca"),
        "warning": ("#fef9c3", "#854d0e", "#fde68a"),
        "success": ("#dcfce7", "#166534", "#bbf7d0"),
        "info": ("#dbeafe", "#1e40af", "#bfdbfe"),
    }
    bg, fg, border = styles.get(kind, styles["info"])
    st.markdown(
        f"""
        <div style="background: {bg}; color: {fg}; border: 1px solid {border}; padding: 0.6rem 0.9rem; border-radius: 0.6rem; margin: 0.35rem 0;">
            <span style="font-size: 1.0rem;">{html_message}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_notifications(
    *,
    current_data: dict,
    door_data: dict,
    outside_temp_c: float | None,
    outside_is_raining: bool | None,
    historical_data: dict | None,
    hour_24: int | None = None,
) -> list[tuple[str, str]]:
    notifications: list[tuple[str, str]] = []

    def _num(value, default: float | None = None) -> float | None:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    # Air contamination percentage: 0 is perfect, 60 is horrible.
    # Keep backward compatibility with older payloads using `gas`.
    contamination = _num(
        current_data.get(
            "air_contamination",
            current_data.get("air_contamination_pct", current_data.get("gas")),
        )
    )
    oxygenation = _num(current_data.get("oxygenation"))
    light_lux = _num(current_data.get("light"))
    inside_temp = _num(current_data.get("temp"))

    is_window_open = bool(door_data.get("window_open", current_data.get("window_open", False)))

    # 0) Close window if it's open and it's raining outside.
    if is_window_open and outside_is_raining is True:
        notifications.append(("error", "🚨 It's <b>raining (or will rain)</b> outside and the window is <b>open</b>. It is recommended you close the window."))

    # 1) Close window if it's open and it's cold outside (AND colder than inside).
    if is_window_open and outside_temp_c is not None:
        if inside_temp is not None:
            if outside_temp_c < 18 and outside_temp_c < inside_temp:
                notifications.append(("warning", "⚠️ Outside is <b>colder than inside</b>. Consider closing the window to not decrease room temperature."))
        elif outside_temp_c < 18:
            notifications.append(("warning", "⚠️ Outside is <b>under 18°C</b>. Consider closing the window to not decrease room temperature."))

    # 2) Open window if it's closed and oxygenation drops.
    if (not is_window_open) and oxygenation is not None and oxygenation < 30:
        notifications.append(("warning", "⚠️ Oxygenation is <b>below 30</b>. Open the window for better focus."))

    # 3-4) Open window if it's closed and contamination is high.
    if (not is_window_open) and contamination is not None:
        if contamination > 40:
            notifications.append(("error", "🚨 Air contamination is <b>over 40%</b>. Open the window immediately."))
        elif contamination > 25:
            notifications.append(("warning", "⚠️ Air contamination is <b>over 25%</b>. Open the window."))

    # 5) Suggest turning off lights after 10pm when lux is high.
    if hour_24 is None:
        hour_24 = time.localtime().tm_hour

    if light_lux is not None and light_lux > 100 and (hour_24 >= 22 or hour_24 < 6):
        notifications.append(("info", "ℹ️ It's after <b>22:00</b> and the room is <b>bright</b>. Consider turning off the lights to avoid bad sleep quality."))

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


def _atomic_write_json(path: Path, payload: dict) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=4), encoding="utf-8")
    try:
        os.replace(tmp_path, path)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


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


def _read_oxygen_speed_override() -> bool:
    payload = _load_json_safely(OXYGEN_OVERRIDE_PATH)
    if not isinstance(payload, dict):
        return False
    try:
        multiplier = float(payload.get("speed_multiplier", 1.0))
    except (TypeError, ValueError):
        return False
    return multiplier >= 5.0


def _write_oxygen_speed_override(enabled: bool) -> None:
    payload = {"speed_multiplier": 5.0 if enabled else 1.0}
    _atomic_write_json(OXYGEN_OVERRIDE_PATH, payload)


def _toggle_override_state(key: str) -> None:
    st.session_state[key] = not bool(st.session_state.get(key, False))


def _toggle_oxygen_speed_override() -> None:
    enabled = not bool(st.session_state.get("override_oxygen_speed_5x", False))
    st.session_state["override_oxygen_speed_5x"] = enabled
    _write_oxygen_speed_override(enabled)


def _cycle_window_override() -> None:
    current = st.session_state.get("override_window_state")
    if current == "open":
        st.session_state["override_window_state"] = "closed"
    elif current == "closed":
        st.session_state["override_window_state"] = None
    else:
        st.session_state["override_window_state"] = "open"


def _get_effective_hour() -> int:
    if st.session_state.get("override_hour_12am", False):
        return 0
    return time.localtime().tm_hour


if "override_oxygen_speed_5x" not in st.session_state:
    st.session_state["override_oxygen_speed_5x"] = _read_oxygen_speed_override()


@st.cache_data(ttl=600, show_spinner=False)
def _get_outside_weather(location: tuple):
    return get_current_weather(location)


OUTSIDE_LOCATION = (45.6486, 25.6061)
#OUTSIDE_LOCATION = (32.7816, -96.7977) #dallas


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

        effective_hour = _get_effective_hour()

        if st.session_state.get("override_gas_50", False):
            data = dict(data)
            data["air_contamination"] = 50
            data["air_contamination_pct"] = 50
            data["gas"] = 50

        door_data = _get_latest_door_current_data() or {}
        window_override = st.session_state.get("override_window_state")
        if window_override in {"open", "closed"}:
            door_data = dict(door_data)
            door_data["window_open"] = window_override == "open"
        is_window_open = bool(door_data.get("window_open", data.get("window_open", False)))

        outside_temp_c: float | None = None
        outside_is_raining: bool | None = None
        outside_wind_speed_m_s: float | None = None
        try:
            outside_weather = _get_outside_weather(OUTSIDE_LOCATION)
            if outside_weather is not None:
                if len(outside_weather) >= 1:
                    outside_temp_c = outside_weather[0]
                if len(outside_weather) >= 2:
                    outside_is_raining = outside_weather[1]
                if len(outside_weather) >= 3:
                    outside_wind_speed_m_s = outside_weather[2]
        except Exception:
            outside_temp_c = None
            outside_is_raining = None
            outside_wind_speed_m_s = None

        if st.session_state.get("override_outside_5c", False):
            outside_temp_c = 5.0

        historical_data = _get_latest_historical_data()

        with st.container(border=True):
            st.markdown("### 🔔 Notifications")
            notifications = _build_notifications(
                current_data=data,
                door_data=door_data,
                outside_temp_c=outside_temp_c,
                outside_is_raining=outside_is_raining,
                historical_data=historical_data,
                hour_24=effective_hour,
            )

            for kind, message in notifications:
                _render_notification_banner(kind, message)

        # ==========================================
        # 4. DASHBOARD GRID
        # ==========================================
        # Top Row
        col1, col2 = st.columns(2)

        # --- CARD 1: LIGHT LEVEL ---
        with col1:
            with st.container(border=True):
                st.markdown("### ☀️ LIGHT LEVEL")

                light_icon = _light_context_icon(
                    data.get("light"),
                    hour_24=effective_hour,
                )
                
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = data["light"],
                    number = {'prefix': f"{light_icon} ", 'suffix': " LUX", 'font': {'size': 40, 'color': "#bbbbbb", 'weight': 'bold'}},
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
                st.plotly_chart(fig, width="stretch")

        # --- CARD 2: AIR QUALITY ---
        with col2:
            with st.container(border=True):
                st.markdown("### ☁️ Gases in Room")
                # Air contamination percentage: 0 is perfect, 60 is horrible.
                contamination_raw = data.get("air_contamination", data.get("air_contamination_pct", data.get("gas", 0)))
                try:
                    contamination = float(contamination_raw)
                except (TypeError, ValueError):
                    contamination = 0.0
                contamination = max(0.0, min(60.0, contamination))

                if contamination <= 10:
                    status, color, desc, track = "PERFECT", "#22c55e", "Clean air", "#dcfce7"
                elif contamination <= 25:
                    status, color, desc, track = "GOOD", "#eab308", "Slight contamination", "#fef9c3"
                elif contamination <= 40:
                    status, color, desc, track = "POOR", "#f97316", "Noticeable contamination", "#ffedd5"
                else:
                    status, color, desc, track = "HORRIBLE", "#ef4444", "High contamination", "#fee2e2"

                custom_progress_bar_tinted(
                    current=contamination,
                    min_val=0,
                    max_val=60,
                    fill_color=color,
                    track_color=track,
                    height="30px",
                    min_visible_fill_pct=2,
                    label=f"{contamination:.0f}%",
                )
                
                st.markdown(f"""
                    <div style="display: flex; align-items: center; height: 165px; justify-content: center; flex-direction: column;">
                        <h1 style="color: {color}; font-size: 2.5rem; margin: 0;text-align: center">{status}</h1>
                        <p style="font-size: 1.2rem; color: #555; font-weight: bold; text-align: center">Contamination {contamination:.0f}%</p>
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

                temp_trend_delta = _recent_trend_delta(historical_data, metric_key="temp", points_back=5)
                temp_trend_html = _format_temp_delta_html(temp_trend_delta, font_size="1.6rem")

                st.markdown(f"""
                    <div style="height: 180px; display: flex; align-items: center; justify-content: center;">
                        <h1 style="font-size: 4.5rem; margin: 0; color: {temp_color};">{data["temp"]} °C{temp_trend_html}</h1>
                    </div>
                    {outside_temp_html}
                    {outside_rain_html}
                """, unsafe_allow_html=True)

                if is_window_open:
                    predicted_temp = _predict_room_temp_after_minutes(
                        inside_temp_c=temp_value,
                        outside_temp_c=outside_temp_c,
                        wind_speed_m_s=outside_wind_speed_m_s,
                        t_minutes=10.0,
                    )
                    
                    minutes_to_22 = _time_to_reach_target_temp_minutes(
                        inside_temp_c=temp_value,
                        outside_temp_c=outside_temp_c,
                        wind_speed_m_s=outside_wind_speed_m_s,
                        target_temp_c=22.0,
                    )

                    # Format values or fallback to "—"
                    pred_str = f"{predicted_temp:.1f} °C" if predicted_temp is not None else "—"
                    time_str = _format_minutes_duration(minutes_to_22) if minutes_to_22 is not None else "—"

                    pred_delta_html = (
                        _format_temp_delta_html(
                            (predicted_temp - temp_value) if predicted_temp is not None else None,
                            font_size="1.2rem",
                        )
                    )

                    time_icon = ""
                    if time_str != "—":
                        # If we're above target, it's a cooling trend toward 22°C. Else warming.
                        time_icon = "📉" if temp_value > 22.0 else "📈"
                    time_value_html = f"{time_icon} {time_str}" if time_icon else time_str

                    # Use flexbox with space-around to perfectly center and space the metrics
                    st.markdown(f"""
                        <div style="display: flex; justify-content: space-around; align-items: center; margin-top: 1rem;">
                            <div style="text-align: center;">
                                <p style="font-size: 0.9rem; margin-bottom: 0.2rem; font-weight: 600;">Predicted temp (IN 10 MIN)</p>
                                <p style="font-size: 2.2rem; font-weight: 400; margin: 0;">{pred_str}{pred_delta_html}</p>
                            </div>
                            <div style="text-align: center;">
                                <p style="font-size: 0.9rem; margin-bottom: 0.2rem; font-weight: 600;">Time until 22°C</p>
                                <p style="font-size: 2.2rem; font-weight: 400; margin: 0;">{time_value_html}</p>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    if predicted_temp is None or minutes_to_22 is None:
                        st.caption("Prediction/time may be unavailable if outside temp or wind speed is missing, or if 22°C isn't reachable while the window is open.")

        # --- CARD 4: DOOR STATUS ---
        with col4:
            with st.container(border=True):
                st.markdown("### 🪟 WINDOW STATUS")

                # Door/window tracking is stored separately (door_current.json),
                # but keep a soft fallback for older files.
                is_open = is_window_open
                oxygenation = data.get("oxygenation")
                if oxygenation is None:
                    oxygenation = 100 if is_open else 0
                
                env_note_html = ""

                if is_open:
                    icon = "🪟"
                    is_colder_outside = (outside_temp_c is not None and outside_temp_c < 18 and outside_temp_c < temp_value)
                    violates_env = (outside_is_raining is True) or is_colder_outside

                    if outside_is_raining is True:
                        bg_color = "#f97316"  # raining -> stronger warning
                        desc = "Main window open (unfavorable: rain)."
                        env_note_html = (
                            '<div style="margin-top: 0.35rem; font-weight: 700; color: #f97316; text-align: center;">'
                            'Unfavorable: <b>raining</b> outside'
                            "</div>"
                        )
                    elif is_colder_outside:
                        bg_color = "#eab308"  # cold -> warning
                        desc = "Main window open (unfavorable: colder outside)."
                        env_note_html = (
                            '<div style="margin-top: 0.35rem; font-weight: 700; color: #eab308; text-align: center;">'
                            'Unfavorable: outside is <b>colder than inside</b>'
                            "</div>"
                        )
                    else:
                        bg_color = "#22c55e"
                        desc = "Main window open."
                        env_note_html = (
                        '<div style="margin-top: 0.35rem; font-weight: 700; color: #9ca3af; text-align: center;">'
                        'Room is being aired out!'
                        '</div>'
                        )
                    text = "OPEN"
                else:
                    icon = "🪟"
                    bg_color = "#eb5353"
                    text = "CLOSED"
                    desc = "Main window closed."
                    env_note_html = (
                        '<div style="margin-top: 0.35rem; font-weight: 700; color: #9ca3af; text-align: center;">'
                        'Environment isolated'
                        '</div>'
                    )
                    
                st.markdown(f"""
                    <div style="display: flex; align-items: center; justify-content: center; height: 180px; gap: 20px;">
                        <span style="font-size: 5rem;">{icon}</span>
                        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center;">
                            <span style="background-color: {bg_color}; color: white; padding: 10px 25px; border-radius: 25px; font-weight: bold; font-size: 1.5rem; letter-spacing: 1px;">
                                {text}
                            </span>
                            {env_note_html}
                        </div>
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

                # Temperature grows when the window is open (prediction/time row).
                # Add a modest spacer here so Window Status matches without overshooting.
                spacer_px = 55 if is_open else 0
                if spacer_px:
                    st.markdown(f'<div style="height: {spacer_px}px;"></div>', unsafe_allow_html=True)

        override_cols = st.columns([8, 1])
        with override_cols[1]:
            with st.container(border=True):
                st.caption("Overrides")
                label = "Out 5C" if st.session_state.get("override_outside_5c", False) else "Out"
                st.button(label, key="override_outside_5c_btn", on_click=_toggle_override_state, args=("override_outside_5c",))
                label = "12 AM" if st.session_state.get("override_hour_12am", False) else "12"
                st.button(label, key="override_hour_12am_btn", on_click=_toggle_override_state, args=("override_hour_12am",))
                label = "Gas 50" if st.session_state.get("override_gas_50", False) else "Gas"
                st.button(label, key="override_gas_50_btn", on_click=_toggle_override_state, args=("override_gas_50",))
                label = "O2 5x" if st.session_state.get("override_oxygen_speed_5x", False) else "O2"
                st.button(label, key="override_oxygen_speed_5x_btn", on_click=_toggle_oxygen_speed_override)
                window_state = st.session_state.get("override_window_state")
                if window_state == "open":
                    label = "Win O"
                elif window_state == "closed":
                    label = "Win C"
                else:
                    label = "Win"
                st.button(label, key="override_window_state_btn", on_click=_cycle_window_override)

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