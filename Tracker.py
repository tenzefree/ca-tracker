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

# --- APP CONFIG ---
st.set_page_config(page_title="CA Jarvis", page_icon="🧠", layout="wide")

# --- LIGHT MODE STYLING (Apple Style) ---
st.markdown("""
    <style>
    /* Main Background */
    .stApp {background-color: #FFFFFF;}
    
    /* Cards */
    .card {
        background-color: #F8F9FA;
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 15px;
        border: 1px solid #E0E0E0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Typography */
    h1, h2, h3 {color: #111111 !important;}
    p {color: #444444;}
    
    /* Timer Box */
    .timer-box {
        text-align: center;
        padding: 30px;
        background: #F0F2F6;
        border-radius: 20px;
        border: 1px solid #D1D5DB;
    }
    
    /* Expander Styling */
    div[data-testid="stExpander"] {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 10px;
    }
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

# --- 🧠 AI ENGINE ---
def ai_brain(df):
    insights = []
    recommendation = {"task": "FR", "reason": "Start your journey!"}
    
    if df.empty:
        return recommendation, ["Start logging to activate AI insights."]

    # 1. GAP ANALYSIS
    last_studied = df[df['Category'] == 'Study'].groupby('Activity')['Date'].max()
    today_dt = datetime.now()
    max_gap = -1
    
    for subj in SUBJECTS:
        found = False
        for act in last_studied.index:
            if subj in act:
                found = True
                last_date = datetime.strptime(last_studied[act], "%Y-%m-%d")
                gap = (today_dt - last_date).days
                if gap > max_gap:
                    max_gap = gap
                    recommendation = {"task": subj, "reason": f"Neglected for {gap} days."}
                break
        if not found:
            recommendation = {"task": subj, "reason": "Subject untouched!"}
            break

    # 2. BIO-RHYTHM
    df['Hour'] = pd.to_datetime(df['Start']).dt.hour
    morning_focus = df[(df['Hour'] < 12) & (df['Category'] == 'Study')]['Rating'].mean()
    night_focus = df[(df['Hour'] >= 18) & (df['Category'] == 'Study')]['Rating'].mean()
    
    if pd.notna(morning_focus) and pd.notna(night_focus):
        if morning_focus > night_focus + 0.5:
            insights.append("☀️ **Morning Peak:** You focus 25% better before noon.")
        elif night_focus > morning_focus + 0.5:
            insights.append("🌙 **Night Owl:** Your focus peaks after 6 PM.")

    return recommendation, insights

# --- SIDEBAR ---
with st.sidebar:
    st.title("CA Jarvis 🧠")
    st.caption("Light Edition")
    
    page = st.radio("Menu", ["🏠 Home", "📅 Timeline", "🧠 Insights", "⚙️ Data"])
    
    st.markdown("---")
    days_left = (EXAM_DATE - date.today()).days
    st.success(f"📅 **{days_left} Days** Left")

# =========================================
# PAGE 1: HOME (COMMAND CENTER)
# =========================================
if page == "🏠 Home":
    
    data = load_data()
    df = pd.DataFrame(data)
    rec, insights = ai_brain(df)

    # 1. AI RECOMMENDATION CARD
    st.markdown(f"""
    <div class="card" style="border-left: 5px solid #007BFF;">
        <h3 style="margin:0; color:#333;">🤖 AI Suggestion</h3>
        <p style="font-size: 18px; color: #111;">Next Best Action: <b>{rec['task']}</b></p>
        <p style="color: #666; font-size: 14px;">Reason: {rec['reason']}</p>
    </div>
    """, unsafe_allow_html=True)

    # 2. LIVE TRACKER
    st.subheader("🔴 Live Tracker")
    
    if 'start_time' not in st.session_state: st.session_state.start_time = None

    if st.session_state.start_time is None:
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1: cat = st.selectbox("Category", ["Study", "Biological", "Logistics", "Leisure", "Wasted"])
        with c2: 
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
        # RUNNING TIMER (LIGHT THEME)
        elapsed = time.time() - st.session_state.start_time
        st.markdown(f"""
        <div class="timer-box">
            <h1 style="font-size:80px; color:#DC3545; margin:0; font-weight:bold;">{time.strftime('%H:%M:%S', time.gmtime(elapsed))}</h1>
            <h3 style="color:#555;">{st.session_state.curr_act}</h3>
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
            note = st.text_input("Topic / Note")
            rating = st.slider("Efficiency Rating", 1, 5, 4)
            
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
                st.toast("Saved Successfully!", icon="✅")
                time.sleep(1)
                st.rerun()

# =========================================
# PAGE 2: TIMELINE
# =========================================
if page == "📅 Timeline":
    st.title("📅 Day View")
    data = load_data()
    if data:
        df = pd.DataFrame(data)
        df['Start'] = pd.to_datetime(df['Start'])
        df['End'] = pd.to_datetime(df['End'])
        
        today = datetime.now().strftime("%Y-%m-%d")
        day_df = df[df['Date'] == today]
        
        if not day_df.empty:
            # Light Mode Chart Colors
            colors = {"Study": "#28A745", "Wasted": "#DC3545", "Biological": "#007BFF", "Leisure": "#FFC107"}
            
            fig = px.timeline(day_df, x_start="Start", x_end="End", y="Category", 
                              color="Category", hover_data=["Activity", "Note"], height=400,
                              color_discrete_map=colors)
            fig.update_yaxes(autorange="reversed")
            fig.layout.template = "plotly_white" # CLEAN WHITE BACKGROUND
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### 📝 Activity Log")
            st.dataframe(day_df[['Start', 'Activity', 'Duration_Min', 'Note']], use_container_width=True)
        else:
            st.info("No activities logged today.")

# =========================================
# PAGE 3: AI CORTEX
# =========================================
if page == "🧠 Insights":
    st.title("🧠 Cortex Analysis")
    
    data = load_data()
    if data:
        df = pd.DataFrame(data)
        rec, insights = ai_brain(df)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔍 Patterns")
            if insights:
                for i in insights: st.info(i)
            else:
                st.write("Keep logging to reveal patterns.")
                
        with col2:
            st.subheader("🤖 Mentor Prompt")
            st.write("Generate a prompt for ChatGPT to act as your CA Coach.")
            if st.button("Generate Prompt"):
                total_hrs = df['Duration_Min'].sum() / 60
                prompt = f"I am a CA Final student (May 2026). I have studied {total_hrs:.1f} hours total. My data shows I am currently focusing on {rec['task']}. Please give me a schedule."
                st.code(prompt)

# =========================================
# PAGE 4: DATA VAULT
# =========================================
if page == "⚙️ Data":
    st.title("⚙️ Data Management")
    
    data = load_data()
    if data:
        df = pd.DataFrame(data)
        
        # EXCEL EXPORT
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='JarvisData')
        
        st.download_button("📥 Download Excel Backup", data=output.getvalue(), 
                           file_name="CA_Jarvis_Backup.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    st.write("---")
    uploaded = st.file_uploader("Restore Excel Backup", type=['xlsx'])
    if uploaded and st.button("Load Data"):
        new_df = pd.read_excel(uploaded)
        # Type conversion for JSON
        for col in ['Start', 'End', 'Date']: new_df[col] = new_df[col].astype(str)
        save_data(new_df.to_dict(orient='records'))
        st.success("Data Restored.")
        time.sleep(1)
        st.rerun()
