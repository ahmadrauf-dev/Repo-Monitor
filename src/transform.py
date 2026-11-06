import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, ValidationError


class RepositoryRawSchema(BaseModel):
    """Pydantic model to validate incoming raw repository data from GitHub API."""
    id: int
    name: str
    full_name: str
    owner: Dict[str, Any]
    html_url: str
    description: Optional[str] = None
    language: Optional[str] = None
    stargazers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0
    watchers_count: int = 0
    size: int = 0
    created_at: str
    updated_at: str
    pushed_at: Optional[str] = None
    has_issues: bool = True
    has_projects: bool = False
    has_wiki: bool = False
    has_pages: bool = False
    has_discussions: bool = False
    archived: bool = False
    license: Optional[Dict[str, Any]] = None
    topics: List[str] = Field(default_factory=list)
    default_branch: Optional[str] = "main"


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 datetime string into timezone-aware UTC datetime."""
    if not dt_str:
        return None
    try:
        # Handles e.g. 2026-03-01T12:00:00Z
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def calculate_push_recency_score(days: float) -> float:
    """Calculate 0-100 score based on days since last push."""
    if pd.isna(days) or days < 0:
        return 0.0
    if days <= 7:
        return 100.0
    if days >= 365:
        return 0.0
    return round(max(0.0, 100.0 - ((days - 7.0) / (365.0 - 7.0)) * 100.0), 2)


def calculate_documentation_score(
    has_license: int,
    has_wiki: int,
    has_pages: int,
    desc_len: int,
    topics_cnt: int
) -> float:
    """Calculate 0-100 score assessing documentation completeness."""
    score = 0.0
    score += 35.0 if has_license == 1 else 0.0
    score += 25.0 if (has_wiki == 1 or has_pages == 1) else 0.0
    score += min(25.0, (desc_len / 40.0) * 25.0)
    score += min(15.0, topics_cnt * 3.0)
    return round(min(100.0, score), 2)


def calculate_community_health_score(
    has_issues: int,
    has_discussions: int,
    has_projects: int,
    fork_to_star_ratio: float
) -> float:
    """Calculate 0-100 score evaluating community infrastructure."""
    score = 0.0
    score += 25.0 if has_issues == 1 else 0.0
    score += 25.0 if has_discussions == 1 else 0.0
    score += 20.0 if has_projects == 1 else 0.0
    score += min(30.0, fork_to_star_ratio * 150.0)
    return round(min(100.0, score), 2)


def calculate_maintenance_health_score(
    is_archived: int,
    push_recency: float,
    doc_score: float,
    comm_score: float,
    issues_to_star: float
) -> float:
    """Calculate 0-100 composite repository maintenance health score."""
    if is_archived == 1:
        return 0.0
    issue_management = max(0.0, 100.0 - (issues_to_star * 400.0))
    health = (
        0.40 * push_recency +
        0.25 * doc_score +
        0.20 * comm_score +
        0.15 * issue_management
    )
    return round(min(100.0, max(0.0, health)), 2)


def calculate_contributor_friendliness_score(
    is_archived: int,
    push_recency: float,
    open_issues: int,
    doc_score: float,
    comm_score: float
) -> float:
    """Calculate 0-100 score indicating suitability for new contributors."""
    if is_archived == 1 or push_recency < 10.0:
        return 0.0
    
    # Repos with some issues are great to contribute to, but thousands may indicate burnout
    if open_issues <= 0:
        issue_work_factor = 5.0
    elif open_issues <= 150:
        issue_work_factor = min(35.0, (open_issues / 15.0) * 35.0)
    else:
        issue_work_factor = max(15.0, 35.0 - ((open_issues - 150) / 1000.0) * 20.0)

    score = (
        0.35 * push_recency +
        issue_work_factor +
        0.20 * doc_score +
        0.10 * comm_score
    )
    return round(min(100.0, max(0.0, score)), 2)


def classify_activity_status(days_since_push: float) -> str:
    """Categorize repository activity status based on push recency."""
    if pd.isna(days_since_push):
        return "Unknown"
    if days_since_push <= 60:
        return "Active"
    elif days_since_push <= 180:
        return "Moderate"
    elif days_since_push <= 365:
        return "Low Activity"
    else:
        return "Inactive"


def transform_repositories(raw_json_path: str = "data/raw/repositories.json") -> pd.DataFrame:
    """
    Load raw JSON repository data, validate with Pydantic, and transform into
    an analysis-ready pandas DataFrame with 27 rich metrics.
    """
    file_path = Path(raw_json_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Raw data file not found at {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        content = json.load(f)

    # Support both wrapped metadata format and legacy items-only format
    items = content.get("items", []) if isinstance(content, dict) else content
    category_name = content.get("metadata", {}).get("category_name", "General") if isinstance(content, dict) else "General"

    print(f"Loaded {len(items)} raw repository records from {raw_json_path}")
    print("Validating records using Pydantic schema...")

    validated_records = []
    validation_errors = 0

    for idx, item in enumerate(items):
        try:
            repo_schema = RepositoryRawSchema(**item)
            validated_records.append(repo_schema)
        except ValidationError as err:
            validation_errors += 1
            if validation_errors <= 3:
                print(f"Validation error in item {idx}: {err.errors()[0]}")

    print(f"Pydantic Validation complete: {len(validated_records)} valid records, {validation_errors} rejected.")

    now_utc = datetime.now(timezone.utc)
    rows = []

    for r in validated_records:
        created_dt = parse_iso_datetime(r.created_at)
        updated_dt = parse_iso_datetime(r.updated_at)
        pushed_dt = parse_iso_datetime(r.pushed_at)

        # Elapsed days calculations
        repo_age_days = round((now_utc - created_dt).total_seconds() / 86400.0, 1) if created_dt else np.nan
        days_since_update = round((now_utc - updated_dt).total_seconds() / 86400.0, 1) if updated_dt else np.nan
        days_since_push = round((now_utc - pushed_dt).total_seconds() / 86400.0, 1) if pushed_dt else np.nan

        # Boolean flags
        has_lic = 1 if (r.license and r.license.get("key") and r.license.get("key") != "other") else 0
        has_iss = 1 if r.has_issues else 0
        has_proj = 1 if r.has_projects else 0
        has_wik = 1 if r.has_wiki else 0
        has_pag = 1 if r.has_pages else 0
        has_disc = 1 if r.has_discussions else 0
        is_arch = 1 if r.archived else 0

        desc = r.description or ""
        desc_length = len(desc)
        topics_count = len(r.topics)

        # Ratios (Metric 18, 19, 20)
        fork_to_star = round(r.forks_count / (r.stargazers_count + 1), 4)
        issues_to_star = round(r.open_issues_count / (r.stargazers_count + 1), 4)
        issues_to_fork = round(r.open_issues_count / (r.forks_count + 1), 4)

        # Scored metrics (Metric 21, 22, 23, 24, 25)
        push_score = calculate_push_recency_score(days_since_push)
        doc_score = calculate_documentation_score(has_lic, has_wik, has_pag, desc_length, topics_count)
        comm_score = calculate_community_health_score(has_iss, has_disc, has_proj, fork_to_star)
        maint_score = calculate_maintenance_health_score(is_arch, push_score, doc_score, comm_score, issues_to_star)
        contrib_score = calculate_contributor_friendliness_score(is_arch, push_score, r.open_issues_count, doc_score, comm_score)

        # Status & Abandonment flag (Metric 26, 27)
        activity_status = classify_activity_status(days_since_push)
        is_abandoned = 1 if (is_arch == 1 or (days_since_push > 365 and r.open_issues_count > 10)) else 0

        owner_login = r.owner.get("login", "unknown") if isinstance(r.owner, dict) else str(r.owner)
        license_name = r.license.get("name", "None") if (r.license and isinstance(r.license, dict)) else "None"

        row = {
            # Identifying Metadata
            "repo_id": r.id,
            "name": r.name,
            "full_name": r.full_name,
            "owner": owner_login,
            "html_url": r.html_url,
            "description": desc,
            "language": r.language if r.language else "Unknown",
            "category": category_name,
            "license": license_name,
            "default_branch": r.default_branch or "main",
            "created_at": created_dt.isoformat() if created_dt else None,
            "updated_at": updated_dt.isoformat() if updated_dt else None,
            "pushed_at": pushed_dt.isoformat() if pushed_dt else None,

            # Raw Metrics (1 - 17)
            "stars_count": r.stargazers_count,
            "forks_count": r.forks_count,
            "open_issues_count": r.open_issues_count,
            "watchers_count": r.watchers_count,
            "size_kb": r.size,
            "repo_age_days": repo_age_days,
            "days_since_last_push": days_since_push,
            "days_since_last_update": days_since_update,
            "has_issues_enabled": has_iss,
            "has_projects_enabled": has_proj,
            "has_wiki_enabled": has_wik,
            "has_pages_enabled": has_pag,
            "has_discussions_enabled": has_disc,
            "has_license": has_lic,
            "is_archived": is_arch,
            "topics_count": topics_count,
            "description_length": desc_length,

            # Derived & Composite Metrics (18 - 27)
            "fork_to_star_ratio": fork_to_star,
            "issues_to_star_ratio": issues_to_star,
            "issues_to_fork_ratio": issues_to_fork,
            "push_recency_score": push_score,
            "documentation_score": doc_score,
            "community_health_score": comm_score,
            "maintenance_health_score": maint_score,
            "contributor_friendliness_score": contrib_score,
            "activity_status": activity_status,
            "is_potentially_abandoned": is_abandoned
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    print(f"Data transformed successfully into DataFrame shape: {df.shape}")
    print(f"Total metrics processed: 27 metrics (17 raw + 10 derived).")
    return df


if __name__ == "__main__":
    df = transform_repositories()
    print("\nDataFrame Preview:")
    print(df[["full_name", "language", "stars_count", "maintenance_health_score", "contributor_friendliness_score", "activity_status"]].head(10))