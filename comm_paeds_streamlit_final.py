'''Coding test to run a Waiting list trajectory
simulation for Community Paeds at Leeds Community Health'''

# Import libraries
import pandas as pd
import streamlit as st

# Streamlit setup
st.set_page_config(page_title="Waiting List Simulator", layout="wide")

# Sidebar Controls
st.sidebar.title("Simulation Controls")
initial_waiting_list = (st.sidebar.number_input("Initial Waiting List",
                        min_value=0,
                        max_value=2500,
                        value=1500,
                        step=1)
)
demand_adjustment = (st.sidebar.number_input("Demand Adjustment (+/- patients)",
                    min_value=-100,
                    max_value=100,
                    value=0,
                    step=1)
)
capacity_adjustment =   st.sidebar.number_input("Capacity Adjustment (+/- slots)",
                        min_value=-100,
                        max_value=100,
                        value=0,
                        step=1)

# Main Title
st.title("Community Paediatrics >52 Weeks Waiting List Simulation")
st.markdown("This simulation uses demand and capacity data from Excel to project waiting list impact over time.")

# Load data source (excel file in this test)
df = pd.read_excel('data_source_test.xlsx')

# Define Inputs
daily_demand = df['Demand'] + demand_adjustment
daily_capacity = df['Capacity'] + capacity_adjustment# appointments available per day
days_to_simulate = len(df)

# Simulate Waiting List Over Time
waiting_list = [initial_waiting_list]

for day in range(days_to_simulate):     # loops through each row of the input file
    demand = daily_demand.iloc[day]     # scalar value
    capacity = daily_capacity.iloc[day] # scalar value

    net_change = demand - capacity      # scalar result
    new_waiting_list = max(waiting_list[-1] + net_change, 0)
    waiting_list.append(new_waiting_list)

# Add results to DataFrame
df['Simulated_Waiting_List'] = waiting_list[1:]  # skip initial value

# Visualise the Impact
st.area_chart(df.set_index('Day')['Simulated_Waiting_List'])

# Optional download
st.download_button(
    label="Download Simulation Results",
    data=df.to_csv(index=False),
    file_name="waiting_list_simulation.csv"
)
