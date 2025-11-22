import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import time
import os
import io
from datetime import datetime, date, timedelta

# --- MILITARY CONFIGURATION ---
st.set_page_config(page_title="CA TITAN OS", page_icon="🛡️", layout="wide")
DATA_FILE = "titan_logs.json" # Stores time history
MASTER_DB_FILE = "titan_master_db.json" # Stores the Syllabus Excel data in JSON format for speed
EXAM_DATE = date(2026, 5, 1)

# --- CUSTOM CSS (POWER BI DARK THEME) ---
st.markdown("""
    <style>
    .stApp {background-color: #121212; color: #e0e0e0;}
    .metric-card {background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 4px solid #00E5FF; text-align: center;}
    .strict-alert {background-color: #3a0000; color: #ff4444; padding: 10px; border-radius: 5px; font-weight: bold; border: 1px solid red;}
    div[data-testid="stExpander"] {background-color: #1E1E1E; border: 1px solid #333;}
    h1, h2, h3 {color: #ffffff !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 1. DATA ENGINE ---
def load_logs():
    if not os.path.exists(DATA_FILE): return []
    try:
        with open(DATA_FILE, 'r') as f: return json.load(f)
    except: return []

def save_logs(data):
    with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=4)

def load_master_db():
    if not os.path.exists(MASTER_DB_FILE): return None
    try:
        with open(MASTER_DB_FILE, 'r') as f: 
            data = json.load(f)
            return pd.DataFrame(data)
    except: return None

def save_master_db(df):
    # Convert Date columns to string before saving to JSON
    date_cols = ['Rev_1_Date', 'Rev_2_Date', 'Rev_3_Date', 'Rev_4_Date', 'Rev_5_Date']
    for col in date_cols:
        if col in df.columns:
            df[col] = df[col].astype(str)
    
    with open(MASTER_DB_FILE, 'w') as f: 
        json.dump(df.to_dict(orient='records'), f, indent=4)

# --- 2. GAP FILLER ALGORITHM (STRICT MODE) ---
def check_and_fill_gaps(new_start_time):
    logs = load_logs()
    if not logs: return # First entry ever
    
    # Get last entry
    df_logs = pd.DataFrame(logs)
    df_logs['End'] = pd.to_datetime(df_logs['End'])
    df_logs['Start'] = pd.to_datetime(df_logs['Start'])
    
    # Filter for TODAY only (don't fill gap from yesterday night)
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_logs = df_logs[df_logs['Date'] == today_str].sort_values('End')
    
    if today_logs.empty: return

    last_end = today_logs.iloc[-1]['End']
    current_start = datetime.fromtimestamp(new_start_time)
    
    # Gap calculation (in minutes)
    gap_minutes = (current_start - last_end).total_seconds() / 60
    
    # If gap > 10 mins, mark as WASTED
    if gap_minutes > 10:
        gap_entry = {
            "Date": today_str,
            "Start": last_end.strftime("%Y-%m-%d %H:%M:%S"),
            "End": current_start.strftime("%Y-%m-%d %H:%M:%S"),
            "Subject": "SYSTEM",
            "Topic": "UNACCOUNTED GAP",
            "Type": "WASTED",
            "Duration": round(gap_minutes, 2),
            "Focus": 0,
            "Confidence": "Low"
        }
        logs.append(gap_entry)
        save_logs(logs)
        return round(gap_minutes, 0)
    return 0

# --- 3. EXCEL TEMPLATE GENERATOR ---
def generate_master_template():
    columns = [
        'Subject', 'Chapter', 'Topic', 'Est_Hours', 'Current_Status', # Status: Pending, Class Done, Revision
        'Confidence', # High, Med, Low
        'Rev_Count', 'Rev_1_Date', 'Rev_2_Date', 'Rev_3_Date', 'Rev_4_Date', 'Rev_5_Date',
        'RTP_Status', 'MTP_Status' # Pending, Done
    ]
    # Dummy Data
    data = [
        ['FR', 'Financial Instruments', 'Equity vs Liability', 2.5, 'Pending', 'Low', 0, '', '', '', '', '', 'Pending', 'Pending'],
        ['Audit', 'Ethics', 'Clauses 1-10', 4.0, 'Class Done', 'Med', 0, '', '', '', '', '', 'Done', 'Pending']
    ]
    return pd.DataFrame(data, columns=columns)

# --- SIDEBAR (CONTROLLER) ---
with st.sidebar:
    st.title("🛡️ TITAN OS")
    days_left = (EXAM_DATE - date.today()).days
    
    # Military Status
    if days_left < 300: color = "red"
    else: color = "orange"
    st.markdown(f"<h2 style='color:{color}; text-align:center;'>{days_left} DAYS</h2>", unsafe_allow_html=True)
    st.caption("TARGET: MAY 2026")
    
    st.markdown("---")
    
    # MASTER DB LOADER
    master_df = load_master_db()
    
    if master_df is None:
        st.error("⚠️ NO DATABASE LOADED")
        st.info("Go to 'Data Hangar' tab to upload your Master Excel.")
        active_subjects = []
    else:
        active_subjects = master_df['Subject'].unique().tolist()

    # --- TIMER INTERFACE ---
    if 'start_time' not in st.session_state: st.session_state.start_time = None

    if st.session_state.start_time is None:
        st.subheader("🚀 Initiate Sequence")
        
        # 1. Category Selection
        mode = st.selectbox("Operation Mode", ["Self Study", "Class/Coaching", "Biological (Sleep/Eat)", "Logistics", "Wasted"])
        
        if mode in ["Self Study", "Class/Coaching"]:
            if master_df is not None:
                subj = st.selectbox("Subject", active_subjects)
                # Filter Chapters based on Subject
                chapters = master_df[master_df['Subject'] == subj]['Chapter'].unique().tolist()
                chap = st.selectbox("Chapter", chapters)
                # Filter Topics based on Chapter
                topics = master_df[(master_df['Subject'] == subj) & (master_df['Chapter'] == chap)]['Topic'].unique().tolist()
                topic = st.selectbox("Topic", topics + ["➕ Add Ad-hoc Topic"])
                
                if topic == "➕ Add Ad-hoc Topic":
                    topic = st.text_input("Enter New Topic Name")
            else:
                st.warning("Upload Excel to select Topics")
                subj, chap, topic = "Ad-hoc", "Ad-hoc", "Manual Entry"
        else:
            subj, chap = mode, "General"
            topic = st.text_input("Activity Details", placeholder="e.g., Lunch, Sleep, Commute")

        if st.button("▶ EXECUTE", type="primary", use_container_width=True):
            # Check for Gaps before starting
            gap = check_and_fill_gaps(time.time())
            if gap > 0:
                st.toast(f"⚠️ Strict Mode: {gap} mins marked as WASTED!", icon="💀")
            
            st.session_state.start_time = time.time()
            st.session_state.curr_mode = mode
            st.session_state.curr_subj = subj
            st.session_state.curr_chap = chap
            st.session_state.curr_topic = topic
            st.rerun()
            
    else:
        # RUNNING STATE
        elapsed = time.time() - st.session_state.start_time
        st.markdown(f"""
        <div class="metric-card" style="border-color: #00FF00;">
            <h1 style="color:#00FF00 !important; font-size: 40px; margin:0;">{time.strftime('%H:%M:%S', time.gmtime(elapsed))}</h1>
            <p>{st.session_state.curr_topic}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("⏹ TERMINATE & LOG", type="primary", use_container_width=True):
            st.session_state.duration = time.time() - st.session_state.start_time
            st.session_state.start_time = None
            st.session_state.show_save = True
            st.rerun()

    # SAVE DIALOG
    if st.session_state.get("show_save"):
        st.markdown("---")
        st.markdown("### 📝 Mission Report")
        
        # Logic: If Study, show Academic Fields. Else simple.
        is_academic = st.session_state.curr_mode in ["Self Study", "Class/Coaching"]
        
        if is_academic:
            c1, c2 = st.columns(2)
            focus = c1.slider("Focus (1-5)", 1, 5, 4)
            conf = c2.select_slider("Confidence", options=["Low", "Med", "High"], value="Med")
            
            # Update Master DB options
            st.caption("Update Master DB Status:")
            status_update = st.selectbox("Mark Topic As:", ["No Change", "Class Done", "Revision 1 Done", "Revision 2 Done", "Revision 3 Done", "Exam Ready"])
            rtp_update = st.checkbox("RTP Solved?")
            mtp_update = st.checkbox("MTP Solved?")
        else:
            focus = 0
            conf = "N/A"
            status_update = "N/A"

        if st.button("💾 SAVE TO DATABASE", use_container_width=True):
            # 1. Save to Time Logs
            mins = round(st.session_state.duration / 60, 2)
            eff_mins = mins * (focus/5) if focus > 0 else 0
            
            log_entry = {
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Start": (datetime.now() - timedelta(seconds=st.session_state.duration)).strftime("%Y-%m-%d %H:%M:%S"),
                "End": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Subject": st.session_state.curr_subj,
                "Chapter": st.session_state.curr_chap,
                "Topic": st.session_state.curr_topic,
                "Type": st.session_state.curr_mode,
                "Duration": mins,
                "Focus": focus,
                "Effective": round(eff_mins, 2),
                "Confidence": conf
            }
            logs = load_logs()
            logs.append(log_entry)
            save_logs(logs)
            
            # 2. Update Master DB (If Academic)
            if is_academic and master_df is not None:
                # Find the row index
                mask = (master_df['Subject'] == st.session_state.curr_subj) & \
                       (master_df['Chapter'] == st.session_state.curr_chap) & \
                       (master_df['Topic'] == st.session_state.curr_topic)
                
                if mask.any():
                    idx = master_df.index[mask][0]
                    master_df.at[idx, 'Confidence'] = conf
                    
                    if status_update == "Class Done": master_df.at[idx, 'Current_Status'] = "Class Done"
                    elif "Revision" in status_update:
                        rev_num = status_update.split(" ")[1] # Get 1, 2 etc
                        master_df.at[idx, 'Rev_Count'] = int(rev_num)
                        master_df.at[idx, f'Rev_{rev_num}_Date'] = datetime.now().strftime("%Y-%m-%d")
                    
                    if rtp_update: master_df.at[idx, 'RTP_Status'] = "Done"
                    if mtp_update: master_df.at[idx, 'MTP_Status'] = "Done"
                    
                    save_master_db(master_df)
                    st.toast("Master DB Updated!", icon="💾")
            
            st.session_state.show_save = False
            st.rerun()

# --- DASHBOARD TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Command Center", "📅 24H Timeline", "📂 Syllabus Matrix", "⚙️ Data Hangar"])

# ==========================
# TAB 1: COMMAND CENTER
# ==========================
with tab1:
    logs = load_logs()
    df_logs = pd.DataFrame(logs)
    
    if not df_logs.empty:
        today = datetime.now().strftime("%Y-%m-%d")
        today_df = df_logs[df_logs['Date'] == today]
        
        # 1. MILITARY DRILL SERGEANT
        total_study = today_df[today_df['Type'].isin(["Self Study", "Class/Coaching"])]['Duration'].sum()
        total_waste = today_df[today_df['Type'].isin(["Wasted", "UNACCOUNTED"])]['Duration'].sum()
        
        if total_waste > total_study:
            st.markdown(f"<div class='strict-alert'>🚨 ALERT: You have wasted {int(total_waste)} mins today! Get back to work!</div>", unsafe_allow_html=True)
        
        # 2. KPI ROW
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Study Today", f"{int(total_study/60)}h {int(total_study%60)}m")
        
        avg_focus = today_df[today_df['Focus'] > 0]['Focus'].mean()
        c2.metric("Focus Efficiency", f"{avg_focus:.1f}/5" if pd.notna(avg_focus) else "-")
        
        if master_df is not None:
            total_topics = len(master_df)
            done_topics = len(master_df[master_df['Current_Status'] != 'Pending'])
            c3.metric("Syllabus Velocity", f"{done_topics}/{total_topics} Topics")
        
        # 3. CONFIDENCE RAG MATRIX
        st.subheader("Confidence Matrix")
        if master_df is not None:
            rag_counts = master_df['Confidence'].value_counts().reset_index()
            fig_rag = px.pie(rag_counts, names='Confidence', values='count', 
                             color='Confidence', 
                             color_discrete_map={"High":"#00FF00", "Med":"#FFFF00", "Low":"#FF0000"})
            st.plotly_chart(fig_rag, use_container_width=True)

# ==========================
# TAB 2: 24H TIMELINE
# ==========================
with tab2:
    st.subheader("🕵️ 24-Hour Audit")
    if not df_logs.empty:
        # Ensure datetime format
        df_logs['Start'] = pd.to_datetime(df_logs['Start'])
        df_logs['End'] = pd.to_datetime(df_logs['End'])
        
        # Filter for Today
        today_viz = df_logs[df_logs['Date'] == datetime.now().strftime("%Y-%m-%d")]
        
        if not today_viz.empty:
            fig_timeline = px.timeline(today_viz, x_start="Start", x_end="End", y="Type", color="Type",
                                       color_discrete_map={"Self Study":"#00FF00", "WASTED":"#FF0000", "Class/Coaching":"#00CCFF"},
                                       hover_data=["Topic", "Duration"])
            fig_timeline.update_yaxes(autorange="reversed")
            fig_timeline.layout.template = "plotly_dark"
            st.plotly_chart(fig_timeline, use_container_width=True)
            
            st.dataframe(today_viz[['Start', 'Type', 'Subject', 'Topic', 'Duration', 'Focus']].sort_values('Start', ascending=False), use_container_width=True)
        else:
            st.info("No logs for today.")

# ==========================
# TAB 3: SYLLABUS MATRIX
# ==========================
with tab3:
    st.subheader("📂 Master Database View")
    if master_df is not None:
        # Filter
        subj_filter = st.multiselect("Filter Subject", master_df['Subject'].unique())
        status_filter = st.multiselect("Filter Status", master_df['Current_Status'].unique())
        
        view_df = master_df.copy()
        if subj_filter: view_df = view_df[view_df['Subject'].isin(subj_filter)]
        if status_filter: view_df = view_df[view_df['Current_Status'].isin(status_filter)]
        
        st.dataframe(view_df, use_container_width=True, height=500)
    else:
        st.warning("Upload Master Excel in 'Data Hangar' to view this.")

# ==========================
# TAB 4: DATA HANGAR
# ==========================
with tab4:
    st.title("⚙️ Data Hangar")
    
    c1, c2 = st.columns(2)
    
    # 1. DOWNLOAD TEMPLATE
    with c1:
        st.subheader("1. Get Template")
        st.write("Download this blank structure, fill your Classes/Chapters, then upload.")
        template_df = generate_master_template()
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            template_df.to_excel(writer, index=False)
        
        st.download_button("📥 Download Blank Master Excel", data=output.getvalue(), 
                           file_name="Titan_Master_Template.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # 2. UPLOAD MASTER
    with c2:
        st.subheader("2. Upload Master DB")
        st.write("⚠️ Uploading here will OVERWRITE the Topic List (Study logs will remain safe).")
        uploaded_master = st.file_uploader("Drop Filled Excel Here", type=['xlsx'])
        
        if uploaded_master:
            if st.button("⚠️ OVERWRITE MASTER DB"):
                new_master = pd.read_excel(uploaded_master)
                save_master_db(new_master)
                st.success("Master DB Updated! Reloading...")
                time.sleep(2)
                st.rerun()

    st.markdown("---")
    st.subheader("3. Backup & Restore (Full System)")
    
    # EXPORT LOGS
    logs = load_logs()
    if logs:
        log_df = pd.DataFrame(logs)
        out_logs = io.BytesIO()
        with pd.ExcelWriter(out_logs, engine='xlsxwriter') as writer:
            log_df.to_excel(writer, index=False)
            
        st.download_button("📥 Download Study Logs (History)", data=out_logs.getvalue(),
                           file_name=f"Titan_Logs_{datetime.now().strftime('%Y%m%d')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
