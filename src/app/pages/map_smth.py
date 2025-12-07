from datetime import timedelta
import time
from load_data import load_review, load_listings, scrape_data
from Create_map import create_map, load_data
from display_stat import city_display_data, listings_display_data, neibourhood_display_data
import streamlit as st
from streamlit_folium import st_folium

def draw_map(m, fg, height= 680):
    start_time = time.perf_counter()
    st_data = st_folium(m, use_container_width=True,height=height, returned_objects=[], feature_group_to_add=fg, key = 'map')   
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"draw map executed in {elapsed_time:.4f} seconds.")
    return st_data

def clear_data():
    load_data.clear()
    load_review.clear()
    load_listings.clear()
    st.session_state['city'] = 'Singapore, Singapore, Singapore'


def change_city_button(city):
    load_data.clear()
    load_review.clear()
    load_listings.clear()
    st.session_state['city'] = city

# init page
if __name__ == "__main__":
    st.set_page_config(
        layout="wide",
        page_icon="🌏",
        initial_sidebar_state="collapsed",
    )

    # hide header bar
    # disable loading animation
    st.markdown(
        """
        <style>
        [data-testid='stHeaderActionElements'] { display: none; }
        [data-testid='stElementToolbar'] { display: none; }
        [data-baseweb="tab-panel"], * {
            opacity: 100% !important;
        }
        [data-testid="stHorizontalBlock"] {
                gap: 0;
                padding: 0;
                margin-right: 0;
        }
        [data-testid="stVerticalBlock"] {
                gap: 0; 
                padding: 0;
                border-radius: 0px;
                padding: 0;
                margin-bottom: 0px;
            }
        .block-container {
            padding-top: 0rem;
            padding-bottom: 0rem;
            padding-left: 0rem;
            padding-right: 0rem;
        }
        .st-key-1 {
            gap: 0; 
            background-color: #e6e6e6;
            border-radius: 0px;
            padding: 0px;
            text-align: center;
        }
        
        
        .st-key-stat_container {
            background-color: 	#fbf7ed;
            border-radius: 0px;
            padding: 0px;
            height: 100vh; 
            width: 100%;
        }
        div[data-testid="stVerticalBlock"]:has(div.review-marker):not(:has(div.parent)) {
                border-radius: 20px !important;
                padding-bottom: 1rem;
                padding-top: 1rem;
                padding-left: 1.25rem;
                padding-right: 3rem;
                margin-left: 27px;
                margin-right: 10px;
                width: 90%;
                margin-bottom: 10px;
                background-color: white;
                margin-top: 15px;
        }
        .st-emotion-cache-tn0cau {
            display: flex ;
            gap: 0rem;
            width: 100%;
            max-width: 100%;
            height: auto;
            min-width: 1rem;
            flex-flow: column;
            flex: 1 1 0%;
            -webkit-box-align: stretch;
            align-items: stretch;
            -webkit-box-pack: start;
        }
        p{
            font-family: Arial, Helvetica Neue, Helvetica, sans-serif;
            font-size: 12.4em;
            line-height: 1.3
        }

        .listings-name{
            text-align: center;
            font-weight: 700;
            margin-bottom: 0px !important;
            padding-left: 20px !important;
            padding-right: 20px !important;
        }
        .st-key-airbnb_detail * {
            color: black;
            border-radius: 20px !important;
            padding-left: 0px !important;
            margin-left: 0px;
        }    
        .st-key-airbnb_detail {
            border-radius: 20px !important;
            padding-left: 0px !important;
            margin-left: 0px;
        }
        .listings-host{
            padding-left: 0px !important;
            padding-bottom: 5px !important;
            margin-top: 5px !important;
            margin-bottom: 5px !important;
            color: black;
        }
        header {
            visibility: hidden;
        }
        .fullHeight {
            height: 100%; 
            width: 100%;
            overflow: auto; 
        }
        [class*="st-key-city_"]{
            margin-bottom: 7px;
            margin-top: 7px;

        }
        .review_section {
            min-height: 50px !important; 
            max-height: 500px !important; 
            padding-bottom: 1rem;
            padding-top: 1rem;
            padding-left: 1.25rem;
            padding-right: 3rem;
            background-color: white;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    if 'last_interaction' not in st.session_state:
        st.session_state['last_interaction'] = None
    if 'city' not in st.session_state:
        st.session_state['city'] = 'Singapore, Singapore, Singapore'
    if 'data' not in st.session_state:
        st.session_state['data'] = None


# load data
    df_reviews = load_review(st.session_state['city'])
    df_listings = load_listings(st.session_state['city'])
    try:
        df_scrape = scrape_data()
    except Exception:
        df_scrape = {"no_data":"no_data"}


    #place holder
    header = st.container()
    body = st.container()


    #implement
    with header:
        st.markdown("<div class='fullHeight'>", unsafe_allow_html=True)
        h1,h2 = st.columns([7.7,3.6])
        with h1:
            st.title(f":rainbow[THIS IS {st.session_state['city']}]")
        with h2:
            menu_col, cities_col = st.columns([2,2.5])
            with menu_col:
                st.space(10)
                with st.popover("ALL KIND OF CITIES"):
                    for city in df_scrape.keys():
                        st.button(city,on_click=change_city_button, key = f'city_{city}', args=[city])
            with cities_col:
                st.space(10)
                cola,colb = st.columns([2,2])
                with cola:
                    st.button("🔃",on_click=clear_data)
                with colb.container(horizontal_alignment= 'center'):
                    with st.popover("Menu"):
                        st.page_link("main.py", label="App")



    with body.container():
        with st.spinner("Creating map..."):
            m, fg = create_map(st.session_state['city']) 

        col1, col2 = st.columns([2,1])
        # render map
        with col1.container(height=680):
            map_data = draw_map(m, fg)
            if map_data and map_data != st.session_state['last_interaction']:
                st.session_state['data'] = map_data
                st.session_state['last_interaction'] = map_data
        st_data = st.session_state['data']
        # stat screen
        with col2:
            with st.container(border=True,height=680,key="stat_container"):
                    st.markdown('<div class="parent"/>', unsafe_allow_html=True)
                    if(not st_data):
                        city_display_data(df_listings)
                    elif isinstance(st_data, dict) :
                        neibourhood_display_data(listings = df_listings, st_data = st_data)
                    else:
                        listings_display_data(df_reviews=df_reviews,df_listings=df_listings,data=st_data)
    
    if st_data != st.session_state['data']:
        st.session_state['data'] = st_data
        st.rerun()