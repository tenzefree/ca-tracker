import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from datetime import datetime, timedelta, date

# --- CONFIGURATION ---
st.set_page_config(page_title="CA Titan Platinum", page_icon="🛡️", layout="wide")
DB_FILE = "CA_Titan_DB.xlsx"
EXAM_DATE = date(2026, 5, 1)

# --- LIGHT MODE MILITARY STYLING ---
st.markdown("""
    <style>
    .stApp {background-color: #FFFFFF; color: #111;}
    
    /* Dashboard Cards */
    .metric-box {
        background-color: #F8F9FA;
        border-left: 5px solid #2C5282;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-radius: 5px;
    }
    
    /* Strict Alert - Red Box */
    .strict-alert {
        background-color: #FFF5F5;
        border: 2px solid #C53030;
        color: #C53030;
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 20px;
    }
    
    /* Revision Alert - Yellow Box */
    .rev-alert {
        background-color: #FFFFF0;
        border: 2px solid #D69E2E;
        color: #744210;
        padding: 10px;
        border-radius: 5px;
    }
    
    /* Timer */
    .timer-display {
        font-size: 80px; 
        font-weight: bold; 
        color: #2F855A;
        text-align: center;
        background: #F0FFF4;
        border: 1px solid #9AE6B4;
        border-radius: 20px;
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 1. DATABASE ENGINE (SINGLE EXCEL) ---
def init_db():
    if not os.path.exists(DB_FILE):
        # DETAILED MASTER SHEET
        df_master = pd.DataFrame(columns=[
            'Subject', 'Chapter', 'Topic', 'Est_Hours', 
            'Status', 'Confidence', # Pending, Class Done, Rev 1...
            'Rev_Count', 'Last_Studied', 'RTP_Done', 'MTP_Done'
        ])
        # LOGS SHEET
        df_logs = pd.DataFrame(columns=[
            'Date', 'Start_Time', 'End_Time', 'Category', 
            'Subject', 'Topic', 'Duration_Mins', 'Focus', 'Note'
        ])
        
        with pd.ExcelWriter(DB_FILE, engine='xlsxwriter') as writer:
            df_master.to_excel(writer, sheet_name='Master', index=False)
            df_logs.to_excel(writer, sheet_name='Logs', index=False)

def load_db():
    try:
        if not os.path.exists(DB_FILE): init_db()
        xls = pd.ExcelFile(DB_FILE)
        master = pd.read_excel(xls, 'Master')
        logs = pd.read_excel(xls, 'Logs')
        return master, logs
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

def save_db(master, logs):
    try:
        with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='w') as writer:
            master.to_excel(writer, sheet_name='Master', index=False)
            logs.to_excel(writer, sheet_name='Logs', index=False)
        return True
    except PermissionError:
        st.error("🚨 CRITICAL: Close 'CA_Titan_DB.xlsx' immediately! File is locked.")
        return False

# --- 2. INTELLIGENCE ENGINES ---

def check_strict_gaps(logs):
    """Checks if user wasted time between tasks."""
    if logs.empty: return logs, 0
    
    logs['End_Time'] = pd.to_datetime(logs['End_Time'])
    today = datetime.now().strftime("%Y-%m-%d")
    today_logs = logs[logs['Date'] == today].sort_values('End_Time')
    
    if today_logs.empty: return logs, 0
    
    last_end = today_logs.iloc[-1]['End_Time']
    now = datetime.now()
    gap_mins = (now - last_end).total_seconds() / 60
    
    # STRICT RULE: 10 Mins Tolerance
    if gap_mins > 10:
        new_row = {
            'Date': today, 'Start_Time': last_end, 'End_Time': now,
            'Category': 'WASTED', 'Subject': '-', 'Topic': 'UNACCOUNTED GAP',
            'Duration_Mins': round(gap_mins, 2), 'Focus': 0, 'Note': 'Strict Mode Auto-Detect'
        }
        logs = pd.concat([logs, pd.DataFrame([new_row])], ignore_index=True)
        return logs, gap_mins
    return logs, 0

def calculate_velocity(master, logs):
    """Predicts finish date based on speed."""
    if master.empty: return "No Data"
    
    total_topics = len(master)
    done_topics = len(master[master['Status'].isin(['Mastered', 'Rev 3', 'Rev 2', 'Rev 1', 'Class Done'])])
    
    if done_topics == 0: return "Calculating..."
    
    # Assume start date was first log
    if logs.empty: return "No Logs"
    first_log = pd.to_datetime(logs['Date']).min()
    days_passed = (datetime.now() - first_log).days + 1
    
    avg_speed = done_topics / days_passed # topics per day
    remaining = total_topics - done_topics
    days_needed = remaining / avg_speed if avg_speed > 0 else 999
    
    finish_date = datetime.now() + timedelta(days=days_needed)
    return finish_date.strftime("%d %b %Y")

def get_revision_dues(master):
    """Finds topics due for revision based on 1-3-7 rule."""
    if master.empty: return []
    
    master['Last_Studied'] = pd.to_datetime(master['Last_Studied'], errors='coerce')
    today = datetime.now()
    dues = []
    
    for idx, row in master.iterrows():
        if pd.isna(row['Last_Studied']): continue
        
        days_gap = (today - row['Last_Studied']).days
        rev_count = row['Rev_Count']
        
        # Logic: Rev 0->1 (1 day), Rev 1->2 (3 days), Rev 2->3 (7 days)
        if rev_count == 0 and days_gap >= 1: dues.append(row['Topic'])
        elif rev_count == 1 and days_gap >= 3: dues.append(row['Topic'])
        elif rev_count == 2 and days_gap >= 7: dues.append(row['Topic'])
        elif rev_count >= 3 and days_gap >= 15: dues.append(row['Topic'])
        
    return dues

# --- MAIN APP ---
init_db()
master_df, logs_df = load_db()

# SIDEBAR
with st.sidebar:
    st.title("🛡️ TITAN OS")
    days = (EXAM_DATE - date.today()).days
    st.success(f"📅 **{days} Days** to May 2026")
    
    if st.button("🔄 Refresh DB"): st.rerun()

# TABS
tab_cmd, tab_track, tab_db, tab_audit = st.tabs(["📊 Command Center", "⏱️ Tracker", "🗃️ Master Excel", "🕵️ 24H Audit"])

# ==========================
# TAB 1: COMMAND CENTER (POWER BI STYLE)
# ==========================
with tab_cmd:
    # 1. STRICT ALERTS
    if not logs_df.empty:
        today = datetime.now().strftime("%Y-%m-%d")
        t_df = logs_df[logs_df['Date'] == today]
        waste = t_df[t_df['Category'] == 'WASTED']['Duration_Mins'].sum()
        study = t_df[t_df['Category'].str.contains('Study|Class')]['Duration_Mins'].sum()
        
        if waste > study:
            st.markdown(f"<div class='strict-alert'>🚨 DISCIPLINE ALERT: Wasted Time ({int(waste)}m) > Study Time ({int(study)}m). UNACCEPTABLE.</div>", unsafe_allow_html=True)

    # 2. REVISION RADAR
    dues = get_revision_dues(master_df)
    if dues:
        st.markdown(f"<div class='rev-alert'>⚡ <b>{len(dues)} Topics Due for Revision:</b> {', '.join(dues[:5])}...</div>", unsafe_allow_html=True)

    st.write("") # Spacer

    # 3. VELOCITY & METRICS
    col1, col2, col3, col4 = st.columns(4)
    
    finish_date = calculate_velocity(master_df, logs_df)
    col1.metric("Projected Finish Date", finish_date, delta="Based on current speed")
    
    if not master_df.empty:
        coverage = len(master_df[master_df['Status']!='Pending']) / len(master_df) * 100
        col2.metric("Syllabus Coverage", f"{coverage:.1f}%")
        
        high_conf = len(master_df[master_df['Confidence']=='High'])
        col3.metric("High Confidence", f"{high_conf} Topics")
        
    today_eff = t_df['Duration_Mins'].sum() / 60 if not logs_df.empty else 0
    col4.metric("Total Logged Today", f"{today_eff:.1f} hrs")

    st.markdown("---")
    
    # 4. CHARTS
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Confidence Matrix")
        if not master_df.empty:
            fig = px.pie(master_df, names='Confidence', color='Confidence',
                         color_discrete_map={'High':'#48BB78', 'Med':'#ECC94B', 'Low':'#F56565', 'nan':'#CBD5E0'})
            st.plotly_chart(fig, use_container_width=True)
            
    with c2:
        st.subheader("Study Trend (Last 7 Days)")
        if not logs_df.empty:
            # Group by date
            daily = logs_df[logs_df['Category'].str.contains('Study')].groupby('Date')['Duration_Mins'].sum().reset_index()
            fig2 = px.bar(daily.tail(7), x='Date', y='Duration_Mins', title="Study Minutes")
            st.plotly_chart(fig2, use_container_width=True)

# ==========================
# TAB 2: TRACKER (STRICT)
# ==========================
with tab_track:
    if 'start_time' not in st.session_state: st.session_state.start_time = None

    if st.session_state.start_time is None:
        # --- IDLE ---
        c1, c2 = st.columns([1, 2])
        with c1:
            cat = st.selectbox("Category", ["Study (Core)", "Classes", "Biological", "Logistics", "Wasted"])
        with c2:
            if "Study" in cat or "Class" in cat:
                if master_df.empty:
                    st.error("Master DB Empty! Go to 'Master Excel' tab to add topics.")
                    sub, top = "-", "-"
                else:
                    sub = st.selectbox("Subject", master_df['Subject'].unique())
                    # Filter Chapters
                    chaps = master_df[master_df['Subject']==sub]['Chapter'].unique()
                    chap = st.selectbox("Chapter", chaps)
                    # Filter Topics
                    tops = master_df[(master_df['Subject']==sub) & (master_df['Chapter']==chap)]['Topic'].unique()
                    top = st.selectbox("Topic", list(tops) + ["➕ ADD NEW TOPIC"])
                    
                    if top == "➕ ADD NEW TOPIC":
                        top = st.text_input("Enter New Topic Name")
                        st.session_state.is_new = True
                    else:
                        st.session_state.is_new = False
            else:
                sub = "-"
                top = st.text_input("Description", placeholder="e.g. Sleep, Lunch")
                st.session_state.is_new = False

        if st.button("▶ INITIATE", type="primary", use_container_width=True):
            # GAP CHECK
            logs_df, gap = check_strict_gaps(logs_df)
            if gap > 0:
                save_db(master_df, logs_df)
                st.toast(f"⚠️ Strict Mode: {int(gap)} mins marked WASTED", icon="🚨")
            
            st.session_state.start_time = datetime.now()
            st.session_state.cat = cat
            st.session_state.sub = sub
            st.session_state.top = top
            st.session_state.chap = locals().get('chap', '-')
            st.rerun()

    else:
        # --- RUNNING ---
        elapsed = datetime.now() - st.session_state.start_time
        st.markdown(f"<div class='timer-display'>{str(timedelta(seconds=elapsed.seconds))}</div>", unsafe_allow_html=True)
        st.write(f"**Current:** {st.session_state.top}")
        
        if st.button("⏹ STOP & REPORT", type="primary", use_container_width=True):
            st.session_state.end_time = datetime.now()
            st.session_state.show_log = True
            st.rerun()

    # SAVE FORM
    if st.session_state.get("show_log"):
        st.markdown("---")
        with st.form("log_form"):
            st.subheader("📝 Mission Debrief")
            
            if "Study" in st.session_state.cat or "Class" in st.session_state.cat:
                c1, c2, c3 = st.columns(3)
                focus = c1.slider("Focus", 1, 5, 4)
                status = c2.selectbox("New Status", ["Class Done", "Rev 1", "Rev 2", "Rev 3", "Mastered"])
                conf = c3.select_slider("Confidence", ["Low", "Med", "High"])
                rtp = st.checkbox("RTP Solved?")
                mtp = st.checkbox("MTP Solved?")
            else:
                focus = 0
                status, conf = "-", "-"
                rtp, mtp = False, False
                
            note = st.text_input("Notes")
            
            if st.form_submit_button("💾 WRITE TO EXCEL"):
                duration = (st.session_state.end_time - st.session_state.start_time).total_seconds() / 60
                
                # 1. Update Master DB
                if "Study" in st.session_state.cat:
                    if st.session_state.is_new:
                        new_row = {
                            'Subject': st.session_state.sub, 'Chapter': st.session_state.chap, 'Topic': st.session_state.top,
                            'Status': status, 'Confidence': conf, 'Est_Hours': 2,
                            'Rev_Count': 0, 'Last_Studied': datetime.now().strftime("%Y-%m-%d"), 
                            'RTP_Done': "Yes" if rtp else "No", 'MTP_Done': "Yes" if mtp else "No"
                        }
                        master_df = pd.concat([master_df, pd.DataFrame([new_row])], ignore_index=True)
                    else:
                        # Find Row
                        mask = (master_df['Subject'] == st.session_state.sub) & (master_df['Topic'] == st.session_state.top)
                        if mask.any():
                            idx = master_df[mask].index[0]
                            master_df.at[idx, 'Status'] = status
                            master_df.at[idx, 'Confidence'] = conf
                            master_df.at[idx, 'Last_Studied'] = datetime.now().strftime("%Y-%m-%d")
                            if "Rev" in status: master_df.at[idx, 'Rev_Count'] += 1
                            if rtp: master_df.at[idx, 'RTP_Done'] = "Yes"
                            if mtp: master_df.at[idx, 'MTP_Done'] = "Yes"

                # 2. Add Log
                new_log = {
                    'Date': st.session_state.start_time.strftime("%Y-%m-%d"),
                    'Start_Time': st.session_state.start_time,
                    'End_Time': st.session_state.end_time,
                    'Category': st.session_state.cat,
                    'Subject': st.session_state.sub,
                    'Topic': st.session_state.top,
                    'Duration_Mins': round(duration, 2),
                    'Focus': focus, 'Note': note
                }
                logs_df = pd.concat([logs_df, pd.DataFrame([new_log])], ignore_index=True)
                
                save_db(master_df, logs_df)
                st.session_state.start_time = None
                st.session_state.show_log = False
                st.success("Data Recorded.")
                time.sleep(1)
                st.rerun()

# ==========================
# TAB 3: MASTER EXCEL
# ==========================
with tab_db:
    st.subheader("🗃️ Syllabus Master Sheet")
    st.info("You can Add Topics, Change Status, or Edit Confidence directly here.")
    
    if not master_df.empty:
        edited_master = st.data_editor(master_df, num_rows="dynamic", use_container_width=True, height=500)
        if st.button("💾 Save Syllabus Changes"):
            save_db(edited_master, logs_df)
            st.success("Updated Excel!")

# ==========================
# TAB 4: 24H AUDIT
# ==========================
with tab_audit:
    st.subheader("🕵️ Daily Timeline Audit")
    if not logs_df.empty:
        logs_df['Start_Time'] = pd.to_datetime(logs_df['Start_Time'])
        logs_df['End_Time'] = pd.to_datetime(logs_df['End_Time'])
        
        today = datetime.now().strftime("%Y-%m-%d")
        day_df = logs_df[logs_df['Date'] == today]
        
        if not day_df.empty:
            fig = px.timeline(day_df, x_start="Start_Time", x_end="End_Time", y="Category", 
                              color="Category", hover_data=["Topic", "Duration_Mins"],
                              color_discrete_map={"WASTED":"#E53E3E", "Study (Core)":"#38A169", "Classes":"#3182CE"})
            fig.update_yaxes(autorange="reversed")
            fig.layout.template = "plotly_white"
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No logs for today.")
