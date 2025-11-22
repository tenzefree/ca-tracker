import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import time
import os
import io
from datetime import datetime, date, timedelta

# --- APP CONFIGURATION ---
st.set_page_config(page_title="CA Final Zen", page_icon="🧘", layout="centered")

# --- CONSTANTS ---
DATA_FILE = "ca_final_data.json"
EXAM_DATE = date(2026, 5, 1)
SUBJECTS = ["FR", "AFM", "Audit", "DT", "IDT", "IBS", "SPOM"]
TARGET_HOURS = {"FR": 250, "AFM": 200, "Audit": 150, "DT": 200, "IDT": 150, "IBS": 100, "SPOM": 80}

# --- DATA ENGINE ---
def load_data():
    if not os.path.exists(DATA_FILE): return []
    try:
        with open(DATA_FILE, 'r') as f: return json.load(f)
    except: return []

def save_data(data):
    with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=4)

def add_entry(entry):
    data = load_data()
    data.append(entry)
    save_data(data)

def get_streak(df):
    if df.empty: return 0
    dates = pd.to_datetime(df['Date']).dt.date.unique()
    dates.sort()
    streak = 0
    today = date.today()
    
    # Check if we studied today or yesterday to keep streak alive
    if today in dates:
        streak = 1
        check_date = today - timedelta(days=1)
    elif (today - timedelta(days=1)) in dates:
        streak = 0 # Will start counting loop below
        check_date = today - timedelta(days=1)
    else:
        return 0
        
    # Count backwards
    for i in range(len(dates)):
        if check_date in dates:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    return streak

# --- STYLING ---
st.markdown("""
    <style>
    .stApp {background-color: #f9f9f9;}
    .big-font {font-size:20px !important;}
    div[data-testid="stMetricValue"] {font-size: 24px;}
    </style>
    """, unsafe_allow_html=True)

# --- MAIN LOGIC ---
if 'start_time' not in st.session_state: st.session_state.start_time = None

# --- TABS ---
tab_focus, tab_insights, tab_data = st.tabs(["🧘 Focus", "📊 Insights", "⚙️ Vault"])

# =========================================
# TAB 1: FOCUS (The Simple Timer)
# =========================================
with tab_focus:
    # 1. HEADER: DAYS LEFT
    days_left = (EXAM_DATE - date.today()).days
    st.progress((1000 - days_left)/1000, text=f"⏳ {days_left} Days to May '26")

    # 2. TIMER LOGIC
    if st.session_state.start_time is None:
        # --- IDLE STATE ---
        st.markdown("### 🎯 Start a Session")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            task_input = st.selectbox("Subject", SUBJECTS)
        with col2:
            mode = st.selectbox("Type", ["Study", "Class", "Practice", "Review"])
            
        topic = st.text_input("Topic (Optional)", placeholder="What are you learning?")
        st.session_state.temp_topic = topic
        
        st.write("")
        if st.button("⭕ START FOCUS", type="primary", use_container_width=True):
            st.session_state.start_time = time.time()
            st.session_state.current_task = task_input
            st.session_state.current_mode = mode
            st.rerun()
            
        # Quick Daily Stats below button
        data = load_data()
        if data:
            df = pd.DataFrame(data)
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_mins = df[df['Date'] == today_str]['Duration'].sum()
            
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Today", f"{int(today_mins)}m")
            c2.metric("Streak", f"🔥 {get_streak(df)} days")
            c3.metric("Entries", len(df))

    else:
        # --- RUNNING STATE (Minimalist) ---
        elapsed = time.time() - st.session_state.start_time
        
        st.markdown(f"""
        <div style='text-align: center; padding: 40px; background: white; border-radius: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <h2 style='color: #555;'>{st.session_state.current_mode}: {st.session_state.current_task}</h2>
            <h1 style='font-size: 80px; color: #FF4B4B; margin: 10px 0;'>
                {time.strftime('%H:%M:%S', time.gmtime(elapsed))}
            </h1>
            <p style='color: #888;'>Stay focused. Put the phone away.</p>
        </div>
        <br>
        """, unsafe_allow_html=True)

        if st.button("⏹️ STOP SESSION", type="secondary", use_container_width=True):
            st.session_state.duration = time.time() - st.session_state.start_time
            st.session_state.start_time = None
            st.session_state.show_save = True
            st.rerun()
        
        time.sleep(1)
        st.rerun()

    # --- SAVE DIALOG ---
    if st.session_state.get("show_save"):
        with st.expander("💾 Save Session", expanded=True):
            focus = st.slider("How focused were you?", 1, 5, 4)
            mins = st.session_state.duration / 60
            
            if st.button("Confirm & Save"):
                entry = {
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Task": st.session_state.current_task, # Subject
                    "Mode": st.session_state.current_mode, # Type
                    "Topic": st.session_state.temp_topic,
                    "Duration": round(mins, 2),
                    "Focus": focus,
                    "Effective": round(mins * (focus/5), 2)
                }
                add_entry(entry)
                st.session_state.show_save = False
                st.toast("Saved! Great work!", icon="🚀")
                time.sleep(1)
                st.rerun()

# =========================================
# TAB 2: INSIGHTS (Visuals)
# =========================================
with tab_insights:
    data = load_data()
    if not data:
        st.info("Start tracking to see insights.")
    else:
        df = pd.DataFrame(data)
        
        # 1. HEATMAP (Consistency)
        st.subheader("📅 Consistency Heatmap")
        daily_counts = df.groupby('Date')['Duration'].sum().reset_index()
        fig_heat = px.bar(daily_counts, x='Date', y='Duration', color='Duration', 
                          color_continuous_scale='Greens', height=250)
        fig_heat.update_layout(xaxis_title=None, yaxis_title="Mins")
        st.plotly_chart(fig_heat, use_container_width=True)
        
        # 2. NEGLECTED SUBJECTS
        st.subheader("⚠️ Attention Needed")
        last_studied = df.groupby('Task')['Date'].max()
        today = datetime.now().strftime("%Y-%m-%d")
        today_dt = datetime.strptime(today, "%Y-%m-%d")
        
        alerts = []
        for subj in SUBJECTS:
            if subj not in last_studied:
                alerts.append(f"⚪ Never studied **{subj}**")
            else:
                last_date = datetime.strptime(last_studied[subj], "%Y-%m-%d")
                days_gap = (today_dt - last_date).days
                if days_gap > 3:
                    alerts.append(f"⚠️ **{subj}**: {days_gap} days ago")
        
        if alerts:
            for a in alerts[:3]: st.write(a)
        else:
            st.success("You are balancing all subjects well!")

        # 3. PROGRESS RINGS
        st.subheader("🎯 Subject Mastery")
        cols = st.columns(3)
        for i, subj in enumerate(SUBJECTS[:3]): # Show top 3, extend logic if needed
            done = df[df['Task'] == subj]['Duration'].sum() / 60
            target = TARGET_HOURS[subj]
            pct = min(done/target, 1)
            
            with cols[i]:
                st.markdown(f"**{subj}**")
                st.progress(pct)
                st.caption(f"{int(done)}/{target}h")

# =========================================
# TAB 3: VAULT (Excel Import/Export)
# =========================================
with tab_data:
    st.subheader("⚙️ Data Vault")
    
    data = load_data()
    if data:
        df = pd.DataFrame(data)
        
        # EXCEL EXPORT
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Logs')
        
        st.download_button(
            "📥 Download Excel Backup",
            data=output.getvalue(),
            file_name=f"CA_Zen_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # EXCEL IMPORT
    st.write("---")
    uploaded = st.file_uploader("Restore from Excel", type=['xlsx'])
    if uploaded and st.button("Load Data"):
        try:
            new_df = pd.read_excel(uploaded)
            # Convert timestamps to string dates if needed
            if 'Date' in new_df.columns: new_df['Date'] = new_df['Date'].astype(str)
            save_data(new_df.to_dict(orient='records'))
            st.success("Restored!")
            time.sleep(1)
            st.rerun()
        except:
            st.error("Invalid Excel file.")

    # DATA EDITOR
    with st.expander("View/Edit Raw Data"):
        if data:
            edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
            if st.button("Save Edits"):
                save_data(edited.to_dict(orient='records'))
                st.rerun()
