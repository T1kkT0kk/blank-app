import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import gspread
from google.oauth2.service_account import Credentials
import json
import streamlit.components.v1 as components # New import for stable scrolling

# 1. Page Configuration
st.set_page_config(page_title="ASD|SKY Task Vault", layout="wide")

# 2. Cloud Engine
def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_info = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

client = get_gsheet_client()

# ASD|SKY PROJECT TRACKER: Ensure ID is accurate
SHEET_ID = "1d94q4Gwb961oDWc9UasPYWc-yXDLi3vX-epx_uHIVY0" 

sh = client.open_by_key(SHEET_ID)
ws_projects = sh.worksheet("projects")
ws_logs = sh.worksheet("logs")

@st.cache_data(ttl=60)
def fetch_cloud_data():
    p_list = ws_projects.col_values(1)[1:]
    logs_df = pd.DataFrame(ws_logs.get_all_records())
    return p_list, logs_df

# 3. Tracker Logic (2026 ASD|SKY Calendar)
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

# --- CSS: Refined Architectural Layout ---
st.markdown("""
    <style>
    .block-container { padding-top: 5rem; }
    .custom-header {
        padding: 4px 12px; border-radius: 6px; font-weight: bold; margin-bottom: 2px;
        display: flex; justify-content: flex-start; align-items: center; font-size: 0.9rem;
    }
    .header-payday { background-color: rgba(76, 175, 80, 0.12); border: 1px solid rgba(76, 175, 80, 0.4); color: #4CAF50; }
    .header-holiday { background-color: rgba(255, 75, 75, 0.12); border: 1px solid rgba(255, 75, 75, 0.4); color: #ff4b4b; }
    .header-standard { color: #888; border-bottom: 1px solid #333; border-radius: 0; }
    .header-weekend { background-color: rgba(255, 152, 0, 0.1); border: 1px solid rgba(255, 152, 0, 0.3); color: #FF9800; }
    
    .weekend-window { background-color: rgba(255, 152, 0, 0.05); border-radius: 8px; padding: 10px; margin-bottom: 10px; border: 1px dashed rgba(255, 152, 0, 0.2); }
    
    .today-node {
        background-color: #00d4ff; width: 20px; height: 20px; border-radius: 50%;
        margin-right: 15px; display: inline-block; animation: neon-pulse 2.5s infinite ease-in-out;
    }
    @keyframes neon-pulse {
        0% { box-shadow: 0 0 5px rgba(0, 212, 255, 0.3); background-color: rgba(0, 212, 255, 0.7); }
        50% { box-shadow: 0 0 25px rgba(0, 212, 255, 1.0); background-color: rgba(0, 212, 255, 1.0); }
        100% { box-shadow: 0 0 5px rgba(0, 212, 255, 0.3); background-color: rgba(0, 212, 255, 0.7); }
    }
    .today-date-text { color: #00d4ff !important; font-weight: 800 !important; }
    .project-stack { color: #00d4ff; font-weight: bold; }
    [data-testid="stSidebar"] .stVerticalBlock { gap: 0rem; }
    </style>
    """, unsafe_allow_html=True)

# 4. Sidebar: Navigation & Project Registry
with st.sidebar:
    st.title("📂 ASD|SKY Vault")
    
    # IMPROVED: Parent-level scroll script for stable "Jump to Today"
    if st.button("📍 Jump to Today", use_container_width=True):
        components.html(
            """
            <script>
                var element = window.parent.document.getElementById('today-marker');
                if (element) {
                    element.scrollIntoView({behavior: 'smooth'});
                }
            </script>
            """,
            height=0,
        )
    
    st.divider()
    
    with st.expander("✨ New Project Number", expanded=False):
        with st.form("new_project_form", clear_on_submit=True):
            new_proj_val = st.text_input("Project Number & Name")
            if st.form_submit_button("Save to Registry"):
                if new_proj_val:
                    ws_projects.append_row([new_proj_val])
                    st.cache_data.clear(); st.rerun()
    
    with st.expander("📋 Project Registry", expanded=True):
        search_reg = st.text_input("🔍 Filter")
        project_list, all_logs = fetch_cloud_data()
        filtered_p = [p for p in project_list if search_reg.lower() in p.lower()]
        for p_code in filtered_p:
            col_c, col_d = st.columns([4, 1])
            col_c.write(f"**{p_code}**")
            if col_d.button("🗑️", key=f"reg_del_{p_code}"):
                row_idx = project_list.index(p_code) + 2 
                ws_projects.delete_rows(row_idx)
                st.cache_data.clear(); st.rerun()

# --- TAB 1: ROLLING MONTH SCHEDULE ---
tab_live, tab_search = st.tabs(["📅 Rolling Month (Live)", "🔍 Search Archive"])

def auto_sync_log(row_id, date_str, project, task, hours):
    ws_logs.update([[date_str, project, task, hours]], f"A{row_id}")
    st.cache_data.clear()

@st.fragment
def entry_row(sheet_row, entry, d_key, project_list):
    c_p, c_t, c_h = st.columns([1.5, 3, 1.0])
    opts = project_list + ["PTO", "Holiday"]
    new_p = c_p.selectbox("PN", options=opts, index=opts.index(entry['project_code']) if entry['project_code'] in opts else 0, key=f"p_{sheet_row}", label_visibility="collapsed")
    new_t = c_t.text_input("Activity", value=entry['task'], key=f"t_{sheet_row}", label_visibility="collapsed")
    new_h = c_h.number_input("Hrs", value=float(entry['hours']), step=0.5, key=f"h_{sheet_row}", label_visibility="collapsed")
    if new_p != entry['project_code'] or new_t != entry['task'] or new_h != float(entry['hours']):
        auto_sync_log(sheet_row, d_key, new_p, new_t, new_h)

with tab_live:
    today = date.today()
    month_start = today - timedelta(days=15)
    week_anchor = month_start - timedelta(days=month_start.weekday())
    
    for week_idx in range(5):
        w_start = week_anchor + timedelta(days=week_idx * 7)
        w_end = w_start + timedelta(days=6)
        
        is_current_week = (w_start <= today <= w_end)
        folder_label = f"Week of {w_start.strftime('%b %d')} - {w_end.strftime('%b %d')}"
        
        with st.expander(folder_label, expanded=is_current_week):
            for i in range(7):
                d = w_start + timedelta(days=i)
                if not (month_start <= d <= (month_start + timedelta(days=30))):
                    continue
                
                d_key = d.strftime("%Y-%m-%d")
                is_today = (d == today)
                is_weekend = (d.weekday() >= 5)
                payday, holiday_name = get_tracker_info(d)
                day_entries = all_logs[all_logs['log_date'] == d_key] if not all_logs.empty else pd.DataFrame()
                
                # JUMP ANCHOR: Now uses a standard HTML ID
                if is_today: st.markdown('<div id="today-marker"></div>', unsafe_allow_html=True)

                # DYNAMIC COLOR LOGIC: Ensures today is highlighted even on weekends
                node_tag = f'<span class="today-node"></span>' if is_today else ''
                date_display = d.strftime("%A, %b %d")
                if is_today: date_display = f'<span class="today-date-text">{date_display}</span>'

                if is_weekend:
                    st.markdown(f'<div class="custom-header header-weekend">{node_tag}{date_display} — Weekend</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="weekend-window"><b>PN:</b> Weekend &nbsp; | &nbsp; <b>Activity:</b> Weekend</div>', unsafe_allow_html=True)
                else:
                    with st.container(border=True):
                        if payday: st.markdown(f'<div class="custom-header header-payday">{node_tag}{date_display} — PAYDAY 💰</div>', unsafe_allow_html=True)
                        elif holiday_name: st.markdown(f'<div class="custom-header header-holiday">{node_tag}{date_display} — {holiday_name} 🏖️</div>', unsafe_allow_html=True)
                        else: st.markdown(f'<div class="custom-header header-standard">{node_tag}{date_display}</div>', unsafe_allow_html=True)

                        st.markdown("<div style='margin-bottom: -18px;'></div>", unsafe_allow_html=True)
                        for idx, entry in day_entries.iterrows():
                            entry_row(idx + 2, entry, d_key, project_list)

                        with st.popover(f"➕ Add Entry"):
                            col1, col2, col3 = st.columns(3)
                            h_val = 8.0 if day_entries.empty else 0.0
                            if col1.button("Project", key=f"add_p_{d_key}", use_container_width=True):
                                ws_logs.append_row([d_key, project_list[0], '', h_val])
                                st.cache_data.clear(); st.rerun()
                            if col2.button("PTO", key=f"add_pto_{d_key}", use_container_width=True):
                                ws_logs.append_row([d_key, 'PTO', 'Personal Time Off', h_val])
                                st.cache_data.clear(); st.rerun()
                            if col3.button("Holiday", key=f"add_h_{d_key}", use_container_width=True):
                                h_text = holiday_name if holiday_name else "Office Closed"
                                ws_logs.append_row([d_key, 'Holiday', h_text, h_val])
                                st.cache_data.clear(); st.rerun()

# --- SEARCH TAB remains unchanged ---
with tab_search:
    st.write("### 🗄️ Project Task Archive")
    col_a, col_b = st.columns([2, 2])
    with col_a: keyword = st.text_input("🔍 Search Keyword")
    with col_b: date_range = st.date_input("📅 Date Range", value=(today - timedelta(days=365), today))
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