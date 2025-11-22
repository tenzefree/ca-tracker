import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from datetime import datetime, timedelta, date

# ==========================================
# 1. APP CONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="CA Titan Platinum", page_icon="🛡️", layout="wide")

DB_FILE = "CA_Titan_DB.xlsx"
EXAM_DATE = date(2026, 5, 1)

# Professional Light Mode Styling
st.markdown("""
    <style>
    /* Global Settings */
    .stApp {background-color: #FFFFFF; color: #1A202C;}
    
    /* Metric Cards */
    .metric-box {
        background-color: #F8F9FA;
        border: 1px solid #E2E8F0;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* Strict Alert (Red) */
    .strict-alert {
        background-color: #FFF5F5;
        border: 1px solid #FC8181;
        color: #C53030;
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 15px;
    }
    
    /* Revision Alert (Yellow) */
    .rev-alert {
        background-color: #FFFFF0;
        border: 1px solid #F6E05E;
        color: #744210;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        font-size: 14px;
    }

    /* Timer Display */
    .timer-box {
        text-align: center;
        padding: 40px;
        background: #F0FFF4;
        border: 2px solid #48BB78;
        border-radius: 15px;
        margin-top: 20px;
    }
    .timer-text {
        font-size: 80px;
        font-weight: bold;
        color: #2F855A;
        line-height: 1;
    }
    
    /* Headings */
    h1, h2, h3 {color: #2D3748 !important;}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DATABASE ENGINE (SINGLE EXCEL FILE)
# ==========================================

def init_db():
    """Creates the Excel DB with two sheets if it doesn't exist."""
    if not os.path.exists(DB_FILE):
        # Sheet 1: Master Syllabus
        df_master = pd.DataFrame(columns=[
            'Subject', 'Chapter', 'Topic', 'Est_Hours', 
            'Status', 'Confidence', # Status: Pending, Class Done... Confidence: High/Med/Low
            'Rev_Count', 'Last_Studied', 'RTP_Done', 'MTP_Done'
        ])
        # Sheet 2: Daily Logs
        df_logs = pd.DataFrame(columns=[
            'Date', 'Start_Time', 'End_Time', 'Category', 
            'Subject', 'Topic', 'Duration_Mins', 'Focus', 'Note'
        ])
        
        try:
            with pd.ExcelWriter(DB_FILE, engine='xlsxwriter') as writer:
                df_master.to_excel(writer, sheet_name='Master', index=False)
                df_logs.to_excel(writer, sheet_name='Logs', index=False)
        except Exception as e:
            st.error(f"Error creating database: {e}")

def load_db():
    """Reads data from Excel."""
    try:
        if not os.path.exists(DB_FILE): init_db()
        
        xls = pd.ExcelFile(DB_FILE)
        master = pd.read_excel(xls, 'Master')
        logs = pd.read_excel(xls, 'Logs')
        
        # Ensure correct data types
        if not logs.empty:
            logs['Start_Time'] = pd.to_datetime(logs['Start_Time'])
            logs['End_Time'] = pd.to_datetime(logs['End_Time'])
            
        return master, logs
    except Exception as e:
        st.error(f"Database Read Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

def save_db(master, logs):
    """Writes data back to Excel."""
    try:
        with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='w') as writer:
            master.to_excel(writer, sheet_name='Master', index=False)
            logs.to_excel(writer, sheet_name='Logs', index=False)
        return True
    except PermissionError:
        st.error("🚨 CRITICAL ERROR: Please close 'CA_Titan_DB.xlsx' on your computer before saving data!")
        return False
    except Exception as e:
        st.error(f"Save Failed: {e}")
        return False

# ==========================================
# 3. INTELLIGENCE LOGIC
# ==========================================

def check_strict_gaps(logs_df, current_start_time):
    """Strict Mode: Auto-detects wasted time gaps > 10 mins."""
    if logs_df.empty: return logs_df, 0
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_logs = logs_df[logs_df['Date'] == today_str].sort_values('End_Time')
    
    if today_logs.empty: return logs_df, 0
    
    last_end = today_logs.iloc[-1]['End_Time']
    gap_mins = (current_start_time - last_end).total_seconds() / 60
    
    if gap_mins > 10:
        new_row = {
            'Date': today_str,
            'Start_Time': last_end,
            'End_Time': current_start_time,
            'Category': 'WASTED',
            'Subject': '-', 'Topic': 'UNACCOUNTED GAP',
            'Duration_Mins': round(gap_mins, 2),
            'Focus': 0, 'Note': 'Strict Mode Auto-Detect'
        }
        logs_df = pd.concat([logs_df, pd.DataFrame([new_row])], ignore_index=True)
        return logs_df, gap_mins
        
    return logs_df, 0

def get_revision_alerts(master_df):
    """1-3-7 Day Revision Rule Logic."""
    if master_df.empty: return []
    
    alerts = []
    today = datetime.now().date()
    
    # Filter rows where Last_Studied is present
    valid_rows = master_df.dropna(subset=['Last_Studied']).copy()
    valid_rows['Last_Studied'] = pd.to_datetime(valid_rows['Last_Studied']).dt.date
    
    for idx, row in valid_rows.iterrows():
        gap = (today - row['Last_Studied']).days
        cnt = row['Rev_Count']
        topic = f"{row['Subject']} - {row['Topic']}"
        
        if (cnt == 0 and gap >= 1) or (cnt == 1 and gap >= 3) or (cnt == 2 and gap >= 7) or (cnt >= 3 and gap >= 15):
            alerts.append(topic)
            
    return alerts

def calculate_velocity(master_df, logs_df):
    """Predicts finish date."""
    if master_df.empty or logs_df.empty: return "N/A"
    
    done_count = len(master_df[master_df['Status'].isin(['Mastered', 'Rev 3', 'Rev 2', 'Rev 1', 'Class Done'])])
    total_count = len(master_df)
    
    if done_count == 0: return "Calculating..."
    
    start_date = logs_df['Date'].min()
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        
    days_passed = (datetime.now().date() - start_date).days + 1
    rate = done_count / days_passed # Topics per day
    
    if rate <= 0: return "Stalled"
    
    days_needed = (total_count - done_count) / rate
    finish_date = datetime.now() + timedelta(days=days_needed)
    return finish_date.strftime("%d %b %Y")

# ==========================================
# 4. APP INTERFACE
# ==========================================

init_db()
master_df, logs_df = load_db()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ CA Titan OS")
    days_left = (EXAM_DATE - date.today()).days
    st.success(f"📅 **{days_left} Days** to May '26")
    
    if st.button("🔄 Refresh Database"):
        st.rerun()

# --- TABS ---
tab_cmd, tab_track, tab_db, tab_audit = st.tabs(["📊 Command Center", "⏱️ Tracker", "🗃️ Master DB", "🕵️ 24H Audit"])

# ==========================
# TAB 1: COMMAND CENTER
# ==========================
with tab_cmd:
    # 1. Strict Alerts
    if not logs_df.empty:
        today = datetime.now().strftime("%Y-%m-%d")
        today_df = logs_df[logs_df['Date'] == today]
        
        waste = today_df[today_df['Category'] == 'WASTED']['Duration_Mins'].sum()
        study = today_df[today_df['Category'].str.contains('Study|Class')]['Duration_Mins'].sum()
        
        if waste > study:
            st.markdown(f"<div class='strict-alert'>🚨 DISCIPLINE ALERT: Wasted ({int(waste)}m) > Study ({int(study)}m). GET TO WORK.</div>", unsafe_allow_html=True)

    # 2. Revision Alerts
    alerts = get_revision_alerts(master_df)
    if alerts:
        st.markdown(f"<div class='rev-alert'>⚡ <b>Revision Due:</b> {', '.join(alerts[:5])}...</div>", unsafe_allow_html=True)

    # 3. Metrics
    c1, c2, c3, c4 = st.columns(4)
    
    c1.metric("Projected Finish", calculate_velocity(master_df, logs_df))
    
    coverage = 0
    if not master_df.empty:
        coverage = len(master_df[master_df['Status'] != 'Pending']) / len(master_df) * 100
    c2.metric("Syllabus Done", f"{coverage:.1f}%")
    
    today_hrs = today_df['Duration_Mins'].sum() / 60 if not logs_df.empty else 0
    c3.metric("Hours Today", f"{today_hrs:.1f}h")
    
    high_conf = len(master_df[master_df['Confidence'] == 'High']) if not master_df.empty else 0
    c4.metric("High Confidence", f"{high_conf} Topics")

    st.markdown("---")

    # 4. Visuals
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Confidence Matrix")
        if not master_df.empty:
            fig = px.pie(master_df, names='Confidence', color='Confidence', 
                         color_discrete_map={'High':'#48BB78', 'Med':'#ECC94B', 'Low':'#F56565', 'nan':'#CBD5E0'})
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Study Trend (7 Days)")
        if not logs_df.empty:
            # Filter only Study
            study_logs = logs_df[logs_df['Category'].str.contains("Study|Class")]
            daily = study_logs.groupby('Date')['Duration_Mins'].sum().reset_index().tail(7)
            fig2 = px.bar(daily, x='Date', y='Duration_Mins', color_discrete_sequence=['#3182CE'])
            st.plotly_chart(fig2, use_container_width=True)

# ==========================
# TAB 2: TRACKER
# ==========================
with tab_track:
    # Init Timer State
    if 'start_time' not in st.session_state: st.session_state.start_time = None

    # --- IDLE STATE ---
    if st.session_state.start_time is None:
        st.subheader("🚀 Initiate Activity")
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            cat = st.selectbox("Category", ["Study (Core)", "Classes", "Biological", "Logistics", "Wasted"])
            
        with c2:
            # Dynamic Logic for Study
            if "Study" in cat or "Class" in cat:
                if not master_df.empty:
                    subjects = master_df['Subject'].unique()
                    sel_sub = st.selectbox("Subject", subjects)
                    
                    topics = master_df[master_df['Subject'] == sel_sub]['Topic'].unique()
                    sel_top = st.selectbox("Topic", list(topics) + ["➕ Add New Topic"])
                    
                    if sel_top == "➕ Add New Topic":
                        sel_top = st.text_input("Enter New Topic Name")
                        new_chap = st.text_input("Chapter Name")
                        is_new = True
                    else:
                        is_new = False
                        new_chap = ""
                else:
                    st.warning("Master DB Empty. Go to 'Master DB' tab to add data.")
                    sel_sub, sel_top, is_new, new_chap = "-", "-", False, ""
            else:
                sel_sub = "-"
                sel_top = st.text_input("Activity Details", placeholder="e.g. Sleep, Lunch, Commute")
                is_new, new_chap = False, ""

        st.write("")
        if st.button("▶ START TIMER", type="primary", use_container_width=True):
            now = datetime.now()
            
            # 1. Check Strict Gaps
            logs_df, gap = check_strict_gaps(logs_df, now)
            if gap > 0:
                save_db(master_df, logs_df) # Save the wasted gap immediately
                st.toast(f"⚠️ Strict Mode: {int(gap)} mins marked WASTED!", icon="🚨")
            
            # 2. Start
            st.session_state.start_time = now
            st.session_state.cat = cat
            st.session_state.sub = sel_sub
            st.session_state.top = sel_top
            st.session_state.is_new = is_new
            st.session_state.new_chap = new_chap
            st.rerun()

    # --- RUNNING STATE ---
    else:
        elapsed = datetime.now() - st.session_state.start_time
        seconds = int(elapsed.total_seconds())
        
        st.markdown(f"""
        <div class="timer-box">
            <div class="timer-text">{str(timedelta(seconds=seconds))}</div>
            <h3 style="color:#718096; margin-top:10px;">{st.session_state.top}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("⏹ STOP & LOG", type="primary", use_container_width=True):
            st.session_state.end_time = datetime.now()
            st.session_state.show_save = True
            st.rerun()

    # --- SAVE MODAL ---
    if st.session_state.get("show_save"):
        st.markdown("---")
        with st.form("log_form"):
            st.subheader("📝 Update Records")
            
            # Contextual Inputs
            if "Study" in st.session_state.cat:
                c1, c2, c3 = st.columns(3)
                focus = c1.slider("Focus Level", 1, 5, 4)
                status = c2.selectbox("Status Update", ["Pending", "Class Done", "Rev 1", "Rev 2", "Rev 3", "Mastered"])
                conf = c3.select_slider("Confidence", ["Low", "Med", "High"])
                
                chk1, chk2 = st.columns(2)
                rtp = chk1.checkbox("RTP Solved?")
                mtp = chk2.checkbox("MTP Solved?")
            else:
                focus = 0
                status, conf = "-", "-"
                rtp, mtp = False, False
                
            note = st.text_input("Notes")
            
            if st.form_submit_button("💾 CONFIRM & SAVE"):
                duration = (st.session_state.end_time - st.session_state.start_time).total_seconds() / 60
                
                # 1. Update Log
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
                # Reload to ensure sync
                m_df, l_df = load_db()
                l_df = pd.concat([l_df, pd.DataFrame([new_log])], ignore_index=True)
                
                # 2. Update Master (If Study)
                if "Study" in st.session_state.cat:
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    
                    if st.session_state.is_new:
                        # Create New Row
                        new_master = {
                            'Subject': st.session_state.sub, 'Chapter': st.session_state.new_chap, 'Topic': st.session_state.top,
                            'Status': status, 'Confidence': conf, 'Rev_Count': 0, 'Last_Studied': today_str,
                            'RTP_Done': "Yes" if rtp else "No", 'MTP_Done': "Yes" if mtp else "No"
                        }
                        m_df = pd.concat([m_df, pd.DataFrame([new_master])], ignore_index=True)
                    else:
                        # Update Existing Row
                        mask = (m_df['Subject'] == st.session_state.sub) & (m_df['Topic'] == st.session_state.top)
                        if mask.any():
                            idx = m_df[mask].index[0]
                            m_df.at[idx, 'Status'] = status
                            m_df.at[idx, 'Confidence'] = conf
                            m_df.at[idx, 'Last_Studied'] = today_str
                            if "Rev" in status: m_df.at[idx, 'Rev_Count'] += 1
                            if rtp: m_df.at[idx, 'RTP_Done'] = "Yes"
                            if mtp: m_df.at[idx, 'MTP_Done'] = "Yes"

                # 3. Save
                if save_db(m_df, l_df):
                    st.session_state.start_time = None
                    st.session_state.show_save = False
                    st.success("Saved Successfully!")
                    time.sleep(1)
                    st.rerun()

# ==========================
# TAB 3: MASTER DB
# ==========================
with tab_db:
    st.subheader("🗃️ Master Syllabus Management")
    st.info("You can edit this table directly. Changes are written to Excel immediately upon 'Save'.")
    
    if not master_df.empty:
        edited_master = st.data_editor(master_df, num_rows="dynamic", use_container_width=True, height=600)
        if st.button("💾 Save Master DB Changes"):
            save_db(edited_master, logs_df)
            st.success("Database Updated!")
            time.sleep(1)
            st.rerun()
    else:
        st.warning("Database is empty. Add rows above.")

# ==========================
# TAB 4: 24H AUDIT
# ==========================
with tab_audit:
    st.subheader("🕵️ Daily Timeline Audit")
    
    if not logs_df.empty:
        today = datetime.now().strftime("%Y-%m-%d")
        today_logs = logs_df[logs_df['Date'] == today]
        
        if not today_logs.empty:
            fig = px.timeline(today_logs, x_start="Start_Time", x_end="End_Time", y="Category", 
                              color="Category", hover_data=["Topic", "Duration_Mins"],
                              color_discrete_map={"WASTED":"#E53E3E", "Study (Core)":"#38A169", "Classes":"#3182CE"})
            fig.update_yaxes(autorange="reversed")
            fig.layout.template = "plotly_white"
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(today_logs[['Start_Time', 'End_Time', 'Category', 'Subject', 'Topic', 'Duration_Mins']], use_container_width=True)
        else:
            st.info("No logs for today.")
