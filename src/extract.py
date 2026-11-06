import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import requests


CATEGORIES = {
    "1": {
        "key": "ai",
        "name": "Artificial Intelligence & Machine Learning",
        "query": "topic:machine-learning stars:>10",
        "description": "Repositories focused on machine learning algorithms, deep learning models, and AI tools."
    },
    "2": {
        "key": "data",
        "name": "Data Science & Analytics",
        "query": "topic:data-science stars:>10",
        "description": "Data analysis, scientific computing, visualization, and data engineering projects."
    },
    "3": {
        "key": "web",
        "name": "Web Development",
        "query": "topic:web stars:>10",
        "description": "Web frameworks, APIs, frontend libraries, and full-stack applications."
    },
    "4": {
        "key": "devops",
        "name": "DevOps & Cloud Infrastructure",
        "query": "topic:devops stars:>10",
        "description": "Infrastructure-as-code, containers, orchestration, and CI/CD automation."
    },
    "5": {
        "key": "mobile",
        "name": "Mobile App Development",
        "query": "topic:android stars:>10",
        "description": "Mobile applications, SDKs, and tooling for modern mobile platforms."
    },
    "6": {
        "key": "systems",
        "name": "Systems & High Performance (Rust)",
        "query": "language:rust stars:>20",
        "description": "Fast, memory-safe systems programming, tools, and libraries."
    },
    "7": {
        "key": "python",
        "name": "Python Ecosystem",
        "query": "language:python stars:>50",
        "description": "Top open-source Python libraries, utilities, and developer frameworks."
    },
    "8": {
        "key": "general",
        "name": "General Popular Open Source",
        "query": "stars:>100",
        "description": "Diverse collection of the most starred public open-source repositories."
    }
}

SEARCH_URL = "https://api.github.com/search/repositories"


def display_categories():
    """Print the available contribution categories."""
    print("\n" + "=" * 65)
    print(" GitHub Repository Monitor - Select Contribution Category")
    print("=" * 65)
    for num, cat in CATEGORIES.items():
        print(f" [{num}] {cat['name']}")
        print(f"     {cat['description']}")
    print("=" * 65)


def resolve_category(choice: str) -> dict:
    """Resolve category from a key or number string."""
    choice = str(choice).strip().lower()
    # Check numeric key
    if choice in CATEGORIES:
        return CATEGORIES[choice]
    # Check category key string
    for cat in CATEGORIES.values():
        if choice in (cat["key"].lower(), cat["name"].lower()):
            return cat
    # Default fallback
    return CATEGORIES["8"]


def prompt_user_category() -> dict:
    """Interactively prompt user to select a category if terminal is interactive."""
    display_categories()
    if sys.stdin.isatty():
        try:
            val = input("Enter choice [1-8] (default: 8): ").strip()
            return resolve_category(val if val else "8")
        except (KeyboardInterrupt, EOFError):
            print("\nDefaulting to [8] General Popular Open Source.")
            return CATEGORIES["8"]
    return CATEGORIES["8"]


def extract_repositories(
    category_info: dict,
    target_count: int = 300,
    output_path: str = "data/raw/repositories.json",
    token: str = None
) -> str:
    """
    Extract repositories from GitHub API with pagination and rate limit handling.
    Fetches up to `target_count` repositories (default: 300).
    """
    token = token or os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Repo-Monitor-ETL/1.0"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        print("Using GitHub API Token for authenticated requests.")
    else:
        print("No GitHub token found. Using unauthenticated requests (10 requests/min limit).")

    query = category_info["query"]
    per_page = 100
    # GitHub search returns at most 1000 results (10 pages)
    total_pages = min(10, (target_count + per_page - 1) // per_page)
    all_items = []

    print(f"\nStarting Extraction for Category: '{category_info['name']}'")
    print(f"Search Query: '{query}'")
    print(f"Target Count: {target_count} repos across up to {total_pages} pages.\n")

    for page in range(1, total_pages + 1):
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
            "page": page
        }

        while True:
            try:
                response = requests.get(SEARCH_URL, headers=headers, params=params, timeout=30)
                
                # Check for rate limit
                if response.status_code == 403 or response.status_code == 429:
                    reset_time = int(response.headers.get("x-ratelimit-reset", time.time() + 60))
                    sleep_duration = max(5, int(reset_time - time.time()) + 2)
                    print(f"Rate limit reached. Pausing for {sleep_duration} seconds until reset...")
                    time.sleep(sleep_duration)
                    continue

                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])
                all_items.extend(items)
                
                print(f"Page {page}/{total_pages} fetched: +{len(items)} repos (Total: {len(all_items)})")
                
                if len(items) < per_page or len(all_items) >= target_count:
                    break

                # Sleep briefly between requests to respect rate limits
                time.sleep(2.0)
                break

            except requests.RequestException as e:
                print(f"Error on page {page}: {e}. Retrying in 5 seconds...")
                time.sleep(5)

        if len(all_items) >= target_count:
            break

    
    all_items = all_items[:target_count]


    payload = {
        "metadata": {
            "category_key": category_info["key"],
            "category_name": category_info["name"],
            "query": query,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "total_extracted": len(all_items),
            "target_count": target_count
        },
        "items": all_items
    }

    # Save to output file
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"\nExtraction complete! Saved {len(all_items)} repositories to {output_path}")
    return str(out_file)


def main():
    parser = argparse.ArgumentParser(description="Extract GitHub repository data across categories.")
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Category number (1-8) or key (ai, data, web, devops, mobile, systems, python, general)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=300,
        help="Number of repositories to fetch (default: 300)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/raw/repositories.json",
        help="Output raw JSON file path"
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="GitHub Personal Access Token (optional)"
    )
    args = parser.parse_args()

    if args.category:
        category_info = resolve_category(args.category)
    else:
        category_info = prompt_user_category()

    extract_repositories(
        category_info=category_info,
        target_count=args.limit,
        output_path=args.output,
        token=args.token
    )


if __name__ == "__main__":
    main()