"""
Waiting List Trajectory Simulation for Community Paediatrics
-------------------------------------------------------------
This Streamlit app models the projected waiting list for >52 week breaches
in Leeds Community Health's Community Paediatrics Service. It uses historical
demand and capacity data, with user-defined adjustments, to simulate future
waiting list trajectories and visualise the impact over time.

Author: Gary.white; gary.white@opelconsultancy.net
"""

# ---Import Required Libraries---
from datetime import datetime, date
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# ---Streamlit Page Configuration---
st.set_page_config(page_title="Waiting List Simulator", layout="wide")

# ---Load Data Source---
df = pd.read_excel('data_source_main.xlsx')
df['Week'] = pd.to_datetime(df['Week'])

# ---Session Setup---
if "selected_service" not in st.session_state:
    st.session_state.selected_service = ""

# ---Landing Page & Service Selection---
if st.session_state.selected_service == "":
    st.title("Leeds Community Health Waiting List Simulator")
    st.markdown("""Welcome to the simulation tool for projecting >52 week breaches.""")

    # Dropdown
    service_options = [""] + sorted(df["Service"].dropna().unique())
    selected_service = st.selectbox("🏥 Select a service to view", options=service_options)

    if selected_service:
        st.session_state.selected_service = selected_service
        st.rerun()
    else:
        st.info("Please choose a service to continue.")
        st.stop()

# ---Back to Landing Page Button---
if st.button("🔙 Back to Landing Page"):
    st.session_state.selected_service = ""
    st.rerun()

# ---Update Title with Service Name---
selected_service = st.session_state.selected_service
st.title(f"{selected_service} >52 Weeks Waiting List Simulation")
st.markdown("""This simulation uses demand and capacity data to project
            waiting list impact over time.""")

# ---Filter Data for Selected Service---
df = df[df["Service"] == selected_service]

# ---Sidebar Controls---
st.sidebar.title("Simulation Controls")

initial_value_from_data = int(df['Over52Weeks'].iloc[0])
initial_waiting_list = st.sidebar.number_input(
    "Initial Waiting List",
    min_value=0,
    max_value=3000,
    value=initial_value_from_data,
    step=1
)

# Initiative Onboarding Events
st.sidebar.subheader("Initiative")
initiative_events = []
for i in range(1, 6):
    with st.sidebar.expander(f"Initiative {i}"):
        initiative_start_raw = st.date_input(
            f"Start Date for Initiative {i}",
            value=date(2025, 10, 1),
            key=f"Initiative_date_{i}"
        )
        initiative_start = datetime.combine(initiative_start_raw, datetime.min.time())
        initiative_capacity = st.number_input(
            f"Extra Weekly Capacity from initiative {i}",
            min_value=0,
            max_value=100,
            value=0,
            key=f"initiative_capacity_{i}"
        )
        initiative_events.append((initiative_start, initiative_capacity))

# Toggle to show 'Do Nothing' scenario
show_comparison = st.sidebar.checkbox(
    "Show 'Do Nothing' Comparison",
    value=False
)

# ---Apply Initiative Capacity Adjustments---
df['initiative_Capacity_Adjustment'] = 0
for initiative_date, capacity_boost in initiative_events:
    df.loc[df['Week'] >= initiative_date, 'initiative_Capacity_Adjustment'] += capacity_boost

# ---Apply All Adjustments To Demand & Capacity---
weekly_demand = df['Starts']
weekly_capacity = df['Stops'] + df['initiative_Capacity_Adjustment']
weeks_to_simulate = len(df)

# ---Simulate 'With Initiatives' Trajectory---
waiting_list = [initial_waiting_list]
for week in range(weeks_to_simulate):
    demand = weekly_demand.iloc[week]
    capacity = weekly_capacity.iloc[week]
    net_change = demand - capacity
    new_waiting_list = max(waiting_list[-1] + net_change, 0)
    waiting_list.append(new_waiting_list)
df['Simulated_Waiting_List'] = waiting_list[1:]

# ---Simulate 'Do Nothing' Trajectory---
weekly_capacity_no_initiatives = df['Stops']
waiting_list_no_initiatives = [initial_waiting_list]
for week in range(weeks_to_simulate):
    demand = weekly_demand.iloc[week]
    capacity = weekly_capacity_no_initiatives.iloc[week]
    net_change = demand - capacity
    new_waiting_list = max(waiting_list_no_initiatives[-1] + net_change, 0)
    waiting_list_no_initiatives.append(new_waiting_list)
df['Waiting_List_No_Initiatives'] = waiting_list_no_initiatives[1:]

# ---Prepare Actuals Line---
if 'Actual Waiting List' not in df.columns:
    df['Actual Waiting List'] = 0
actuals_df = df[df['Actual Waiting List'].notna()]

# ---Visualise Waiting List Trajectory---
fig = go.Figure()
today = datetime.today()
past_df = df[df['Week'] < today]
future_df = df[df['Week'] >= today]

# Past trajectory using actuals from 'Over52Weeks'
fig.add_trace(go.Scatter(
    x=past_df['Week'],
    y=past_df['Over52Weeks'],
    mode='lines',
    name='Past Trajectory',
    line={"color": '#708090'},
    fill='tozeroy',
    opacity=0.5
))

# Future trajectory with initiatives
fig.add_trace(go.Scatter(
    x=future_df['Week'],
    y=future_df['Simulated_Waiting_List'],
    mode='lines',
    name='With Initiatives',
    line={"color": '#005EB8'},
    fill='tozeroy',
    opacity=0.6
))

# Future trajectory without initiatives
if show_comparison:
    fig.add_trace(go.Scatter(
        x=future_df['Week'],
        y=future_df['Waiting_List_No_Initiatives'],
        mode='lines',
        name='Do Nothing Scenario',
        line=dict(color="red", dash='dot'),
        fill='tozeroy',
        opacity=0.3
    ))

# Actuals line (past and future)
if not actuals_df.empty:
    fig.add_trace(go.Scatter(
        x=actuals_df['Week'],
        y=actuals_df['Actual Waiting List'],
        mode='lines+markers',
        name='Actuals',
        line=dict(color='black', width=1),
        marker=dict(size=5),
        opacity=0.9,
        fill=None,
        legendgroup='actuals',
        hovertemplate=(
            "<b>Actual Waiting List</b><br>" +
            "Week: %{x|%d-%b-%Y}<br>" +
            "Size: %{y}<extra></extra>"
        )
    ))

# Vertical line for today
fig.add_vline(
    x=today,
    line_width=0.4,
    line_dash="dash",
    line_color="black"
)

# Annotation for "Today"
fig.add_annotation(
    x=today,
    y=max(df['Simulated_Waiting_List']),
    text="Today",
    showarrow=True,
    arrowhead=3,
    arrowsize=0.5,
    ax=0,
    ay=-60,
    font=dict(family="Arial", size=12, color="black"),
    align="center"
)

# Initiative markers
locum_colors = ['red', 'orange', 'green', 'purple', 'blue']
for i, (initiative_date, capacity_boost) in enumerate(initiative_events, start=1):
    if capacity_boost > 0:
        matching_weeks = df[df['Week'] >= initiative_date]
        if not matching_weeks.empty:
            marker_date = matching_weeks.iloc[0]['Week']
            y_value = matching_weeks.iloc[0]['Simulated_Waiting_List']
            fig.add_trace(go.Scatter(
                x=[marker_date],
                y=[y_value],
                mode='markers',
                marker=dict(size=10, color=locum_colors[i - 1]),
                name=f"Initiative {i}",
                hovertemplate=(
                    f"<b>Initiative {i} Start</b><br>"
                    f"Week: {marker_date.strftime('%d-%b-%Y')}<br>"
                    f"Capacity Boost: {capacity_boost} patients/week<br>"
                    "<extra></extra>"
                )
            ))

# Chart layout
fig.update_layout(
    xaxis_title="Week",
    yaxis_title="Waiting List Size",
    showlegend=True,
    height=500,
    xaxis=dict(
        tickangle=-45,
        dtick="M1",
        tickformat="%d-%b-%Y"
    )
)

# Display chart
st.plotly_chart(fig, use_container_width=True)

# Download button
st.download_button(
    label="Download Simulation Results",
    data=df.to_csv(index=False),
    file_name="waiting_list_simulation.csv"
)

# Footer
st.markdown("© BI Team, Leeds Community Health")
