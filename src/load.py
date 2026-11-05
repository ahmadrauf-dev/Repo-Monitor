import sqlite3
from pathlib import Path
from typing import Optional
import pandas as pd


def load_data(
    df: pd.DataFrame,
    db_path: str = "data/processed/repositories.db",
    csv_path: str = "data/processed/repositories.csv"
) -> dict:
    """
    Load cleaned DataFrame into SQLite database and export as CSV.
    """
    
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    csv_file = Path(csv_path)
    csv_file.parent.mkdir(parents=True, exist_ok=True)

    
    conn = sqlite3.connect(str(db_file))
    try:
        # Write table
        df.to_sql("repositories", conn, if_exists="replace", index=False)
        
        # Create useful indexes for quick query filtering
        cursor = conn.cursor()
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_repo_id ON repositories(repo_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_language ON repositories(language);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity ON repositories(activity_status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_health ON repositories(maintenance_health_score);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contrib ON repositories(contributor_friendliness_score);")
        conn.commit()
    finally:
        conn.close()

    # 2. Export to CSV
    df.to_csv(str(csv_file), index=False, encoding="utf-8")

    print(f"Data successfully loaded into:")
    print(f" - SQLite Database: {db_path} (Table: repositories, {len(df)} rows)")
    print(f" - CSV File:        {csv_path} ({len(df)} rows)")

    return {
        "db_path": str(db_file),
        "csv_path": str(csv_file),
        "row_count": len(df)
    }


def load_from_db(
    db_path: str = "data/processed/repositories.db",
    query: Optional[str] = None
) -> pd.DataFrame:
    """
    Helper function to query repository data back from SQLite for EDA and reporting.
    """
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"Database file not found at {db_file}")

    sql_query = query or "SELECT * FROM repositories"
    conn = sqlite3.connect(str(db_file))
    try:
        df = pd.read_sql_query(sql_query, conn)
    finally:
        conn.close()
    return df


if __name__ == "__main__":
    from src.transform import transform_repositories
    transformed_df = transform_repositories()
    load_data(transformed_df)