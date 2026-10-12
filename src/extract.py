import requests
import json
from pathlib import Path

URL = "https://api.github.com/search/repositories"

params = {
    "q": "language:python",
    "sort": "stars",
    "order": "desc",
    "per_page": 10
}

response = requests.get(URL, params=params, timeout=30)
response.raise_for_status()

data = response.json()

# Create the raw data directory
output_dir = Path("data/raw")
output_dir.mkdir(parents=True, exist_ok=True)

# Save the original API response
output_file = output_dir / "repositories.json"

with output_file.open("w", encoding="utf-8") as file:
    json.dump(data, file, indent=4)

print(f"Extracted {len(data['items'])} repositories")
print(f"Raw data saved to {output_file}")