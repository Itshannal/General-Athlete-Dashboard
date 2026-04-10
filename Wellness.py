################ Importing Packages ################
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import date, datetime

################ Page Config ################
st.set_page_config(page_title="Athlete Performance Dashboard", layout="wide")

################ Data Initialization ################
CSV_FILE = 'athlete_data.csv'

# Ensure CSV exists with correct headers
if not os.path.exists(CSV_FILE):
    df_init = pd.DataFrame(columns=[
        'Date', 'Athlete_ID', 'Load', 'HSD', 'Accel',
        'Sleep', 'Fatigue', 'Stress', 'Soreness'
    ])
    df_init.to_csv(CSV_FILE, index=False)


################ Load Data ################
@st.cache_data(ttl=60)  # Cache for 1 minute to allow updates to show
def load_data():
    df = pd.read_csv(CSV_FILE)
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
    return df


df = load_data()

################ Sidebar Filters ################
st.sidebar.header("Filters")

if not df.empty:
    athlete_list = ["All"] + sorted(list(df['Athlete_ID'].unique()))
    selected_athlete = st.sidebar.selectbox("Select Athlete", athlete_list)

    # Date Filter
    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Filtering Logic
    filtered_df = df.copy()
    if selected_athlete != "All":
        filtered_df = filtered_df[filtered_df['Athlete_ID'] == selected_athlete]

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]
else:
    st.sidebar.warning("No data found in CSV.")
    filtered_df = pd.DataFrame()
    selected_athlete = "All"


# --- CALCULATE ACWR ---
def calculate_acwr(group):
    group = group.sort_values('Date').set_index('Date')
    # Use 7D and 28D rolling averages
    acute = group['Load'].rolling(window='7D').mean()
    chronic = group['Load'].rolling(window='28D').mean()
    group['ACWR'] = (acute / chronic)
    return group.reset_index()


if not filtered_df.empty and 'Load' in filtered_df.columns:
    df_acwr = filtered_df.groupby('Athlete_ID', group_keys=False).apply(calculate_acwr)
else:
    df_acwr = filtered_df.copy()

################# Main UI #################
st.title("Athlete Monitoring Dashboard")
tab_load, tab_recovery, tab_analysis, tab_entry = st.tabs([
    "📈 Training Load", "🛌 Recovery & Wellness", "🔬 Advanced Analysis", "📝 Data Entry"
])

# --- TAB 1: TRAINING LOAD ---
with tab_load:
    if not df_acwr.empty:
        st.subheader("Weekly Player Load")
        fig_load = px.line(df_acwr, x='Date', y='Load', color='Athlete_ID', markers=True)
        st.plotly_chart(fig_load, use_container_width=True)

        st.subheader("High Speed Distance (HSD)")
        fig_hsd = px.bar(filtered_df, x='Date', y='HSD', color='Athlete_ID', barmode='group')
        st.plotly_chart(fig_hsd, use_container_width=True)

        st.subheader("Acute:Chronic Workload Ratio (ACWR)")
        fig_acwr = px.line(df_acwr, x='Date', y='ACWR', color='Athlete_ID')
        fig_acwr.add_hrect(y0=0.8, y1=1.3, fillcolor="green", opacity=0.1, annotation_text="Sweet Spot")
        fig_acwr.add_hline(y=1.5, line_dash="dash", line_color="red", annotation_text="Danger Zone")
        st.plotly_chart(fig_acwr, use_container_width=True)
    else:
        st.info("Please enter data in the 'Data Entry' tab to see analysis.")

# --- TAB 2: RECOVERY & WELLNESS ---
with tab_recovery:
    if not filtered_df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Sleep", f"{filtered_df['Sleep'].mean():.1f} hrs")
        c2.metric("Avg Fatigue", f"{filtered_df['Fatigue'].mean():.1f}/10")
        c3.metric("Avg Soreness", f"{filtered_df['Soreness'].mean():.1f}/10")

        st.subheader("Sleep vs. Fatigue Correlation")
        fig_sleep = px.scatter(filtered_df, x='Sleep', y='Fatigue', color='Athlete_ID', trendline="ols")
        st.plotly_chart(fig_sleep, use_container_width=True)

        # Radar Chart for Specific Athlete
        if selected_athlete != "All":
            st.subheader(f"Readiness Radar: {selected_athlete}")
            athlete_latest = filtered_df[filtered_df['Athlete_ID'] == selected_athlete].iloc[-1]
            team_avg = df[['Sleep', 'Fatigue', 'Stress', 'Soreness']].mean()

            categories = ['Sleep', 'Fatigue', 'Stress', 'Soreness']

            # Normalizing/Inverting so "Outward" on radar is always "Good"
            athlete_vals = [(athlete_latest['Sleep'] / 10) * 10, 11 - athlete_latest['Fatigue'],
                            11 - athlete_latest['Stress'], 11 - athlete_latest['Soreness']]
            team_vals = [(team_avg['Sleep'] / 10) * 10, 11 - team_avg['Fatigue'], 11 - team_avg['Stress'],
                         11 - team_avg['Soreness']]

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=athlete_vals, theta=categories, fill='toself', name=selected_athlete))
            fig_radar.add_trace(
                go.Scatterpolar(r=team_vals, theta=categories, fill='toself', name='Team Avg', line_dash='dot'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])))
            st.plotly_chart(fig_radar, use_container_width=True)
    else:
        st.info("No data available for recovery metrics.")

# --- TAB 3: ADVANCED ANALYSIS ---
with tab_analysis:
    if len(filtered_df) > 1:
        st.header("Team Correlations")
        numeric_cols = filtered_df.select_dtypes(include=['float64', 'int64']).columns
        corr = filtered_df[numeric_cols].corr()
        fig_corr = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r')
        st.plotly_chart(fig_corr, use_container_width=True)

        st.subheader("Raw Filtered Data")
        st.dataframe(filtered_df)
    else:
        st.info("Not enough data for correlation analysis.")

# --- TAB 4: DATA ENTRY ---
with tab_entry:
    st.header("Daily Data Entry")
    with st.form("entry_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            e_date = st.date_input("Date", value=date.today())
            e_id = st.text_input("Athlete ID (e.g. Player_1)")
            e_load = st.number_input("Load (AU)", 0, 2000, 300)
        with col2:
            e_hsd = st.number_input("HSD (m)", 0, 5000, 200)
            e_accel = st.number_input("Accels", 0, 500, 20)
            e_sleep = st.slider("Sleep (hrs)", 4.0, 12.0, 8.0)
        with col3:
            e_fatigue = st.slider("Fatigue (1-10)", 1, 10, 3)
            e_stress = st.slider("Stress (1-10)", 1, 10, 3)
            e_sore = st.slider("Soreness (1-10)", 1, 10, 3)

        submitted = st.form_submit_button("Save Session")
        if submitted:
            if not e_id:
                st.error("Please enter an Athlete ID")
            else:
                new_row = pd.DataFrame([{
                    'Date': e_date.strftime('%Y-%m-%d'),
                    'Athlete_ID': e_id,
                    'Load': e_load, 'HSD': e_hsd, 'Accel': e_accel,
                    'Sleep': e_sleep, 'Fatigue': e_fatigue,
                    'Stress': e_stress, 'Soreness': e_sore
                }])
                new_row.to_csv(CSV_FILE, mode='a', header=False, index=False)
                st.cache_data.clear()  # Clear cache so data shows up immediately
                st.success("Data Saved! Refreshing...")
                st.rerun()

    if st.button("🗑️ Delete Last Entry"):
        df_current = pd.read_csv(CSV_FILE)
        if not df_current.empty:
            df_current.iloc[:-1].to_csv(CSV_FILE, index=False)
            st.cache_data.clear()
            st.warning("Last entry removed.")
            st.rerun()
