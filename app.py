import sqlite3
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add root directory to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.extract import CATEGORIES
from src.pipeline import run_pipeline

# Configure page settings
st.set_page_config(
    page_title="Repo-Monitor | GitHub Health & Contributor Hub",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for polished dashboard feel
st.markdown("""
<style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.0rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
    .repo-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .topic-pill {
        display: inline-block;
        background-color: #F1F5F9;
        color: #334155;
        font-size: 0.78rem;
        font-weight: 500;
        padding: 2px 8px;
        border-radius: 12px;
        margin-right: 6px;
        margin-bottom: 4px;
    }
    .deep-dive-box {
        background-color: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data_from_db():
    """Load repository data from SQLite database or fallback to CSV."""
    db_path = Path("data/processed/repositories.db")
    csv_path = Path("data/processed/repositories.csv")
    
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        df = pd.read_sql_query("SELECT * FROM repositories", conn)
        conn.close()
        return df
    elif csv_path.exists():
        return pd.read_csv(str(csv_path))
    else:
        st.error("No processed data found. Please run the ETL pipeline first.")
        return pd.DataFrame()


# Load dataset
df_all = load_data_from_db()

# ==========================================
# SIDEBAR CONTROLS
# ==========================================
st.sidebar.title("🔍 Repo-Monitor Controls")

if df_all.empty:
    st.warning("Database is empty. Please run `python src/pipeline.py` first.")
    st.stop()

# Category display & switcher
current_cat = df_all["category"].iloc[0] if "category" in df_all.columns else "General"
st.sidebar.info(f"📁 **Active Dataset Category:**\n{current_cat}")

with st.sidebar.expander("⚡ Change & Fetch Category", expanded=False):
    category_options = {
        f"[{num}] {cat['name']}": cat['key']
        for num, cat in CATEGORIES.items()
    }
    selected_cat_label = st.selectbox(
        "Select Category",
        options=list(category_options.keys()),
        index=0
    )
    chosen_key = category_options[selected_cat_label]
    
    if st.button("🚀 Fetch & Run ETL", use_container_width=True):
        with st.spinner(f"Fetching 300 repositories for '{selected_cat_label}' and running ETL pipeline..."):
            try:
                run_pipeline(category_key=chosen_key, limit=300)
                st.cache_data.clear()
                st.success("Dataset updated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to fetch data: {e}")

st.sidebar.subheader("Filter Repositories")

# Search keyword
search_query = st.sidebar.text_input("Search Name / Description", placeholder="e.g. vision, transformer, api...")

# Language filter
available_languages = sorted([lang for lang in df_all["language"].dropna().unique() if lang != "Unknown"])
selected_languages = st.sidebar.multiselect(
    "Filter by Language",
    options=available_languages,
    default=[]
)

# Activity status filter
activity_options = ["Active", "Moderate", "Low Activity", "Inactive"]
selected_activity = st.sidebar.multiselect(
    "Activity Status",
    options=activity_options,
    default=activity_options
)

# Health Score slider
min_health = st.sidebar.slider(
    "Min Maintenance Health Score",
    min_value=0,
    max_value=100,
    value=0,
    step=5
)

# Contributor Friendliness slider
min_contrib = st.sidebar.slider(
    "Min Contributor Friendliness Score",
    min_value=0,
    max_value=100,
    value=0,
    step=5
)

# Minimum Stars slider
max_stars = int(df_all["stars_count"].max()) if not df_all.empty else 100000
min_stars = st.sidebar.slider(
    "Minimum Stars",
    min_value=0,
    max_value=min(20000, max_stars),
    value=0,
    step=100
)

# Checkbox: Exclude abandoned
hide_abandoned = st.sidebar.checkbox("Exclude Potentially Abandoned", value=False)

# Refresh button
if st.sidebar.button("🔄 Reload Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Built with Streamlit & Plotly • GitHub Health & Contributor ETL")

# ==========================================
# DATA FILTERING LOGIC
# ==========================================
df_filtered = df_all.copy()

if search_query:
    q = search_query.lower()
    df_filtered = df_filtered[
        df_filtered["name"].str.lower().str.contains(q, na=False) |
        df_filtered["description"].str.lower().str.contains(q, na=False)
    ]

if selected_languages:
    df_filtered = df_filtered[df_filtered["language"].isin(selected_languages)]

if selected_activity:
    df_filtered = df_filtered[df_filtered["activity_status"].isin(selected_activity)]

if min_health > 0:
    df_filtered = df_filtered[df_filtered["maintenance_health_score"] >= min_health]

if min_contrib > 0:
    df_filtered = df_filtered[df_filtered["contributor_friendliness_score"] >= min_contrib]

if min_stars > 0:
    df_filtered = df_filtered[df_filtered["stars_count"] >= min_stars]

if hide_abandoned:
    df_filtered = df_filtered[df_filtered["is_potentially_abandoned"] == 0]

# ==========================================
# MAIN DASHBOARD HEADER & KPIS
# ==========================================
st.markdown('<div class="main-title">GitHub Open Source Health & Contributor Monitor</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Interactive ETL & EDA pipeline evaluating repository activity, maintenance health, and beginner-friendly contribution opportunities.</div>',
    unsafe_allow_html=True
)

# Top KPI metrics row
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Repositories", f"{len(df_filtered):,} of {len(df_all):,}")
with col2:
    active_cnt = (df_filtered["activity_status"] == "Active").sum()
    active_pct = round((active_cnt / len(df_filtered) * 100), 1) if len(df_filtered) > 0 else 0
    st.metric("Active Repos", f"{active_cnt:,}", f"{active_pct}%")
with col3:
    avg_health = round(df_filtered["maintenance_health_score"].mean(), 1) if len(df_filtered) > 0 else 0
    st.metric("Avg Health Score", f"{avg_health} / 100")
with col4:
    avg_contrib = round(df_filtered["contributor_friendliness_score"].mean(), 1) if len(df_filtered) > 0 else 0
    st.metric("Avg Contrib Score", f"{avg_contrib} / 100")
with col5:
    abandoned_cnt = (df_filtered["is_potentially_abandoned"] == 1).sum()
    abandoned_pct = round((abandoned_cnt / len(df_filtered) * 100), 1) if len(df_filtered) > 0 else 0
    st.metric("At-Risk / Abandoned", f"{abandoned_cnt:,}", f"{abandoned_pct}%", delta_color="inverse")

st.markdown("---")

# ==========================================
# DASHBOARD TABS
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🌟 Contributor Matchmaker",
    "🎯 Repository Deep-Dive Card",
    "🔍 Repository Explorer",
    "📊 Interactive EDA Charts",
    "⚠️ Health & Maintenance Audit"
])

# ------------------------------------------
# TAB 1: CONTRIBUTOR MATCHMAKER
# ------------------------------------------
with tab1:
    st.subheader("🌟 Top Recommended Repositories for Contributors")
    st.write(
        "Surfacing repositories that combine active maintenance, available open issues to tackle, "
        "comprehensive documentation, open-source licenses, and non-archived status."
    )

    top_matches = df_filtered[df_filtered["activity_status"] == "Active"].sort_values(
        by=["contributor_friendliness_score", "stars_count"],
        ascending=[False, False]
    ).head(15)

    if top_matches.empty:
        st.info("No active repositories match your current filter criteria. Try easing the filters in the sidebar.")
    else:
        for _, repo in top_matches.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="repo-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0;">
                            <a href="{repo['html_url']}" target="_blank" style="text-decoration: none; color: #0284C7;">
                                {repo['full_name']} ↗
                            </a>
                        </h3>
                        <div>
                            <span style="background-color: #E0F2FE; color: #0369A1; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.88rem;">
                                Contrib Score: {repo['contributor_friendliness_score']}/100
                            </span>
                            &nbsp;
                            <span style="background-color: #DCFCE7; color: #15803D; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.88rem;">
                                Health: {repo['maintenance_health_score']}/100
                            </span>
                        </div>
                    </div>
                    <p style="color: #475569; margin: 8px 0 12px 0;">{repo['description'] or 'No description provided.'}</p>
                    <div style="display: flex; flex-wrap: wrap; gap: 16px; font-size: 0.9rem; color: #64748B;">
                        <span>💻 <b>Language:</b> {repo['language']}</span>
                        <span>⭐ <b>Stars:</b> {repo['stars_count']:,}</span>
                        <span>🍴 <b>Forks:</b> {repo['forks_count']:,}</span>
                        <span>🎯 <b>Open Issues:</b> {repo['open_issues_count']:,}</span>
                        <span>🕒 <b>Last Push:</b> {int(repo['days_since_last_push'])} days ago</span>
                        <span>📜 <b>License:</b> {repo['license']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 2: REPOSITORY DEEP-DIVE CARD
# ------------------------------------------
with tab2:
    st.subheader("🎯 Repository Health & Contributor Deep-Dive")
    st.write("Inspect the multi-dimensional health fingerprint and contribution audit of any single repository.")

    repo_options = df_filtered["full_name"].tolist() if not df_filtered.empty else df_all["full_name"].tolist()
    
    selected_full_name = st.selectbox(
        "Search or Select a Repository to Inspect:",
        options=repo_options,
        index=0
    )

    if selected_full_name:
        repo_data = df_all[df_all["full_name"] == selected_full_name].iloc[0]

        # Top Card Header
        st.markdown(f"""
        <div class="deep-dive-box">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h2 style="margin: 0; color: #0F172A;">{repo_data['full_name']}</h2>
                    <p style="color: #64748B; margin-top: 4px; font-size: 1.05rem;">{repo_data['description'] or 'No description available.'}</p>
                </div>
                <a href="{repo_data['html_url']}" target="_blank" style="background-color: #0F172A; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: 500; font-size: 0.9rem;">
                    View on GitHub ↗
                </a>
            </div>
            <div style="margin-top: 10px;">
                <span class="topic-pill">💻 {repo_data['language']}</span>
                <span class="topic-pill">📜 {repo_data['license']}</span>
                <span class="topic-pill">🌿 Branch: {repo_data['default_branch']}</span>
                <span class="topic-pill">📦 Size: {repo_data['size_kb']:,} KB</span>
                <span class="topic-pill">📅 Age: {int(repo_data['repo_age_days'])} days</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 4 Metric Cards Row
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)
        with d_col1:
            st.metric("Total Stars", f"{repo_data['stars_count']:,} ⭐")
        with d_col2:
            st.metric("Total Forks", f"{repo_data['forks_count']:,} 🍴")
        with d_col3:
            st.metric("Open Issues & PRs", f"{repo_data['open_issues_count']:,} 🎯")
        with d_col4:
            st.metric("Commit Freshness", f"{int(repo_data['days_since_last_push'])} days ago", f"Status: {repo_data['activity_status']}")

        # Radar Chart & Automated Verdict Columns
        radar_col, verdict_col = st.columns([1.1, 1])

        with radar_col:
            st.markdown("#### 🕸️ 5-Pillar Health Radar")
            radar_categories = [
                'Commit Recency',
                'Documentation',
                'Community Health',
                'Maintenance Health',
                'Contributor Score'
            ]
            radar_values = [
                repo_data['push_recency_score'],
                repo_data['documentation_score'],
                repo_data['community_health_score'],
                repo_data['maintenance_health_score'],
                repo_data['contributor_friendliness_score']
            ]

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=radar_values + [radar_values[0]],
                theta=radar_categories + [radar_categories[0]],
                fill='toself',
                fillcolor='rgba(14, 165, 233, 0.25)',
                line=dict(color='#0284C7', width=2),
                name=repo_data['name']
            ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9))
                ),
                showlegend=False,
                margin=dict(l=30, r=30, t=20, b=20),
                height=340
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        with verdict_col:
            st.markdown("#### 📋 Contribution & Health Audit Verdict")

            # Determine badge and verdict
            is_active = repo_data['activity_status'] == 'Active'
            is_abandoned = repo_data['is_potentially_abandoned'] == 1
            contrib_score = repo_data['contributor_friendliness_score']

            if is_abandoned:
                verdict_badge = "🔴 High Abandonment Risk"
                verdict_color = "#FEE2E2"
                text_color = "#991B1B"
                verdict_msg = "This repository shows strong signs of neglect. Code hasn't been pushed recently and open issues remain unaddressed."
            elif contrib_score >= 80:
                verdict_badge = "🟢 Prime Contribution Candidate"
                verdict_color = "#DCFCE7"
                text_color = "#166534"
                verdict_msg = "Highly recommended for new and seasoned contributors! Fresh commit history, active maintainers, and good issue availability."
            elif contrib_score >= 50:
                verdict_badge = "🟡 Moderate Contribution Potential"
                verdict_color = "#FEF9C3"
                text_color = "#854D0E"
                verdict_msg = "Viable project with moderate activity, but may take longer to receive PR reviews or maintainer feedback."
            else:
                verdict_badge = "🟠 Low Contributor Activity"
                verdict_color = "#FFEDD5"
                text_color = "#9A3412"
                verdict_msg = "Repository has low commit frequency or limited available beginner issues."

            st.markdown(f"""
            <div style="background-color: {verdict_color}; color: {text_color}; padding: 12px; border-radius: 8px; font-weight: 600; font-size: 1.05rem; margin-bottom: 12px;">
                {verdict_badge}
            </div>
            """, unsafe_allow_html=True)
            st.write(verdict_msg)

            st.markdown("##### Detailed Checks:")
            # Check 1: Commit Recency
            if repo_data['days_since_last_push'] <= 30:
                st.markdown("✅ **Fresh Commits:** Pushed within the last 30 days.")
            elif repo_data['days_since_last_push'] <= 90:
                st.markdown("✅ **Active Commits:** Pushed within the last 90 days.")
            else:
                st.markdown(f"⚠️ **Stale Commits:** Last code push was {int(repo_data['days_since_last_push'])} days ago.")

            # Check 2: Issues
            if 10 <= repo_data['open_issues_count'] <= 300:
                st.markdown(f"✅ **Sweet Spot Issues:** {repo_data['open_issues_count']} open issues (manageable workload for contributors).")
            elif repo_data['open_issues_count'] > 300:
                st.markdown(f"⚠️ **High Issue Volume:** {repo_data['open_issues_count']} issues (potential maintenance backlog).")
            else:
                st.markdown(f"ℹ️ **Few Issues:** {repo_data['open_issues_count']} issues (may have fewer beginner tasks).")

            # Check 3: License & Docs
            if repo_data['has_license'] == 1:
                st.markdown(f"✅ **Open Source License:** {repo_data['license']}")
            else:
                st.markdown("❌ **No Approved License Detected:** May have copyright restrictions.")

            if repo_data['has_discussions_enabled'] == 1:
                st.markdown("✅ **Community Discussions Active**")

# ------------------------------------------
# TAB 3: REPOSITORY EXPLORER
# ------------------------------------------
with tab3:
    st.subheader("🔍 Interactive Repository Explorer")
    st.write(f"Showing **{len(df_filtered)}** matching repositories across all 27 processed metrics.")

    display_cols = [
        "name", "language", "stars_count", "forks_count", "open_issues_count",
        "maintenance_health_score", "contributor_friendliness_score",
        "activity_status", "days_since_last_push", "html_url"
    ]
    
    st.dataframe(
        df_filtered[display_cols],
        column_config={
            "html_url": st.column_config.LinkColumn("GitHub Link", display_text="Open GitHub"),
            "stars_count": st.column_config.NumberColumn("Stars", format="%d ⭐"),
            "forks_count": st.column_config.NumberColumn("Forks", format="%d"),
            "open_issues_count": st.column_config.NumberColumn("Open Issues", format="%d"),
            "maintenance_health_score": st.column_config.ProgressColumn("Health Score", min_value=0, max_value=100, format="%.1f"),
            "contributor_friendliness_score": st.column_config.ProgressColumn("Contrib Score", min_value=0, max_value=100, format="%.1f"),
            "days_since_last_push": st.column_config.NumberColumn("Days Since Push", format="%d d")
        },
        use_container_width=True,
        height=500
    )

    # Download CSV button
    csv_bytes = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Dataset as CSV",
        data=csv_bytes,
        file_name="filtered_repositories.csv",
        mime="text/csv"
    )

# ------------------------------------------
# TAB 4: INTERACTIVE EDA CHARTS (PLOTLY)
# ------------------------------------------
with tab4:
    st.subheader("📊 Interactive Exploratory Data Analysis (EDA)")
    st.write("Hover, zoom, and pan across interactive charts to uncover repository ecosystem patterns.")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # Chart 1: Interactive Language Distribution
        st.markdown("#### 💻 Top Programming Languages")
        top_langs = df_filtered["language"].value_counts().head(8).reset_index()
        top_langs.columns = ["Language", "Count"]

        if not top_langs.empty:
            fig_lang = px.bar(
                top_langs,
                x="Count",
                y="Language",
                orientation="h",
                color="Count",
                color_continuous_scale="Blues",
                text="Count"
            )
            fig_lang.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                coloraxis_showscale=False,
                margin=dict(l=10, r=10, t=10, b=10),
                height=350
            )
            st.plotly_chart(fig_lang, use_container_width=True)
        else:
            st.info("No language data available.")

    with chart_col2:
        # Chart 2: Interactive Stars vs Forks Scatter (Plotly)
        st.markdown("#### ⭐ Popularity: Stars vs. Forks (Hover to Inspect)")
        if len(df_filtered) > 0:
            fig_scatter = px.scatter(
                df_filtered,
                x="forks_count",
                y="stars_count",
                color="maintenance_health_score",
                color_continuous_scale="Plasma",
                hover_name="full_name",
                hover_data={
                    "language": True,
                    "stars_count": ":,",
                    "forks_count": ":,",
                    "open_issues_count": ":,",
                    "maintenance_health_score": ":.1f",
                    "activity_status": True
                },
                labels={
                    "forks_count": "Forks (log10)",
                    "stars_count": "Stars (log10)",
                    "maintenance_health_score": "Health Score"
                },
                log_x=True,
                log_y=True
            )
            fig_scatter.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=350
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("No data for scatter plot.")

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        # Chart 3: Commit Freshness Histogram (Plotly)
        st.markdown("#### 🕒 Commit Freshness (Days Since Last Push)")
        if len(df_filtered) > 0:
            fig_push = px.histogram(
                df_filtered,
                x="days_since_last_push",
                nbins=35,
                color="activity_status",
                color_discrete_map={
                    "Active": "#10B981",
                    "Moderate": "#3B82F6",
                    "Low Activity": "#F59E0B",
                    "Inactive": "#EF4444"
                },
                labels={"days_since_last_push": "Days Since Last Push", "activity_status": "Status"}
            )
            fig_push.add_vline(x=60, line_dash="dash", line_color="#10B981", annotation_text="Active (60d)")
            fig_push.add_vline(x=365, line_dash="dash", line_color="#EF4444", annotation_text="Inactive (365d)")
            fig_push.update_layout(
                barmode='stack',
                margin=dict(l=10, r=10, t=10, b=10),
                height=350
            )
            st.plotly_chart(fig_push, use_container_width=True)
        else:
            st.info("No push recency data.")

    with chart_col4:
        # Chart 4: Open Issues by Activity Status (Plotly Boxplot)
        st.markdown("#### 🎯 Open Issues by Activity Status")
        if len(df_filtered) > 0:
            fig_box = px.box(
                df_filtered,
                x="activity_status",
                y="open_issues_count",
                color="activity_status",
                color_discrete_map={
                    "Active": "#10B981",
                    "Moderate": "#3B82F6",
                    "Low Activity": "#F59E0B",
                    "Inactive": "#EF4444"
                },
                labels={"activity_status": "Activity Status", "open_issues_count": "Open Issues (log10)"},
                log_y=True
            )
            fig_box.update_layout(
                showlegend=False,
                margin=dict(l=10, r=10, t=10, b=10),
                height=350
            )
            st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.info("No open issues data.")

# ------------------------------------------
# TAB 5: HEALTH & MAINTENANCE AUDIT
# ------------------------------------------
with tab5:
    st.subheader("⚠️ Project Health & Abandonment Audit")
    st.write("Detect inactive, stagnant, or abandoned repositories using multi-metric indicators.")

    audit_col1, audit_col2 = st.columns([1, 1.2])

    with audit_col1:
        st.markdown("#### 🔄 Activity Lifecycle Breakdown")
        status_counts = df_filtered["activity_status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]

        if not status_counts.empty:
            fig_pie = px.pie(
                status_counts,
                names="Status",
                values="Count",
                hole=0.45,
                color="Status",
                color_discrete_map={
                    "Active": "#10B981",
                    "Moderate": "#3B82F6",
                    "Low Activity": "#F59E0B",
                    "Inactive": "#EF4444"
                }
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=340
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No activity data.")

    with audit_col2:
        st.markdown("#### 📈 Maintenance Health Score Distribution")
        if len(df_filtered) > 0:
            fig_hist = px.histogram(
                df_filtered,
                x="maintenance_health_score",
                nbins=25,
                color_discrete_sequence=["#0EA5E9"],
                labels={"maintenance_health_score": "Health Score (0-100)"}
            )
            fig_hist.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=340
            )
            st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("#### 🚨 Flagged Repositories (Potentially Abandoned or Archived)")
    st.write(
        "Criteria: Repositories that are either explicitly **archived**, or haven't received a code push "
        "in over **365 days** while carrying unresolved open issues."
    )

    flagged_repos = df_filtered[df_filtered["is_potentially_abandoned"] == 1].sort_values(
        by=["stars_count"], ascending=False
    )

    if flagged_repos.empty:
        st.success("🎉 No potentially abandoned repositories found under current filter selection!")
    else:
        st.dataframe(
            flagged_repos[[
                "full_name", "language", "stars_count", "open_issues_count",
                "days_since_last_push", "is_archived", "maintenance_health_score", "html_url"
            ]],
            column_config={
                "html_url": st.column_config.LinkColumn("GitHub Link", display_text="Open GitHub"),
                "stars_count": st.column_config.NumberColumn("Stars", format="%d ⭐"),
                "open_issues_count": st.column_config.NumberColumn("Unresolved Issues", format="%d ⚠️"),
                "days_since_last_push": st.column_config.NumberColumn("Days Stagnant", format="%d days"),
                "is_archived": st.column_config.CheckboxColumn("Archived"),
                "maintenance_health_score": st.column_config.NumberColumn("Health Score", format="%.1f / 100")
            },
            use_container_width=True,
            height=300
        )
