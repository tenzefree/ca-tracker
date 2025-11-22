import streamlit as st
import pandas as pd
import plotly.express as px
import json
import time
import os
import io
from datetime import datetime, date

# --- APP CONFIG (Mobile Friendly) ---
st.set_page_config(page_title="CA Tracker", page_icon="🎓", layout="centered") # 'Centered' looks better on mobile

# --- CONFIGURATION ---
DATA_FILE = "ca_final_data.json"
EXAM_DATE = date(2026, 5, 1)

# Targets (Hours)
SUBJECT_TARGETS = {
    "FR": 250, "AFM": 200, "Audit": 150, 
    "DT": 200, "IDT": 150, "IBS": 100, "SPOM": 80
}

# --- SCHEMA ---
ACTIVITIES = {
    "1. Coaching": ["FR Class", "AFM Class", "Audit Class", "DT Class", "IDT Class"],
    "2. Self Study": ["FR Study", "AFM Study", "Audit Study", "DT Study", "IDT Study", "IBS (Paper 6)"],
    "3. SPOM": ["Set A (Law)", "Set B (Costing)"],
    "4. Practice": ["Full Mock (3Hr)", "RTP/MTP Solving", "Answer Writing"],
    "5. Bio & Admin": ["Sleep", "Meals", "Sport/Walk", "Commute", "Marriage Works"]
}

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

# --- UTILS ---
def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Study Log')
    return output.getvalue()

# --- MAIN UI ---
# Hide the hamburger menu for a cleaner app look
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- NAVIGATION (Mobile Tab Style) ---
# We use tabs at the top instead of a sidebar to feel like an app
tab1, tab2, tab3, tab4 = st.tabs(["⏱️ Timer", "📊 Stats", "🎯 Goals", "⚙️ Data"])

# ==========================
# TAB 1: TIMER (HOME)
# ==========================
with tab1:
    # Countdown Banner
    days = (EXAM_DATE - date.today()).days
    st.info(f"🔥 **{days} Days** until May '26")

    # State
    if 'start_time' not in st.session_state: st.session_state.start_time = None

    # IDLE SCREEN
    if st.session_state.start_time is None:
        st.subheader("Start Session")
        group = st.selectbox("Group", list(ACTIVITIES.keys()))
        task = st.selectbox("Activity", ACTIVITIES[group])
        topic = st.text_input("Topic (Optional)", placeholder="e.g. Forex")
        st.session_state.temp_topic = topic
        
        st.write("") # Spacer
        if st.button("🚀 START TIMER", type="primary", use_container_width=True):
            st.session_state.start_time = time.time()
            st.session_state.current_group = group
            st.session_state.current_task = task
            st.rerun()

    # RUNNING SCREEN
    else:
        elapsed = time.time() - st.session_state.start_time
        # Big Timer Text
        st.markdown(f"""
        <div style='text-align: center; padding: 20px;'>
            <h1 style='font-size: 60px; color: #00C853; margin: 0;'>
                {time.strftime('%H:%M:%S', time.gmtime(elapsed))}
            </h1>
            <p style='color: gray; font-size: 18px;'>{st.session_state.current_task}</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("⏹️ STOP & SAVE", type="primary", use_container_width=True):
            st.session_state.duration = time.time() - st.session_state.start_time
            st.session_state.start_time = None
            st.session_state.show_log = True
            st.rerun()
        
        time.sleep(1)
        st.rerun()

    # SAVE POPUP
    if st.session_state.get("show_log"):
        st.markdown("---")
        st.caption("Session Details")
        focus = st.slider("🧠 Focus Level", 1, 5, 4)
        
        mins = st.session_state.duration / 60
        eff_mins = mins * (focus/5)
        
        if st.button("✅ CONFIRM ENTRY", use_container_width=True):
            entry = {
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Time": datetime.now().strftime("%H:%M"),
                "Group": st.session_state.current_group,
                "Task": st.session_state.current_task,
                "Topic": st.session_state.temp_topic,
                "Duration": round(mins, 2),
                "Focus": focus,
                "Effective": round(eff_mins, 2)
            }
            add_entry(entry)
            st.session_state.show_log = False
            # NOTIFICATION: Toast Message
            st.toast(f"Saved! {int(mins)} mins added.", icon="🎉")
            time.sleep(1)
            st.rerun()

# ==========================
# TAB 2: STATS (DASHBOARD)
# ==========================
with tab2:
    data = load_data()
    if data:
        df = pd.DataFrame(data)
        
        # Summary Cards
        c1, c2 = st.columns(2)
        total_hrs = df['Duration'].sum()/60
        eff_hrs = df['Effective'].sum()/60
        
        c1.metric("Total Hours", f"{total_hrs:.1f}")
        c2.metric("Quality Hours", f"{eff_hrs:.1f}")
        
        # Charts
        st.subheader("Weekly Trend")
        daily = df.groupby('Date')['Duration'].sum().reset_index()
        fig = px.bar(daily, x='Date', y='Duration', height=300)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Subject Split")
        fig2 = px.pie(df, names='Task', values='Duration', height=300)
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Log your first session to see charts.")

# ==========================
# TAB 3: GOALS (PROGRESS)
# ==========================
with tab3:
    st.subheader("Syllabus Tracker")
    data = load_data()
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=['Task', 'Duration'])
    
    for subj, target in SUBJECT_TARGETS.items():
        # Filter loosely for subject name
        done = df[df['Task'].str.contains(subj, case=False, na=False)]['Duration'].sum() / 60
        pct = min(done/target, 1.0)
        
        col_txt, col_bar = st.columns([1, 3])
        with col_txt:
            st.write(f"**{subj}**")
        with col_bar:
            st.progress(pct)
            st.caption(f"{int(done)}/{target} Hrs")

# ==========================
# TAB 4: DATA (SETTINGS)
# ==========================
with tab4:
    st.subheader("⚙️ Data Management")
    
    # 1. EXCEL EXPORT
    data = load_data()
    if data:
        df = pd.DataFrame(data)
        excel_data = convert_df_to_excel(df)
        
        st.download_button(
            label="📥 Download Excel (.xlsx)",
            data=excel_data,
            file_name=f"CA_Backup_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # 2. EXCEL IMPORT
    st.write("Restore Data from Excel")
    uploaded_file = st.file_uploader("Upload .xlsx", type=['xlsx'])
    
    if uploaded_file:
        if st.button("⚠️ Load Data", use_container_width=True):
            try:
                new_df = pd.read_excel(uploaded_file)
                # Ensure date format is string for JSON
                if 'Date' in new_df.columns:
                    new_df['Date'] = new_df['Date'].astype(str)
                
                imported_data = new_df.to_dict(orient='records')
                save_data(imported_data)
                st.toast("Restored Successfully!", icon="✅")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error("Error reading file. Make sure it's the same format as the Export.")

    # 3. DATA EDITOR
    st.markdown("---")
    with st.expander("✏️ Edit Raw Data"):
        if data:
            df_edit = pd.DataFrame(data)
            edited = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
            if st.button("Save Edits"):
                save_data(edited.to_dict(orient='records'))
                st.toast("Edits Saved!", icon="💾")
                st.rerun()
