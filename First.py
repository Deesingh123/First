# First.py → SINGLE PROCESS CATEGORY + BOLD COLORS + DUPLICATES REMOVED
import streamlit as st
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Process Readiness Tracker", layout="wide")

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT3so_mMFyNEBJGBZuEYzTxaWDMSJg0nGznK4ln9r4i2OTRzL_AxATf8sSBgwEdfA/pub?gid=1714107674&single=true&output=csv"
REFRESH = 30

@st.cache_data(ttl=REFRESH)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        df = df.dropna(how='all').reset_index(drop=True)
        df = df.fillna("—")
        
        # REMOVE DUPLICATE COLUMNS (keep first "Process Category")
        df = df.loc[:, ~df.columns.duplicated()]
        
        return df
    except Exception as e:
        st.error(f"Data load error: {e}")
        return pd.DataFrame()

placeholder = st.empty()
while True:
    df = load_data()

    with placeholder.container():
        if df.empty:
            st.warning("No data loaded.")
            time.sleep(REFRESH)
            st.rerun()

        st.markdown(f"""
        <div style="text-align:center; padding:30px; background:#1d4ed8; color:white; border-radius:15px; margin-bottom:30px;">
            <h1 style="margin:0;">Process Readiness Tracker</h1>
            <p style="margin:5px; font-size:1.3rem;">
                Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • Auto-refresh {REFRESH}s
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Column detection (focus on key ones)
        category_col = "Process Category"  # After drop duplicates, this is the single one
        if category_col not in df.columns:
            # Fallback if name varies
            category_col = next((c for c in df.columns if "process category" in c.lower()), df.columns[0])

        sub_col = next((c for c in df.columns if "sub" in c.lower()), None)
        owner_col = next((c for c in df.columns if "owner" in c.lower()), None)
        target_col = next((c for c in df.columns if "target" in c.lower()), None)
        status_col = next((c for c in df.columns if "status" in c.lower()), None)
        remark_col = next((c for c in df.columns if "remark" in c.lower()), None)

        # Date parsing
        if target_col:
            df[target_col] = pd.to_datetime(df[target_col], errors='coerce', dayfirst=True)
        today = pd.Timestamp.today().normalize()

        # Final Status
        def get_status(row):
            closed = status_col and str(row[status_col]).lower().strip() in ["closed", "close", "done"]
            overdue = target_col and pd.notna(row[target_col]) and row[target_col] < today
            if closed and not overdue: return "Closed On Time"
            if closed and overdue: return "Closed (Late)"
            if overdue: return "NOT CLOSED – DELAYED!"
            return "Open"
        df["Final Status"] = df.apply(get_status, axis=1)

        # Filters
        col1, col2, col3 = st.columns(3)
        filtered = df.copy()

        with col1:
            if owner_col:
                owners = ["All"] + sorted(filtered[owner_col].dropna().unique().tolist())
                chosen_owner = st.selectbox("Owner", owners, key="owner_filter")
                if chosen_owner != "All":
                    filtered = filtered[filtered[owner_col] == chosen_owner]

        with col2:
            if category_col:
                cats = ["All"] + sorted(filtered[category_col].dropna().unique().tolist())
                chosen_cat = st.selectbox("Process Category", cats, key="cat_filter")
                if chosen_cat != "All":
                    filtered = filtered[filtered[category_col] == chosen_cat]

        with col3:
            view = st.selectbox("Show", ["All Items", "Only Delayed", "Only Open", "Only Closed"], key="view_filter")
            if view == "Only Delayed":
                filtered = filtered[filtered["Final Status"].str.contains("DELAYED")]
            elif view == "Only Open":
                filtered = filtered[filtered["Final Status"] == "Open"]
            elif view == "Only Closed":
                filtered = filtered[~filtered["Final Status"].str.contains("Open|DELAYED")]

        # Alert
        delayed = len(filtered[filtered["Final Status"].str.contains("DELAYED")])
        if delayed:
            st.error(f"URGENT: {delayed} items DELAYED & NOT CLOSED!")
        else:
            st.success("All items are On Track or Closed")

        # Table columns
        cols_to_show = [category_col, sub_col, owner_col, target_col, status_col, remark_col, "Final Status"]
        valid_cols = [c for c in cols_to_show if c and c in filtered.columns]
        table_df = filtered[valid_cols].reset_index(drop=True)

        # HTML Table with bold colors + hide category repeats
        html = [
            '<style>',
            'table{width:100%;border-collapse:collapse;font-family:Arial}',
            'th,td{padding:12px;border:1px solid #333;color:black !important;font-size:15px;text-align:left}',
            'th{background:#1e40af;color:white !important}',
            '</style><table>'
        ]
        html.append('<tr>' + ''.join(f'<th>{c}</th>' for c in table_df.columns) + '</tr>')

        prev_cat = None
        for _, row in table_df.iterrows():
            status = row["Final Status"]
            if "DELAYED" in status:
                bg = "#ef4444"  # Bold red
                text_color = "white;font-weight:bold"
            elif "On Time" in status:
                bg = "#22c55e"  # Bold green
                text_color = "white"
            elif status == "Open":
                bg = "#fbbf24"  # Bold yellow
                text_color = "black"
            else:
                bg = "#e5e7eb"  # Light gray
                text_color = "black"

            cells = []
            for col in table_df.columns:
                val = str(row[col])
                display_val = val
                if col == category_col:
                    if val == prev_cat:
                        display_val = ""  # Hide repeat
                    else:
                        prev_cat = val

                cells.append(f'<td style="background:{bg};color:{text_color}">{display_val}</td>')
            html.append('<tr>' + ''.join(cells) + '</tr>')

        html.append('</table>')
        st.markdown(''.join(html), unsafe_allow_html=True)

        st.sidebar.success("SINGLE COLUMN + BOLD COLORS")
        st.sidebar.download_button("Download View", table_df.to_csv(index=False).encode(), "Readiness.csv", "text/csv")

    time.sleep(REFRESH)
    st.rerun()