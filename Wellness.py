################ Importing Packages ################
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

################ Page Config ################
st.set_page_config(page_title="Athlete Performance Dashboard", layout="wide")

################ Load Data ################
@st.cache_data
def load_data():
    # Attempt to load, create if missing to prevent crash
    try:
        df = pd.read_csv('athlete_data.csv')
        df['Date'] = pd.to_datetime(df['Date'])
    except FileNotFoundError:
        # Fallback empty dataframe with required columns
        df = pd.DataFrame(columns=['Date', 'Athlete_ID', 'Load', 'HSD', 'Accel', 'Sleep', 'Fatigue', 'Stress', 'Soreness'])
    return df

df = load_data()

################ Sidebar Filters ################
st.sidebar.header("Filters")
athlete_list = ["All"] + list(df['Athlete_ID'].unique())
selected_athlete = st.sidebar.selectbox("Select Athlete", athlete_list)

# Handle empty dataframe for date_input
if not df.empty:
    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()
else:
    min_date = date.today()
    max_date = date.today()

date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

filtered_df = df.copy()
if selected_athlete != "All":
    filtered_df = filtered_df[filtered_df['Athlete_ID'] == selected_athlete]

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]

# --- FIXED ACWR CALCULATION ---
def calculate_acwr(group):
    # 1. Capture the ID immediately so we don't lose it
    current_id = group['Athlete_ID'].iloc[0]
    
    # 2. Sort and handle index
    group = group.sort_values('Date').set_index('Date')
    
    # 3. Create a complete date range for this specific athlete
    idx = pd.date_range(group.index.min(), group.index.max())
    
    # 4. Reindex and fill only the numeric Load with 0
    group = group.reindex(idx)
    group['Load'] = group['Load'].fillna(0)
    
    # 5. Restore the Athlete_ID for the newly created date rows
    group['Athlete_ID'] = current_id
    
    # 6. Calculate rolling metrics
    # window='7D' looks at the last 7 days of the index
    acute = group['Load'].rolling(window='7D', min_periods=1).mean()
    chronic = group['Load'].rolling(window='28D', min_periods=1).mean()
    
    group['ACWR'] = (acute / chronic)
    
    return group.reset_index().rename(columns={'index': 'Date'})

if not filtered_df.empty:
    # Group by Athlete and apply calculation
    df_acwr = filtered_df.groupby('Athlete_ID', group_keys=False).apply(calculate_acwr)
else:
    df_acwr = pd.DataFrame()

################# Main Tabs #################
st.title("Athlete Monitoring")
tab_load, tab_recovery, tab_analysis, tab_entry = st.tabs(["Training Load", "Recovery & Wellness", "Advanced Analysis", "Data Entry"])

# --- TAB 1: DATA ENTRY (Moved to end in code but stays as tab) ---
with tab_entry:
    st.header("Data Entry Form")
    with st.form("daily_entry_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            entry_date = st.date_input("Session Date", value=date.today())
            entry_athlete = st.selectbox("Athlete ID", df['Athlete_ID'].unique() if not df.empty else ["N/A"])
            entry_load = st.number_input("Training Load (AU)", min_value=0, max_value=2000, step=10)
        with col2:
            entry_hsd = st.number_input("High Speed Distance (m)", min_value=0, max_value=5000, step=50)
            entry_accel = st.number_input("Accelerations", min_value=0, max_value=500, step=1)
            entry_sleep = st.slider("Sleep Duration (Hours)", 4.0, 12.0, 8.0, 0.5)
        with col3:
            entry_fatigue = st.select_slider("Fatigue (1=Fresh, 10=Exhausted)", options=range(1, 11), value=3)
            entry_stress = st.select_slider("Stress (1=Low, 10=High)", options=range(1, 11), value=3)
            entry_soreness = st.select_slider("Soreness (1=None, 10=Severe)", options=range(1, 11), value=3)

        submitted = st.form_submit_button("Submit Session Data")
        if submitted:
            new_row = [entry_date, entry_athlete, entry_load, entry_hsd, entry_accel, entry_sleep, entry_fatigue, entry_stress, entry_soreness]
            new_df = pd.DataFrame([new_row])
            new_df.to_csv('athlete_data.csv', mode='a', header=False, index=False)
            st.success("Data Saved! Please refresh page.")
            st.balloons()

    if st.button("Delete Last Entry"):
        df_current = pd.read_csv('athlete_data.csv')
        if not df_current.empty:
            df_current.iloc[:-1].to_csv('athlete_data.csv', index=False)
            st.warning("Last entry deleted.")

# --- TAB 2: TRAINING LOAD ---
with tab_load:
    if not df_acwr.empty:
        st.subheader("Weekly Player Load")
        fig_load = px.line(df_acwr, x='Date', y='Load', color='Athlete_ID', markers=True)
        st.plotly_chart(fig_load, use_container_width=True)

        st.subheader("Acute:Chronic Workload Ratio (ACWR)")
        fig_acwr_plot = px.line(df_acwr, x='Date', y='ACWR', color='Athlete_ID')
        fig_acwr_plot.add_hrect(y0=0.8, y1=1.3, fillcolor="green", opacity=0.2, annotation_text="Sweet Spot")
        fig_acwr_plot.add_hline(y=1.5, line_dash="dash", line_color="red", annotation_text="Danger Zone")
        st.plotly_chart(fig_acwr_plot, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

# --- TAB 3: RECOVERY & WELLNESS ---
with tab_recovery:
    if not filtered_df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Sleep", f"{filtered_df['Sleep'].mean():.1f} hrs")
        c2.metric("Avg Fatigue", f"{filtered_df['Fatigue'].mean():.1f}/10")
        c3.metric("Avg Soreness", f"{filtered_df['Soreness'].mean():.1f}/10")

        if selected_athlete != "All":
            athlete_latest = filtered_df.iloc[-1]
            team_avg = df[['Sleep', 'Fatigue', 'Stress', 'Soreness']].mean()
            categories = ['Sleep', 'Fatigue (Inv)', 'Stress (Inv)', 'Soreness (Inv)']
            
            # Inverting scales so larger area = better recovery
            a_vals = [(athlete_latest['Sleep']/9)*10, 11-athlete_latest['Fatigue'], 11-athlete_latest['Stress'], 11-athlete_latest['Soreness']]
            t_vals = [(team_avg['Sleep']/9)*10, 11-team_avg['Fatigue'], 11-team_avg['Stress'], 11-team_avg['Soreness']]

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=a_vals, theta=categories, fill='toself', name=selected_athlete))
            fig_radar.add_trace(go.Scatterpolar(r=t_vals, theta=categories, fill='toself', name='Team Avg'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])))
            st.plotly_chart(fig_radar, use_container_width=True)
    else:
        st.info("Adjust filters to see recovery data.")

# --- TAB 4: ADVANCED ANALYSIS ---
with tab_analysis:
    if not filtered_df.empty:
        corr = filtered_df[['Load', 'HSD', 'Sleep', 'Fatigue', 'Stress', 'Soreness']].corr()
        st.plotly_chart(px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r'), use_container_width=True)
        st.dataframe(filtered_df)
