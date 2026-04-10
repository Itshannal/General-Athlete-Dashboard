################ Importing Packages ################
import streamlit as st #framework
import pandas as pd #data analysis
import plotly.express as px #graphing

################ Page Config ################
st.set_page_config(page_title="Athlete Performance Dashboard", layout="wide")


################ Load Data ################
@st.cache_data
def load_data():
    df = pd.read_csv('athlete_data.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    return df

df = load_data()

################ Sidebar Filters ################
st.sidebar.header("Filters")
athlete_list = ["All"] + list(df['Athlete_ID'].unique())
selected_athlete = st.sidebar.selectbox("Select Athlete", athlete_list)

date_range = st.sidebar.date_input(
    "Date Range",
    value=(df['Date'].min(), df['Date'].max()),
    min_value=df['Date'].min(),
    max_value=df['Date'].max()
)

filtered_df = df.copy()
if selected_athlete != "All":
    filtered_df = filtered_df[filtered_df['Athlete_ID'] == selected_athlete]

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]


# ---CALCULATE ACWR  ---
def calculate_acwr(group):
    group = group.sort_values('Date').set_index('Date')
    acute = group['Load'].rolling(window='7D').mean()
    chronic = group['Load'].rolling(window='28D').mean()
    group['ACWR'] = (acute / chronic)
    return group.reset_index()


if not filtered_df.empty:
    df_acwr = filtered_df.groupby('Athlete_ID', group_keys=False).apply(calculate_acwr)
else:
    df_acwr = filtered_df.copy()



################# Main Tabs #################
st.title("Athlete Monitoring")
tab_load, tab_recovery, tab_analysis, tab_entry  = st.tabs(["Training Load", "Recovery & Wellness", "Advanced Analysis", "Data Entry"])

# --- TAB 1: TRAINING LOAD ---
with tab_entry:
    st.header(" Data Entry")

    import pandas as pd
    import streamlit as st
    from datetime import date

    st.divider()
    st.header("Data Entry Form")

    with st.form("daily_entry_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            # Date and Athlete Selection
            entry_date = st.date_input("Session Date", value=date.today())
            entry_athlete = st.selectbox("Athlete ID", df['Athlete_ID'].unique())
            entry_load = st.number_input("Training Load (AU)", min_value=0, max_value=2000, step=10)

        with col2:
            # Performance Metrics
            entry_hsd = st.number_input("High Speed Distance (m)", min_value=0, max_value=5000, step=50)
            entry_accel = st.number_input("Accelerations", min_value=0, max_value=500, step=1)
            entry_sleep = st.slider("Sleep Duration (Hours)", 4.0, 12.0, 8.0, 0.5)

        with col3:
            # Wellness Metrics (1-10)
            entry_fatigue = st.select_slider("Fatigue Level (1=Fresh, 10=Exhausted)", options=range(1, 11), value=3)
            entry_stress = st.select_slider("Stress Level (1=Low, 10=High)", options=range(1, 11), value=3)
            entry_soreness = st.select_slider("Soreness Level (1=None, 10=Severe)", options=range(1, 11), value=3)

        submitted = st.form_submit_button("Submit Session Data")

        if submitted:
            # Create a new row
            new_data = {
                'Date': entry_date.strftime('%Y-%m-%d'),
                'Athlete_ID': entry_athlete,
                'Load': entry_load,
                'HSD': entry_hsd,
                'Accel': entry_accel,
                'Sleep': entry_sleep,
                'Fatigue': entry_fatigue,
                'Stress': entry_stress,
                'Soreness': entry_soreness
            }

            # Convert to DataFrame and append to CSV
            new_df = pd.DataFrame([new_data])
            new_df.to_csv('athlete_data.csv', mode='a', header=False, index=False)

            st.success(f"Data for {entry_athlete} on {entry_date} successfully saved!")
            st.info("The charts above will update once the page refreshes.")
            st.balloons()
    if st.button("Delete Last Entry"):
        df_current = pd.read_csv('athlete_data.csv')
        if not df_current.empty:
            df_updated = df_current.iloc[:-1]  # Remove last row
            df_updated.to_csv('athlete_data.csv', index=False)
            st.warning("Last entry deleted. Please refresh the page.")
        else:
            st.error("CSV is already empty.")



with tab_load:
    st.header("Training Load")


    st.subheader("Weekly Player Load")
    fig_load = px.line(df_acwr, x='Date', y='Load', color='Athlete_ID', markers=True)
    st.plotly_chart(fig_load, use_container_width=True)

    st.subheader("High Speed Distance (HSD)")
    fig_hsd = px.bar(filtered_df, x='Date', y='HSD', color='Athlete_ID', barmode='group')
    st.plotly_chart(fig_hsd, use_container_width=True)

    st.subheader("Acute:Chronic Workload Ratio (ACWR)")
    fig_acwr = px.line(df_acwr, x='Date', y='ACWR', color='Athlete_ID')
    fig_acwr.add_hrect(y0=0.8, y1=1.3, fillcolor="green", opacity=0.2, annotation_text="Sweet Spot")
    fig_acwr.add_hline(y=0.8, line_dash="dot", line_color="blue", annotation_text="Under-training (<0.8)")
    fig_acwr.add_hline(y=1.5, line_dash="dash", line_color="red", annotation_text="High Risk (>1.5)")
    st.plotly_chart(fig_acwr, use_container_width=True)

# --- TAB 2: RECOVERY & WELLNESS ---
with tab_recovery:
    st.header("Recovery & Wellness")

    # KPI Tiles for quick viewing
    c1, c2, c3 = st.columns(3)
    c1.metric("Average Sleep", f"{filtered_df['Sleep'].mean():.1f} hrs")
    c2.metric("Average Fatigue", f"{filtered_df['Fatigue'].mean():.1f}/10")
    c3.metric("Average Soreness", f"{filtered_df['Soreness'].mean():.1f}/10")




    st.subheader("Sleep vs. Fatigue Correlation")
        # Scatter plot to see if more sleep = less fatigue
    fig_sleep = px.scatter(filtered_df, x='Sleep', y='Fatigue', color='Athlete_ID',
                               trendline="ols")
    st.plotly_chart(fig_sleep, use_container_width=True)


    st.subheader("Stress Score Heatmap")
    stress_pivot = filtered_df.pivot(index='Athlete_ID', columns='Date', values='Stress')
    fig_heat = px.imshow(stress_pivot, color_continuous_scale='RdYlGn_r')
    st.plotly_chart(fig_heat, use_container_width=True)

    import plotly.graph_objects as go

    #Radar Chart
    if selected_athlete != "All":
        st.subheader(f"Recovery Profile")

        # 1. Get data for the specific athlete (Latest session)
        athlete_latest = filtered_df[filtered_df['Athlete_ID'] == selected_athlete].iloc[-1]

        # 2. Get Team Average for the same metrics
        team_avg = df[['Sleep', 'Fatigue', 'Stress', 'Soreness']].mean()

        # Define metrics for the radar
        # Note: We "invert" Fatigue, Stress, and Soreness so that 10 is always 'GOOD'
        categories = ['Sleep', 'Fatigue (Inverted)', 'Stress (Inverted)', 'Soreness (Inverted)']

        athlete_values = [
            (athlete_latest['Sleep'] / 9) * 10,  # Scale sleep to 10
            11 - athlete_latest['Fatigue'],
            11 - athlete_latest['Stress'],
            11 - athlete_latest['Soreness']
        ]

        team_values = [
            (team_avg['Sleep'] / 9) * 10,
            11 - team_avg['Fatigue'],
            11 - team_avg['Stress'],
            11 - team_avg['Soreness']
        ]

        # Create Radar Chart
        fig_radar = go.Figure()

        fig_radar.add_trace(go.Scatterpolar(
            r=athlete_values,
            theta=categories,
            fill='toself',
            name=selected_athlete,
            line_color='rgb(31, 119, 180)'
        ))

        fig_radar.add_trace(go.Scatterpolar(
            r=team_values,
            theta=categories,
            fill='toself',
            name='Team Average',
            line_color='rgba(255, 0, 0, 0.5)',
            line_dash='dot'
        ))

        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 10])
            ),
            showlegend=True,
            title=f"{selected_athlete}"
        )

        st.plotly_chart(fig_radar, use_container_width=True)
    else:
        st.info("Select a specific athlete in the sidebar to view their Readiness Radar.")

# --- TAB 3: ADVANCED ANALYSIS ---
with tab_analysis:
    st.header("Team Correlations")
    # Correlation Matrix
    corr = filtered_df[['Load', 'HSD', 'Sleep', 'Fatigue', 'Stress', 'Soreness']].corr()
    fig_corr = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r')
    st.plotly_chart(fig_corr, use_container_width=True)

    st.subheader("Raw Filtered Data")
    st.dataframe(filtered_df)

