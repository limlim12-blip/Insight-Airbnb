from load_data import load_review, load_listings, scrape_data
import streamlit as st
from load_data import load_review, load_listings, scrape_data
from Create_map import create_map_1
from display_stat import city_display_data, listings_display_data
import streamlit as st
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import FunctionTransformer, Pipeline
from sklearn.impute import SimpleImputer
from pages.map_smth import draw_map, clear_data, change_city_button

@st.cache_resource
def train_recommender(data, n_neighbors = 4):
    def weight(x, factor):
        return x * factor
    features = ['price', 'latitude', 'longitude', 'room_type', 'amenities']
    X = data[features]
    
    numeric_transformer = Pipeline(steps=[  
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('weight', FunctionTransformer(weight, kw_args={'factor': 10}))
    ])
    
    roomtype_transformer = Pipeline(steps=[  
        ('onehot', OneHotEncoder(handle_unknown='ignore')),
        ('weight', FunctionTransformer(weight, kw_args={'factor': 20}))
    ])
    amenities_transformer = CountVectorizer(token_pattern=r'[^;]+', binary=True)
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, ['price', 'latitude', 'longitude']),
            ('room', roomtype_transformer, ['room_type']),
            ('amen', amenities_transformer, 'amenities'),
        ],
        remainder='drop'
    )
    
    model = Pipeline(steps=[('preprocessor', preprocessor),
                            ('knn', NearestNeighbors(n_neighbors= n_neighbors))])
    model.fit(X)
    return model

def update_state(st_data):
    st.session_state['data'] = st_data


if __name__ == "__main__":

    st.set_page_config(
        layout="wide",
        page_icon="🌏",
        initial_sidebar_state="collapsed",
    )

    if 'city' not in st.session_state:
        st.session_state['city'] = 'Singapore, Singapore, Singapore'
    if 'data' not in st.session_state:
        st.session_state['data'] = None
    if 'last_interaction' not in st.session_state:
        st.session_state['last_interaction'] = None
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
        [data-testid="stVerticalBlock"]:not(:has(div.recommendations)) {
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
        [data-testid="stMarkdownContainer"] {
            margin: 0px !important;
            padding: 0px !important;

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
            margin: 0px !important;
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
            st.header(f":rainbow[THIS IS {st.session_state['city']}]")
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
                        st.page_link("pages/map_smth.py", label="Map")



    with body.container():
        with st.spinner("Creating map..."):
            m, fg = create_map_1(st.session_state['city']) 

        col1, col2 = st.columns([1,1])
        # render map
        with col1.container(height=350):
            map_data = draw_map(m, fg, 350)
            if map_data != st.session_state['last_interaction']:
                st.session_state['data'] = map_data
                st.session_state['last_interaction'] = map_data
                st.rerun()
            st_data = st.session_state['data']
        # stat screen
        with col2:
            with st.container(border=True,height=350,key="stat_container"):
                    st.markdown('<div class="parent"/>', unsafe_allow_html=True)
                    if(not st_data):
                        city_display_data(df_listings)
                    elif df_listings['id'].isin([st_data]).any():
                        listings_display_data(df_reviews=df_reviews,df_listings=df_listings,data=st_data)
    

    st.space(10)
    model = train_recommender(df_listings,4)

    _, title, _= st.columns([0.1, 4, 0.1])
    _, col1, divider, col2, _ = st.columns([0.05, 0.8, 0.01, 2, 0.05])

    with col1:
        if  isinstance(st_data, str) and df_listings['id'].isin([st_data]).any():
            current_item = df_listings.loc[df_listings['id'].astype(str) == st_data].iloc[0]
        else:
            current_item = df_listings.iloc[[0]].iloc[0]
        
        st.subheader(f"**Viewing:** [{current_item['name']}](%s)" %current_item['listing_url'])
        st.space(5)
        image_html = f"""
            <style>
                .crop-image2 {{
                    width: 420px !important;
                    border: 0.5px solid black;
                    height: 200px !important;
                    object-fit: fill !important; 
                    border-radius: 8px !important;
                }}
            </style>
            <img src="{current_item['picture_url']}" class="crop-image2">
        """
        st.markdown(image_html, unsafe_allow_html=True)
        st.space(20)
        st.write(f"💰 **Price:** ${current_item['price'].round(2)}")
        st.write(f"⭐ **Rating:** {current_item['review_scores_rating']}")
        st.write(f"📍 **Location:** {current_item['neighbourhood']}")
        st.space('medium')


    with divider:
        st.space('medium')
        st.markdown(
                """
                <style>
                    .vertical-line {
                        border-left: 2px solid #A3A8B8; 
                        height: 300px; 
                        margin: auto;
                    }
                </style>
                <div class="vertical-line"></div>
                """,
                unsafe_allow_html=True
            )


    with col2:
        data = current_item[['price', 'latitude', 'longitude', 'review_scores_rating', 'room_type', 'amenities']].to_frame().T
        input = model.named_steps['preprocessor'].transform(data)
        distances, indices  = model.named_steps['knn'].kneighbors(input)
        
        rcm_idx = indices[0][1:]
        recommendations = df_listings.iloc[rcm_idx]
        
        rcm_cols = st.columns(3)
        for idx, col in enumerate(rcm_cols):
            rec = recommendations.iloc[idx]
            with col:
                with st.container(border=True):
                    st.markdown('<div class="recommendations"/>', unsafe_allow_html=True)
                    image_html = f"""
                        <style>
                            .crop-image {{
                                width: 340px !important;
                                height: 200px !important;
                                object-fit: fill !important; 
                                border-radius: 8px !important;
                                border: 0.5px solid black;
                            }}
                        </style>
                        <img src="{rec['picture_url']}" class="crop-image">
                    """
                    st.markdown(image_html, unsafe_allow_html=True)
                    st.write(f"**[{rec['name']}](%s)**" %rec['listing_url'])
                    
                    price_diff = rec['price'] - current_item['price']
                    if price_diff < 0:
                        st.markdown(f"**${rec['price'].round(2)}** (:green[{price_diff.round(2)}])")
                    else:
                        st.markdown(f"**${rec['price'].round(2)}** (:red[+{price_diff.round(2)}])")
                    
                    st.button("View", key=f"btn_{rec['id']}", on_click=update_state, args = (rec['id'],))