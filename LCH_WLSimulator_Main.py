"""
Waiting List Trajectory Simulation for Community Paediatrics
-------------------------------------------------------------
This Streamlit app models the projected waiting list for >52 week breaches
in Leeds Community Health's Community Paediatrics Service. It uses historical
demand and capacity data, with user-defined adjustments, to simulate future
waiting list trajectories and visualise the impact over time.

Author: Gary.white; gary.white@opelconsultancy.net
"""

from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")  # Enable full-width layout

# --- Load and Prepare Data ---
df = pd.read_excel("data_source_branch4.xlsx")
df.columns = df.columns.str.strip().str.replace(" ", "_").str.replace("(", "").str.replace(")", "")
df["WeekCommencing"] = pd.to_datetime(df["WeekCommencing"])

# --- Session Setup ---
if "selected_service" not in st.session_state:
    st.session_state.selected_service = ""

# --- Landing Page ---
if st.session_state.selected_service == "":
    st.title("Leeds Community Health Waiting List Simulator")
    st.markdown("Welcome to the simulation tool for projecting >52 week breaches.")
    service_options = [""] + sorted(df["Entity"].dropna().unique())
    selected_service = st.selectbox("🏥 Select a service to view", options=service_options)
    if selected_service:
        st.session_state.selected_service = selected_service
        st.rerun()
    else:
        st.info("Please choose a service to continue.")
        st.stop()

# --- Back Button ---
if st.button("🔙 Back to Landing Page"):
    st.session_state.selected_service = ""
    st.rerun()

# --- Filter Data for Selected Service ---
selected_service = st.session_state.selected_service
service_df = df[df["Entity"] == selected_service].sort_values("WeekCommencing")
today = pd.to_datetime(datetime.today().date())
historic = service_df[service_df["WeekCommencing"] < today]

# --- Styled Title ---
st.markdown(f"<h2 style='font-weight:bold;'>{selected_service} &gt;52 Week Waiting List Simulation</h2>",
            unsafe_allow_html=True)

# --- Percentile Calculation ---
clock_start_65 = int(historic["ClockStarts"].dropna().quantile(0.65))
clock_stop_65 = int(historic["ClockStops"].dropna().quantile(0.65))

# --- Sidebar: Initiative Inputs ---
st.sidebar.header("📌 Capacity Initiatives")

initiatives = []
colors = ["firebrick", "darkgreen", "orange", "purple", "teal"]

for i in range(5):
    with st.sidebar.expander("Initiative", expanded=False):
        name = st.text_input("Initiative Name", key=f"name_{i}")
        start = st.date_input("Start Date", key=f"start_{i}")
        change = st.number_input("Capacity Change", value=0, step=1, key=f"change_{i}")
        
        use_end = st.checkbox("Set End Date?", key=f"use_end_{i}")
        end = None
        if use_end:
            end = st.date_input("End Date", key=f"end_{i}")

        if name and change != 0:
            initiative = {
                "name": name,
                "start": pd.to_datetime(start),
                "change": change,
                "color": colors[i % len(colors)]
            }
            if end:
                initiative["end"] = pd.to_datetime(end)

            initiatives.append(initiative)

# --- Sidebar: Waiting List Resets ---
st.sidebar.header("🔄 Waiting List Resets")

# Reset 1
enable_reset_1 = st.sidebar.checkbox("Enable Reset 1", value=False)
if enable_reset_1:
    reset_date_1 = st.sidebar.date_input("Reset 1 Date", value=datetime(2025, 11, 1), key="reset_date_1")
    last_actual_row = service_df[service_df["WeekCommencing"] < today].iloc[-1]
    default_reset_value_1 = int(last_actual_row["Over52Weeks"])
    reset_value_1 = st.sidebar.number_input("Reset 1 Value", min_value=1, max_value=3000,
                                            value=default_reset_value_1, step=1, key="reset_value_1")
else:
    reset_date_1 = None
    reset_value_1 = None

# Reset 2
enable_reset_2 = st.sidebar.checkbox("Enable Reset 2", value=False)
if enable_reset_2:
    reset_date_2 = st.sidebar.date_input("Reset 2 Date", value=datetime(2026, 1, 1), key="reset_date_2")
    default_reset_value_2 = int(last_actual_row["Over52Weeks"])
    reset_value_2 = st.sidebar.number_input("Reset 2 Value", min_value=1, max_value=3000,
                                            value=default_reset_value_2, step=1, key="reset_value_2")
else:
    reset_date_2 = None
    reset_value_2 = None

# --- Baseline Overlay Toggle (placed after resets) ---
show_baseline = st.sidebar.checkbox("📊 Show 'Do Nothing' Baseline", value=True)

# --- Forecast Simulation with Initiative Effects ---
def simulate_future(df, weeks_ahead, initiatives):
    last_actual_row = df[df["WeekCommencing"] < today].iloc[-1]
    wl = last_actual_row["Over52Weeks"]
    start_date = last_actual_row["WeekCommencing"]

    future_data = []
    for i in range(weeks_ahead):
        next_week = start_date + pd.Timedelta(weeks=i+1)

        extended_historic = df[df["WeekCommencing"] < next_week]
        clock_start_65 = int(extended_historic["ClockStarts_52+_weeks"].dropna().quantile(0.65))
        clock_stop_65 = int(extended_historic["ClockStops_52+_weeks"].dropna().quantile(0.65))

        adjusted_clock_stop = clock_stop_65
        for item in initiatives:
            if item["start"] <= next_week and ("end" not in item or next_week <= item["end"]):
                adjusted_clock_stop += item["change"]

        if i == 0:
            adjusted_clock_stop = last_actual_row["ClockStops_52+_weeks"]

        # Apply resets if dates match
        if reset_date_1 and next_week.date() == reset_date_1:
            wl = reset_value_1
        if reset_date_2 and next_week.date() == reset_date_2:
            wl = reset_value_2

        wl = max(0, wl - adjusted_clock_stop)

        if i < weeks_ahead - 1:
            wl_next = wl + clock_start_65
        else:
            wl_next = wl

        future_data.append({
            "WeekCommencing": next_week,
            "Simulated_WaitingList": wl_next
        })

        wl = wl_next

    return pd.DataFrame(future_data)

# Simulate 'Do Nothing' Baseline
baseline_future = simulate_future(service_df, weeks_ahead=52, initiatives=[])

# Simulate Forecast with Initiatives
future = simulate_future(service_df, weeks_ahead=52, initiatives=initiatives)

# --- Plot Actuals + Forecast ---
fig = go.Figure()

# Actuals
fig.add_trace(go.Scatter(
    x=historic["WeekCommencing"],
    y=historic["Over52Weeks"],
    mode="lines",
    line=dict(color="lightgrey", width=2),
    fill="tozeroy",
    name="Actual"
))

# Optional: Baseline Overlay
if show_baseline:
    fig.add_trace(go.Scatter(
        x=baseline_future["WeekCommencing"],
        y=baseline_future["Simulated_WaitingList"],
        mode="lines",
        line=dict(color="lightblue", width=0),
        fill="tozeroy",
        fillcolor="rgba(173,216,230,0.4)",
        name="Do Nothing Baseline",
        hovertemplate=(
            "<b>Do Nothing Baseline</b><br>" +
            "Week: %{x|%d-%b-%Y}<br>" +
            "Waiting List: %{y}<extra></extra>"
        )
    ))

# Forecast
fig.add_trace(go.Scatter(
    x=future["WeekCommencing"],
    y=future["Simulated_WaitingList"],
    mode="lines",
    line=dict(color="royalblue", width=2),
    fill="tozeroy",
    name="Forecast"
))

# Initiative Markers
for item in initiatives:
    future["date_diff"] = (future["WeekCommencing"] - item["start"]).abs()
    closest = future.loc[future["date_diff"].idxmin()]
    x_val = closest["WeekCommencing"]
    y_val = closest["Simulated_WaitingList"]

    fig.add_trace(go.Scatter(
        x=[x_val],
        y=[y_val],
        mode="markers",
        marker=dict(color=item["color"], size=10, symbol="circle"),
        name=item["name"],
        hovertemplate=f"{item['name']}<br>Change: {item['change']}<extra></extra>"
    ))

# Reset Markers
for label, date, value in [
    ("Reset 1", reset_date_1, reset_value_1),
    ("Reset 2", reset_date_2, reset_value_2)
]:
    if date:
        match = future[future["WeekCommencing"].dt.date == date]
        if not match.empty:
            point = match.iloc[0]
            fig.add_trace(go.Scatter(
                x=[point["WeekCommencing"]],
                y=[point["Simulated_WaitingList"]],
                mode="markers",
                marker=dict(color="black", size=12, symbol="x"),
                name=f"Waiting List {label}",
                hovertemplate=(
                    f"<b>Waiting List {label}</b><br>"
                    f"Week: {point['WeekCommencing'].strftime('%d-%b-%Y')}<br>"
                    f"New Value: {value}<extra></extra>"
                )
            ))

# --- Update Layout: X-axis ticks and rotation ---
fig.update_layout(
    xaxis=dict(
        tickangle=45,               # Upward diagonal
        dtick="M1",                 # Month interval
        tickformat="%b-%y",         # Format mmm-yy
        title="Week Commencing",
        tickfont=dict(size=10)
    ),
    yaxis=dict(title="Waiting List Size"),
    margin=dict(t=40, b=80, r=160),
    legend=dict(
        orientation="v",
        yanchor="top",
        y=1,
        xanchor="left",
        x=1.02,
        font=dict(size=10)
    )
)

# --- Display Chart ---
st.plotly_chart(fig, use_container_width=True)  # Stretch chart to full width

# --- Combine actuals and forecast for download ---
download_df = pd.concat([
    historic[["WeekCommencing", "Over52Weeks"]].rename(columns={"Over52Weeks": "Actual_WaitingList"}),
    future[["WeekCommencing", "Simulated_WaitingList"]]
], ignore_index=True)

def get_active_initiatives(week):
    active = []
    for i in initiatives:
        if i["start"] <= week and ("end" not in i or week <= i["end"]):
            label = f"{i['name']} ({i['change']:+})"
            active.append(label)
    return "; ".join(active) if active else ""

download_df["Initiatives_Applied"] = download_df["WeekCommencing"].apply(get_active_initiatives)

# --- CSV Download Button ---
st.download_button(
    label="📥 Download Forecast with Active Initiatives (CSV)",
    data=download_df.to_csv(index=False).encode("utf-8"),
    file_name=f"{selected_service}_forecast_with_initiatives.csv",
    mime="text/csv"
)

# --- Footer ---
st.markdown("© BI Team, Leeds Community Health")         
