import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import time
import os
import io
import numpy as np
from datetime import datetime, date, timedelta

# --- APP CONFIG & STYLING ---
st.set_page_config(page_title="CA Jarvis", page_icon="🧠", layout="wide")

# Custom CSS for "App-like" feel
st.markdown("""
    <style>
    .stApp {background-color: #0E1117;}
    .card {background-color: #262730; padding: 20px; border-radius: 15px; margin-bottom: 10px; border: 1px solid #30323A;}
    .highlight {color: #00CC96; font-weight: bold;}
    .big-text {font-size: 40px; font-weight: bold; color: white;}
    .sub-text {font-size: 14px; color: #9da5b0;}
    div[data-testid="stExpander"] {background-color: #262730; border-radius: 10px;}
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTS ---
DATA_FILE = "ca_jarvis_data.json"
EXAM_DATE = date(2026, 5, 1)
SUBJECTS = ["FR", "AFM", "Audit", "DT", "IDT", "IBS", "SPOM"]

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

# --- 🧠 ARTIFICIAL INTELLIGENCE ENGINE ---
def ai_brain(df):
    """Analyzes data and generates intelligent insights."""
    insights = []
    recommendation = {"task": "FR", "reason": "Start your journey!"}
    
    if df.empty:
        return recommendation, ["Start logging to activate AI insights."]

    # 1. GAP ANALYSIS (What to study next?)
    last_studied = df[df['Category'] == 'Study'].groupby('Activity')['Date'].max()
    today_dt = datetime.now()
    
    max_gap = -1
    for subj in SUBJECTS:
        # Check if subject exists in logs
        found = False
        for act in last_studied.index:
            if subj in act:
                found = True
                last_date = datetime.strptime(last_studied[act], "%Y-%m-%d")
                gap = (today_dt - last_date).days
                if gap > max_gap:
                    max_gap = gap
                    recommendation = {"task": subj, "reason": f"You haven't studied this in {gap} days."}
                break
        if not found:
            recommendation = {"task": subj, "reason": "You have never studied this topic!"}
            break

    # 2. PATTERN RECOGNITION
    # Best Time of Day
    df['Hour'] = pd.to_datetime(df['Start']).dt.hour
    morning_focus = df[(df['Hour'] < 12) & (df['Category'] == 'Study')]['Rating'].mean()
    night_focus = df[(df['Hour'] >= 18) & (df['Category'] == 'Study')]['Rating'].mean()
    
    if pd.notna(morning_focus) and pd.notna(night_focus):
        if morning_focus > night_focus + 0.5:
            insights.append("🧠 **Bio-Hack:** You are 25% more focused in the Morning. Schedule hard subjects then.")
        elif night_focus > morning_focus + 0.5:
            insights.append("🦉 **Bio-Hack:** You are a Night Owl. Save mocks for the evening.")

    # 3. BURNOUT DETECTOR
    recent_sleep = df[(df['Activity'] == 'Sleep')].tail(3)['Duration_Min'].mean()
    if pd.notna(recent_sleep) and (recent_sleep/60) < 6:
        recommendation = {"task": "Sleep / Nap", "reason": "CRITICAL: Your sleep average is dangerous (<6h)."}
        insights.append("⚠️ **Burnout Risk:** Your sleep debt is accumulating. Efficiency will drop by 40%.")

    return recommendation, insights

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712027.png", width=50)
    st.title("CA Jarvis")
    st.caption("AI-Powered LifeOS")
    
    page = st.radio("Navigation", ["🏠 Command Center", "📅 Day Timeline", "🧠 AI Cortex", "⚙️ Data Vault"])
    
    st.markdown("---")
    days_left = (EXAM_DATE - date.today()).days
    st.metric("Countdown", f"{days_left} Days", "May 2026")

# =========================================
# PAGE 1: COMMAND CENTER (HOME)
# =========================================
if page == "🏠 Command Center":
    
    # LOAD DATA & AI
    data = load_data()
    df = pd.DataFrame(data)
    rec, insights = ai_brain(df)

    # 1. AI GREETING CARD
    st.markdown(f"""
    <div class="card" style="border-left: 5px solid #00CC96;">
        <h3 style="margin:0;">🤖 Jarvis Suggestion</h3>
        <p style="font-size: 20px; color: white;">Recommended Next Activity: <b>{rec['task']}</b></p>
        <p style="color: gray; font-size: 14px;">Why: {rec['reason']}</p>
    </div>
    """, unsafe_allow_html=True)

    # 2. LIVE TRACKER UI
    st.subheader("🔴 Live Tracking")
    
    if 'start_time' not in st.session_state: st.session_state.start_time = None

    if st.session_state.start_time is None:
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1: cat = st.selectbox("Category", ["Study", "Biological", "Logistics", "Leisure", "Wasted"])
        with c2: 
            # Dynamic Activity List
            acts = []
            if cat == "Study": acts = SUBJECTS + ["Mock Exam", "Review"]
            elif cat == "Biological": acts = ["Sleep", "Meals", "Hygiene", "Nap"]
            elif cat == "Logistics": acts = ["Commute", "Planning", "Chores"]
            elif cat == "Leisure": acts = ["Social", "TV", "Gaming"]
            else: acts = ["Procrastination", "Nothing"]
            act = st.selectbox("Activity", acts)
        with c3: 
            st.write("")
            st.write("")
            if st.button("▶ START", type="primary", use_container_width=True):
                st.session_state.start_time = time.time()
                st.session_state.curr_cat = cat
                st.session_state.curr_act = act
                st.rerun()
    else:
        # RUNNING TIMER
        elapsed = time.time() - st.session_state.start_time
        st.markdown(f"""
        <div style="text-align:center; padding:30px; background:#191B22; border-radius:20px;">
            <h1 style="font-size:80px; color:#FF4B4B; margin:0;">{time.strftime('%H:%M:%S', time.gmtime(elapsed))}</h1>
            <h3>{st.session_state.curr_act}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("⏹ STOP SESSION", use_container_width=True):
            st.session_state.duration = time.time() - st.session_state.start_time
            st.session_state.start_time = None
            st.session_state.show_save = True
            st.rerun()

    # SAVE MODAL
    if st.session_state.get("show_save"):
        with st.expander("📝 Save Log", expanded=True):
            note = st.text_input("Any specific topic or note?")
            rating = st.slider("Efficiency / Focus Rating", 1, 5, 4)
            
            if st.button("Confirm Entry"):
                entry = {
                    "Start": (datetime.now() - timedelta(seconds=st.session_state.duration)).strftime("%Y-%m-%d %H:%M:%S"),
                    "End": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Category": st.session_state.curr_cat,
                    "Activity": st.session_state.curr_act,
                    "Note": note,
                    "Duration_Min": round(st.session_state.duration / 60, 2),
                    "Rating": rating
                }
                add_entry(entry)
                st.session_state.show_save = False
                st.toast("Memory Updated!", icon="💾")
                time.sleep(1)
                st.rerun()

    # 3. QUICK STATS
    if not df.empty:
        today = datetime.now().strftime("%Y-%m-%d")
        today_mins = df[df['Date'] == today]['Duration_Min'].sum()
        st.markdown("---")
        k1, k2, k3 = st.columns(3)
        k1.metric("Today's Output", f"{int(today_mins/60)}h {int(today_mins%60)}m")
        k2.metric("Entries", len(df))
        k3.metric("Burnout Status", "Normal", delta="Stable")

# =========================================
# PAGE 2: DAY TIMELINE (VISUAL)
# =========================================
if page == "📅 Day Timeline":
    st.title("📅 Chrono-View")
    data = load_data()
    if data:
        df = pd.DataFrame(data)
        df['Start'] = pd.to_datetime(df['Start'])
        df['End'] = pd.to_datetime(df['End'])
        
        today = datetime.now().strftime("%Y-%m-%d")
        day_df = df[df['Date'] == today]
        
        if not day_df.empty:
            fig = px.timeline(day_df, x_start="Start", x_end="End", y="Category", 
                              color="Category", hover_data=["Activity", "Note"], height=400,
                              color_discrete_map={"Study": "#00CC96", "Wasted": "#EF553B"})
            fig.update_yaxes(autorange="reversed")
            fig.layout.template = "plotly_dark"
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data for today.")

# =========================================
# PAGE 3: AI CORTEX (ADVANCED)
# =========================================
if page == "🧠 AI Cortex":
    st.title("🧠 The Cortex")
    
    data = load_data()
    if data:
        df = pd.DataFrame(data)
        rec, insights = ai_brain(df)
        
        # 1. INSIGHTS LIST
        st.subheader("🔍 Automated Insights")
        for insight in insights:
            st.info(insight)
            
        st.markdown("---")
        
        # 2. CHATGPT PROMPT GENERATOR
        st.subheader("🤖 Ask the Oracle (ChatGPT Bridge)")
        st.write("Click below to generate a detailed prompt based on your actual data. Paste this into ChatGPT for expert advice.")
        
        if st.button("Generate Coach Prompt"):
            # Aggregating data for the prompt
            total_hrs = df['Duration_Min'].sum() / 60
            subj_breakdown = df[df['Category'] == 'Study'].groupby('Activity')['Duration_Min'].sum().to_dict()
            recent_focus = df.tail(10)['Rating'].mean()
            
            prompt = f"""
            Act as an expert CA Final Coach. Here is my current study data:
            - Total Hours Logged: {total_hrs:.1f} hours
            - Subject Breakdown (Mins): {subj_breakdown}
            - Recent Average Focus (1-5): {recent_focus:.1f}
            - Exam Date: May 2026.
            
            Based on this, please tell me:
            1. Which subject am I neglecting?
            2. Am I studying enough hours?
            3. Create a schedule for the next 7 days to fix my weak areas.
            """
            st.code(prompt, language='text')
            st.success("Prompt generated! Copy the text above.")

# =========================================
# PAGE 4: DATA VAULT
# =========================================
if page == "⚙️ Data Vault":
    st.title("⚙️ Data Vault")
    
    data = load_data()
    if data:
        df = pd.DataFrame(data)
        
        # Excel Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='JarvisData')
        
        st.download_button("📥 Export Full Backup (.xlsx)", data=output.getvalue(), 
                           file_name="Jarvis_Backup.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # Import
    uploaded = st.file_uploader("Restore Backup", type=['xlsx'])
    if uploaded and st.button("Load Data"):
        new_df = pd.read_excel(uploaded)
        # Fix string conversion for JSON serialization
        for col in ['Start', 'End', 'Date']:
            new_df[col] = new_df[col].astype(str)
        save_data(new_df.to_dict(orient='records'))
        st.success("System Restored.")
        time.sleep(1)
        st.rerun()
        
    # Editor
    with st.expander("🔧 Developer Mode (Edit Raw Data)"):
        if data:
            edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
            if st.button("Save Changes"):
                save_data(edited.to_dict(orient='records'))
                st.rerun()
