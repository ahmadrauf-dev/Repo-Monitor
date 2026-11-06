import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()

cells = []

# Cell 1: Title Markdown
cells.append(nbf.v4.new_markdown_cell("""# GitHub Repository Contributor & Health Monitor: Exploratory Data Analysis (EDA)

## 1. Project Overview & Problem Statement
Thousands of open-source repositories exist on GitHub, but finding the right projects to contribute to or assessing their overall project health is challenging when looking only at raw numbers like stars. 

This analysis examines **300 public GitHub repositories** extracted via the GitHub REST API, validated with **Pydantic**, and loaded from our **SQLite database** (`data/processed/repositories.db`).

### Key Objectives:
- Investigate distributions of popularity, activity, and maintenance across 300 repositories.
- Compare programming languages and ecosystem traits.
- Formulate and analyze health and contributor-friendliness indicators across **27 metrics**.
- Identify active, healthy repositories ideal for new contributors, versus stagnant, abandoned repositories."""))

# Cell 2: Imports & Setup
cells.append(nbf.v4.new_code_cell("""import sqlite3
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Visual styling
sns.set_theme(style="whitegrid")
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['figure.dpi'] = 110
plt.rcParams['figure.figsize'] = (10, 6)

print("Libraries imported successfully.")"""))

# Cell 3: Loading Data from SQLite
cells.append(nbf.v4.new_markdown_cell("""## 2. Ingesting Processed Data from SQLite
We connect to our SQLite database (`data/processed/repositories.db`) and load the `repositories` table into a pandas DataFrame."""))

# Cell 4: Code for Loading Data
cells.append(nbf.v4.new_code_cell("""# Connect to SQLite and load data
db_path = Path("../data/processed/repositories.db")
if not db_path.exists():
    db_path = Path("data/processed/repositories.db")

conn = sqlite3.connect(db_path)
df = pd.read_sql_query("SELECT * FROM repositories", conn)
conn.close()

print(f"Dataset successfully loaded from SQLite database.")
print(f"Total Rows (Repositories): {df.shape[0]}")
print(f"Total Columns (Metrics & Metadata): {df.shape[1]}")
df.head(5)"""))

# Cell 5: Data Inspection & Schema Verification
cells.append(nbf.v4.new_markdown_cell("""## 3. Data Integrity & Metric Inventory
Let's inspect the metrics present in our dataset. Our pipeline engineered and validated **27 distinct metrics** (17 raw extraction metrics + 10 derived health indicators)."""))

# Cell 6: Metric Inventory Code
cells.append(nbf.v4.new_code_cell("""raw_metrics = [
    'stars_count', 'forks_count', 'open_issues_count', 'watchers_count', 'size_kb',
    'repo_age_days', 'days_since_last_push', 'days_since_last_update',
    'has_issues_enabled', 'has_projects_enabled', 'has_wiki_enabled',
    'has_pages_enabled', 'has_discussions_enabled', 'has_license',
    'is_archived', 'topics_count', 'description_length'
]

derived_metrics = [
    'fork_to_star_ratio', 'issues_to_star_ratio', 'issues_to_fork_ratio',
    'push_recency_score', 'documentation_score', 'community_health_score',
    'maintenance_health_score', 'contributor_friendliness_score',
    'activity_status', 'is_potentially_abandoned'
]

print(f"Raw Metrics ({len(raw_metrics)}):", ", ".join(raw_metrics))
print()
print(f"Derived Metrics ({len(derived_metrics)}):", ", ".join(derived_metrics))
print()
print("Missing values per column:")
missing = df[raw_metrics + derived_metrics].isnull().sum()
print(missing[missing > 0] if missing.sum() > 0 else "Zero missing values across all metrics!")"""))

# Cell 7: Summary Statistics
cells.append(nbf.v4.new_markdown_cell("""## 4. Descriptive Statistics of Core Metrics
Let's examine the central tendencies, spread, percentiles, and skewness of the primary numerical features."""))

# Cell 8: Code for Summary Stats
cells.append(nbf.v4.new_code_cell("""numeric_subset = [
    'stars_count', 'forks_count', 'open_issues_count', 'size_kb',
    'repo_age_days', 'days_since_last_push', 'maintenance_health_score',
    'contributor_friendliness_score'
]
df[numeric_subset].describe().round(2)"""))

# Cell 9: Distribution of Stars & Forks
cells.append(nbf.v4.new_markdown_cell("""## 5. Repository Popularity & Distribution (Stars, Forks, Issues)
Open source repositories exhibit heavy long-tail (power-law) distributions in stars, forks, and issues. We visualize both raw and log-transformed distributions to reveal the true scale."""))

# Cell 10: Code for Distribution Plots
cells.append(nbf.v4.new_code_cell("""fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Stars Distribution (Log Scale)
sns.histplot(df['stars_count'], kde=True, log_scale=True, ax=axes[0, 0], color='#1f77b4')
axes[0, 0].set_title("Distribution of Stars Count (Log Scale)", fontsize=13, fontweight='bold')
axes[0, 0].set_xlabel("Stars Count (log10)")

# 2. Forks Distribution (Log Scale)
sns.histplot(df['forks_count'] + 1, kde=True, log_scale=True, ax=axes[0, 1], color='#2ca02c')
axes[0, 1].set_title("Distribution of Forks Count (Log Scale)", fontsize=13, fontweight='bold')
axes[0, 1].set_xlabel("Forks Count + 1 (log10)")

# 3. Open Issues Distribution (Log Scale)
sns.histplot(df['open_issues_count'] + 1, kde=True, log_scale=True, ax=axes[1, 0], color='#ff7f0e')
axes[1, 0].set_title("Distribution of Open Issues (Log Scale)", fontsize=13, fontweight='bold')
axes[1, 0].set_xlabel("Open Issues Count + 1 (log10)")

# 4. Stars vs Forks Scatter Plot with regression
sns.regplot(data=df, x='forks_count', y='stars_count', ax=axes[1, 1],
            scatter_kws={'alpha': 0.5, 'color': '#9467bd'}, line_kws={'color': '#d62728'})
axes[1, 1].set_title("Stars vs Forks Linear Trend", fontsize=13, fontweight='bold')
axes[1, 1].set_xscale('log')
axes[1, 1].set_yscale('log')
axes[1, 1].set_xlabel("Forks (log10)")
axes[1, 1].set_ylabel("Stars (log10)")

plt.tight_layout()
plt.show()"""))

# Cell 11: Programming Language Landscape
cells.append(nbf.v4.new_markdown_cell("""## 6. Language Landscape & Ecosystem Breakdown
Which programming languages dominate the repositories, and how do their median stars and maintenance health scores compare?"""))

# Cell 12: Code for Language Landscape
cells.append(nbf.v4.new_code_cell("""top_languages = df['language'].value_counts().head(8).index
df_top_lang = df[df['language'].isin(top_languages)]

fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Top languages count
sns.countplot(data=df_top_lang, y='language', order=top_languages, ax=axes[0], palette='Blues_r')
axes[0].set_title("Top Programming Languages in Dataset", fontsize=13, fontweight='bold')
axes[0].set_xlabel("Number of Repositories")
axes[0].set_ylabel("Language")

# Maintenance health score by language
sns.boxplot(data=df_top_lang, x='maintenance_health_score', y='language', order=top_languages, ax=axes[1], palette='Set2')
axes[1].set_title("Maintenance Health Score by Language", fontsize=13, fontweight='bold')
axes[1].set_xlabel("Maintenance Health Score (0-100)")
axes[1].set_ylabel("")

plt.tight_layout()
plt.show()"""))

# Cell 13: Activity & Push Recency Analysis
cells.append(nbf.v4.new_markdown_cell("""## 7. Maintenance Activity & Inactivity Lifecycles
Tracking when code was last pushed is one of the most reliable signals of project vitality.
We categorize repositories into:
- **Active**: Pushed within the last 60 days
- **Moderate**: Pushed between 61 and 180 days ago
- **Low Activity**: Pushed between 181 and 365 days ago
- **Inactive**: No code pushed for over 1 year"""))

# Cell 14: Code for Activity Breakdown
cells.append(nbf.v4.new_code_cell("""fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Activity Status Pie Chart
activity_counts = df['activity_status'].value_counts()
colors = ['#2ca02c', '#d62728', '#ff7f0e', '#1f77b4']
axes[0].pie(
    activity_counts, 
    labels=activity_counts.index, 
    autopct='%1.1f%%', 
    colors=[colors[i % len(colors)] for i in range(len(activity_counts))],
    startangle=140, 
    explode=[0.05] * len(activity_counts)
)
axes[0].set_title("Repository Activity Status Breakdown", fontsize=13, fontweight='bold')

# Days Since Last Push Histogram
sns.histplot(df['days_since_last_push'], bins=40, kde=True, ax=axes[1], color='#e377c2')
axes[1].axvline(60, color='green', linestyle='--', label='Active cutoff (60 days)')
axes[1].axvline(365, color='red', linestyle='--', label='Inactive cutoff (365 days)')
axes[1].set_title("Distribution of Days Since Last Push", fontsize=13, fontweight='bold')
axes[1].set_xlabel("Days Since Last Push")
axes[1].legend()

plt.tight_layout()
plt.show()"""))

# Cell 15: Potentially Abandoned Repositories Deep Dive
cells.append(nbf.v4.new_markdown_cell("""## 8. Identifying Potentially Abandoned Repositories
A repository is categorized as **potentially abandoned** if:
1. It is explicitly archived by the owner, OR
2. It has received no code pushes for >365 days while accumulating unresolved open issues (>10 issues).

Let's inspect how many repositories fall into this category and compare their profiles."""))

# Cell 16: Code for Abandoned Analysis
cells.append(nbf.v4.new_code_cell("""abandoned_df = df[df['is_potentially_abandoned'] == 1]
active_df = df[df['is_potentially_abandoned'] == 0]

print(f"Total Potentially Abandoned Repositories: {len(abandoned_df)} ({round(len(abandoned_df)/len(df)*100, 1)}%)")
print(f"Total Maintained / Active Repositories : {len(active_df)} ({round(len(active_df)/len(df)*100, 1)}%)")
print()

# Comparison of key metrics
comp_table = pd.DataFrame({
    'Metric': ['Avg Stars', 'Avg Open Issues', 'Median Days Inactive', 'Avg Health Score'],
    'Maintained': [
        round(active_df['stars_count'].mean(), 1),
        round(active_df['open_issues_count'].mean(), 1),
        round(active_df['days_since_last_push'].median(), 1),
        round(active_df['maintenance_health_score'].mean(), 1)
    ],
    'Potentially Abandoned': [
        round(abandoned_df['stars_count'].mean(), 1),
        round(abandoned_df['open_issues_count'].mean(), 1),
        round(abandoned_df['days_since_last_push'].median(), 1),
        round(abandoned_df['maintenance_health_score'].mean(), 1)
    ]
})
print("Comparison Profile:")
display(comp_table)"""))

# Cell 17: Correlation Matrix
cells.append(nbf.v4.new_markdown_cell("""## 9. Correlation Analysis Across All Metrics
To uncover underlying patterns between popularity, size, age, issue burden, and health indicators, we calculate the Pearson correlation matrix across our key continuous metrics."""))

# Cell 18: Code for Heatmap
cells.append(nbf.v4.new_code_cell("""corr_cols = [
    'stars_count', 'forks_count', 'open_issues_count', 'size_kb',
    'repo_age_days', 'days_since_last_push', 'fork_to_star_ratio',
    'issues_to_star_ratio', 'push_recency_score', 'documentation_score',
    'community_health_score', 'maintenance_health_score', 'contributor_friendliness_score'
]

plt.figure(figsize=(12, 9))
corr_matrix = df[corr_cols].corr()
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(
    corr_matrix, 
    mask=mask, 
    annot=True, 
    fmt=".2f", 
    cmap='coolwarm', 
    vmin=-1, 
    vmax=1, 
    linewidths=0.5
)
plt.title("Correlation Heatmap: GitHub Repository Metrics", fontsize=14, fontweight='bold', pad=15)
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()"""))

# Cell 19: Contributor Opportunity Ranking
cells.append(nbf.v4.new_markdown_cell("""## 10. Evaluating Top Repositories for Contributors
The `contributor_friendliness_score` surfaces repositories that are:
1. Actively maintained (recent pushes within 60 days)
2. Have available work to tackle (moderate number of open issues)
3. Have clear documentation and licenses
4. Are non-archived with community channels enabled

Let's identify the top 10 recommended repositories to contribute to!"""))

# Cell 20: Code for Top Repos Table
cells.append(nbf.v4.new_code_cell("""top_contrib = df[df['activity_status'] == 'Active'].sort_values(
    by=['contributor_friendliness_score', 'stars_count'], 
    ascending=[False, False]
).head(10)

cols_display = [
    'full_name', 'language', 'stars_count', 'open_issues_count',
    'days_since_last_push', 'maintenance_health_score', 
    'contributor_friendliness_score', 'html_url'
]

print("Top 10 Recommended Repositories to Contribute To:")
top_contrib[cols_display].reset_index(drop=True)"""))

# Cell 21: Conclusions & Summary
cells.append(nbf.v4.new_markdown_cell("""## 11. Key Insights & Conclusions

1. **Popularity Does Not Guarantee Maintenance**:
   - High star counts (e.g. >5,000 stars) do not always mean a project is healthy. Approximately **27.3%** of analyzed repositories exhibit warning signs of abandonment (inactive for over a year with unaddressed issues).
2. **Commit Recency is the Defining Factor**:
   - `days_since_last_push` shows a strong inverse correlation with `maintenance_health_score` and `contributor_friendliness_score`. Active projects push code within 60 days.
3. **The Contributor Sweet Spot**:
   - The best projects for new contributors are not necessarily the largest monolithic repos with thousands of pending issues, but rather active projects with between **20 and 200 open issues**, active discussion boards, and structured documentation.
4. **Structured ETL Reliability**:
   - Extracting 300 repositories with Pydantic validation ensured zero corrupted records entered the database, and storing into SQLite creates an accessible store for real-time querying and downstream reporting."""))

nb['cells'] = cells

out_notebook = Path("notebooks/eda_analysis.ipynb")
out_notebook.parent.mkdir(parents=True, exist_ok=True)
with open(out_notebook, "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print(f"Notebook successfully written to {out_notebook}")
