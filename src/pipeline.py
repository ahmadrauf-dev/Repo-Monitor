import argparse
import sys
import time
from pathlib import Path

# Add src/ to path if run directly
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from src.extract import CATEGORIES, extract_repositories, prompt_user_category, resolve_category
from src.transform import transform_repositories
from src.load import load_data


def run_pipeline(
    category_key: str = None,
    limit: int = 300,
    skip_extract: bool = False,
    token: str = None
):
    """
    Execute the full ETL Pipeline:
    1. Category Selection
    2. Extraction from GitHub API
    3. Pydantic validation & feature transformation (27 metrics)
    4. Loading into SQLite database and CSV
    """
    start_time = time.time()
    print("\n" + "=" * 70)
    print(" GITHUB REPOSITORY CONTRIBUTOR & HEALTH MONITOR - ETL PIPELINE")
    print("=" * 70)

    raw_json_path = "data/raw/repositories.json"

    # Step 1: Category Selection & Extraction
    if not skip_extract:
        if category_key:
            category_info = resolve_category(category_key)
        else:
            category_info = prompt_user_category()

        print(f"\n[STEP 1/3] Extracting repositories for category: {category_info['name']}")
        extract_repositories(
            category_info=category_info,
            target_count=limit,
            output_path=raw_json_path,
            token=token
        )
    else:
        print(f"\n[STEP 1/3] Skipping extraction. Using existing raw file: {raw_json_path}")

    # Step 2: Transformation & Pydantic Validation
    print(f"\n[STEP 2/3] Transforming and validating data with Pydantic & pandas...")
    df = transform_repositories(raw_json_path=raw_json_path)

    # Step 3: Loading to Database & CSV
    print(f"\n[STEP 3/3] Loading dataset into SQLite database and CSV file...")
    load_summary = load_data(df)

    elapsed_time = round(time.time() - start_time, 2)

    # Display Pipeline Summary
    print("\n" + "=" * 70)
    print(" ETL PIPELINE RUN SUMMARY")
    print("=" * 70)
    print(f"Total Repositories Processed : {len(df)}")
    print(f"Total Metrics Engineered     : 27 metrics")
    print(f"Database Destination        : {load_summary['db_path']} (Table: repositories)")
    print(f"CSV Destination             : {load_summary['csv_path']}")
    print(f"Total Execution Time        : {elapsed_time}s")
    print("-" * 70)

    print("\nActivity Breakdown:")
    for status, count in df["activity_status"].value_counts().items():
        pct = round(count / len(df) * 100, 1)
        print(f" - {status:<15}: {count:>4} repos ({pct:>4}%)")

    abandoned_count = int(df["is_potentially_abandoned"].sum())
    abandoned_pct = round(abandoned_count / len(df) * 100, 1)
    print(f" - Potentially Abandoned: {abandoned_count} repos ({abandoned_pct}%)")

    print("\nTop 5 Recommended Repositories to Contribute To:")
    print("-" * 70)
    top_candidates = df.sort_values(
        by=["contributor_friendliness_score", "stars_count"],
        ascending=[False, False]
    ).head(5)

    for _, row in top_candidates.iterrows():
        print(f" * {row['full_name']} ({row['language']})")
        print(f"   Stars: {row['stars_count']:,} | Issues: {row['open_issues_count']:,} | Health: {row['maintenance_health_score']}/100 | Contrib Score: {row['contributor_friendliness_score']}/100")
        print(f"   URL: {row['html_url']}")

    print("=" * 70 + "\n")
    return df


def main():
    parser = argparse.ArgumentParser(description="End-to-End GitHub Repository ETL Pipeline.")
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Category: 1-8 or key (ai, data, web, devops, mobile, systems, python, general)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=300,
        help="Number of repositories to process (default: 300)"
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip extraction step and process existing raw data"
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="GitHub Personal Access Token"
    )
    args = parser.parse_args()

    run_pipeline(
        category_key=args.category,
        limit=args.limit,
        skip_extract=args.skip_extract,
        token=args.token
    )


if __name__ == "__main__":
    main()