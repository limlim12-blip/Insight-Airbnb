from bs4 import BeautifulSoup
import requests
import pandas as pd
import os
from datetime import datetime
#date this to date that
sing_dates = [
    datetime.strptime(date, "%d %B, %Y").strftime("%Y-%m-%d") 
    for date in ["28 September, 2025", "25 June, 2025", "21 March, 2025", "28 December, 2024"]
]
bang_dates = [
    datetime.strptime(date, "%d %B, %Y").strftime("%Y-%m-%d") 
    for date in [ "24 June, 2025", "19 March, 2025", "25 December, 2024"]
]
tai_dates = [
    datetime.strptime(date, "%d %B, %Y").strftime("%Y-%m-%d") 
    for date in ["29 June, 2025", "28 March, 2025", "31 December, 2024"]
]
#files link tail = file dir
files = [   "data/listings.csv.gz",
            "data/calendar.csv.gz",
            "data/reviews.csv.gz",
            "visualisations/listings.csv",
            "visualisations/reviews.csv",
            "visualisations/neighbourhoods.csv",
            "visualisations/neighbourhoods.geojson"
        ]
#cities
CITIES = {
    "singapore": ("singapore/sg/singapore", sing_dates),
    "bangkok": ("thailand/central-thailand/bangkok", bang_dates),
    "taipei": ("taiwan/northern-taiwan/taipei", tai_dates),
}

#intuitive download file
def download_file(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    else:
        raise ValueError(f"{r.status_code}/{url}")

#get_file
def get_raw():
    for city, (path, dates) in CITIES.items():
        for date in dates:
            for file in files:
                url = f"https://data.insideairbnb.com/{path}/{date}/{file}"
                print(f"Downloading {url}")
                download_file(url, f"raw/{city}/{date}/{file}")
get_raw()