import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Milestone Tracker", layout="wide")

# REPLACE WITH YOUR NEW CSV URL
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSERW8jK8wY8-01wqcDBtNY_g8Km2g3QyxNjT1BWIg2II95wvouLQ1wsgWckkY56Q/pub?gid=1960938483&single=true&output=csv"

REFRESH = 60  # seconds

@st.cache_data(ttl=REFRESH)
def load_data():
    try:
        df = pd.read_csv(CSV_URL, header=None)  # No header in your sheet
        df = df.iloc[1:]  # Skip any title row
        df = df[[0,1,2,3]]  # Only columns A B C D
        df.columns = ["Task", "Milestone_Type", "Plan_Date", "Actual_Date"]
        df = df.fillna("—")
        df = df.reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Load once — Streamlit will re-run the script on changes/cached TTL
df = load_data()

if df.empty:
    st.title("📋 Milestone Tracker Dashboard")
    st.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • Auto-refresh {REFRESH}s")
    st.warning("No data loaded. Check CSV URL.")
    st.stop()

# FIXED DATE PARSING (handles "1-Nov", "20-Jan" correctly)
current_year = datetime.now().year

def parse_date(val):
    if pd.isna(val) or val == "—" or str(val).strip() == "":
        return pd.NaT
    s = str(val).strip()
    # Add current year if only dd-MMM format
    try:
        if '-' in s and len(s.split('-')) == 2:
            s = s + f"-{current_year}"
        return pd.to_datetime(s, dayfirst=True, errors='coerce')
    except Exception:
        return pd.to_datetime(s, dayfirst=True, errors='coerce')

df['Plan_Date'] = df['Plan_Date'].apply(parse_date)
df['Actual_Date'] = df['Actual_Date'].apply(parse_date)
today = pd.Timestamp.today().normalize()

# Status logic
def get_status(row):
    actual = row['Actual_Date']
    plan = row['Plan_Date']
    if pd.notna(actual):
        if pd.notna(plan) and actual <= plan:
            return "Completed On Time"
        else:
            return "Delayed"
    elif pd.notna(plan) and plan < today:
        return "Overdue (No Actual)"
    else:
        return "Pending"

df['Status'] = df.apply(get_status, axis=1)

# UI
st.title("📋 Milestone Tracker Dashboard")
st.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • Auto-refresh {REFRESH}s")

# Milestone Type Filter
milestone_options = ["All", "WBS", "Sub Milestone"]
chosen_milestone = st.selectbox("Filter by Milestone Type", milestone_options, key="milestone_filter")

filtered = df.copy()
if chosen_milestone != "All":
    filtered = filtered[filtered["Milestone_Type"] == chosen_milestone]

# Urgent Alert
delayed_count = len(filtered[filtered['Status'].str.contains("Delayed|Overdue")])
if delayed_count > 0:
    st.error(f"URGENT: {delayed_count} milestones DELAYED or OVERDUE!")
else:
    st.success("All milestones are on track")

# Prepare table for display
table_df = filtered[["Task", "Milestone_Type", "Plan_Date", "Actual_Date", "Status"]].copy()
table_df['Plan_Date'] = table_df['Plan_Date'].dt.strftime('%d-%b').replace("NaT", "—")
table_df['Actual_Date'] = table_df['Actual_Date'].dt.strftime('%d-%b').replace("NaT", "—")

# Hide repeating Task names (clean grouped look)
prev_task = None
for i, row in table_df.iterrows():
    if row['Task'] == prev_task:
        table_df.at[i, 'Task'] = ""
    else:
        prev_task = row['Task']

# HTML Table with bold colors
html = [
    '<style>',
    'table{width:100%;border-collapse:collapse;font-family:Arial}',
    'th,td{padding:12px;border:1px solid #333;color:black !important;font-size:15px;text-align:left}',
    'th{background:#1e40af;color:white !important}',
    '</style><table>'
]
html.append('<tr>' + ''.join(f'<th>{col}</th>' for col in table_df.columns) + '</tr>')

for _, row in table_df.iterrows():
    status = row['Status']
    if "Delayed" in status or "Overdue" in status:
        bg = "#ef4444"; text = "white;font-weight:bold"
    elif "On Time" in status or "Completed" in status:
        bg = "#22c55e"; text = "white"
    elif "Pending" in status:
        bg = "#fbbf24"; text = "black"
    else:
        bg = "#e5e7eb"; text = "black"

    cells = ''.join(f'<td style="background:{bg};color:{text}">{val}</td>' for val in row)
    html.append(f'<tr>{cells}</tr>')

html.append('</table>')
st.markdown(''.join(html), unsafe_allow_html=True)

# Download button
st.sidebar.success("MILESTONE DASHBOARD • NO IMAGE")
st.sidebar.download_button(
    "Download Current View",
    table_df.to_csv(index=False).encode(),
    "Milestones.csv",
    "text/csv"
)