# Insight-Airbnb

## Project Description

This project is an interactive Streamlit web application designed for exploring and analyzing Airbnb listing data across multiple cities The application provides a comprehensive platform for users to gain insights into city-wide rental statistics and discover personalized listing recommendations. This project was inspired by [inside-airbnb](https://insideairbnb.com/get-the-data/).


Key features of the application include:

* **Interactive Map Visualization:** A dynamic map (using `folium` and `streamlit_folium`) displays the geographical distribution of listings, allowing users to select individual properties.
* **City-wide and Listing-specific Statistics:** The app presents aggregated statistical data for the selected city, which switches to a detailed view of an individual listing when selected on the map.
* **K-Nearest Neighbors (KNN) Recommender System:** The core feature is a recommendation engine that suggests similar listings for any viewed property.
* **Multi-City Support:** The application is built to load data and switch between different cities, provided the data is available for scraping.

## Tech Stack

The application is built primarily using Python and relies on the following key libraries:

 **Web Framework:** `streamlit` 
 **Data Analysis:** `pandas`, `numpy`, `polars` 
 **Machine Learning:** `scikit_learn` (for KNN model and preprocessing) 
 **Mapping/Geospatial:** `folium`, `streamlit_folium`, `geopandas` 
 **Web Scraping:** `beautifulsoup4`, `Requests` (implied by `scrape_data` function) 



## Installation and Setup
You can use this project directly at [Insight-airbnb](https://insight-airbnb-1.streamlit.app/).

To run this project locally, you need Python installed on your system.

### Step 1: Clone the repository

```bash
git clone <repository_url>
cd Insight-Airbnb-main
````

### Step 2: Install dependencies

All required libraries are listed in `requirements.txt`. You can install them using `pip`:

```bash
pip install -r requirements.txt
```

### Step 3: Run the application

Start the Streamlit application from the project root directory:

```bash
streamlit run src/app/main.py
```

The application will automatically open in your default web browser.
## How to Use the Project

1.  **View City Overview:** Upon launching, the application will display the interactive map and summary statistics for the default city (e.g., **Singapore, Singapore, Singapore**).
2.  **Interact with the Map:** Click on any listing marker on the map to select it. This will update the right panel with the selected listing's details, stats, and personalized recommendations.
3.  **Explore Recommendations:** Below the map, the **Recommendations** section will display similar listings, showing the price difference compared to your selected item. You can click the **"View"** button for a recommended listing to make it the new active listing, or click at the listings' name to redirect to [listing's Airbnb profile](https://www.airbnb.com/).
4.  **Change City:** Click the **"ALL KIND OF CITIES"** popover button in the header to view and select different cities from the available list.
5.  **More data visualization**: For a little more detail data exploration, you can check out **Map** at the **Menu** popover button

    
