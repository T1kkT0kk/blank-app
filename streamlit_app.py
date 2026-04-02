import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import gspread
from google.oauth2.service_account import Credentials
import json

# 1. Page Configuration
st.set_page_config(page_title="ASD|SKY Task Vault", layout="wide")

# 2. Cloud Engine: Google Sheets Connection
def get_gsheet_client():
    """Connects to Google Sheets using the TOML Secrets"""
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_info = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

client = get_gsheet_client()

# PASTE YOUR UNIQUE SPREADSHEET ID HERE [cite: 2026-02-28]
SHEET_ID = "PASTE_YOUR_LONG_ID_HERE" 

sh = client.open_by_key(SHEET_ID)
ws_projects = sh.worksheet("projects")
ws_logs = sh.worksheet("logs")

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

# --- CSS: Refined Architectural Layout & Blue Datum ---
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
    
    .today-node {
        background-color: #00d4ff; width: 20px; height: 20px; border-radius: 50%;
        margin-right: 15px; display: inline-block; animation: neon-pulse 2.5s infinite ease-in-out;
    }
    @keyframes neon-pulse {
        0% { box-shadow: 0 0 5px rgba(0, 212, 255, 0.3); background-color: rgba(0, 212, 255, 0.7); }
        50% { box-shadow: 0 0 25px rgba(0, 212, 255, 1.0); background-color: rgba(0, 212, 255, 1.0); }
        100% { box-shadow: 0 0 5px rgba(0, 212, 255, 0.3); background-color: rgba(0, 212, 255, 0.7); }
    }
    .today-date-text { color: #00d4ff; font-weight: 800; }
    .recap-table { width: 100%; border-collapse: collapse; color: white; margin-top: 20px; }
    .recap-table td { padding: 18px 10px; border-bottom: 1px solid #222; vertical-align: top; line-height: 1.7; }
    .project-stack { color: #00d4ff; font-weight: bold; }
    [data-testid="stSidebar"] .stVerticalBlock { gap: 0rem; }
    </style>
    """, unsafe_allow_html=True)

# 4. Sidebar: Project Registry (Cloud Sync)
with st.sidebar:
    st.title("📂 Register Projects")
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    
    with st.expander("✨ New Project Number", expanded=False):
        with st.form("new_project_form", clear_on_submit=True):
            new_proj_val = st.text_input("Project Number & Name")
            st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
            if st.form_submit_button("Save to Registry"):
                if new_proj_val:
                    ws_projects.append_row([new_proj_val])
                    st.rerun()
    
    st.divider()

    with st.expander("📋 Project Number Registry", expanded=True):
        search_reg = st.text_input("🔍 Filter Registry")
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        
        p_data = ws_projects.col_values(1)[1:] 
        filtered_p = [p for p in p_data if search_reg.lower() in p.lower()]
        
        for p_code in filtered_p:
            st.markdown('<div style="margin-bottom: 12px;">', unsafe_allow_html=True)
            col_c, col_d = st.columns([4, 1])
            col_c.write(f"**{p_code}**")
            if col_d.button("🗑️", key=f"reg_del_{p_code}"):
                row_idx = p_data.index(p_code) + 2 
                ws_projects.delete_rows(row_idx)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 1: 5-DAY SCHEDULE (LIVE) ---
tab_live, tab_recap, tab_search = st.tabs(["📋 5-Day Schedule (Live)", "📅 10-Day Recap", "🔍 Search Archive"])

all_logs = pd.DataFrame(ws_logs.get_all_records())

with tab_live:
    today = date.today()
    monday_this_week = today - timedelta(days=today.weekday())
    st.write(f"### Current Week: {monday_this_week.strftime('%b %d')} - {(monday_this_week + timedelta(days=4)).strftime('%b %d')}")
    
    project_list = ws_projects.col_values(1)[1:]
    
    for i in range(5):
        d = monday_this_week + timedelta(days=i)
        d_key = d.strftime("%Y-%m-%d")
        is_today = (d == today)
        payday, holiday_name = get_tracker_info(d)
        
        day_entries = all_logs[all_logs['log_date'] == d_key] if not all_logs.empty else pd.DataFrame()
        
        with st.container(border=True):
            node_tag = f'<span class="today-node"></span>' if is_today else ''
            date_display = d.strftime("%A, %b %d")
            if is_today: date_display = f'<span class="today-date-text">{date_display}</span>'
            
            if payday:
                st.markdown(f'<div class="custom-header header-payday">{node_tag}{date_display} — PAYDAY 💰</div>', unsafe_allow_html=True)
            elif holiday_name:
                st.markdown(f'<div class="custom-header header-holiday">{node_tag}{date_display} — {holiday_name} 🏖️</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="custom-header header-standard">{node_tag}{date_display}</div>', unsafe_allow_html=True)

            st.markdown("<div style='margin-bottom: -18px;'></div>", unsafe_allow_html=True)

            for idx, entry in day_entries.iterrows():
                sheet_row = idx + 2 
                c_p, c_t, c_h = st.columns([1.5, 3, 1.0])
                with c_p:
                    opts = project_list + ["PTO", "Holiday"]
                    new_p = st.selectbox("PN", options=opts, index=opts.index(entry['project_code']) if entry['project_code'] in opts else 0, key=f"p_{sheet_row}", label_visibility="collapsed")
                with c_t:
                    new_t = st.text_input("Activity", value=entry['task'], key=f"t_{sheet_row}", label_visibility="collapsed")
                with c_h:
                    new_h = st.number_input("Hrs", value=float(entry['hours']), step=0.5, key=f"h_{sheet_row}", label_visibility="collapsed")

                # FIXED: Swapped 'update_row' for the standard '.update()'
                if new_p != entry['project_code'] or new_t != entry['task'] or new_h != float(entry['hours']):
                    ws_logs.update([[d_key, new_p, new_t, new_h]], f"A{sheet_row}")
                    st.rerun()

            with st.popover(f"➕ Add Entry to {d.strftime('%a')}"):
                if not project_list:
                    st.warning("⚠️ Register a PN first!")
                else:
                    col1, col2, col3 = st.columns(3)
                    h_val = (9.0 if i < 4 else 4.0) if day_entries.empty else 0.0
                    if col1.button("Project", key=f"add_p_{d_key}", use_container_width=True):
                        ws_logs.append_row([d_key, project_list[0], '', h_val])
                        st.rerun()
                    if col2.button("PTO", key=f"add_pto_{d_key}", use_container_width=True):
                        ws_logs.append_row([d_key, 'PTO', 'Personal Time Off', h_val])
                        st.rerun()
                    if col3.button("Holiday", key=f"add_h_{d_key}", use_container_width=True):
                        h_text = holiday_name if holiday_name else "Office Closed"
                        ws_logs.append_row([d_key, 'Holiday', h_text, h_val])
                        st.rerun()
                if not day_entries.empty:
                    st.divider()
                    if st.button(f"🗑️ Clear all for {d.strftime('%a')}", key=f"clear_{d_key}", type="primary", use_container_width=True):
                        rows_to_del = day_entries.index.tolist()
                        for r in reversed(rows_to_del):
                            ws_logs.delete_rows(r + 2)
                        st.rerun()

# --- TABS 2 & 3: RECAP & ARCHIVE ---
with tab_recap:
    st.write("### 10-Day Recap")
    monday_last_week = monday_this_week - timedelta(days=7)
    if not all_logs.empty:
        recent_logs = all_logs[all_logs['log_date'] >= monday_last_week.strftime("%Y-%m-%d")]
        if not recent_logs.empty:
            recap_df = recent_logs.groupby('log_date').agg({'project_code': lambda x: '<br>'.join(x.fillna('').astype(str)), 'task': lambda x: '<br>'.join(x.fillna('').astype(str)), 'hours': 'sum'}).reset_index().sort_values('log_date', ascending=False)
            html_table = "<table class='recap-table'><tr><th>Date</th><th>Project Number</th><th>Description</th><th>Total Hours</th></tr>"
            for _, row in recap_df.iterrows():
                formatted_date = pd.to_datetime(row['log_date']).strftime('%a, %b %d')
                html_table += f"<tr><td>{formatted_date}</td><td class='project-stack'>{row['project_code']}</td><td>{row['task']}</td><td>{row['hours']:g}</td></tr>"
            st.markdown(html_table + "</table>", unsafe_allow_html=True)

with tab_search:
    st.write("### 🗄️ Project Task Archive")
    col_a, col_b = st.columns([2, 2])
    with col_a: keyword = st.text_input("🔍 Search Keyword")
    with col_b: date_range = st.date_input("📅 Date Range", value=(today - timedelta(days=365), today))
    if len(date_range) == 2 and not all_logs.empty:
        start_date, end_date = date_range
        mask = (all_logs['log_date'] >= start_date.strftime("%Y-%m-%d")) & \
               (all_logs['log_date'] <= end_date.strftime("%Y-%m-%d")) & \
               (all_logs['task'].astype(str).str.contains(keyword, case=False) | all_logs['project_code'].astype(str).str.contains(keyword, case=False))
        raw_res = all_logs[mask]
        if not raw_res.empty:
            arch_df = raw_res.groupby('log_date').agg({'project_code': lambda x: '<br>'.join(x.fillna('').astype(str)), 'task': lambda x: '<br>'.join(x.fillna('').astype(str)), 'hours': 'sum'}).reset_index().sort_values('log_date', ascending=False)
            html_arch = "<table class='recap-table'><tr><th>Date</th><th>Project Number</th><th>Description</th><th>Total Hours</th></tr>"
            for _, row in arch_df.iterrows():
                html_arch += f"<tr><td>{pd.to_datetime(row['log_date']).strftime('%b %d, %Y')}</td><td class='project-stack'>{row['project_code']}</td><td>{row['task']}</td><td>{row['hours']:g}</td></tr>"
            st.markdown(html_arch + "</table>", unsafe_allow_html=True)