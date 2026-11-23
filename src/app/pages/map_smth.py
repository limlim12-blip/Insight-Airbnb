import time
import streamlit as st
from streamlit_folium import st_folium

from Create_map import create_map, load_data
from display_stat import (
    city_display_data,
    listings_display_data,
    neibourhood_display_data,
)
from load_data import load_listings, load_review, scrape_data


def draw_map(m, fg, height=750):
    start_time = time.perf_counter()
    st_data = st_folium(
        m,
        use_container_width=True,
        height=height,
        returned_objects=[],
        feature_group_to_add=fg,
        key="map",
    )
    print(f"draw map executed in {time.perf_counter() - start_time:.4f} seconds.")
    return st_data


def clear_data():
    load_data.clear()
    load_review.clear()
    load_listings.clear()
    st.session_state["city"] = "Singapore, Singapore, Singapore"
    st.session_state["data"] = None
    st.session_state["last_interaction"] = None


def change_city_button(city):
    load_data.clear()
    load_review.clear()
    load_listings.clear()
    st.session_state["city"] = city
    st.session_state["data"] = None
    st.session_state["last_interaction"] = None


if __name__ == "__main__":
    try:
        st.set_page_config(
            layout="wide",
            page_title="Insight Airbnb - Full Map",
            page_icon="🌏",
            initial_sidebar_state="collapsed",
        )

        st.markdown(
            """
            <style>
            [data-testid='stHeaderActionElements'] { display: none; }
            [data-testid='stElementToolbar'] { display: none; }
            header[data-testid="stHeader"] {
                background: transparent;
                height: 0rem;
            }
            .block-container {
                padding: 0.6rem 1.1rem 1rem 1.1rem !important;
                max-width: 100% !important;
            }
            [data-testid="stHorizontalBlock"] {
                gap: 0.75rem;
            }
            .stMarkdown h2, .stMarkdown h3 {
                margin: 0 !important;
                padding: 0.15rem 0 !important;
                line-height: 1.25 !important;
            }
            .st-key-1 {
                background-color: #e6e6e6;
                border-radius: 8px;
                padding: 0.45rem 0.75rem;
                text-align: center;
            }
            .st-key-1 h3 {
                font-size: clamp(1.1rem, 1.7vw, 1.75rem) !important;
            }
            .st-key-stat_container {
                background-color: #fbf7ed;
                border-radius: 8px;
                padding: 0.5rem;
                height: 82vh !important;
                min-height: 480px !important;
                overflow-y: auto !important;
                width: 100%;
            }
            .st-key-map_container {
                height: 82vh !important;
                min-height: 480px !important;
                overflow: hidden !important;
                padding: 0 !important;
            }
            .st-key-map_container iframe {
                height: 82vh !important;
                min-height: 480px !important;
            }
            div[data-testid="stVerticalBlock"]:has(div.review-marker):not(:has(div.parent)) {
                border-radius: 16px !important;
                padding: 1rem 1.25rem;
                margin: 0.75rem auto;
                width: 95%;
                background-color: white;
            }
            .listings-name {
                text-align: center;
                font-weight: 700;
                font-size: clamp(1.05rem, 1.5vw, 1.45rem) !important;
                margin-bottom: 0px !important;
                padding: 0 0.75rem !important;
            }
            .st-key-airbnb_detail * {
                color: black;
            }
            .listings-host {
                padding: 0 0 4px 0 !important;
                margin: 4px 0 !important;
                color: black;
            }
            [class*="st-key-city_"] {
                margin: 4px 0;
            }
            button[kind="secondary"], button[data-testid="stPopoverButton"] {
                white-space: nowrap !important;
            }
            @media (max-width: 992px) {
                .st-key-stat_container, .st-key-map_container, .st-key-map_container iframe {
                    height: 55vh !important;
                    min-height: 360px !important;
                }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        if "last_interaction" not in st.session_state:
            st.session_state["last_interaction"] = None
        if "city" not in st.session_state:
            st.session_state["city"] = "Singapore, Singapore, Singapore"
        if "data" not in st.session_state:
            st.session_state["data"] = None

        df_reviews = load_review(st.session_state["city"])
        df_listings = load_listings(st.session_state["city"])
        try:
            df_scrape = scrape_data()
        except Exception:
            df_scrape = {"Singapore, Singapore, Singapore": []}

        h1, h2 = st.columns([1.8, 1.2], vertical_alignment="center")
        with h1:
            st.markdown(f"## :rainbow[THIS IS {st.session_state['city']}]")
        with h2:
            menu_col, reset_col, page_col = st.columns([3.2, 1, 1.6])
            with menu_col:
                with st.popover("ALL KIND OF CITIES", use_container_width=True):
                    for city in df_scrape.keys():
                        st.button(
                            city,
                            on_click=change_city_button,
                            key=f"city_{city}",
                            args=[city],
                            use_container_width=True,
                        )
            with reset_col:
                st.button("🔃", on_click=clear_data, use_container_width=True)
            with page_col:
                with st.popover("Menu", use_container_width=True):
                    st.page_link("main.py", label="App")

        with st.spinner("Creating map..."):
            m, fg = create_map(st.session_state["city"])

        col1, col2 = st.columns([1.8, 1.2])
        with col1.container(key="map_container", border=True):
            map_data = draw_map(m, fg, 820)
            if (
                map_data is not None
                and map_data != st.session_state["last_interaction"]
            ):
                st.session_state["data"] = map_data
                st.session_state["last_interaction"] = map_data
                st.rerun()
        st_data = st.session_state["data"]

        with col2:
            with st.container(border=True, key="stat_container"):
                st.markdown('<div class="parent"/>', unsafe_allow_html=True)
                if not st_data:
                    city_display_data(df_listings)
                elif isinstance(st_data, dict):
                    neibourhood_display_data(listings=df_listings, st_data=st_data)
                else:
                    listings_display_data(
                        df_reviews=df_reviews,
                        df_listings=df_listings,
                        data=st_data,
                    )
    except Exception as e:
        st.error("🚨 An unexpected error")
        st.code(f"{e}", language="text")
        time.sleep(1)
