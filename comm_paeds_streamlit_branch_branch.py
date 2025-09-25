"""
Waiting List Trajectory Simulation for Community Paediatrics
-------------------------------------------------------------
This Streamlit app models the projected waiting list for >52 week breaches
in Leeds Community Health's Community Paediatrics Service. It uses historical
demand and capacity data, with user-defined adjustments, to simulate future
waiting list trajectories and visualize the impact over time.

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
df = pd.read_excel('data_source_testv0.2.xlsx')

# ---Ensure 'Week' Column is in datetime format---
df['Week'] = pd.to_datetime(df['Week'])

# ---Sidebar Controls---
st.sidebar.title("Simulation Controls")

# ---Initial Waiting List Size---
initial_value_from_data = int(df['WaitingList'].iloc[0])
initial_waiting_list = st.sidebar.number_input(
    "Initial Waiting List",
    min_value=0,
    max_value=3000,
    value=initial_value_from_data,
    step=1
)

# ---Global Adjustment To Daily Demand---
demand_adjustment = st.sidebar.number_input(
    "Global Demand Adjustment (+/- patients)",
    min_value=0,
    max_value=100,
    value=0,
    step=1
)

# ---Global Adjustment To Daily Capacity---
capacity_adjustment = st.sidebar.number_input(
    "Global Capacity Adjustment (+/- slots)",
    min_value=0,
    max_value=100,
    value=0,
    step=1
)

# ---Locum Onboarding Events---
st.sidebar.subheader("Locum Onboarding Events")
locum_events = []
for i in range(1, 6):
    with st.sidebar.expander(f"Locum {i}"):
        locum_start_raw = st.date_input(
            f"Start Date for Locum {i}",
            value=date(2025, 10, 1),
            key=f"locum_date_{i}"
        )
        locum_start = datetime.combine(locum_start_raw, datetime.min.time())
        locum_capacity = st.number_input(
            f"Extra Weekly Capacity from Locum {i}",
            min_value=0,
            max_value=100,
            value=0,
            key=f"locum_capacity_{i}"
        )
        locum_events.append((locum_start, locum_capacity))

# ---Main Page Title And Description---
st.title("Community Paediatrics >52 Weeks Waiting List Simulation")
st.markdown("""This simulation uses demand and capacity data to project
waiting list impact over time.""")

# ---Apply Locum-Specific Capacity Adjustments---
df['Locum_Capacity_Adjustment'] = 0
for locum_date, capacity_boost in locum_events:
    df.loc[df['Week'] >= locum_date, 'Locum_Capacity_Adjustment'] += capacity_boost

# ---Apply All Adjustments To Demand & Capacity---
weekly_demand = df['Starts'] + demand_adjustment
weekly_capacity = df['Stops'] + capacity_adjustment + df['Locum_Capacity_Adjustment']
weeks_to_simulate = len(df)

# ---Initialise Waiting List Simulation---
waiting_list = [initial_waiting_list]

# ---Run Simulation Over Each Week---
for week in range(weeks_to_simulate):
    demand = weekly_demand.iloc[week]
    capacity = weekly_capacity.iloc[week]
    net_change = demand - capacity
    new_waiting_list = max(waiting_list[-1] + net_change, 0)
    waiting_list.append(new_waiting_list)

# ---Store Simulation Results In DataFrame---
df['Simulated_Waiting_List'] = waiting_list[1:]

# ---Visualise Waiting List Trajectory with Past vs Future Split---
fig = go.Figure()
today = datetime.today()

# Split the DataFrame
past_df = df[df['Week'] < today]
future_df = df[df['Week'] >= today]

# Past trajectory
fig.add_trace(go.Scatter(
    x=past_df['Week'],
    y=past_df['Simulated_Waiting_List'],
    mode='lines',
    name='Past Trajectory',
    line=dict(color='lightgrey'),
    fill='tozeroy',
    opacity=0.5
))

# Future trajectory
fig.add_trace(go.Scatter(
    x=future_df['Week'],
    y=future_df['Simulated_Waiting_List'],
    mode='lines',
    name='Projected Trajectory',
    line=dict(color='royalblue'),
    fill='tozeroy'
))

# Vertical line for today (without annotation_text to avoid error)
fig.add_vline(
    x=today,
    line_width=0.4, #Thin line
    line_dash="dash",
    line_color="black"
)

# Separate annotation for "Today" label
fig.add_annotation(
    x=today,
    y=max(df['Simulated_Waiting_List']),
    text="Today",
    showarrow=True,
    arrowhead=3, # Choose from 0-8 for different arrow styles
    arrowsize=0.5, # Scale arrow size
    ax=0,
    ay=-60, # Add label above line
    font=dict(
        family="Arial",  # Or "Verdana", "Courier New", etc.
        size=12,
        color="black"
    ),
    align="center"
)

# Locum markers
locum_colors = ['red', 'orange', 'green', 'purple', 'blue']
for i, (locum_date, capacity_boost) in enumerate(locum_events, start=1):
    if capacity_boost > 0:
        matching_weeks = df[df['Week'] >= locum_date]
        if not matching_weeks.empty:
            marker_date = matching_weeks.iloc[0]['Week']
            y_value = matching_weeks.iloc[0]['Simulated_Waiting_List']
            fig.add_trace(go.Scatter(
                x=[marker_date],
                y=[y_value],
                mode='markers',
                marker=dict(size=10, color=locum_colors[i - 1]),
                name=f"Locum {i}",
                hovertemplate=(
                    f"<b>Locum {i} Start</b><br>"
                    f"Week: {marker_date.strftime('%d-%b-%Y')}<br>"
                    f"Capacity Boost: {capacity_boost} patients/week<br>"
                    "<extra></extra>"
                )
            ))

# ---Layout Of Chart---
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

# ---Display Chart---
st.plotly_chart(fig, use_container_width=True)

# ---Optional Download Of Results---
st.download_button(
    label="Download Simulation Results",
    data=df.to_csv(index=False),
    file_name="waiting_list_simulation.csv"
)

# ---Footer---
st.markdown("© BI Team, Leeds Community Health")
