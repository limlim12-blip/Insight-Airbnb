import os
import time
import hashlib
from urllib.parse import quote

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import ticker
import pandas as pd
import polars as pl
import requests
import streamlit as st
from bs4 import BeautifulSoup

url = "https://insideairbnb.com/get-the-data/"
script_dir = os.path.dirname(os.path.abspath(__file__))
cities_csv_path = os.path.join(script_dir, "../../raw/cities.csv")
file_path = os.path.join(script_dir, "../../raw/currency.csv")
currency_csv = pd.read_csv(file_path)

LARGE_CITY = [
    "Paris, Île-de-France, France",
    "New Zealand",
    "London, England, United Kingdom",
    "Rome, Lazio, Italy",
    "Ireland",
    "Los Angeles, California, United States",
    "Lisbon, Lisbon, Portugal",
    "Hawaii, Hawaii, United States",
    "Sicily, Sicilia, Italy",
]

DIRECT_FALLBACK_URLS = {
    "Bangkok, Central Thailand, Thailand": {
        "listings": "https://data.insideairbnb.com/thailand/central-thailand/bangkok/2025-06-24/data/listings.csv.gz",
        "reviews": "https://data.insideairbnb.com/thailand/central-thailand/bangkok/2025-06-24/data/reviews.csv.gz",
        "geojson": "https://data.insideairbnb.com/thailand/central-thailand/bangkok/2025-06-24/visualisations/neighbourhoods.geojson",
    },
    "Taipei, Northern Taiwan, Taiwan": {
        "listings": "https://data.insideairbnb.com/taiwan/northern-taiwan/taipei/2025-06-29/data/listings.csv.gz",
        "reviews": "https://data.insideairbnb.com/taiwan/northern-taiwan/taipei/2025-06-29/data/reviews.csv.gz",
        "geojson": "https://data.insideairbnb.com/taiwan/northern-taiwan/taipei/2025-06-29/visualisations/neighbourhoods.geojson",
    },
    "Singapore, Singapore, Singapore": {
        "listings": "https://data.insideairbnb.com/singapore/sg/singapore/2025-09-28/data/listings.csv.gz",
        "reviews": "https://data.insideairbnb.com/singapore/sg/singapore/2025-09-28/data/reviews.csv.gz",
        "geojson": "https://data.insideairbnb.com/singapore/sg/singapore/2025-09-28/visualisations/neighbourhoods.geojson",
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
}


@st.cache_data(ttl=86400)
def scrape_data():
    if os.path.exists(cities_csv_path):
        df = pd.read_csv(cities_csv_path, encoding="utf-8-sig")
        hidden_mask = (
            df["hide"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["true", "1", "yes", "y"])
        )
        visible = df.loc[~hidden_mask]
        return {
            row["city"]: [
                row["listings_url"],
                "",
                row["reviews_url"],
                "",
                "",
                "",
                row["geojson_url"],
            ]
            for _, row in visible.iterrows()
        }

    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "lxml")
    all_cities_data = {}
    for city in soup.find_all("h3"):
        city_name = city.get_text(strip=True)
        if not city_name or city_name in LARGE_CITY:
            continue
        table = city.find_next("table")
        if table is None:
            continue
        links = [
            quote(link["href"], safe=":/?=&") for link in table.find_all("a", href=True)
        ]
        if len(links) >= 7:
            all_cities_data[city_name] = links
    return all_cities_data


@st.cache_data(ttl=86400)
def fetch_to_tmp(file_url: str) -> str:
    if os.path.exists(file_url):
        return file_url
    cache_dir = "/tmp/insight_airbnb_cache"
    os.makedirs(cache_dir, exist_ok=True)
    digest = hashlib.md5(file_url.encode()).hexdigest()[:12]
    filename = os.path.basename(file_url.split("?")[0])
    local_path = os.path.join(cache_dir, f"{digest}_{filename}")
    if not os.path.exists(local_path):
        with requests.get(file_url, headers=HEADERS, stream=True, timeout=60) as r:
            r.raise_for_status()
            tmp_path = local_path + ".tmp"
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
            os.replace(tmp_path, local_path)
    return local_path


def _resolve_url(city: str, link_idx: int, kind: str) -> str:
    try:
        return scrape_data()[city][link_idx]
    except Exception:
        fallback = DIRECT_FALLBACK_URLS.get(
            city, DIRECT_FALLBACK_URLS["Singapore, Singapore, Singapore"]
        )
        return fallback[kind]


@st.cache_data
def load_review(city="Singapore, Singapore, Singapore"):
    start_time = time.perf_counter()
    remote_url = _resolve_url(city, 2, "reviews")
    local_path = fetch_to_tmp(remote_url)

    pf = pl.scan_csv(local_path, low_memory=False)
    pf = pf.with_columns(
        pl.col("comments").str.replace_all("<br/>", "\n"),
    ).reverse()
    df = pf.collect().to_pandas()
    print(f"reviews executed in {time.perf_counter() - start_time:.4f} seconds.")
    return df


@st.cache_data
def load_listings(city="Singapore, Singapore, Singapore"):
    start_time = time.perf_counter()
    country = city.split(",")[0].strip().upper()
    try:
        exchange_rate = currency_csv.loc[
            currency_csv["Country"] == country, "Exchange_Rate"
        ].item()
    except Exception:
        exchange_rate = 1

    remote_url = _resolve_url(city, 0, "listings")
    local_path = fetch_to_tmp(remote_url)

    pf = pl.scan_csv(
        local_path, schema_overrides={"id": pl.String, "license": pl.String}
    )
    pf = (
        pf.with_columns(
            pl.col("id")
            .cast(pl.String)
            .str.strip_chars()
            .str.replace(r"\.0$", "")
            .alias("id"),
            pl.col("price").str.replace_all(r"[\$,]", "").alias("price"),
        )
        .with_columns(pl.col("price").cast(pl.Float64, strict=False).alias("price"))
        .with_columns((pl.col("price") / exchange_rate).alias("price"))
        .sort("price", nulls_last=True)
    )
    df = pf.collect().to_pandas()
    df["id"] = df["id"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    print(f"listings executed in {time.perf_counter() - start_time:.4f} seconds.")
    return df


@st.cache_data
def load_geojson(city="Singapore, Singapore, Singapore"):
    start_time = time.perf_counter()
    remote_url = _resolve_url(city, 6, "geojson")
    local_path = fetch_to_tmp(remote_url)

    geojson_data = gpd.read_file(local_path, encoding="utf-8")
    world_bounds = gpd.read_file(
        os.path.join(script_dir, "../../world.geojson"), encoding="utf-8"
    )
    print(f"geojson executed in {time.perf_counter() - start_time:.4f} seconds.")
    return geojson_data, world_bounds


@st.cache_resource
def load_fig(listings):
    # fig1
    counts = listings["room_type"].value_counts()[::-1]
    room_type = listings["room_type"].unique()[::-1]
    bar_colors = {
        "Private room": "blue",
        "Entire home/apt": "purple",
        "Shared room": "red",
        "Hotel room": "green",
    }
    colors = [bar_colors[i] for i in counts.index]
    fig1, ax1 = plt.subplots(figsize=(3, 4.5))
    fig1.patch.set_facecolor("#fbf7ed")
    ax1.set_facecolor("#fbf7ed")
    ax1.barh(room_type, counts, height=0.6, color=colors)
    ax1.tick_params(axis="y", labelleft=False)
    ax1.set_xlabel(
        "listings",
        fontdict={"family": "serif", "color": "darkblue", "size": 18},
        labelpad=10,
    )
    for i, room in enumerate(room_type):
        ax1.text(
            sum(counts) / len(counts) / 10,
            i + 0.5,
            room,
            horizontalalignment="left",
            verticalalignment="center",
            fontsize=17,
            fontweight=400,
        )

    plt.xticks(fontsize=12)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # % of room_type
    room_type_counts = listings["room_type"].value_counts()
    room_type_counts = room_type_counts.rename(
        index={"Entire home/apt": "Entire homes/Apartments"}
    )

    # top host table
    table_listings = listings[["host_name", "room_type", "host_total_listings_count"]]
    table_listings = pd.get_dummies(
        table_listings, columns=["room_type"], prefix="", prefix_sep=""
    )
    table_listings = table_listings.groupby("host_name")
    top_host_table = table_listings.sum()
    top_host_table["host_total_listings_count"] = table_listings.count()[
        "host_total_listings_count"
    ]
    top_host_table = top_host_table.sort_values(
        by="host_total_listings_count", ascending=False
    ).head(100)
    top_host_table.rename(
        columns={"host_total_listings_count": "total_listings"}, inplace=True
    )
    top_host_table.reset_index(inplace=True, col_level=0)

    cols = top_host_table.columns.to_list()
    top_host_table = top_host_table[[cols[0]] + cols[1:][::-1]]

    # fig 2
    fig2_tick = [
        "0",
        "1-30",
        "31-60",
        "61-90",
        "91-120",
        "121-150",
        "151-180",
        "181-210",
        "211-240",
        "241-255+",
    ]
    bins = [-1, 0, 30, 60, 90, 120, 150, 180, 210, 240, 10 * 1000]
    binned_data = pd.Series(
        pd.cut(listings["estimated_occupancy_l365d"], bins=bins, labels=fig2_tick)
    )
    binned_data = binned_data.value_counts()
    fig2, ax2 = plt.subplots(figsize=(12.5, 4))
    bar2 = ax2.bar(fig2_tick, binned_data, width=0.8)
    ax2.margins(0.03)
    ax2.yaxis.set_major_locator(ticker.MultipleLocator(base=1000))
    ax2.tick_params(axis="y", left=False)
    ax2.set_xlabel(
        "occupancy (last 12 months)",
        fontdict={"family": "serif", "color": "darkblue", "size": 20},
        labelpad=10,
    )
    ax2.set_ylabel(
        "listings",
        fontdict={"family": "serif", "color": "darkblue", "size": 20},
        labelpad=10,
    )
    ax2.tick_params(axis="x", labelsize=12)
    ax2.tick_params(axis="y", labelsize=14)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    fig2.patch.set_facecolor("#fbf7ed")
    ax2.set_facecolor("#fbf7ed")
    for bar in bar2:
        height = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            s=f"{height}",
            horizontalalignment="center",
            verticalalignment="bottom",
            fontsize=16,
            fontweight=400,
        )

    # fig3
    limit_litings_host = listings
    limit_litings_host.loc[
        listings["calculated_host_listings_count"] > 10,
        "calculated_host_listings_count",
    ] = 10
    fig3, ax3 = plt.subplots(figsize=(12.5, 4))
    data = limit_litings_host["calculated_host_listings_count"].value_counts()
    data_index = [item for item in range(1, 11) if item not in data.index]
    new_s = pd.Series(0, index=data_index)
    if not new_s.empty:
        data = pd.concat([data, new_s])[::-1]

    data.sort_index(inplace=True)
    bar3 = ax3.bar(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10+"], list(data))
    ax3.margins(0.03)
    ax3.yaxis.set_major_locator(ticker.MultipleLocator(base=1000))
    for bar in bar3:
        height = bar.get_height()
        ax3.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            s=f"{height}",
            horizontalalignment="center",
            verticalalignment="bottom",
            fontsize=16,
            fontweight=400,
        )
    ax3.set_xlabel(
        "listings per host",
        fontdict={"family": "serif", "color": "darkblue", "size": 18},
        labelpad=10,
    )
    ax3.set_ylabel(
        "listings",
        fontdict={"family": "serif", "color": "darkblue", "size": 18},
        labelpad=10,
    )
    ax3.tick_params(axis="x", labelsize=14)
    ax3.tick_params(axis="y", labelsize=16)
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)
    fig3.patch.set_facecolor("#fbf7ed")
    ax3.set_facecolor("#fbf7ed")

    # fig4
    limit_data = listings
    limit_data.loc[listings["minimum_nights"] > 35, "minimum_nights"] = 35
    data = limit_data["minimum_nights"].value_counts()

    data_index = [item for item in range(1, 36) if item not in data.index]
    new_row = pd.Series(0, index=data_index)
    if not new_row.empty:
        data = pd.concat([data, new_row])
    data.sort_index(inplace=True)
    fig4, ax4 = plt.subplots(figsize=(12.5, 5), dpi=300)
    bar4 = ax4.bar([str(i) for i in range(1, 35)] + ["35+"], list(data), width=0.6)
    ax4.margins(0.02)
    ax4.yaxis.set_major_locator(ticker.MultipleLocator(base=1000))
    ax4.set_xlabel(
        "listings per host",
        fontdict={"family": "serif", "color": "darkblue", "size": 18},
        labelpad=10,
    )
    ax4.set_ylabel(
        "listings",
        fontdict={"family": "serif", "color": "darkblue", "size": 18},
    )
    ax4.tick_params(axis="x", labelsize=12)
    ax4.tick_params(axis="y", labelsize=12)
    ax4.spines["top"].set_visible(False)
    ax4.spines["right"].set_visible(False)
    fig4.patch.set_facecolor("#fbf7ed")
    ax4.set_facecolor("#fbf7ed")
    xticks = ax4.get_xticklabels()
    for i in range(len(xticks) - 1):
        if data[int(xticks[i].get_text())] == 0:
            xticks[i].set_visible(False)
    for bar in bar4:
        height = bar.get_height()
        if height != 0:
            ax4.text(
                bar.get_x() + bar.get_width() / 2,
                height,
                s=f"{height}",
                horizontalalignment="center",
                verticalalignment="bottom",
                color="red",
                fontsize=14,
                fontweight=400,
            )
    ax4.axvline(x=28.5, linestyle="--", linewidth=2, dashes=(5, 2), color="red")
    ax4.text(
        x=28.5,
        y=data.max() // 2,
        s="STR Threshold",
        rotation=-90,
        fontsize=19,
        color="b",
    )
    return fig1, room_type_counts, top_host_table, fig2, fig3, fig4
