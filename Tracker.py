import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="CA Titan (Light)", page_icon="🛡️", layout="wide")
DB_FILE = "CA_Titan_DB.xlsx"

# --- LIGHT MODE STYLING ---
st.markdown("""
    <style>
    /* White Background */
    .stApp {background-color: #FFFFFF; color: #000000;}
    
    /* Cards */
    .metric-card {
        background-color: #F8F9FA; 
        border: 1px solid #E0E0E0; 
        padding: 15px; 
        border-radius: 10px; 
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Strict Alert Box */
    .alert-box {
        background-color: #FFF5F5; 
        border: 1px solid #FC8181; 
        padding: 10px; 
        border-radius: 5px; 
        color: #C53030;
        font-weight: bold;
    }
    
    /* Timer Box */
    .timer-box {
        text-align: center;
        padding: 40px;
        background: #F0FFF4;
        border: 2px solid #48BB78;
        border-radius: 15px;
    }
    
    h1, h2, h3 {color: #1A202C !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 1. EXCEL DATABASE ENGINE ---
def init_db():
    """Creates the Master Excel file if it doesn't exist."""
    if not os.path.exists(DB_FILE):
        # Sheet 1: Master Syllabus
        df_master = pd.DataFrame(columns=[
            'Subject', 'Chapter', 'Topic', 'Est_Hours', 
            'Status', 'Confidence', # Status: Pending, Class Done, Revision... Confidence: High, Med, Low
            'Rev_Count', 'RTP_Done', 'MTP_Done'
        ])
        # Sheet 2: Activity Logs
        df_logs = pd.DataFrame(columns=[
            'Date', 'Start_Time', 'End_Time', 'Category', 
            'Subject', 'Topic', 'Duration_Mins', 'Focus', 'Note'
        ])
        
        try:
            with pd.ExcelWriter(DB_FILE, engine='xlsxwriter') as writer:
                df_master.to_excel(writer, sheet_name='Master', index=False)
                df_logs.to_excel(writer, sheet_name='Logs', index=False)
        except Exception as e:
            st.error(f"Error creating DB: {e}")

def load_db():
    """Reads both sheets."""
    try:
        if not os.path.exists(DB_FILE):
            init_db()
            
        # Read Excel
        xls = pd.ExcelFile(DB_FILE)
        df_master = pd.read_excel(xls, 'Master')
        df_logs = pd.read_excel(xls, 'Logs')
        
        # Ensure Columns Exist (Fixes bugs if Excel was edited manually)
        if 'Duration_Mins' not in df_logs.columns: df_logs['Duration_Mins'] = 0.0
        
        return df_master, df_logs
    except Exception as e:
        st.error(f"Error loading Database: {e}")
        return pd.DataFrame(), pd.DataFrame()

def save_db(df_master, df_logs):
    """Writes back to Excel safely."""
    try:
        with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='w') as writer:
            df_master.to_excel(writer, sheet_name='Master', index=False)
            df_logs.to_excel(writer, sheet_name='Logs', index=False)
        return True
    except PermissionError:
        st.error("🚨 CRITICAL: You have the Excel file open! Close 'CA_Titan_DB.xlsx' and click Save again.")
        return False
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False

# --- 2. LOGIC HANDLERS ---

def perform_gap_check(logs_df, current_start_time):
    """Checks if there is a gap between last log and now."""
    if logs_df.empty: return logs_df, 0
    
    # Ensure Date formats
    logs_df['End_Time'] = pd.to_datetime(logs_df['End_Time'])
    
    # Filter for Today Only
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_logs = logs_df[logs_df['Date'] == today_str].copy()
    
    if today_logs.empty: return logs_df, 0
    
    # Get last end time
    last_end = today_logs.iloc[-1]['End_Time']
    
    # Calculate Gap
    gap_mins = (current_start_time - last_end).total_seconds() / 60
    
    if gap_mins > 15: # Tolerance 15 mins
        new_row = {
            'Date': today_str,
            'Start_Time': last_end,
            'End_Time': current_start_time,
            'Category': 'WASTED',
            'Subject': '-', 'Topic': 'UNACCOUNTED GAP',
            'Duration_Mins': round(gap_mins, 2),
            'Focus': 0, 'Note': 'Auto-detected Strict Mode'
        }
        # Add to dataframe
        new_df = pd.DataFrame([new_row])
        logs_df = pd.concat([logs_df, new_df], ignore_index=True)
        return logs_df, gap_mins
        
    return logs_df, 0

# --- MAIN APP ---
init_db()
master_df, logs_df = load_db()

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2913/2913520.png", width=50)
    st.title("Titan OS")
    st.caption("Excel-Core Edition")
    if st.button("🔄 Refresh DB"):
        st.rerun()

# Tabs
tab_track, tab_dash, tab_db = st.tabs(["⏱️ Tracker", "📊 Dashboard", "🗃️ Database"])

# ==========================
# TAB 1: TRACKER
# ==========================
with tab_track:
    # Timer State
    if 'start_time' not in st.session_state: st.session_state.start_time = None

    # --- IDLE SCREEN ---
    if st.session_state.start_time is None:
        st.subheader("🚀 Initiate Session")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            cat = st.selectbox("Category", ["Study (Core)", "Classes", "Biological", "Logistics", "Wasted"])
        
        with c2:
            if "Study" in cat or "Class" in cat:
                if not master_df.empty:
                    sub_list = master_df['Subject'].unique().tolist()
                    sel_sub = st.selectbox("Subject", sub_list)
                    
                    top_list = master_df[master_df['Subject'] == sel_sub]['Topic'].unique().tolist()
                    sel_top = st.selectbox("Topic", top_list + ["➕ New Topic"])
                    
                    if sel_top == "➕ New Topic":
                        sel_top = st.text_input("Enter Topic Name")
                        new_chap = st.text_input("Enter Chapter Name")
                        is_new = True
                    else:
                        is_new = False
                else:
                    st.warning("Master DB Empty. Add topics in 'Database' tab.")
                    sel_sub, sel_top = "Gen", "Gen"
                    is_new = False
            else:
                sel_sub = "-"
                sel_top = st.text_input("Activity Details", placeholder="e.g. Lunch, Commute")
                is_new = False

        if st.button("▶ START", type="primary", use_container_width=True):
            now = datetime.now()
            
            # 1. Check Gaps Logic
            updated_logs, gap = perform_gap_check(logs_df, now)
            
            if gap > 0:
                # Save the gap immediately to Excel
                save_db(master_df, updated_logs)
                st.toast(f"⚠️ Strict Mode: {int(gap)} mins marked as WASTED", icon="🚨")
            
            # 2. Start Timer
            st.session_state.start_time = now
            st.session_state.cat = cat
            st.session_state.sub = sel_sub
            st.session_state.top = sel_top
            st.session_state.is_new = is_new
            if is_new: st.session_state.new_chap = new_chap
            st.rerun()

    # --- RUNNING SCREEN ---
    else:
        elapsed = datetime.now() - st.session_state.start_time
        secs = int(elapsed.total_seconds())
        
        st.markdown(f"""
        <div class="timer-box">
            <h1 style="font-size: 80px; margin:0; color: #28A745;">{str(timedelta(seconds=secs))}</h1>
            <h3 style="color: #555;">{st.session_state.top}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("⏹ STOP & SAVE", type="primary", use_container_width=True):
            st.session_state.end_time = datetime.now()
            st.session_state.show_save = True
            st.rerun()

    # --- SAVE MODAL ---
    if st.session_state.get("show_save"):
        st.markdown("---")
        with st.form("save_form"):
            st.subheader("📝 Log Details")
            
            if "Study" in st.session_state.cat:
                c1, c2 = st.columns(2)
                focus = c1.slider("Focus", 1, 5, 4)
                status = c2.selectbox("Status", ["Pending", "Class Done", "Rev 1", "Rev 2", "Rev 3", "Mastered"])
                conf = st.select_slider("Confidence", ["Low", "Med", "High"])
            else:
                focus = 0
                status, conf = "N/A", "N/A"
            
            note = st.text_input("Notes")
            
            if st.form_submit_button("💾 SAVE TO EXCEL"):
                # 1. Update Log Dataframe
                duration = (st.session_state.end_time - st.session_state.start_time).total_seconds() / 60
                
                # Reload DB to ensure we have latest gap data
                m_df, l_df = load_db()
                
                new_log = {
                    'Date': st.session_state.start_time.strftime("%Y-%m-%d"),
                    'Start_Time': st.session_state.start_time,
                    'End_Time': st.session_state.end_time,
                    'Category': st.session_state.cat,
                    'Subject': st.session_state.sub,
                    'Topic': st.session_state.top,
                    'Duration_Mins': round(duration, 2),
                    'Focus': focus,
                    'Note': note
                }
                l_df = pd.concat([l_df, pd.DataFrame([new_log])], ignore_index=True)
                
                # 2. Update Master Dataframe (If Study)
                if "Study" in st.session_state.cat:
                    if st.session_state.is_new:
                        # Add New Topic
                        new_row = {
                            'Subject': st.session_state.sub, 'Chapter': st.session_state.new_chap,
                            'Topic': st.session_state.top, 'Status': status, 'Confidence': conf,
                            'Rev_Count': 0, 'RTP_Done': 'No', 'MTP_Done': 'No'
                        }
                        m_df = pd.concat([m_df, pd.DataFrame([new_row])], ignore_index=True)
                    else:
                        # Update Existing
                        mask = (m_df['Subject'] == st.session_state.sub) & (m_df['Topic'] == st.session_state.top)
                        if mask.any():
                            idx = m_df[mask].index[0]
                            m_df.at[idx, 'Status'] = status
                            m_df.at[idx, 'Confidence'] = conf
                            if "Rev" in status:
                                m_df.at[idx, 'Rev_Count'] = m_df.at[idx, 'Rev_Count'] + 1
                
                # 3. Save to File
                if save_db(m_df, l_df):
                    st.session_state.start_time = None
                    st.session_state.show_save = False
                    st.success("Saved to Excel!")
                    time.sleep(1)
                    st.rerun()

# ==========================
# TAB 2: DASHBOARD
# ==========================
with tab_dash:
    st.subheader("📊 Analytics")
    
    if not logs_df.empty:
        # Ensure Dates
        logs_df['Start_Time'] = pd.to_datetime(logs_df['Start_Time'])
        logs_df['End_Time'] = pd.to_datetime(logs_df['End_Time'])
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_df = logs_df[logs_df['Date'] == today]
        
        # 1. Summary
        studymins = today_df[today_df['Category'].str.contains("Study|Class")]['Duration_Mins'].sum()
        wastemins = today_df[today_df['Category'] == "WASTED"]['Duration_Mins'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Study Today", f"{int(studymins/60)}h {int(studymins%60)}m")
        c2.metric("Wasted/Gap", f"{int(wastemins/60)}h {int(wastemins%60)}m", delta_color="inverse")
        
        if not master_df.empty:
            done = len(master_df[master_df['Status'] == 'Mastered'])
            total = len(master_df)
            c3.metric("Syllabus Mastered", f"{done}/{total}")
        
        st.markdown("---")
        
        # 2. Timeline Chart (Light Mode)
        if not today_df.empty:
            st.write("Today's Timeline")
            fig = px.timeline(today_df, x_start="Start_Time", x_end="End_Time", y="Category", 
                              color="Category",
                              color_discrete_map={"WASTED": "#E53E3E", "Study (Core)": "#38A169", "Biological": "#3182CE"})
            fig.update_yaxes(autorange="reversed")
            fig.layout.template = "plotly_white" # Light theme
            st.plotly_chart(fig, use_container_width=True)
        
        # 3. Confidence Chart
        if not master_df.empty:
            st.write("Topic Confidence")
            fig2 = px.pie(master_df, names='Confidence', 
                          color='Confidence', 
                          color_discrete_map={'High':'#48BB78', 'Med':'#ECC94B', 'Low':'#F56565'})
            st.plotly_chart(fig2, use_container_width=True)

# ==========================
# TAB 3: DATABASE
# ==========================
with tab_db:
    st.subheader("🗃️ Excel Manager")
    st.info("Edit cells below -> Click Save. Do NOT open the Excel file manually while using this.")
    
    t1, t2 = st.tabs(["Master Syllabus", "Logs History"])
    
    with t1:
        if not master_df.empty:
            edited_master = st.data_editor(master_df, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Update Master DB"):
                save_db(edited_master, logs_df)
                st.success("Saved!")
                
    with t2:
        if not logs_df.empty:
            edited_logs = st.data_editor(logs_df, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Update Logs"):
                save_db(master_df, edited_logs)
                st.success("Saved!")
