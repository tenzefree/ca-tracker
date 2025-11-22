import streamlit as st
import pandas as pd
import plotly.express as px
import json
import time
import os
import io
from datetime import datetime, date, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="CA LifeOS", page_icon="🧬", layout="wide")
DATA_FILE = "ca_life_os.json"
EXAM_DATE = date(2026, 5, 1)

# --- HIERARCHY (TRACK EVERYTHING) ---
SCHEMA = {
    "📚 Study (Core)": ["FR Class", "AFM Class", "Audit Class", "DT Class", "IDT Class", "Self Study", "Practice/Mock"],
    "💤 Biological": ["Sleep", "Nap", "Meals", "Shower/Hygiene"],
    "🏃‍♂️ Health": ["Gym/Walk", "Meditation", "Doctor"],
    "🏠 Logistics": ["Commute", "Housework", "Planning/Admin", "Marriage Works"],
    "🍿 Leisure": ["Social Media", "TV/Movies", "Friends/Outing", "Gaming"],
    "🗑️ Wasted Time": ["Procrastination", "Nothing/Idle"]
}

# --- COLORS FOR TIMELINE ---
COLORS = {
    "📚 Study (Core)": "#00CC96",  # Green
    "💤 Biological": "#636EFA",    # Blue
    "🏃‍♂️ Health": "#AB63FA",       # Purple
    "🏠 Logistics": "#FFA15A",     # Orange
    "🍿 Leisure": "#FF6692",       # Pink
    "🗑️ Wasted Time": "#EF553B"    # Red
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

# --- SIDEBAR (THE CONTROLLER) ---
with st.sidebar:
    st.title("🧬 CA LifeOS")
    days = (EXAM_DATE - date.today()).days
    st.caption(f"Target: May 2026 ({days} days left)")
    
    st.markdown("---")
    
    # 🔴 LIVE TRACKER
    if 'start_time' not in st.session_state: st.session_state.start_time = None
    
    if st.session_state.start_time is None:
        st.subheader("🔴 Start Activity")
        cat = st.selectbox("Category", list(SCHEMA.keys()))
        act = st.selectbox("Activity", SCHEMA[cat])
        note = st.text_input("Note", placeholder="Details...")
        
        if st.button("▶ START", type="primary", use_container_width=True):
            st.session_state.start_time = time.time()
            st.session_state.curr_cat = cat
            st.session_state.curr_act = act
            st.session_state.curr_note = note
            st.rerun()
            
    else:
        elapsed = time.time() - st.session_state.start_time
        st.markdown(f"""
        <div style='background:#1E1E1E; padding:15px; border-radius:10px; text-align:center;'>
            <h2 style='color:white; margin:0;'>{time.strftime('%H:%M:%S', time.gmtime(elapsed))}</h2>
            <p style='color:#AAA; margin:0;'>{st.session_state.curr_act}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("⏹ STOP & LOG", type="primary", use_container_width=True):
            st.session_state.duration = time.time() - st.session_state.start_time
            st.session_state.start_time = None
            st.session_state.show_save = True
            st.rerun()

    # SAVE POPUP
    if st.session_state.get("show_save"):
        st.markdown("---")
        st.write("📝 **Review Entry**")
        
        # Logic: If study, ask Focus. If Leisure, ask Guilt?
        rating = 0
        if "Study" in st.session_state.curr_cat:
            rating = st.slider("Focus Level", 1, 5, 4)
        elif "Leisure" in st.session_state.curr_cat or "Waste" in st.session_state.curr_cat:
            rating = st.slider("Enjoyment/Regret Level", 1, 5, 3)
            
        if st.button("💾 Confirm"):
            start_dt = datetime.now() - timedelta(seconds=st.session_state.duration)
            entry = {
                "Start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "End": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Category": st.session_state.curr_cat,
                "Activity": st.session_state.curr_act,
                "Note": st.session_state.curr_note,
                "Duration_Min": round(st.session_state.duration / 60, 2),
                "Rating": rating
            }
            add_entry(entry)
            st.session_state.show_save = False
            st.toast("Logged to LifeOS", icon="🧬")
            time.sleep(1)
            st.rerun()

# --- MAIN DASHBOARD ---
tab_day, tab_study, tab_life, tab_data = st.tabs(["📅 Day Tracker", "📚 Study HQ", "🧬 Life Stats", "⚙️ Data"])

# =========================================
# TAB 1: THE DAY TRACKER (TIMELINE)
# =========================================
with tab_day:
    st.subheader("Today's Timeline (24h)")
    
    data = load_data()
    if data:
        df = pd.DataFrame(data)
        df['Start'] = pd.to_datetime(df['Start'])
        df['End'] = pd.to_datetime(df['End'])
        
        # Filter for TODAY
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_df = df[df['Date'] == today_str].copy()
        
        if not today_df.empty:
            # 1. GANTT CHART
            fig = px.timeline(today_df, x_start="Start", x_end="End", y="Category", 
                              color="Category", hover_data=["Activity", "Note", "Duration_Min"],
                              color_discrete_map=COLORS, height=350)
            fig.update_yaxes(autorange="reversed") # Top to bottom
            st.plotly_chart(fig, use_container_width=True)
            
            # 2. STATS ROW
            total_min = today_df['Duration_Min'].sum()
            study_min = today_df[today_df['Category'].str.contains("Study")]['Duration_Min'].sum()
            waste_min = today_df[today_df['Category'].str.contains("Waste|Leisure")]['Duration_Min'].sum()
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Tracked Time", f"{int(total_min/60)}h {int(total_min%60)}m")
            k2.metric("Study Output", f"{int(study_min/60)}h {int(study_min%60)}m")
            k3.metric("Non-Productive", f"{int(waste_min/60)}h {int(waste_min%60)}m", delta_color="inverse")
            
            # Productivity Pulse
            if (total_min - waste_min) > 0:
                prod_score = int((study_min / total_min) * 100)
                k4.metric("Day Score", f"{prod_score}%")
            
            # 3. DETAILED LIST
            st.markdown("#### 📝 Activity Log")
            st.dataframe(today_df[['Start', 'Category', 'Activity', 'Duration_Min', 'Note']].sort_values('Start', ascending=False), use_container_width=True)
        else:
            st.info("No activities logged today yet. Start the tracker in the sidebar!")
    else:
        st.info("Database empty.")

# =========================================
# TAB 2: STUDY HQ (ACADEMIC)
# =========================================
with tab_study:
    if data:
        df = pd.DataFrame(data)
        study_df = df[df['Category'].str.contains("Study")]
        
        if not study_df.empty:
            c1, c2 = st.columns([2, 1])
            
            with c1:
                st.subheader("Subject Breakdown")
                fig_sun = px.sunburst(study_df, path=['Category', 'Activity'], values='Duration_Min', color='Activity')
                st.plotly_chart(fig_sun, use_container_width=True)
                
            with c2:
                st.subheader("Focus Trend")
                # Average focus by activity
                focus_group = study_df.groupby('Activity')['Rating'].mean().reset_index()
                fig_bar = px.bar(focus_group, x='Rating', y='Activity', orientation='h', title="Avg Focus (1-5)")
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning("No study data found.")

# =========================================
# TAB 3: LIFE STATS (BIO/LOGISTICS)
# =========================================
with tab_life:
    if data:
        df = pd.DataFrame(data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💤 Sleep Analysis")
            sleep_df = df[df['Activity'] == "Sleep"]
            if not sleep_df.empty:
                avg_sleep = sleep_df['Duration_Min'].mean() / 60
                st.metric("Avg Sleep / Night", f"{avg_sleep:.1f} hrs")
                
                # Sleep Chart
                fig_sleep = px.bar(sleep_df, x='Date', y='Duration_Min', title="Sleep Duration")
                st.plotly_chart(fig_sleep, use_container_width=True)
            else:
                st.write("No sleep logs.")

        with col2:
            st.subheader("🏠 Logistics & Overhead")
            log_df = df[df['Category'].str.contains("Logistics|Health")]
            if not log_df.empty:
                fig_pie = px.pie(log_df, names='Activity', values='Duration_Min', title="Where does non-study time go?")
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.write("No logistics logs.")

# =========================================
# TAB 4: DATA VAULT
# =========================================
with tab_data:
    st.subheader("⚙️ Manage Data")
    
    if data:
        df = pd.DataFrame(data)
        
        # 1. EXCEL EXPORT
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='LifeLog')
        
        st.download_button(
            "📥 Download Excel Report",
            data=output.getvalue(),
            file_name=f"LifeOS_Backup_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # 2. EXCEL IMPORT
        st.markdown("---")
        uploaded = st.file_uploader("Restore from Excel", type=['xlsx'])
        if uploaded and st.button("Load Data"):
            try:
                new_df = pd.read_excel(uploaded)
                # Format fix
                new_df['Start'] = new_df['Start'].astype(str)
                new_df['End'] = new_df['End'].astype(str)
                new_df['Date'] = new_df['Date'].astype(str)
                
                save_data(new_df.to_dict(orient='records'))
                st.success("Restored!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        # 3. EDITOR
        with st.expander("✏️ Edit / Delete Entries"):
            edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
            if st.button("Save Changes"):
                save_data(edited.to_dict(orient='records'))
                st.rerun()
