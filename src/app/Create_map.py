import json
import time
import branca
import folium
from folium.plugins import Fullscreen, HeatMap, MarkerCluster
import geopandas as gpd
import pandas as pd
import streamlit as st
from load_data import load_geojson, load_listings

VIEW_ZOOM = 16


@st.cache_resource(max_entries=1)
def load_data(city):
    start_time = time.perf_counter()
    df = load_listings(city)

    geojson_data, world_bounds = load_geojson(city)
    vignette_area = (
        world_bounds.geometry.buffer(0).union_all()
        - geojson_data.geometry.buffer(0).union_all()
    )

    # Heatmap
    heatmap_data = df[["latitude", "longitude", "price"]].dropna().copy()
    heatmap_data["price"] = pd.to_numeric(heatmap_data["price"], errors="coerce")
    heatmap_data = heatmap_data.dropna()
    price_min = heatmap_data["price"].quantile(0.02) if len(heatmap_data) else 0
    price_max = heatmap_data["price"].quantile(0.98) if len(heatmap_data) else 100

    # Colormap
    colors = ["blue", "cyan", "lime", "yellow", "red"]
    colormap = branca.colormap.LinearColormap(
        colors=colors,
        vmin=price_min,
        vmax=price_max,
    )
    colormap.caption = "House Price"

    # Markers data
    df = df.copy()
    df["id"] = df["id"].astype(str)
    df["price"] = df["price"].round(2).fillna("unknown").astype("string")

    gdf = gpd.GeoDataFrame(
        df[
            [
                "id",
                "host_id",
                "name",
                "host_name",
                "neighbourhood",
                "room_type",
                "price",
                "number_of_reviews",
            ]
        ],
        geometry=gpd.points_from_xy(df.longitude, df.latitude),
        crs="EPSG:4326",
    )

    print(f"load map data executed in {time.perf_counter() - start_time:.4f} seconds.")
    return geojson_data, vignette_area, heatmap_data, colormap, gdf


def style_function(feature):
    return {
        "fillColor": "#00000000",
        "color": "#3511FF63",
        "fillOpacity": 0.25,
        "opacity": 1,
        "weight": 1,
    }


def highlight_function(feature):
    return {
        "fillColor": "#ff0000",
        "color": "green",
        "weight": 3,
        "opacity": 1,
        "fillOpacity": 0.12,
    }


def vignette_style(feature):
    return {
        "fillColor": "#FFFFFFFF",
        "color": "#3511FF63",
        "fillOpacity": 0.7,
        "opacity": 1,
        "weight": 1,
    }


ROOM_STYLES = {
    "Private room": {"fillColor": "blue", "color": "black", "weight": 0.3, "radius": 5},
    "Entire home/apt": {
        "fillColor": "purple",
        "color": "black",
        "weight": 0.3,
        "radius": 5,
    },
    "Hotel room": {"fillColor": "green", "color": "black", "weight": 0.3, "radius": 5},
    "Shared room": {"fillColor": "red", "color": "black", "weight": 0.3, "radius": 5},
}

ROOM_STYLES_HIGHLIGHT = {
    "Private room": {"fillColor": "blue", "color": "black", "weight": 1, "radius": 10},
    "Entire home/apt": {
        "fillColor": "purple",
        "color": "black",
        "weight": 1,
        "radius": 10,
    },
    "Hotel room": {"fillColor": "green", "color": "black", "weight": 1, "radius": 10},
    "Shared room": {"fillColor": "red", "color": "black", "weight": 1, "radius": 10},
}


def markers_style(feature):
    room_type = feature["properties"]["room_type"]
    return ROOM_STYLES.get(room_type, ROOM_STYLES["Private room"])


def marker_highlight(feature):
    room_type = feature["properties"]["room_type"]
    return ROOM_STYLES_HIGHLIGHT.get(room_type, ROOM_STYLES_HIGHLIGHT["Private room"])


MAP_CSS = """
    <style>
    .leaflet-container {
        font-size: 0.68rem !important;
    }
    .leaflet-tooltip {
        color: #222;
        border: 2px solid #ddd;
        border-radius: 10px;
    }
    .custom-tooltip {
        background-color: white !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        font-size: 11px !important;
        color: #333 !important;
        max-width: 280px !important;
        min-width: 180px !important;
        white-space: normal !important;
    }
    .custom-popup {
        max-width: 220px !important;
        min-width: 160px !important;
        padding: 4px !important;
        font-size: 11px !important;
    }
    .room-legend {
        position: fixed;
        bottom: 24px;
        left: 12px;
        z-index: 999;
        background: rgba(255, 255, 255, 0.92);
        padding: 8px 12px;
        border-radius: 8px;
        border: 1px solid #ccc;
        font-size: 11px;
        line-height: 1.5;
        color: #222;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
    }
    .room-legend span {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 6px;
        border: 1px solid #333;
        vertical-align: middle;
    }
    </style>
"""

ROOM_LEGEND_HTML = """
    <div class="room-legend">
        <b>Room Type</b><br>
        <span style="background:purple;"></span>Entire home/apt<br>
        <span style="background:blue;"></span>Private room<br>
        <span style="background:green;"></span>Hotel room<br>
        <span style="background:red;"></span>Shared room
    </div>
"""

if "data" not in st.session_state:
    st.session_state["data"] = None

POPUP_JS = """
    (feature, layer) => {
        var selectedId = __SELECTED_ID__;
        var label = `🏡 <b style="color: #2196F3;">${feature.properties.name}</b><br>
                     Host: ${feature.properties.host_name}<br>
                     Price: $${feature.properties.price}<br>
                     Reviews: ${feature.properties.number_of_reviews}`;

        layer.bindPopup(label, {
            opacity: 1,
            className: 'custom-popup',
            autoClose: true,
            closeButton: false
        });
        layer.bindTooltip(label, {
            permanent: false,
            direction: 'top',
            className: 'custom-tooltip',
            opacity: 1,
            offset: [0, -10],
            sticky: true
        });

        var originalStyle = Object.assign({}, layer.options);
        var highlightStyle = {
            fillColor: 'yellow',
            color: 'black',
            radius: 10,
            weight: 2,
            fillOpacity: 1
        };

        layer.on('popupclose', function(e) {
            this.setStyle(originalStyle);
        });
        layer.on('popupopen', function(e) {
            this.setStyle(highlightStyle);
            this.bringToFront();
        });

        layer.on('click', (event) => {
            L.DomEvent.stopPropagation(event);
            Streamlit.setComponentValue(String(feature.properties.id));
        });

        if (selectedId && String(feature.properties.id) === selectedId) {
            setTimeout(() => {
                var latlng = layer.getLatLng();
                var group = layer.__parent && layer.__parent._group;
                var map = layer._map || (group && group._map);
                if (!map) return;

                map.setView(latlng, __VIEW_ZOOM__, { animate: false });
                if (group) {
                    group.zoomToShowLayer(layer, () => {
                        layer.openPopup();
                    });
                } else {
                    layer.openPopup();
                }
            }, 250);
        }
    }
"""

NEIGHBOURHOOD_JS = """
    (feature, layer) => {
        var selectedNb = __SELECTED_NEIGHBOURHOOD__;
        var nbName = feature.properties.neighbourhood;
        var label = '<b style="color: #2196F3;">Neighbourhood: </b>' + nbName;

        layer.bindTooltip(label, {
            permanent: false,
            direction: 'top',
            className: 'custom-tooltip',
            opacity: 0.95,
            sticky: true
        });

        if (selectedNb && nbName === selectedNb) {
            layer.setStyle({
                fillColor: '#2196F3',
                color: '#0D47A1',
                weight: 3,
                fillOpacity: 0.18
            });
            setTimeout(() => {
                if (layer._map) {
                    layer._map.fitBounds(layer.getBounds(), { padding: [20, 20] });
                }
            }, 200);
        }

        layer.on('click', (event) => {
            L.DomEvent.stopPropagation(event);
            Streamlit.setComponentValue({
                Neighbourhood: nbName,
            });
        });
    }
"""


def setup_map(geojson_data):
    minx, miny, maxx, maxy = geojson_data.total_bounds
    bounds = [[miny - 0.1, minx - 0.1], [maxy + 0.1, maxx + 0.1]]
    m = folium.Map(
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        min_lat=miny - 0.1,
        min_lon=minx - 0.1,
        max_lat=maxy + 0.1,
        max_lon=maxx + 0.1,
        max_bounds=bounds,
        zoomDelta=0,
        zoomSnap=0.25,
        max_zoom=17,
        zoom_control=False,
        prefer_canvas=True,
    )
    m.get_root().header.add_child(folium.Element(MAP_CSS))
    m.get_root().html.add_child(folium.Element(ROOM_LEGEND_HTML))
    m.fit_bounds([[miny, minx], [maxy, maxx]])
    folium.LayerControl(collapsed=False, position="bottomright", draggable=True).add_to(
        m
    )
    Fullscreen(
        position="topright",
        title="Expand me",
        title_cancel="Exit me",
        force_separate_button=True,
    ).add_to(m)
    return m


def create_map(city):
    start_time = time.perf_counter()
    geojson_data, vignette_area, heatmap_data, colormap, gdf = load_data(city)

    current_data = st.session_state.get("data")
    if isinstance(current_data, dict):
        selected_neighbourhood = current_data.get("Neighbourhood", "")
        selected_listing_id = ""
    elif current_data is not None:
        selected_neighbourhood = ""
        selected_listing_id = str(current_data)
    else:
        selected_neighbourhood = ""
        selected_listing_id = ""

    m = setup_map(geojson_data)

    heatmap = folium.FeatureGroup(name="Price Heatmap", show=True)
    bounds = folium.FeatureGroup(name="Neighbourhoods", show=True)
    marker = folium.FeatureGroup(name="Listings", show=True)

    HeatMap(
        data=heatmap_data,
        name="House Price",
        blur=23,
        radius=30,
        min_opacity=0.2,
    ).add_to(heatmap)
    colormap.add_to(m)

    folium.GeoJson(
        vignette_area,
        style_function=vignette_style,
        name="Vignette Layer",
        control=False,
        overlay=False,
        on_each_feature=folium.JsCode(
            """
            (feature, layer) => {
                layer.on('click', (event) => {
                    Streamlit.setComponentValue(null);
                });
            }
            """
        ),
    ).add_to(bounds)

    nb_js = NEIGHBOURHOOD_JS.replace(
        "__SELECTED_NEIGHBOURHOOD__", json.dumps(selected_neighbourhood)
    )
    folium.GeoJson(
        geojson_data,
        style_function=style_function,
        highlight_function=highlight_function,
        name="GeoJSON Layer",
        zoom_on_click=False,
        control=False,
        overlay=False,
        on_each_feature=folium.JsCode(nb_js),
    ).add_to(bounds)

    marker_cluster = MarkerCluster(
        name="Airbnb Density",
        options={
            "max_cluster_radius": 60,
            "spiderfyOnMaxZoom": True,
            "removeOutsideVisibleBounds": True,
        },
        disableClusteringAtZoom=17,
    )
    popup_js = POPUP_JS.replace(
        "__SELECTED_ID__", json.dumps(selected_listing_id)
    ).replace("__VIEW_ZOOM__", str(VIEW_ZOOM))
    folium.GeoJson(
        gdf,
        name="Listings",
        style_function=markers_style,
        marker=folium.CircleMarker(fill_opacity=0.75, fill=True),
        zoom_on_click=False,
        highlight_function=marker_highlight,
        on_each_feature=folium.JsCode(popup_js),
    ).add_to(marker_cluster)
    marker_cluster.add_to(marker)

    print(f"create_map executed in {time.perf_counter() - start_time:.4f} seconds.")
    return m, [heatmap, bounds, marker]


create_map_1 = create_map
