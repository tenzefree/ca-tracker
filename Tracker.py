import streamlit as st
import pandas as pd
import plotly.express as px
import json
import time
import os
from datetime import datetime, date

# --- CONFIGURATION ---
DATA_FILE = "ca_final_data.json"
EXAM_DATE = date(2026, 5, 1)

# Targets (Hours)
SUBJECT_TARGETS = {
    "FR": 250, "AFM": 200, "Audit": 150, 
    "DT": 200, "IDT": 150, "IBS": 100, "SPOM": 80
}

st.set_page_config(page_title="CA Final Manager", page_icon="🎓", layout="wide")

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
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def add_entry(entry):
    data = load_data()
    data.append(entry)
    save_data(data)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🎓 CA Final Manager")
    days_left = (EXAM_DATE - date.today()).days
    st.success(f"📅 **{days_left} Days** to May '26")
    st.write("---")
    page = st.radio("Menu", ["⏱️ Timer", "📊 Dashboard", "🎯 Progress", "💾 Data Center"])

# --- 1. TIMER PAGE ---
if page == "⏱️ Timer":
    st.title("⏱️ Study Session")
    
    # Init State
    if 'start_time' not in st.session_state: st.session_state.start_time = None
    
    if st.session_state.start_time is None:
        c1, c2 = st.columns(2)
        with c1: group = st.selectbox("Group", list(ACTIVITIES.keys()))
        with c2: task = st.selectbox("Activity", ACTIVITIES[group])
        topic = st.text_input("Topic / Chapter (Optional)", placeholder="e.g. IndAS 115")
        st.session_state.temp_topic = topic
        
        if st.button("🚀 START", type="primary", use_container_width=True):
            st.session_state.start_time = time.time()
            st.session_state.current_group = group
            st.session_state.current_task = task
            st.rerun()
    else:
        elapsed = time.time() - st.session_state.start_time
        st.markdown(f"<h1 style='text-align:center; font-size:80px; color:#4CAF50;'>{time.strftime('%H:%M:%S', time.gmtime(elapsed))}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center;'>{st.session_state.current_task}</h3>", unsafe_allow_html=True)
        
        if st.button("⏹️ STOP & LOG", type="primary", use_container_width=True):
            st.session_state.duration = time.time() - st.session_state.start_time
            st.session_state.start_time = None
            st.session_state.show_log = True
            st.rerun()
        time.sleep(1)
        st.rerun()

    if st.session_state.get("show_log"):
        st.markdown("---")
        with st.form("log"):
            c1, c2 = st.columns(2)
            focus = c1.slider("Focus (1-5)", 1, 5, 4)
            mins = st.session_state.duration / 60
            eff_mins = mins * (focus/5)
            c2.metric("Quality Time", f"{int(eff_mins)} min")
            
            if st.form_submit_button("💾 Save"):
                entry = {
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Group": st.session_state.current_group,
                    "Task": st.session_state.current_task,
                    "Topic": st.session_state.temp_topic,
                    "Duration": round(mins, 2),
                    "Focus": focus,
                    "Effective": round(eff_mins, 2)
                }
                add_entry(entry)
                st.session_state.show_log = False
                st.success("Saved!")
                st.rerun()

# --- 2. DASHBOARD PAGE ---
elif page == "📊 Dashboard":
    st.title("📊 Performance")
    data = load_data()
    if data:
        df = pd.DataFrame(data)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Hours", f"{df['Duration'].sum()/60:.1f}")
        c2.metric("Quality Hours", f"{df['Effective'].sum()/60:.1f}")
        c3.metric("Avg Focus", f"{df['Focus'].mean():.1f}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("By Subject")
            fig = px.pie(df, names='Task', values='Duration', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("Daily Trend")
            daily = df.groupby('Date')['Duration'].sum().reset_index()
            fig2 = px.bar(daily, x='Date', y='Duration')
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Start using the timer to see data here.")

# --- 3. PROGRESS PAGE ---
elif page == "🎯 Progress":
    st.title("🎯 Syllabus Tracker")
    data = load_data()
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=['Task', 'Duration'])
    
    for subj, target in SUBJECT_TARGETS.items():
        done = df[df['Task'].str.contains(subj, case=False, na=False)]['Duration'].sum() / 60
        st.write(f"**{subj}** ({int(done)}/{target} hrs)")
        st.progress(min(done/target, 1.0))

# --- 4. DATA CENTER (NEW!) ---
elif page == "💾 Data Center":
    st.title("💾 Data Center")
    
    tab1, tab2 = st.tabs(["✏️ Edit/Delete Data", "📤 Import & Export"])
    
    # TAB 1: EDITING
    with tab1:
        st.write("Double-click any cell to edit. Select rows and press Delete key on keyboard to remove.")
        data = load_data()
        if data:
            df = pd.DataFrame(data)
            
            # Editable Grid
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor")
            
            if st.button("💾 Save Changes to File", type="primary"):
                # Convert DataFrame back to JSON format
                new_data = edited_df.to_dict(orient='records')
                save_data(new_data)
                st.success("✅ Database updated successfully!")
                time.sleep(1)
                st.rerun()
        else:
            st.warning("No data to edit.")

    # TAB 2: IMPORT / EXPORT
    with tab2:
        col1, col2 = st.columns(2)
        
        # EXPORT SECTION
        with col1:
            st.subheader("📤 Export Backup")
            st.write("Download your data to keep it safe or analyze in Excel.")
            
            data = load_data()
            if data:
                df = pd.DataFrame(data)
                
                # Button 1: CSV (Excel)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📄 Download as Excel (CSV)",
                    data=csv,
                    file_name=f"ca_tracker_backup_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
                # Button 2: JSON (Full Backup)
                json_str = json.dumps(data, indent=4)
                st.download_button(
                    label="📦 Download Full Backup (JSON)",
                    data=json_str,
                    file_name=f"full_backup_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
            else:
                st.write("No data to export yet.")

        # IMPORT SECTION
        with col2:
            st.subheader("📥 Import Data")
            st.write("Restore a backup file (JSON only for now).")
            
            uploaded_file = st.file_uploader("Drop your JSON backup here", type=['json'])
            
            if uploaded_file is not None:
                if st.button("⚠️ Load & Replace Current Data"):
                    try:
                        # Read file
                        imported_data = json.load(uploaded_file)
                        # Validate minimal structure
                        if isinstance(imported_data, list) and len(imported_data) > 0:
                            save_data(imported_data)
                            st.success("✅ Data restored successfully! Refreshing...")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("Invalid file format. Please upload a valid backup from this app.")
                    except Exception as e:
                        st.error(f"Error importing: {e}")
