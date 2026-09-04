import streamlit as st
import pandas as pd
import html as html_lib

st.set_page_config(page_title="CSV Merge Ledger", page_icon="🗂️", layout="wide")

# ---------- Styling (matches the ledger look of the browser version) ----------
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Lora:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  html, body, [class*="css"]  { font-family: 'IBM Plex Mono', ui-monospace, monospace; }
  h1, h2, h3 { font-family: 'Lora', Georgia, serif !important; }
  .stApp { background-color: #E9EEEC; }
  section[data-testid="stSidebar"] { background-color: #E9EEEC; }
  .block-container { padding-top: 2rem; max-width: 900px; }
  .ledger-table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
  .ledger-table th { background:#16241F; color:#E9EEEC; padding:6px 8px; text-align:left;
                      border-right:1px solid #C4CDC7; position: sticky; top: 0; }
  .ledger-table td { padding:6px 8px; border-bottom:1px solid #C4CDC7; border-right:1px solid #C4CDC7;
                      white-space:nowrap; }
  .ledger-table tr:nth-child(even) td { background: rgba(0,0,0,.03); }
  .filled-cell { background:#F5E8D2 !important; box-shadow: inset 3px 0 0 #A66A00; }
  .table-scroll { overflow:auto; max-height:440px; border:1px solid #9AA69E; margin-top:8px; }
  .legend-note { color:#4B5850; font-size:12.5px; margin-top:6px; }
</style>
""", unsafe_allow_html=True)

st.title("CSV Merge Ledger")
st.caption(
    "Load two team sheets, match them by team and date, and fill blank cells in one file "
    "using values from the other — never overwriting a cell that already has data."
)

# ---------- Session state ----------
if "mappings" not in st.session_state:
    st.session_state.mappings = [{"colA": "", "colB": ""}]
if "result_df" not in st.session_state:
    st.session_state.result_df = None
if "filled_cells" not in st.session_state:
    st.session_state.filled_cells = set()
if "stats" not in st.session_state:
    st.session_state.stats = None
if "last_files" not in st.session_state:
    st.session_state.last_files = (None, None)


def normalize(v):
    if v is None:
        return ""
    return str(v).strip().lower()


def is_empty(v):
    return v is None or str(v).strip() == ""


def guess_column(columns, keywords):
    lower = [c.lower() for c in columns]
    for kw in keywords:
        for i, c in enumerate(lower):
            if kw in c:
                return columns[i]
    return columns[0] if columns else None


def safe_index(options, value):
    return options.index(value) if value in options else 0


# ---------- Step 1: upload ----------
st.header("1. Load your files")
col1, col2 = st.columns(2)
with col1:
    file_a = st.file_uploader("File A (target — gets updated)", type="csv", key="file_a")
with col2:
    file_b = st.file_uploader("File B (source — copied from)", type="csv", key="file_b")

# Reset merge results if a new file is uploaded
current_files = (
    file_a.name if file_a else None,
    file_b.name if file_b else None,
)
if current_files != st.session_state.last_files:
    st.session_state.result_df = None
    st.session_state.filled_cells = set()
    st.session_state.stats = None
    st.session_state.last_files = current_files

if file_a and file_b:
    df_a = pd.read_csv(file_a, dtype=str, keep_default_na=False)
    df_b = pd.read_csv(file_b, dtype=str, keep_default_na=False)
    cols_a = list(df_a.columns)
    cols_b = list(df_b.columns)

    st.success(
        f"File A: {len(df_a)} rows, {len(cols_a)} columns  ·  "
        f"File B: {len(df_b)} rows, {len(cols_b)} columns"
    )

    # ---------- Step 2: match keys ----------
    st.header("2. Set the match keys")
    st.caption("Rows are matched when team and date agree in both files.")
    c1, c2 = st.columns(2)
    with c1:
        team_col_a = st.selectbox(
            "File A — team column", cols_a,
            index=safe_index(cols_a, guess_column(cols_a, ["team", "club", "squad"])),
        )
        date_col_a = st.selectbox(
            "File A — date column", cols_a,
            index=safe_index(cols_a, guess_column(cols_a, ["date", "day"])),
        )
    with c2:
        team_col_b = st.selectbox(
            "File B — team column", cols_b,
            index=safe_index(cols_b, guess_column(cols_b, ["team", "club", "squad"])),
        )
        date_col_b = st.selectbox(
            "File B — date column", cols_b,
            index=safe_index(cols_b, guess_column(cols_b, ["date", "day"])),
        )

    teams = sorted({t.strip() for t in df_a[team_col_a].astype(str) if t.strip()})
    team_filter = st.selectbox("Filter to one team (optional)", ["All teams"] + teams)

    # ---------- Step 3: column mapping ----------
    st.header("3. Match up the columns to copy")
    st.caption(
        "For each pair, an empty File A cell gets filled from the matching File B column — "
        "only on rows where team and date match, and only if File A's cell is currently empty."
    )

    remove_idx = None
    for i, m in enumerate(st.session_state.mappings):
        mc1, mc2, mc3 = st.columns([4, 4, 1])
        with mc1:
            m["colA"] = st.selectbox(
                f"File A column {i + 1}", cols_a, key=f"colA_{i}",
                index=safe_index(cols_a, m["colA"]),
            )
        with mc2:
            m["colB"] = st.selectbox(
                f"File B column {i + 1}", cols_b, key=f"colB_{i}",
                index=safe_index(cols_b, m["colB"]),
            )
        with mc3:
            st.write("")
            if st.button("✕", key=f"remove_{i}", help="Remove this pair"):
                remove_idx = i

    if remove_idx is not None:
        st.session_state.mappings.pop(remove_idx)
        st.rerun()

    if st.button("+ Add column pair"):
        st.session_state.mappings.append({"colA": "", "colB": ""})
        st.rerun()

    # ---------- Step 4: run & review ----------
    st.header("4. Fill and review")

    if st.button("Fill empty cells", type="primary"):
        result = df_a.copy()

        b_index = {}
        for _, row in df_b.iterrows():
            key = (normalize(row[team_col_b]), normalize(row[date_col_b]))
            if key != ("", "") and key not in b_index:
                b_index[key] = row

        filled_cells = set()
        matched = 0
        filled = 0
        valid_mappings = [m for m in st.session_state.mappings if m["colA"] and m["colB"]]

        if not valid_mappings:
            st.warning("Add at least one column pair to copy between.")
        else:
            for idx, row in result.iterrows():
                if team_filter != "All teams" and normalize(row[team_col_a]) != normalize(team_filter):
                    continue
                key = (normalize(row[team_col_a]), normalize(row[date_col_a]))
                if key == ("", "") or key not in b_index:
                    continue
                b_row = b_index[key]
                row_matched = False
                for m in valid_mappings:
                    cur = row[m["colA"]]
                    if is_empty(cur) and not is_empty(b_row[m["colB"]]):
                        result.at[idx, m["colA"]] = b_row[m["colB"]]
                        filled_cells.add((idx, m["colA"]))
                        filled += 1
                        row_matched = True
                    elif not is_empty(cur):
                        row_matched = True
                if row_matched:
                    matched += 1

            st.session_state.result_df = result
            st.session_state.filled_cells = filled_cells
            st.session_state.stats = {"matched": matched, "filled": filled}

    if st.session_state.result_df is not None:
        stats = st.session_state.stats
        s1, s2 = st.columns(2)
        s1.metric("Rows matched", stats["matched"])
        s2.metric("Cells filled", stats["filled"])

        display_df = st.session_state.result_df
        if team_filter != "All teams":
            mask = display_df[team_col_a].astype(str).str.strip().str.lower() == team_filter.strip().lower()
            display_df = display_df[mask]

        # Build a styled HTML table so filled cells can be highlighted precisely
        headers = list(display_df.columns)
        rows_html = []
        for idx, row in display_df.iterrows():
            cells = []
            for col in headers:
                val = html_lib.escape(str(row[col]))
                cls = "filled-cell" if (idx, col) in st.session_state.filled_cells else ""
                cells.append(f'<td class="{cls}">{val}</td>')
            rows_html.append(f"<tr>{''.join(cells)}</tr>")

        table_html = (
            '<div class="table-scroll"><table class="ledger-table"><thead><tr>'
            + "".join(f"<th>{html_lib.escape(h)}</th>" for h in headers)
            + "</tr></thead><tbody>"
            + "".join(rows_html)
            + "</tbody></table></div>"
        )
        st.markdown(table_html, unsafe_allow_html=True)
        st.markdown('<p class="legend-note">🟧 highlighted cells were filled by this merge</p>', unsafe_allow_html=True)

        csv_bytes = st.session_state.result_df.to_csv(index=False).encode("utf-8")
        base_name = file_a.name.rsplit(".", 1)[0]
        st.download_button(
            "Download updated File A",
            data=csv_bytes,
            file_name=f"{base_name}_updated.csv",
            mime="text/csv",
        )
else:
    st.info("Upload both File A and File B to begin.")
