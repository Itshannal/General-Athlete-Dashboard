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
    try:
        df = pd.read_csv('athlete_data.csv')
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=['Date', 'Athlete_ID', 'Load', 'HSD', 'Accel', 'Sleep', 'Fatigue', 'Stress', 'Soreness'])

df = load_data()

################ Sidebar Filters ################
st.sidebar.header("Filters")
athlete_list = ["All"] + list(df['Athlete_ID'].unique())
selected_athlete = st.sidebar.selectbox("Select Athlete", athlete_list)

if not df.empty:
    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()
else:
    min_date, max_date = date.today(), date.today()

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

# Sort by date once to ensure all charts look correct
filtered_df = filtered_df.sort_values('Date')

################# Main Tabs #################
st.title("Athlete Monitoring")
tab_load, tab_recovery, tab_analysis, tab_entry = st.tabs(["Training Load", "Recovery & Wellness", "Advanced Analysis", "Data Entry"])

# --- TAB 1: TRAINING LOAD ---
with tab_load:
    st.header("Training Load")
    if not filtered_df.empty:
        st.subheader("Daily Player Load")
        fig_load = px.line(filtered_df, x='Date', y='Load', color='Athlete_ID', markers=True)
        st.plotly_chart(fig_load, use_container_width=True)

        st.subheader("High Speed Distance (HSD)")
        fig_hsd = px.bar(filtered_df, x='Date', y='HSD', color='Athlete_ID', barmode='group')
        st.plotly_chart(fig_hsd, use_container_width=True)
    else:
        st.info("No data found for the current filters.")

# --- TAB 2: RECOVERY & WELLNESS ---
with tab_recovery:
    st.header("Recovery & Wellness")
    if not filtered_df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Sleep", f"{filtered_df['Sleep'].mean():.1f} hrs")
        c2.metric("Avg Fatigue", f"{filtered_df['Fatigue'].mean():.1f}/10")
        c3.metric("Avg Soreness", f"{filtered_df['Soreness'].mean():.1f}/10")

        st.subheader("Sleep vs. Fatigue Correlation")
        fig_sleep = px.scatter(filtered_df, x='Sleep', y='Fatigue', color='Athlete_ID', trendline="ols")
        st.plotly_chart(fig_sleep, use_container_width=True)

        if selected_athlete != "All" and len(filtered_df) > 0:
            st.subheader("Recovery Profile")
            athlete_latest = filtered_df.iloc[-1]
            team_avg = df[['Sleep', 'Fatigue', 'Stress', 'Soreness']].mean()
            categories = ['Sleep', 'Fatigue (Inv)', 'Stress (Inv)', 'Soreness (Inv)']

            a_vals = [(athlete_latest['Sleep']/9)*10, 11-athlete_latest['Fatigue'], 11-athlete_latest['Stress'], 11-athlete_latest['Soreness']]
            t_vals = [(team_avg['Sleep']/9)*10, 11-team_avg['Fatigue'], 11-team_avg['Stress'], 11-team_avg['Soreness']]

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=a_vals, theta=categories, fill='toself', name=selected_athlete))
            fig_radar.add_trace(go.Scatterpolar(r=t_vals, theta=categories, fill='toself', name='Team Avg', line_dash='dot'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=True)
            st.plotly_chart(fig_radar, use_container_width=True)

# --- TAB 3: ADVANCED ANALYSIS ---
with tab_analysis:
    st.header("Team Correlations")
    if not filtered_df.empty:
        numeric_cols = filtered_df.select_dtypes(include=['number'])
        if not numeric_cols.empty:
            corr = numeric_cols.corr()
            st.plotly_chart(px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r'), use_container_width=True)
        st.dataframe(filtered_df)

# --- TAB 4: DATA ENTRY ---
with tab_entry:
    st.header("Data Entry Form")
    with st.form("daily_entry_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            e_date = st.date_input("Session Date", value=date.today())
            e_id = st.selectbox("Athlete ID", df['Athlete_ID'].unique() if not df.empty else ["Add New"])
            e_load = st.number_input("Training Load (AU)", min_value=0, max_value=2000, step=10)
        with col2:
            e_hsd = st.number_input("HSD (m)", min_value=0, max_value=5000, step=50)
            e_accel = st.number_input("Accelerations", min_value=0, max_value=500, step=1)
            e_sleep = st.slider("Sleep (Hours)", 4.0, 12.0, 8.0, 0.5)
        with col3:
            e_fatigue = st.select_slider("Fatigue (1-10)", options=range(1, 11), value=3)
            e_stress = st.select_slider("Stress (1-10)", options=range(1, 11), value=3)
            e_sore = st.select_slider("Soreness (1-10)", options=range(1, 11), value=3)

        if st.form_submit_button("Submit"):
            new_row = pd.DataFrame([{
                'Date': e_date.strftime('%Y-%m-%d'), 'Athlete_ID': e_id, 'Load': e_load, 
                'HSD': e_hsd, 'Accel': e_accel, 'Sleep': e_sleep, 
                'Fatigue': e_fatigue, 'Stress': e_stress, 'Soreness': e_sore
            }])
            new_row.to_csv('athlete_data.csv', mode='a', header=False, index=False)
            st.success("Entry Saved!")

    if st.button("Delete Last Entry"):
        df_curr = pd.read_csv('athlete_data.csv')
        if not df_curr.empty:
            df_curr.iloc[:-1].to_csv('athlete_data.csv', index=False)
            st.warning("Last entry deleted.")
