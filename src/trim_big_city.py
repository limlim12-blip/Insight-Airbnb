from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from urllib.parse import quote

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://insideairbnb.com/get-the-data/"
MAX_LISTINGS_MB = 2.0
MAX_WORKERS = 16

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
}


def get_remote_size_mb(file_url: str) -> float | None:
    try:
        r = requests.head(file_url, headers=HEADERS, allow_redirects=True, timeout=15)
        if r.status_code == 200 and "Content-Length" in r.headers:
            return round(int(r.headers["Content-Length"]) / (1024 * 1024), 2)

        range_headers = {**HEADERS, "Range": "bytes=0-0"}
        r = requests.get(file_url, headers=range_headers, stream=True, timeout=15)
        r.close()
        content_range = r.headers.get("Content-Range", "")
        if "/" in content_range:
            total_bytes = int(content_range.split("/")[-1])
            return round(total_bytes / (1024 * 1024), 2)
    except Exception:
        return None
    return None


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = (
        here if os.path.isdir(os.path.join(here, "raw")) else os.path.dirname(here)
    )
    csv_path = os.path.join(repo_root, "raw", "cities.csv")
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    manual_hidden = set()
    if os.path.exists(csv_path):
        old_df = pd.read_csv(csv_path, encoding="utf-8-sig")
        mask = (
            old_df["hide"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["true", "1", "yes", "y"])
        )
        manual_hidden = set(old_df.loc[mask, "city"])

    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "lxml")

    # Start strictly below the "Data Downloads" heading
    downloads_heading = soup.find(
        lambda tag: (
            tag.name in ["h1", "h2", "h3"]
            and "Data Downloads" in tag.get_text(strip=True)
        )
    )
    city_headers = (
        downloads_heading.find_all_next("h3")
        if downloads_heading
        else soup.find_all("h3")
    )

    candidates = []
    for h3 in city_headers:
        city = h3.get_text(strip=True)
        table = h3.find_next("table")
        if not city or table is None:
            continue

        links = [quote(a["href"], safe=":/?=&") for a in table.find_all("a", href=True)]
        if len(links) >= 7 and links[0].endswith("/data/listings.csv.gz"):
            candidates.append(
                {
                    "city": city,
                    "listings_url": links[0],
                    "reviews_url": links[2],
                    "geojson_url": links[6],
                }
            )

    print(f"Checking HTTP HEAD sizes for {len(candidates)} cities...")

    kept_rows = []
    dropped_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_to_city = {
            pool.submit(get_remote_size_mb, item["listings_url"]): item
            for item in candidates
        }
        for future in as_completed(future_to_city):
            item = future_to_city[future]
            size_mb = future.result()

            if size_mb is None or size_mb > MAX_LISTINGS_MB:
                dropped_count += 1
                continue

            kept_rows.append(
                {
                    "city": item["city"],
                    "hide": item["city"] in manual_hidden,
                    "listings_mb": size_mb,
                    "listings_url": item["listings_url"],
                    "reviews_url": item["reviews_url"],
                    "geojson_url": item["geojson_url"],
                }
            )

    df = pd.DataFrame(kept_rows).sort_values(by="listings_mb", ascending=False)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(
        f"Done! Kept {len(df)} cities (<= {MAX_LISTINGS_MB} MB), "
        f"removed {dropped_count} oversized/unreachable cities -> {csv_path}"
    )


if __name__ == "__main__":
    main()
