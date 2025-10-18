import streamlit as st
import pandas as pd

# --- Page Configuration ---
st.set_page_config(
    page_title="Project Crashing Simulator",
    page_icon="⏱️",
    layout="wide"
)

# --- Helper Functions ---

def get_successors(df):
    """Generates a dictionary of successors for each activity."""
    successors = {activity: [] for activity in df['Activity']}
    for idx, row in df.iterrows():
        predecessors = str(row['Predecessors']).split(',')
        for pred in predecessors:
            pred = pred.strip()
            if pred and pred != '-' and pred in successors:
                successors[pred].append(row['Activity'])
    return successors

def calculate_cpm(df):
    """
    Performs the Critical Path Method (CPM) calculation.
    Includes Forward Pass, Backward Pass, and Slack calculation.
    """
    df_cpm = df.copy()
    successors = get_successors(df_cpm)

    # --- Forward Pass ---
    df_cpm['ES'] = 0
    df_cpm['EF'] = 0
    
    # We need to iterate until all ES/EF values stabilize, handling complex dependencies
    for _ in range(len(df_cpm)):
        for idx, row in df_cpm.iterrows():
            if row['Predecessors'] == '-':
                df_cpm.loc[idx, 'ES'] = 0
            else:
                preds = [p.strip() for p in str(row['Predecessors']).split(',')]
                max_ef_of_preds = df_cpm[df_cpm['Activity'].isin(preds)]['EF'].max()
                df_cpm.loc[idx, 'ES'] = max_ef_of_preds if pd.notna(max_ef_of_preds) else 0
            
            df_cpm.loc[idx, 'EF'] = df_cpm.loc[idx, 'ES'] + df_cpm.loc[idx, 'Duration']
    
    project_duration = df_cpm['EF'].max()

    # --- Backward Pass ---
    df_cpm['LF'] = project_duration
    df_cpm['LS'] = 0

    # Iterate in reverse order of activities for backward pass
    for _ in range(len(df_cpm)):
      for idx in reversed(df_cpm.index):
          activity = df_cpm.loc[idx, 'Activity']
          if not successors[activity]: # It's an end node
              df_cpm.loc[idx, 'LF'] = project_duration
          else:
              min_ls_of_succs = df_cpm[df_cpm['Activity'].isin(successors[activity])]['LS'].min()
              df_cpm.loc[idx, 'LF'] = min_ls_of_succs if pd.notna(min_ls_of_succs) else project_duration
          
          df_cpm.loc[idx, 'LS'] = df_cpm.loc[idx, 'LF'] - df_cpm.loc[idx, 'Duration']

    # --- Slack Calculation ---
    df_cpm['Slack'] = df_cpm['LS'] - df_cpm['ES']
    df_cpm['Is Critical'] = df_cpm['Slack'] == 0
    
    return df_cpm, project_duration

# --- Main App ---

st.title("⏱️ Interactive Project Crashing Activity")
st.markdown("""
This tool helps you practice **Project Crashing**. The goal is to shorten the project duration by spending more money on certain activities.
The best activities to "crash" are on the **critical path** and have the **lowest crash cost per day**.
""")
st.info("💡 **Instructions:**\n1. Define your project activities in the table below. \n2. Click 'Calculate Initial Plan' to see the starting duration, cost, and critical path. \n3. Use the 'Crash an Activity' section to incrementally shorten the project. Observe how the costs and critical path change!")


# --- Initial Data Setup ---
if 'project_data' not in st.session_state:
    # Use a default example project
    st.session_state.initial_project_data = pd.DataFrame([
        {'Activity': 'A', 'Predecessors': '-',   'Normal Time': 5, 'Normal Cost': 500, 'Crash Time': 4, 'Crash Cost': 700},
        {'Activity': 'B', 'Predecessors': 'A',   'Normal Time': 3, 'Normal Cost': 300, 'Crash Time': 2, 'Crash Cost': 450},
        {'Activity': 'C', 'Predecessors': 'A',   'Normal Time': 4, 'Normal Cost': 400, 'Crash Time': 3, 'Crash Cost': 600},
        {'Activity': 'D', 'Predecessors': 'B',   'Normal Time': 6, 'Normal Cost': 800, 'Crash Time': 4, 'Crash Cost': 1100},
        {'Activity': 'E', 'Predecessors': 'C',   'Normal Time': 5, 'Normal Cost': 600, 'Crash Time': 4, 'Crash Cost': 800},
        {'Activity': 'F', 'Predecessors': 'D,E', 'Normal Time': 3, 'Normal Cost': 200, 'Crash Time': 3, 'Crash Cost': 200}
    ])
    st.session_state.project_data = st.session_state.initial_project_data.copy()
    st.session_state.calculated = False


# --- Input Section ---
st.subheader("1. Define Project Activities")

with st.expander("Edit Project Data", expanded=True):
    edited_data = st.data_editor(
        st.session_state.initial_project_data,
        num_rows="dynamic",
        key="data_editor"
    )

col1, col2, _ = st.columns([1, 1, 4])
if col1.button("Calculate Initial Plan", use_container_width=True, type="primary"):
    # Calculate crash cost per period
    edited_data['Crash Cost/Period'] = (edited_data['Crash Cost'] - edited_data['Normal Cost']) / (edited_data['Normal Time'] - edited_data['Crash Time'])
    edited_data['Crash Cost/Period'] = edited_data['Crash Cost/Period'].fillna(0).astype(int)
    
    # Initialize current state
    edited_data['Duration'] = edited_data['Normal Time']
    edited_data['Current Cost'] = edited_data['Normal Cost']
    
    st.session_state.project_data = edited_data
    st.session_state.initial_project_data = edited_data.copy() # Save the user's new base
    st.session_state.calculated = True
    st.session_state.crash_history = []
    st.rerun()

if col2.button("Reset to Default", use_container_width=True):
    # Completely reset the session state to the original default
    del st.session_state.project_data
    del st.session_state.initial_project_data
    del st.session_state.calculated
    st.rerun()


# --- Calculation and Display Section ---
if st.session_state.calculated:
    st.divider()
    
    # Perform CPM Calculation
    cpm_df, duration = calculate_cpm(st.session_state.project_data)
    total_cost = cpm_df['Current Cost'].sum()
    critical_path_str = " → ".join(cpm_df[cpm_df['Is Critical']]['Activity'])

    st.subheader("2. Analyze Current Project Plan")
    
    # --- Display Metrics ---
    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Project Duration", f"{duration} Days")
    metric2.metric("Total Cost", f"${total_cost:,.0f}")
    metric3.metric("Critical Path(s)", critical_path_str)

    # --- Display Detailed Table ---
    st.dataframe(cpm_df.style.apply(
        lambda row: ['background-color: #f0f2f6' if row['Is Critical'] else '' for _ in row], axis=1
    ))

    st.divider()

    # --- Crashing Section ---
    st.subheader("3. Crash an Activity")

    # Filter for crashable activities on the critical path
    critical_activities = cpm_df[cpm_df['Is Critical']].copy()
    crashable_options = critical_activities[
        critical_activities['Duration'] > critical_activities['Crash Time']
    ].sort_values(by='Crash Cost/Period')

    if not crashable_options.empty:
        crash_col1, crash_col2 = st.columns([2,1])
        
        with crash_col1:
            activity_to_crash = st.selectbox(
                "Select Activity to Crash (Sorted by best value)",
                options=crashable_options['Activity'],
                format_func=lambda x: f"{x} (Cost: ${crashable_options.loc[crashable_options['Activity'] == x, 'Crash Cost/Period'].iloc[0]} per day)"
            )
        
        selected_activity_data = st.session_state.project_data[st.session_state.project_data['Activity'] == activity_to_crash].iloc[0]
        
        with crash_col2:
            if st.button(f"Crash '{activity_to_crash}' by 1 Day", type="primary", use_container_width=True):
                # Update project data in session state
                idx_to_update = st.session_state.project_data.index[st.session_state.project_data['Activity'] == activity_to_crash][0]
                
                st.session_state.project_data.loc[idx_to_update, 'Duration'] -= 1
                st.session_state.project_data.loc[idx_to_update, 'Current Cost'] += selected_activity_data['Crash Cost/Period']
                
                # Log the change
                st.session_state.crash_history.append(
                    f"Crashed '{activity_to_crash}'. Duration: {duration} → {duration-1} days. Cost: ${total_cost:,.0f} → ${total_cost + selected_activity_data['Crash Cost/Period']:,.0f}."
                )
                st.rerun()

    else:
        st.warning("No more activities on the critical path can be crashed.")

    # Display crash history
    if st.session_state.get('crash_history'):
        with st.expander("Show Crash History"):
            for entry in reversed(st.session_state.crash_history):
                st.write(f"🔹 {entry}")
