import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import gspread
from google.oauth2.service_account import Credentials
import json
import threading 

# 1. Page Configuration
st.set_page_config(page_title="ASD|SKY Task Vault", layout="wide")

# 2. Cloud Engine
def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_info = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

client = get_gsheet_client()
SHEET_ID = "1d94q4Gwb961oDWc9UasPYWc-yXDLi3vX-epx_uHIVY0" 
sh = client.open_by_key(SHEET_ID)
ws_projects = sh.worksheet("projects")
ws_logs = sh.worksheet("logs")

# 3. Data Buffering
@st.cache_data(ttl=600)
def fetch_initial_data():
    p_list = ws_projects.col_values(1)[1:]
    logs_df = pd.DataFrame(ws_logs.get_all_records())
    return p_list, logs_df

if 'all_logs' not in st.session_state:
    p_list, logs_df = fetch_initial_data()
    st.session_state.project_list = p_list
    st.session_state.all_logs = logs_df

# --- NEW: Recency Logic ---
# Extract unique codes from the last 50 logs to identify 'Active' projects
last_active = st.session_state.all_logs['project_code'].tail(50).unique().tolist()
recent_projects = [p for p in last_active if p in st.session_state.project_list]
other_projects = sorted([p for p in st.session_state.project_list if p not in recent_projects])

# This is your new master list: Recents first, then alphabetical the rest
smart_list = recent_projects + other_projects

# Background Workers
def bg_append(row_data): ws_logs.append_row(row_data)
def bg_delete(row_idx): ws_logs.delete_rows(row_idx)
def bg_update(row_idx, row_data): ws_logs.update([row_data], f"A{row_idx}")

def get_tracker_info(d):
    last_day = calendar.monthrange(d.year, d.month)[1]
    is_payday = (d.day == 15 or d.day == last_day)
    holidays = {
        date(2026, 1, 1): "New Year's", date(2026, 1, 19): "MLK Day",
        date(2026, 5, 25): "Memorial Day", date(2026, 7, 4): "Independence Day",
        date(2026, 9, 7): "Labor Day", date(2026, 11, 26): "Thanksgiving",
        date(2026, 12, 25): "Christmas"
    }
    return is_payday, holidays.get(d)

# --- CSS: Spacing Refinement (Maintained) ---
st.markdown("""
    <style>
    .block-container { padding-top: 3rem !important; }
    
    [data-testid="stSidebar"] hr {
        margin-top: 20px !important; 
        margin-bottom: 30px !important; 
    }
    
    .nav-btn-link {
        display: flex; align-items: center; justify-content: center;
        width: 100%; padding: 10px 0px; border-radius: 8px;
        background-color: #262730; border: 1px solid rgba(255, 255, 255, 0.1);
        color: white !important; font-size: 0.95rem; font-weight: 500;
        text-decoration: none !important; transition: all 0.2s;
        margin-top: 14px; margin-bottom: 0px !important; cursor: pointer;
    }
    .nav-btn-link:hover { border-color: #00d4ff; background-color: rgba(0, 212, 255, 0.05); }
    
    .active-date-display {
        font-size: 1.1rem; font-weight: bold; color: #00d4ff;
        display: block; margin-top: 0px; margin-bottom: 20px;
    }

    .custom-header {
        padding: 4px 12px; border-radius: 6px; font-weight: bold; margin-bottom: 2px;
        display: flex; justify-content: flex-start; align-items: center; font-size: 0.9rem;
    }
    .header-payday { background-color: rgba(76, 175, 80, 0.12); border: 1px solid rgba(76, 175, 80, 0.4); color: #4CAF50; }
    .header-holiday { background-color: rgba(255, 75, 75, 0.12); border: 1px solid rgba(255, 75, 75, 0.4); color: #ff4b4b; }
    .header-standard { color: #888; border-bottom: 1px solid #333; border-radius: 0; }
    .header-weekend { background-color: rgba(255, 152, 0, 0.1); border: 1px solid rgba(255, 152, 0, 0.3); color: #FF9800; }
    
    .today-node { background-color: #00d4ff; width: 20px; height: 20px; border-radius: 50%; margin-right: 15px; display: inline-block; animation: neon-pulse 2.5s infinite ease-in-out; }
    @keyframes neon-pulse {
        0% { box-shadow: 0 0 5px rgba(0, 212, 255, 0.3); background-color: rgba(0, 212, 255, 0.7); }
        50% { box-shadow: 0 0 25px rgba(0, 212, 255, 1.0); background-color: rgba(0, 212, 255, 1.0); }
        100% { box-shadow: 0 0 5px rgba(0, 212, 255, 0.3); background-color: rgba(0, 212, 255, 0.7); }
    }
    .today-date-text { color: #00d4ff !important; font-weight: 800 !important; }
    .active-week-container { border: 2px solid rgba(0, 212, 255, 0.4); border-radius: 12px; padding: 12px 20px; margin-bottom: 15px; background-color: rgba(0, 212, 255, 0.03); }
    .active-week-label { color: #00d4ff; font-weight: bold; font-size: 1.1rem; display: block; text-align: left; }
    
    #today-marker { scroll-margin-top: 150px; }

    div[data-testid="column"]:nth-of-type(4) button,
    [data-testid="stSidebar"] div[data-testid="column"]:nth-of-type(2) button {
        height: 38px !important; padding: 0px !important; display: flex !important; align-items: center !important; justify-content: center !important;
        font-size: 1.5rem !important; line-height: 0 !important; background: transparent !important; border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    div[data-testid="column"]:nth-of-type(4) button:hover { border-color: #ff4b4b !important; color: #ff4b4b !important; }
    [data-testid="stSidebar"] .stVerticalBlock { gap: 0rem; }
    </style>
    """, unsafe_allow_html=True)
    
# 4. Sidebar
with st.sidebar:
    st.title("📂 ASD Task Tracker")
    st.divider()
    
    today_val = date.today()
    st.markdown(f'<div class="active-date-display">Today: {today_val.strftime("%A, %b %d")}</div>', unsafe_allow_html=True)
    st.markdown('<a href="#today-marker" class="nav-btn-link">📍 Jump to Today</a>', unsafe_allow_html=True)
    
    st.markdown("<div style='margin-bottom: 0px;'></div>", unsafe_allow_html=True)
    st.divider()
    
    with st.expander("✨ Register Project Number", expanded=False):
        with st.form("new_project_form", clear_on_submit=True):
            new_proj_val = st.text_input("Project Number & Name")
            st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
            if st.form_submit_button("Save to Registry"):
                if new_proj_val:
                    ws_projects.append_row([new_proj_val])
                    st.session_state.project_list.append(new_proj_val); st.rerun()
                    
    st.markdown("<div style='margin-bottom: 40px;'></div>", unsafe_allow_html=True)
    
    with st.expander("📋 Project Registry", expanded=True):
        search_reg = st.text_input("🔍 Filter Registry")
        st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
        
        filtered_p = [p for p in st.session_state.project_list if search_reg.lower() in p.lower()]
        for p_code in filtered_p:
            col_c, col_d = st.columns([4, 1], vertical_alignment="center")
            col_c.write(f"**{p_code}**")
            if col_d.button("-", key=f"reg_del_{p_code}", use_container_width=True): 
                row_idx = st.session_state.project_list.index(p_code) + 2
                threading.Thread(target=bg_delete, args=(row_idx,), daemon=True).start()
                st.session_state.project_list.remove(p_code); st.rerun()

# --- MAIN VIEWPORT ---
tab_pay, tab_search = st.tabs(["📅 Pay Cycle Schedule", "🔍 Search Archive"])

def auto_sync_log_async(row_id, date_str, project, task, hours):
    row_data = [date_str, project, task, hours]
    st.session_state.all_logs.iloc[row_id-2] = row_data
    threading.Thread(target=bg_update, args=(row_id, row_data), daemon=True).start()

@st.fragment
def render_day_atomic(d, today):
    d_key = d.strftime("%Y-%m-%d")
    is_today = (d == today)
    is_weekend = (d.weekday() >= 5)
    payday, holiday_name = get_tracker_info(d)
    day_entries = st.session_state.all_logs[st.session_state.all_logs['log_date'] == d_key]
    
    if is_today: st.markdown('<div id="today-marker"></div>', unsafe_allow_html=True)
    node_tag = f'<span class="today-node"></span>' if is_today else ''
    date_display = d.strftime("%A, %b %d")
    if is_today: date_display = f'<span class="today-date-text">{date_display}</span>'

    if is_weekend:
        st.markdown(f'<div class="custom-header header-weekend">{node_tag}{date_display} — Weekend</div>', unsafe_allow_html=True)
    else:
        with st.container(border=True):
            if payday: st.markdown(f'<div class="custom-header header-payday">{node_tag}{date_display} — PAYDAY 💰</div>', unsafe_allow_html=True)
            elif holiday_name: st.markdown(f'<div class="custom-header header-holiday">{node_tag}{date_display} — {holiday_name} 🏖️</div>', unsafe_allow_html=True)
            else: st.markdown(f'<div class="custom-header header-standard">{node_tag}{date_display}</div>', unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom: -18px;'></div>", unsafe_allow_html=True)
            
            for idx, entry in day_entries.iterrows():
                sheet_row = idx + 2
                c_p, c_t, c_h, c_d = st.columns([1.5, 3, 0.7, 0.3], vertical_alignment="center")
                
                # --- UPDATED: Using Smart List in Selectbox ---
                opts = ["Select Project"] + smart_list + ["PTO", "Holiday"]
                
                new_p = c_p.selectbox("PN", options=opts, index=opts.index(entry['project_code']) if entry['project_code'] in opts else 0, key=f"p_{sheet_row}", label_visibility="collapsed")
                new_t = c_t.text_input("Activity", value=entry['task'], key=f"t_{sheet_row}", label_visibility="collapsed")
                raw_h = c_h.text_input("Hrs", value=str(entry['hours']), key=f"h_{sheet_row}", label_visibility="collapsed")
                
                if c_d.button("-", key=f"del_{sheet_row}", use_container_width=True):
                    st.session_state.all_logs = st.session_state.all_logs.drop(idx).reset_index(drop=True)
                    threading.Thread(target=bg_delete, args=(sheet_row,), daemon=True).start(); st.rerun()

                try:
                    new_h = float(raw_h)
                    if new_p != entry['project_code'] or new_t != entry['task'] or new_h != float(entry['hours']):
                        auto_sync_log_async(sheet_row, d_key, new_p, new_t, new_h)
                except ValueError: pass

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            h_val = (9.0 if d.weekday() < 4 else 4.0) if day_entries.empty else 0.0
            if col1.button("+ Project", key=f"add_p_{d_key}", use_container_width=True):
                new_row = [d_key, "Select Project", '', h_val]
                st.session_state.all_logs = pd.concat([st.session_state.all_logs, pd.DataFrame([new_row], columns=st.session_state.all_logs.columns)], ignore_index=True)
                threading.Thread(target=bg_append, args=(new_row,), daemon=True).start(); st.rerun()
            if col2.button("+ PTO", key=f"add_pto_{d_key}", use_container_width=True):
                new_row = [d_key, 'PTO', 'Personal Time Off', h_val]
                st.session_state.all_logs = pd.concat([st.session_state.all_logs, pd.DataFrame([new_row], columns=st.session_state.all_logs.columns)], ignore_index=True)
                threading.Thread(target=bg_append, args=(new_row,), daemon=True).start(); st.rerun()
            if col3.button("+ Holiday", key=f"add_h_{d_key}", use_container_width=True):
                new_row = [d_key, 'Holiday', (holiday_name if holiday_name else "Office Closed"), h_val]
                st.session_state.all_logs = pd.concat([st.session_state.all_logs, pd.DataFrame([new_row], columns=st.session_state.all_logs.columns)], ignore_index=True)
                threading.Thread(target=bg_append, args=(new_row,), daemon=True).start(); st.rerun()

with tab_pay:
    today = date.today()
    if today.day <= 15:
        cycle_start = today.replace(day=1); cycle_end = today.replace(day=15)
    else:
        cycle_start = today.replace(day=16); cycle_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    
    view_start = cycle_start - timedelta(days=7); view_end = cycle_end + timedelta(days=7)

    with st.expander(f"⏮️ Previous Cycle Buffer ({view_start.strftime('%b %d')} - {(cycle_start - timedelta(days=1)).strftime('%b %d')})", expanded=False):
        for i in range(7): render_day_atomic(view_start + timedelta(days=i), today)

    st.markdown(f'<div class="active-week-container"><span class="active-week-label">📂 Official Pay Period: {cycle_start.strftime("%b %d")} - {cycle_end.strftime("%b %d")}</span></div>', unsafe_allow_html=True)
    num_days = (cycle_end - cycle_start).days + 1
    for i in range(num_days): render_day_atomic(cycle_start + timedelta(days=i), today)

    with st.expander(f"⏭️ Next Cycle Buffer ({(cycle_end + timedelta(days=1)).strftime('%b %d')} - {view_end.strftime('%b %d')})", expanded=False):
        for i in range(7): render_day_atomic(cycle_end + timedelta(days=1) + timedelta(days=i), today)

with tab_search:
    st.write("### 🗄️ Project Task Archive")
    all_logs = st.session_state.all_logs
    col_a, col_b = st.columns([2, 2])
    with col_a: keyword = st.text_input("🔍 Search Keyword")
    with col_b: date_range = st.date_input("📅 Date Range", value=(today_val - timedelta(days=365), today_val))
    if len(date_range) == 2 and not all_logs.empty:
        s_date, e_date = date_range
        mask = (all_logs['log_date'] >= s_date.strftime("%Y-%m-%d")) & \
               (all_logs['log_date'] <= e_date.strftime("%Y-%m-%d")) & \
               (all_logs['task'].astype(str).str.contains(keyword, case=False) | all_logs['project_code'].astype(str).str.contains(keyword, case=False))
        raw_res = all_logs[mask]
        if not raw_res.empty:
            arch_df = raw_res.groupby('log_date').agg({'project_code': lambda x: '<br>'.join(x.fillna('').astype(str)), 'task': lambda x: '<br>'.join(x.fillna('').astype(str)), 'hours': 'sum'}).reset_index().sort_values('log_date', ascending=False)
            html_arch = "<table class='recap-table'><tr><th>Date</th><th>Project Number</th><th>Description</th><th>Total Hours</th></tr>"
            for _, row in arch_df.iterrows():
                html_arch += f"<tr><td>{pd.to_datetime(row['log_date']).strftime('%b %d, %Y')}</td><td class='project-stack'>{row['project_code']}</td><td>{row['task']}</td><td>{row['hours']:g}</td></tr>"
            st.markdown(html_arch + "</table>", unsafe_allow_html=True)