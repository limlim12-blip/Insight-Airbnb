import time
from load_data import load_listings, load_geojson
import pandas as pd
import geopandas as gpd
import folium
import branca
from folium.plugins import HeatMap, MarkerCluster, Fullscreen, FastMarkerCluster
import streamlit as st
@st.cache_resource
def load_data(city):
    # get listings.csv singapore
    start_time = time.perf_counter()
    df = load_listings(city)
    
    # get singapore bounds
    geojson_data, world_bounds = load_geojson(city)
    vignette_area = world_bounds.geometry.buffer(0).union_all() -geojson_data.geometry.buffer(0).union_all()

    # heatmap
    heatmap_data = df[["latitude", "longitude", "price"]].dropna()
    heatmap_data['price'] = pd.to_numeric(heatmap_data['price'], errors='coerce')
    price_min = heatmap_data['price'].quantile(0.02)
    price_max = heatmap_data['price'].quantile(0.98)
    if len(heatmap_data['price']) == 0:
        price_min = 0
        price_max = 100

    # colormap 
    colors = ["blue",  "cyan",  "lime",  "yellow", "red"]
    colormap = branca.colormap.LinearColormap(
    colors=colors,
    vmin=price_min,
    vmax=price_max,
    )
    colormap.caption = 'House Price'

    # markers data
    df['price'] = df['price'].round(2).fillna('unknown').astype('string')


    gdf = gpd.GeoDataFrame(
        df[["id", "host_id", "name", "host_name", "neighbourhood", 'room_type', "price", "number_of_reviews"]], 
        geometry=gpd.points_from_xy(df.longitude, df.latitude),
        crs="EPSG:4326"
    )

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"load map data executed in {elapsed_time:.4f} seconds.")
    return geojson_data, vignette_area, heatmap_data, colormap, gdf



#!style func
def style_function(feature):
    return {'fillColor': "#00000000", 'color': "#3511FF63", 'fillOpacity': 0.3, 'opacity': 1, 'weight': 1}
def highlight_function(feature):
    return {'fillColor': '#ff0000', 'color': 'green', 'weight': 4, 'opacity': 1, 'fillOpacity': 0.1}
def vignette_style(feature):
    return {'fillColor': "#FFFFFFFF", 'color': "#3511FF63", 'fillOpacity': 0.7, 'opacity': 1, 'weight': 1}
#room_type_style
ROOM_STYLES = {
    'Private room': {'fillColor': 'blue', 'color': 'black', 'weight': 0.2, 'radius': 4},
    'Entire home/apt': {'fillColor': 'purple', 'color': 'black', 'weight': 0.2, 'radius': 4},
    'Hotel room': {'fillColor': 'green', 'color': 'black', 'weight': 0.2, 'radius': 4},
    'Shared room': {'fillColor': 'red', 'color': 'black', 'weight': 0.2, 'radius': 4}
}
ROOM_STYLES_HIGHLIGHT = {
    'Private room': {'fillColor': 'blue', 'color': 'black', 'weight': 1, 'radius': 10},
    'Entire home/apt': {'fillColor': 'purple', 'color': 'black', 'weight': 1, 'radius': 10},
    'Hotel room': {'fillColor': 'green', 'color': 'black', 'weight': 1, 'radius': 10},
    'Shared room': {'fillColor': 'red', 'color': 'black', 'weight': 1, 'radius': 10}
}
def markers_style(feature):
    room_type = feature['properties']['room_type']
    style = ROOM_STYLES.get(room_type, ROOM_STYLES['Private room'])
    return style
def marker_highlight(feature):
    room_type = feature['properties']['room_type']
    return ROOM_STYLES_HIGHLIGHT.get(room_type, ROOM_STYLES_HIGHLIGHT['Private room'])



#!map
MAP_CSS = """
    <style>
    .leaflet-container {
        font-size: 0.55rem !important;
    }

    .leaflet-tooltip {
        color: #222;
        border: 2px solid #ddd;
        border-radius: 10px; 
    }

    .custom-tooltip {
        background-color: white !important;
        
        border-radius: 12px !important;
        
        padding: 13px 19px !important;
        
        font-size: 10px !important;
        color: #333 !important;
        
        max-width: 300px !important;
        min-width: 200px !important;
        white-space: normal !important;
    }

    .custom-popup {
        max-width: 200px !important;
        min-width: 150px !important;
        padding: 3px !important;
        font-size: 10px !important;

    }
    </style>
"""
if 'data' not in st.session_state:
    st.session_state['data'] = None
POPUP = """
    (feature, layer) => {
        var label = `🏡 <b style="color: #2196F3;">${feature.properties.name}</b><br>
                     Host: ${feature.properties.host_name}<br>
                     Price: $${feature.properties.price}<br>
                     Reviews: ${feature.properties.number_of_reviews}`;

        layer.bindPopup(label, { opacity: 1, className: 'custom-popup',autoClose: false, closeButton: false });
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
        if (String(feature.properties.id) == "REPLACE_ME") {
            setTimeout(() => {
                layer.openPopup();
            }, 100);
        }

        layer.on('popupclose', function(e) {
            this.setStyle(originalStyle);
        });
        layer.on('popupopen', function(e) {
            this.setStyle(highlightStyle);
            this.bringToFront();
        });

        layer.on("click", (event) => {
            Streamlit.setComponentValue(feature.properties.id);
        });
    }
"""
#! 1
def setup_map(geojson_data):
    minx, miny, maxx, maxy = geojson_data.total_bounds
    bounds = [[miny-0.1, minx-0.1], [maxy+0.1, maxx+0.1]]
    m = folium.Map(
                tiles="Cartodb Positron",
                min_lat=miny-0.1,
                min_lon=minx-0.1,
                max_lat=maxy+0.1,
                max_lon=maxx+0.1,
                max_bounds=bounds,
                zoomDelta=0, 
                zoomSnap=0.25,
                max_zoom=16,
                zoom_control=False,
                prefer_canvas=True,
            )
    m.get_root().header.add_child(folium.Element(MAP_CSS))
    m.fit_bounds([[miny, minx], [maxy, maxx]])
    folium.LayerControl(collapsed=False, position='bottomright',draggable=True).add_to(m)
    Fullscreen(
        position="topright", title="Expand me", title_cancel="Exit me", force_separate_button=True
    ).add_to(m)
    return m


def create_map_1(city):
    start_time = time.perf_counter()
    geojson_data, vignette_area, _, _, gdf = load_data(city)

    m = setup_map(geojson_data)

    # Create feature groups
    bounds = folium.FeatureGroup(name="bounds")
    marker = folium.FeatureGroup(name="marker")

    # Add bounds layers
    folium.GeoJson(
        vignette_area, style_function=vignette_style, name='Vignette Layer', control=False,overlay=False,
        on_each_feature= folium.JsCode(   
            """
                (feature, layer) => {
                    layer.on("click", (event) => {
                        Streamlit.setComponentValue(null);
                    });
                }
            """
        )
    ).add_to(bounds)
    folium.GeoJson(
        geojson_data, style_function=style_function, highlight_function=highlight_function, name='GeoJSON Layer', zoom_on_click=True, control=False,overlay=False,
    ).add_to(bounds)

    # Add markers
    folium.GeoJson(
        gdf,
        zoom_on_click=True,
        name="Listings",
        style_function=markers_style,
        marker=folium.CircleMarker(fill_opacity=0.7, fill=True),
        on_each_feature= folium.JsCode(POPUP.replace("REPLACE_ME", f"{st.session_state['data']}"))
    ).add_to(marker)

    # Add plugins
    
    elapsed_time = time.perf_counter() - start_time
    print(f"create_map_1 executed in {elapsed_time:.4f} seconds.")
    return m, [bounds, marker]


#! 2
def create_map(city):
    start_time = time.perf_counter()
    geojson_data, vignette_area, heatmap_data, colormap,gdf = load_data(city)

    minx, miny, maxx, maxy = geojson_data.total_bounds
    bounds = [[miny-0.1, minx-0.1], [maxy+0.1, maxx+0.1]]
    # setup map
    m= setup_map(geojson_data)

    marker = folium.FeatureGroup(name="marker")
    heatmap = folium.FeatureGroup(name="heatmap")
    bounds = folium.FeatureGroup(name="bounds")

    # heatmap + colormap
    HeatMap(data=heatmap_data, name='House Price', blur=23, radius=30, min_opacity=0.2).add_to(heatmap)
    colormap.add_to(m)

    # bounds 
    folium.GeoJson(
        vignette_area, style_function=vignette_style, name='Vignette Layer', control=False,overlay=False,
        on_each_feature= folium.JsCode(   
            """
                (feature, layer) => {
                    layer.on("click", (event) => {
                        Streamlit.setComponentValue(null);
                    });
                }
            """
        )
    ).add_to(bounds)
    folium.GeoJson(
        geojson_data, style_function=style_function, highlight_function=highlight_function, name='GeoJSON Layer', zoom_on_click=True, control=False,overlay=False,
        on_each_feature= folium.JsCode(   
        """
            (feature, layer) => {
                var label = '<b style="color: #2196F3;">Neighbourhood: </b>' + feature.properties.neighbourhood; 
                    layer.bindPopup(label);
                layer.on("click", (event) => {
                    Streamlit.setComponentValue({
                        Neighbourhood: feature.properties.neighbourhood,
                    });
                 });
            }
            
        """
        )

    ).add_to(bounds)
    

    # markers
    marker_cluster = MarkerCluster(
        name="Airbnb Density",options={'max_cluster_radius': 60,'spiderfyOnMaxZoom': True,'removeOutsideVisibleBounds': True}, disableClusteringAtZoom=17
    )
    folium.GeoJson(
        gdf,
        name="Listings",
        style_function= markers_style,
        marker = folium.CircleMarker(fill_opacity=0.7, fill= True),
        zoom_on_click= True,
        highlight_function = marker_highlight,
        #! code lấy từ streamlit-folium
        on_each_feature= folium.JsCode(POPUP)
    ).add_to(marker_cluster)
    marker_cluster.add_to(marker)

    

    # plugins
    m.fit_bounds([[miny, minx], [maxy, maxx]])
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"create map executed in {elapsed_time:.4f} seconds.")
    fg = [heatmap, bounds, marker]
    return m, fg