import streamlit as st
import pandas as pd
import requests
import io
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FAA SDR Explorer",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.main-title {
    font-family: 'Space Mono', monospace;
    font-size: 2.6rem;
    font-weight: 700;
    color: #0a1628;
    letter-spacing: -1px;
    line-height: 1.1;
}

.subtitle {
    font-size: 1rem;
    color: #5a6a85;
    margin-top: 0.25rem;
}

.metric-card {
    background: #0a1628;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    color: white;
}

.metric-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #7a9cc8;
    margin-bottom: 4px;
}

.metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #e8f0fe;
}

.tag {
    display: inline-block;
    background: #e8f0fe;
    color: #0a1628;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.stDownloadButton > button {
    background-color: #0a1628 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.8rem !important;
}

.info-box {
    background: #f0f4ff;
    border-left: 4px solid #2563eb;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    font-size: 0.88rem;
    color: #1e3a5f;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
CURRENT_YEAR = datetime.now().year
AVAILABLE_YEARS = list(range(1995, CURRENT_YEAR + 1))
FAA_DOWNLOAD_BASE = "https://av-info.faa.gov/sdrx/SDR{year}.csv"
FAA_FALLBACK_BASE = "https://www.faa.gov/av-info/download_SDR/{year}/SDR{year}.csv"

# ── Helper functions ──────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_sdr_data(year: int) -> pd.DataFrame:
    """Download and cache SDR CSV for a given year."""
    urls = [
        f"https://av-info.faa.gov/sdrx/SDR{year}.csv",
        f"https://www.faa.gov/av-info/download_SDR/{year}/SDR{year}.csv",
        f"https://av-info.faa.gov/sdr/SDR{year}.csv",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                df = pd.read_csv(io.StringIO(resp.text), low_memory=False, encoding="latin-1")
                df.columns = [c.strip() for c in df.columns]
                return df
        except Exception:
            continue
    return pd.DataFrame()


def safe_value_counts(series, n=15):
    return series.dropna().astype(str).value_counts().head(n)


# ── Header ────────────────────────────────────────────────────────────────────
col_logo, col_head = st.columns([1, 9])
with col_logo:
    st.markdown("## ✈️")
with col_head:
    st.markdown('<div class="main-title">FAA SDR Explorer</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Federal Aviation Administration · Service Difficulty Reports Database</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔧 Data Selection")

    year = st.selectbox(
        "Report Year",
        options=sorted(AVAILABLE_YEARS, reverse=True),
        index=0,
        help="Select the calendar year to load from the FAA database"
    )

    st.markdown("---")
    st.markdown("### 🔍 Filters")
    filter_aircraft = st.text_input("Aircraft Make / Model", placeholder="e.g. BOEING, CESSNA")
    filter_part = st.text_input("Part / Component", placeholder="e.g. ENGINE, LANDING GEAR")
    filter_operator = st.text_input("Operator / Carrier", placeholder="e.g. DELTA, UNITED")

    st.markdown("---")
    st.markdown("""
    <div class="info-box">
    Data sourced directly from the <strong>FAA SDRS database</strong>.<br>
    Reports go back to <strong>1995</strong> and are updated continuously.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    st.markdown("**Links**")
    st.markdown("🔗 [SDRS Portal](https://sdrs.faa.gov)")
    st.markdown("🔗 [FAA SDR Downloads](https://www.faa.gov/av-info/download_SDR)")
    st.markdown("🔗 [AviationDB Query](https://www.aviationdb.com/Aviation/SdrQuery.shtm)")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner(f"Loading {year} SDR data from FAA..."):
    df_raw = load_sdr_data(year)

if df_raw.empty:
    st.error(
        f"⚠️ Could not retrieve SDR data for **{year}** from the FAA servers. "
        "This may be due to network restrictions or the file not yet being published. "
        "Try a different year, or download manually from [faa.gov](https://www.faa.gov/av-info/download_SDR)."
    )
    st.markdown("### 📥 Manual Download")
    st.markdown(f"[Download {year} SDR CSV from FAA](https://www.faa.gov/av-info/download_SDR)")

    st.markdown("---")
    st.markdown("### 🧪 Try with Sample Data")
    if st.button("Load sample dataset (demo)"):
        df_raw = pd.DataFrame({
            "ACMake": ["BOEING", "CESSNA", "AIRBUS", "BOEING", "PIPER"] * 20,
            "ACModel": ["737", "172", "A320", "747", "PA-28"] * 20,
            "PartName": ["ENGINE", "LANDING GEAR", "HYDRAULICS", "AVIONICS", "FUEL SYSTEM"] * 20,
            "OperatorName": ["UNITED", "PRIVATE", "DELTA", "AMERICAN", "PRIVATE"] * 20,
            "Difficulty": ["VIBRATION", "FAILURE", "LEAK", "MALFUNCTION", "CRACK"] * 20,
            "SubmitDate": pd.date_range("2023-01-01", periods=100, freq="3D").astype(str),
        })
        st.success("Sample data loaded!")
    else:
        st.stop()

df = df_raw.copy()

# ── Apply filters ─────────────────────────────────────────────────────────────
def apply_filter(df, col_candidates, query):
    if not query:
        return df
    q = query.upper().strip()
    for col in col_candidates:
        if col in df.columns:
            return df[df[col].astype(str).str.upper().str.contains(q, na=False)]
    return df

# Detect column names flexibly
make_cols = [c for c in df.columns if any(k in c.upper() for k in ["ACMAKE", "MAKE", "AIRCRAFT"])]
model_cols = [c for c in df.columns if "MODEL" in c.upper()]
part_cols = [c for c in df.columns if any(k in c.upper() for k in ["PART", "COMPONENT", "ASSEMBLY"])]
operator_cols = [c for c in df.columns if any(k in c.upper() for k in ["OPERATOR", "CARRIER", "AIRLINE"])]

if filter_aircraft:
    df = apply_filter(df, make_cols + model_cols, filter_aircraft)
if filter_part:
    df = apply_filter(df, part_cols, filter_part)
if filter_operator:
    df = apply_filter(df, operator_cols, filter_operator)

# ── Metrics row ───────────────────────────────────────────────────────────────
st.markdown(f"### 📊 {year} Overview")
m1, m2, m3, m4 = st.columns(4)

total = len(df)
unique_aircraft = df[make_cols[0]].nunique() if make_cols else "N/A"
unique_operators = df[operator_cols[0]].nunique() if operator_cols else "N/A"
unique_parts = df[part_cols[0]].nunique() if part_cols else "N/A"

for col, label, val in zip(
    [m1, m2, m3, m4],
    ["Total Reports", "Aircraft Makes", "Operators", "Part Types"],
    [f"{total:,}", unique_aircraft, unique_operators, unique_parts]
):
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{val}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("")

# ── Charts ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends", "✈️ Aircraft", "🔩 Parts", "📋 Raw Data"])

with tab1:
    # Try to find a date column
    date_cols = [c for c in df.columns if any(k in c.upper() for k in ["DATE", "SUBMIT", "REPORT"])]
    if date_cols:
        try:
            df["_date"] = pd.to_datetime(df[date_cols[0]], errors="coerce")
            monthly = df.dropna(subset=["_date"]).groupby(df["_date"].dt.to_period("M")).size().reset_index()
            monthly.columns = ["Month", "Reports"]
            monthly["Month"] = monthly["Month"].astype(str)
            fig = px.bar(
                monthly, x="Month", y="Reports",
                title=f"Monthly SDR Submissions — {year}",
                color_discrete_sequence=["#2563eb"]
            )
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", font_family="DM Sans")
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.info("Could not parse date column for trend chart.")
    else:
        st.info("No date column detected in this dataset for trend analysis.")

with tab2:
    if make_cols:
        col_a, col_b = st.columns(2)
        with col_a:
            top_makes = safe_value_counts(df[make_cols[0]], 12).reset_index()
            top_makes.columns = ["Make", "Count"]
            fig2 = px.bar(
                top_makes, x="Count", y="Make", orientation="h",
                title="Top Aircraft Makes",
                color="Count", color_continuous_scale="Blues"
            )
            fig2.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                               yaxis=dict(autorange="reversed"), showlegend=False,
                               coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        with col_b:
            if model_cols:
                top_models = safe_value_counts(df[model_cols[0]], 12).reset_index()
                top_models.columns = ["Model", "Count"]
                fig3 = px.pie(
                    top_models, names="Model", values="Count",
                    title="Top Aircraft Models",
                    color_discrete_sequence=px.colors.sequential.Blues_r
                )
                fig3.update_layout(paper_bgcolor="white")
                st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No aircraft make column detected.")

with tab3:
    if part_cols:
        top_parts = safe_value_counts(df[part_cols[0]], 15).reset_index()
        top_parts.columns = ["Part", "Count"]
        fig4 = px.treemap(
            top_parts, path=["Part"], values="Count",
            title="Most Reported Parts / Components",
            color="Count", color_continuous_scale="Blues"
        )
        fig4.update_layout(paper_bgcolor="white")
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No part/component column detected.")

with tab4:
    st.markdown(f"**Showing {len(df):,} records** (filtered from {len(df_raw):,} total)")

    # Column selector
    all_cols = df.columns.tolist()
    selected_cols = st.multiselect("Select columns to display", all_cols, default=all_cols[:8])
    if selected_cols:
        st.dataframe(df[selected_cols].head(500), use_container_width=True, height=420)

    # Download
    csv_out = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"⬇ Download filtered data ({len(df):,} rows)",
        data=csv_out,
        file_name=f"FAA_SDR_{year}_filtered.csv",
        mime="text/csv"
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<small style='color:#9aabbd'>Data sourced from the FAA Service Difficulty Reporting System (SDRS). "
    "For official use, consult <a href='https://sdrs.faa.gov'>sdrs.faa.gov</a>. "
    "This tool is for research and informational purposes only.</small>",
    unsafe_allow_html=True
)
