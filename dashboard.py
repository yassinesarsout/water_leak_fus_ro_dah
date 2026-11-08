import time
import json
import hmac
import hashlib
import threading
from datetime import datetime
from collections import deque

import certifi
import pandas as pd
import streamlit as st
import paho.mqtt.client as mqtt

# ==========================================
# 1. CONFIGURATION & 3-LAYER SECURITY KEYS
# ==========================================
MQTT_BROKER   = "broker.emqx.io"
MQTT_PORT_TLS = 8883  # Layer 2: Encrypted TLS Port
MQTT_USER     = "fusrodah_esp32"
MQTT_PASS     = "iot_spark_secure_2026"

TOPIC_STATUS   = "fusrodah/iotspark4/status"
TOPIC_EVENTS   = "fusrodah/iotspark4/events"
TOPIC_CSV      = "fusrodah/iotspark4/csv"
TOPIC_COMMANDS = "fusrodah/iotspark4/commands"

# Layer 3: Shared HMAC-SHA256 Secret Key (matches ESP32)
SHARED_SECRET = "FUS_RO_DAH_SECRET_KEY_2026"

# Layer 1: Role-Based User Accounts
USERS = {
    "admin":    {"password": "fusrodah2026", "role": "Admin (Full Control)"},
    "operator": {"password": "operator123",  "role": "Operator (Monitor, Close & Silence)"}
}

st.set_page_config(page_title="Fus Ro Dah | Water-Leak Detection", page_icon="💧", layout="wide")

# ==========================================
# 2. SHARED THREAD-SAFE STATE
# ==========================================
@st.cache_resource
def get_shared_state():
    return {
        "connected": False,
        "ms": 0,
        "level": 0.0,
        "slopeA": 0.0,
        "slopeB": 0.0,
        "leakRate": 0.0,
        "minV": 0.0,
        "maxV": 0.0,
        "hum": None,
        "temp": None,
        "humRate": 0.0,
        "class": "WARMUP",      # WARMUP, NORMAL, HUMID_AIR, SMALL_SPILL, LEAK, SENSOR_FAULT
        "state": "WATER_ON",    # WATER_ON, LEAK_OFF, FAULT_OFF, MANUAL_OFF
        "valve": "OPEN",        # OPEN or CLOSED
        "alarm": False,
        "silenced": False,
        "waterFault": False,
        "humFault": False,
        "sysArmed": True,       # True = System OPEN (Armed), False = System CLOSED (Disarmed)
        "last_seen": "Never",
        "history": deque(maxlen=60),
        "events": deque(maxlen=60),
        "csv_rows": deque(maxlen=500),
        "seq": int(time.time())
    }

state = get_shared_state()

def log_event(event_name, details, ms_val=None):
    state["events"].appendleft({
        "Time": datetime.now().strftime("%H:%M:%S"),
        "Board ms": ms_val if ms_val is not None else state["ms"],
        "Event": event_name,
        "Details": details
    })

# ==========================================
# 3. MQTT CLIENT OVER TLS (LAYER 2 & 3)
# ==========================================
@st.cache_resource
def start_mqtt_client():
    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            state["connected"] = True
            client.subscribe(TOPIC_STATUS)
            client.subscribe(TOPIC_EVENTS)
            client.subscribe(TOPIC_CSV)
            log_event("MQTT_TLS_READY", "Dashboard connected over TLS Port 8883")
        else:
            state["connected"] = False

    def on_disconnect(client, userdata, flags, rc, properties=None):
        state["connected"] = False
        log_event("MQTT_DISCONNECTED", "Connection lost — ESP32 local protection stays active")

    def on_message(client, userdata, msg):
        raw_text = msg.payload.decode("utf-8", errors="ignore").strip()
        try:
            if msg.topic == TOPIC_STATUS:
                data = json.loads(raw_text)
                state["ms"]         = data.get("ms", 0)
                state["level"]      = float(data.get("level", 0))
                state["slopeA"]     = float(data.get("slopeA", 0.0))
                state["slopeB"]     = float(data.get("slopeB", 0.0))
                state["leakRate"]   = float(data.get("leakRate", 0.0))
                state["minV"]       = float(data.get("minV", 0.0))
                state["maxV"]       = float(data.get("maxV", 0.0))
                state["hum"]        = data.get("hum", None)
                state["temp"]       = data.get("temp", None)
                state["humRate"]    = float(data.get("humRate", 0.0))
                state["class"]      = data.get("class", "NORMAL")
                state["state"]      = data.get("state", "WATER_ON")
                state["valve"]      = data.get("valve", "OPEN")
                state["alarm"]      = bool(data.get("alarm", False))
                state["silenced"]   = bool(data.get("silenced", False))
                state["waterFault"] = bool(data.get("waterFault", False))
                state["humFault"]   = bool(data.get("humFault", False))
                state["sysArmed"]   = bool(data.get("sysArmed", True))
                state["last_seen"]  = datetime.now().strftime("%H:%M:%S")

                state["history"].append({
                    "time": state["last_seen"],
                    "Water Level (ADC)": state["level"],
                    "Leak Growth Rate (u/s)": state["leakRate"],
                    "Humidity (%)": state["hum"] if state["hum"] is not None else 0.0
                })

            elif msg.topic == TOPIC_EVENTS:
                ev = json.loads(raw_text)
                ev_name = ev.pop("event", "EVENT")
                ev_ms   = ev.pop("ms", None)
                details = ", ".join([f"{k}={v}" for k, v in ev.items()])
                log_event(ev_name, details, ev_ms)

            elif msg.topic == TOPIC_CSV:
                if raw_text.startswith("CSV,") and not raw_text.startswith("CSV,ms"):
                    parts = raw_text.split(",")
                    if len(parts) >= 9:
                        state["csv_rows"].append({
                            "ms": parts[1], "level": float(parts[2]),
                            "slopeA": float(parts[3]), "slopeB": float(parts[4]),
                            "min": float(parts[5]), "max": float(parts[6]),
                            "hum": None if parts[7] == "null" else float(parts[7]),
                            "humRate": float(parts[8]), "label": int(parts[9])
                        })
        except Exception as e:
            log_event("PARSE_ERROR", f"{e} | Raw: {raw_text[:60]}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"fusrodah_dash_{int(time.time())}")
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set(ca_certs=certifi.where())  # Layer 2: TLS 8883 encryption
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    def loop_thread():
        while True:
            try:
                if not state["connected"]:
                    client.connect(MQTT_BROKER, MQTT_PORT_TLS, keepalive=30)
                client.loop_forever()
            except Exception:
                time.sleep(3)

    threading.Thread(target=loop_thread, daemon=True).start()
    return client

mqtt_client = start_mqtt_client()

def send_signed_command(cmd_str, user, fake_attack=False):
    """Layer 3: Signs every command with HMAC-SHA256 + anti-replay sequence number."""
    state["seq"] += 1
    seq = state["seq"]
    msg_to_sign = f"{cmd_str}:{seq}"

    if fake_attack:
        sig = "0000_SPOOFED_HACKER_SIGNATURE_0000"
    else:
        sig = hmac.new(
            SHARED_SECRET.encode("utf-8"),
            msg_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    packet = {"cmd": cmd_str, "user": user, "seq": seq, "sig": sig}
    mqtt_client.publish(TOPIC_COMMANDS, json.dumps(packet, separators=(',', ':')))
    if fake_attack:
        log_event("SIMULATED_ATTACK", f"Sent spoofed '{cmd_str}' with invalid HMAC")
    else:
        log_event("CMD_SENT", f"cmd='{cmd_str}' by '{user}' (seq={seq})")

# ==========================================
# 4. LAYER 1: LOGIN SCREEN
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

if not st.session_state.logged_in:
    st.title("🔒 Fus Ro Dah — IoT Spark 4.0 Security Gateway")
    st.subheader("Property 2: Water-Leak Detection & Shutoff Platform")
    col1, col2 = st.columns([1, 1])
    with col1:
        with st.form("login_form"):
            u = st.text_input("Username (`admin` or `operator`)")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", use_container_width=True):
                if u in USERS and USERS[u]["password"] == p:
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.session_state.role = USERS[u]["role"]
                    log_event("USER_LOGIN", f"User '{u}' authenticated")
                    st.rerun()
                else:
                    log_event("LOGIN_FAILED", f"Failed attempt for user '{u}'")
                    st.error("Invalid credentials!")
    with col2:
        st.info(
            "**Accounts:**\n"
            "- **Admin** (`admin` / `fusrodah2026`): Full access (Open/Close Water, Open/Close Monitoring System, Silence Alarm, CSV Recording)\n"
            "- **Operator** (`operator` / `operator123`): Can monitor, Close Water (`CLOSE`), and Silence Alarm (`SILENCE`), but **cannot** re-open water (`OPEN`) or disarm the system."
        )
    st.stop()

# ==========================================
# 5. HEADER & REMOTE CONTROLS
# ==========================================
is_admin = (st.session_state.username == "admin")

h1, h2, h3 = st.columns([3, 2, 1])
with h1:
    st.title("💧 Fus Ro Dah — Water-Leak Command Center")
with h2:
    st.markdown(f"**User:** `{st.session_state.username}` ({st.session_state.role})")
    link_txt = "🟢 MQTT-TLS 8883 Connected" if state["connected"] else "🔴 Offline (ESP32 Local Autonomy Active)"
    st.markdown(f"**Link:** {link_txt} | **Last seen:** `{state['last_seen']}`")
with h3:
    if st.button("🚪 Log Out", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.subheader("🎛️ Remote Hardware & System Controls (HMAC-SHA256 Signed)")
b1, b2, b3, b4, b5 = st.columns(5)

with b1:
    if st.button("🔴 CLOSE WATER (CLOSE)", use_container_width=True, type="primary"):
        send_signed_command("CLOSE", st.session_state.username)
        st.toast("Sent signed CLOSE command")

with b2:
    # ESP32 tryOpen() requires dry floor (<150 for 3s) and no waterFault; dashboard enforces Admin role
    if st.button("🟢 OPEN WATER (OPEN)", use_container_width=True, disabled=not is_admin):
        send_signed_command("OPEN", st.session_state.username)
        st.toast("Sent signed OPEN command (ESP32 verifies dry floor & sensor health)")
    if not is_admin:
        st.caption("🔒 Admin required to open water")

with b3:
    if st.button("🔕 STOP ALARM (SILENCE)", use_container_width=True):
        send_signed_command("SILENCE", st.session_state.username)
        st.toast("Sent signed SILENCE command (Red LED stops blinking, water stays OFF)")

with b4:
    if state["sysArmed"]:
        if st.button("⏸️ CLOSE SYSTEM (SYS_OFF)", use_container_width=True, disabled=not is_admin):
            send_signed_command("SYS_OFF", st.session_state.username)
            st.toast("Monitoring system disarmed (SYS_OFF)")
    else:
        if st.button("🛡️ OPEN SYSTEM (SYS_ON)", use_container_width=True, disabled=not is_admin):
            send_signed_command("SYS_ON", st.session_state.username)
            st.toast("Monitoring system armed (SYS_ON)")
    if not is_admin:
        st.caption("🔒 Admin required")

with b5:
    if st.button("🕵️ TEST SPOOFED COMMAND", use_container_width=True):
        send_signed_command("OPEN", "hacker_spoof", fake_attack=True)
        st.warning("Spoofed OPEN sent! Watch ESP32 block it in the Event Log.")

# ==========================================
# 6. LIVE TELEMETRY & HARDWARE STATUS FRAGMENT
# ==========================================
@st.fragment(run_every=1.0)
def live_dashboard():
    # 1. Big Operator Status Banner
    sys_badge   = "🛡️ SYSTEM OPEN (ARMED)" if state["sysArmed"] else "⏸️ SYSTEM CLOSED (DISARMED)"
    valve_badge = "🟢 VALVE: OPEN (WATER ON)" if state["valve"] == "OPEN" else f"🟡 VALVE: CLOSED ({state['state']})"
    alarm_badge = "🚨 ALARM BLINKING" if (state["alarm"] and not state["silenced"]) else ("🔕 ALARM SILENCED (SOLID RED)" if state["alarm"] else "✅ NO ALARM")

    if not state["sysArmed"]:
        st.warning(f"### {sys_badge}  |  {valve_badge}  |  Automatic Shutoff Paused")
    elif state["waterFault"] or state["humFault"]:
        fault_which = "WATER SENSOR (>4000)" if state["waterFault"] else "DHT22 HUMIDITY SENSOR"
        st.error(f"### ⚠️ SENSOR FAULT: {fault_which}  |  {valve_badge}  |  {alarm_badge}")
    elif state["class"] == "LEAK" or state["state"] == "LEAK_OFF":
        st.error(f"### 🚨 CONFIRMED LEAK!  |  {valve_badge}  |  Growth: +{state['leakRate']:.1f} u/s  |  {alarm_badge}")
    elif state["class"] == "SMALL_SPILL":
        st.warning(f"### ⚠️ SMALL SPILL (Water Stays ON)  |  {valve_badge}  |  {sys_badge}")
    elif state["class"] == "HUMID_AIR":
        st.info(f"### 🌫️ HUMID AIR (Water Stays ON)  |  {valve_badge}  |  {sys_badge}")
    else:
        st.success(f"### ✅ CLASS: {state['class']}  |  {valve_badge}  |  {sys_badge}")

    # 2. Key Sensor & AI Window Feature Cards (Matches `Features` struct in ESP32)
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Floor Water Level", f"{state['level']:.0f} / 4095", f"Min {state['minV']:.0f} / Max {state['maxV']:.0f}")
    m2.metric("Leak Growth Rate", f"{state['leakRate']:.1f} u/s", f"slopeA: {state['slopeA']:+.1f} | slopeB: {state['slopeB']:+.1f}", delta_color="inverse")
    m3.metric("Air Humidity", "FAULT" if state["hum"] is None else f"{state['hum']:.1f} %", f"{state['humRate']:+.2f} %/s")
    m4.metric("Temperature", "FAULT" if state["temp"] is None else f"{state['temp']:.1f} °C")
    m5.metric("AI Window Class", state["class"], f"State: {state['state']}")
    m6.metric("Hardware LEDs", f"Green: {'ON' if state['valve']=='OPEN' else 'OFF'}", f"Yellow: {'ON' if state['valve']=='CLOSED' else 'OFF'} | Red: {'ON' if state['alarm'] else 'OFF'}")

    # 3. Charts & Event Audit Log
    col_chart, col_events = st.columns([3, 2])
    with col_chart:
        st.subheader("📈 Live Water Level, Leak Growth Speed & Humidity")
        if len(state["history"]) > 0:
            df_h = pd.DataFrame(list(state["history"])).set_index("time")
            st.line_chart(df_h, height=260)
        else:
            st.info("Waiting for `STATUS {...}` packets from ESP32 on `fusrodah/iotspark4/status`...")

    with col_events:
        st.subheader("📜 Live Hardware & Security Event Log (`EVENT {...}`)")
        if len(state["events"]) > 0:
            st.dataframe(pd.DataFrame(list(state["events"])), use_container_width=True, height=260, hide_index=True)
        else:
            st.write("No events yet.")

live_dashboard()

# ==========================================
# 7. BONUS: REMOTE AI CSV DATASET COLLECTOR
# ==========================================
with st.expander("📊 Remote AI Feature Collector (`CSV ON` / `LABEL n` from ESP32)"):
    c_on, c_off, c_lbl, c_dl = st.columns([1, 1, 2, 2])
    with c_on:
        if st.button("▶️ Start CSV Stream", use_container_width=True):
            send_signed_command("CSV ON", st.session_state.username)
    with c_off:
        if st.button("⏹️ Stop CSV Stream", use_container_width=True):
            send_signed_command("CSV OFF", st.session_state.username)
    with c_lbl:
        lbl_choice = st.selectbox("Set Active Training Label:", ["0 - NORMAL", "1 - HUMID_AIR", "2 - SMALL_SPILL", "3 - LEAK"])
        if st.button("Set Label on ESP32", use_container_width=True):
            send_signed_command(f"LABEL {lbl_choice[0]}", st.session_state.username)
    with c_dl:
        st.write(f"Collected Rows: **{len(state['csv_rows'])}**")
        if len(state["csv_rows"]) > 0:
            csv_bytes = pd.DataFrame(list(state["csv_rows"])).to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Recorded AI CSV", data=csv_bytes, file_name="esp32_recorded_windows.csv", mime="text/csv", use_container_width=True)
