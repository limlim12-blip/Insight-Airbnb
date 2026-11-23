import html
import time

import pandas as pd
import streamlit as st
from Create_map import create_map, load_data
from display_stat import (
    city_display_data,
    listings_display_data,
    neibourhood_display_data,
)
from load_data import load_listings, load_review, scrape_data
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.impute import SimpleImputer
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import FunctionTransformer, Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from streamlit_folium import st_folium

try:
    from streamlit_js_eval import streamlit_js_eval
except ImportError:
    streamlit_js_eval = None

DEFAULT_CITY = "Singapore, Singapore, Singapore"
MAIN_VH_RATIO = 0.84
MAIN_MIN, MAIN_MAX = 460, 1100
FALLBACK_MAIN = 720


def get_main_height():
    """Pixel height of the map/stats row, based on the browser window."""
    vh = None
    if streamlit_js_eval is not None:
        vh = streamlit_js_eval(js_expressions="window.innerHeight", key="viewport_h")
    if not vh:
        return FALLBACK_MAIN
    return int(min(MAIN_MAX, max(MAIN_MIN, int(vh) * MAIN_VH_RATIO)))


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
    st.session_state["city"] = DEFAULT_CITY
    st.session_state["data"] = None
    st.session_state["last_interaction"] = None


def change_city_button(city):
    load_data.clear()
    load_review.clear()
    load_listings.clear()
    st.session_state["city"] = city
    st.session_state["data"] = None
    st.session_state["last_interaction"] = None


@st.cache_resource
def train_recommender(data, n_neighbors=4):
    def weight(x, factor):
        return x * factor

    features = ["price", "latitude", "longitude", "room_type", "amenities"]
    X = data[features]

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="mean")),
            ("scaler", StandardScaler()),
            ("weight", FunctionTransformer(weight, kw_args={"factor": 10})),
        ]
    )

    roomtype_transformer = Pipeline(
        steps=[
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ("weight", FunctionTransformer(weight, kw_args={"factor": 20})),
        ]
    )
    amenities_transformer = CountVectorizer(token_pattern=r"[^;]+", binary=True)
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, ["price", "latitude", "longitude"]),
            ("room", roomtype_transformer, ["room_type"]),
            ("amen", amenities_transformer, "amenities"),
        ],
        remainder="drop",
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("knn", NearestNeighbors(n_neighbors=n_neighbors)),
        ]
    )
    model.fit(X)
    return model


def _norm_id(val) -> str:
    return str(val).strip().removesuffix(".0")


def update_state(st_data):
    clean_id = _norm_id(st_data)
    st.session_state["data"] = clean_id
    st.session_state["last_interaction"] = clean_id


def clean(value, default="Unknown"):
    if value is None or value != value:
        return default
    text = str(value).strip()
    return text if text and text.lower() != "unknown" else default


def money(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return "N/A" if value != value else f"${value:,.2f}"


def rating_text(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return "N/A" if value != value else f"{value:.2f}".rstrip("0").rstrip(".")


def card_html(item, delta=None):
    name = html.escape(clean(item["name"], "Untitled listing"))
    url = html.escape(clean(item["listing_url"], "#"), quote=True)
    pic = clean(item["picture_url"], "")
    room = html.escape(clean(item["room_type"], "Stay"))
    area = html.escape(clean(item.get("neighbourhood_cleansed"), "Unknown area"))

    if pic:
        img = f'<img src="{html.escape(pic, quote=True)}" alt="">'
    else:
        img = '<div class="lc-noimg">🏠</div>'

    delta_html = ""
    if delta is not None and delta == delta:
        cls, sign = ("down", "-") if delta < 0 else ("up", "+")
        delta_html = f'<span class="lc-delta {cls}">{sign}${abs(delta):,.2f}</span>'

    return f"""
    <div class="lc">
        <div class="lc-img">{img}<span class="lc-badge">{room}</span></div>
        <a class="lc-title" href="{url}" target="_blank">{name}</a>
        <div class="lc-meta">
            <span><span class="lc-price">{money(item["price"])}</span>{delta_html}</span>
            <span class="lc-rating">⭐ {rating_text(item["review_scores_rating"])}</span>
        </div>
        <div class="lc-loc">📍 {area}</div>
    </div>
    """


CSS = """
<style>
[data-testid='stHeaderActionElements'] { display: none; }
[data-testid='stElementToolbar'] { display: none; }
header[data-testid="stHeader"] {
    background: transparent;
    height: 0rem;
}
.block-container {
    padding: 0.6rem 1.1rem 1.5rem 1.1rem !important;
    max-width: 100% !important;
}
[data-testid="stHorizontalBlock"] {
    gap: 0.75rem;
}
.st-key-stat_container [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
}
.st-key-stat_container [data-testid="stColumn"] {
    min-width: 0 !important;
}
/* stats panel text/spacing exactly as in the original app CSS */
.st-key-stat_container p {
    font-family: Arial, Helvetica Neue, Helvetica, sans-serif;
    margin: 0px !important;
}
.st-key-stat_container [data-testid="stMarkdownContainer"] {
    margin: 0px !important;
    padding: 0px !important;
}
.st-key-stat_container [data-testid="stVerticalBlock"],
.st-key-stat_container [data-testid="stHorizontalBlock"] {
    gap: 0 !important;
}
.st-key-1 {
    gap: 0;
    background-color: #e6e6e6;
    border-radius: 0px;
    padding: 0px;
    text-align: center;
    overflow: hidden !important;
}
/* center the name + count in the header bar (both directions) */
.st-key-1,
.st-key-1 [data-testid="stVerticalBlock"] {
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.st-key-1 [data-testid="stHorizontalBlock"] {
    align-items: center;
}
.st-key-1 h1 {
    padding: 0 !important;
    margin: 0 !important;
    line-height: 1.2 !important;
    text-align: center;
}

/* map + stats: both are native fixed-height containers (same height, stats scrolls) */
.st-key-stat_container {
    background-color: #fbf7ed;
    border-radius: 8px;
    padding: 0px;
    height: MAIN_H !important;
    width: 100%;
}
.st-key-map_container {
    border-radius: 8px;
    height: MAIN_H !important;
    overflow: hidden !important;
    padding: 0 !important;
}
.st-key-map_container iframe {
    height: MAIN_H !important;
    width: 100% !important;
    display: block;
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

/* ---- Currently Viewing / Similar Stays ---- */
.sec-label {
    font-size: 0.74rem;
    font-weight: 800;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #6b7280;
    margin: 0 0 0.1rem 0.15rem;
}
.sec-label.current { color: #1e88e5; }
.st-key-similar_wrap {
    border-left: 2px solid #d5d9e2;
    padding-left: 1rem;
}
[class*="st-key-card_"] {
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.1) !important;
    border-radius: 14px !important;
    padding: 0.45rem !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    transition: box-shadow 0.15s ease;
}
[class*="st-key-card_"]:hover { box-shadow: 0 8px 20px rgba(0, 0, 0, 0.13); }
.st-key-card_current {
    border: 2px solid #1e88e5 !important;
    background: #f3f8ff;
}
[class*="st-key-card_"] [data-testid="stVerticalBlock"] { gap: 0.35rem; }
.lc { display: flex; flex-direction: column; gap: 0.3rem; }
.lc-img {
    position: relative;
    width: 100%;
    aspect-ratio: 21 / 9;
    border-radius: 10px;
    overflow: hidden;
    background: #e5e7eb;
}
.lc-img img { width: 100%; height: 100%; object-fit: cover; display: block; }
.lc-noimg {
    width: 100%; height: 100%;
    display: flex; align-items: center; justify-content: center;
    font-size: 2rem;
}
.lc-badge {
    position: absolute; left: 8px; top: 8px;
    background: rgba(17, 24, 39, 0.78);
    color: #fff;
    font-size: 0.68rem;
    padding: 2px 9px;
    border-radius: 999px;
}
.lc-title {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: 2.6em;
    font-weight: 700;
    font-size: clamp(0.76rem, 0.85vw, 0.88rem);
    line-height: 1.3;
    color: #111827 !important;
    text-decoration: none;
}
.lc-title:hover { text-decoration: underline; }
.lc-meta {
    display: flex; justify-content: space-between; align-items: baseline;
    gap: 0.5rem; white-space: nowrap;
}
.lc-price { font-weight: 800; font-size: 0.95rem; color: #111827; }
.lc-delta { font-size: 0.78rem; font-weight: 700; margin-left: 0.4rem; }
.lc-delta.down { color: #16a34a; }
.lc-delta.up { color: #dc2626; }
.lc-rating { font-size: 0.85rem; color: #374151; }
.lc-loc {
    font-size: 0.8rem; color: #6b7280;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
</style>
"""


def listing_card(item, key, delta=None, current=False):
    with st.container(border=True, key=f"card_{key}"):
        st.markdown(card_html(item, delta), unsafe_allow_html=True)
        if current:
            st.button(
                "Viewing", key="btn_current", disabled=True, use_container_width=True
            )
        else:
            rec_id = _norm_id(rec["id"])
            st.button(
                "View",
                key=f"btn_{idx}_{rec_id}",
                on_click=update_state,
                args=(rec_id,),
                use_container_width=True,
            )


if __name__ == "__main__":
    try:
        st.set_page_config(
            layout="wide",
            page_title="Insight Airbnb",
            page_icon="🏡",
            initial_sidebar_state="collapsed",
        )

        if "city" not in st.session_state:
            st.session_state["city"] = DEFAULT_CITY
        if "data" not in st.session_state:
            st.session_state["data"] = None
        if "last_interaction" not in st.session_state:
            st.session_state["last_interaction"] = None

        main_h = get_main_height()
        st.markdown(CSS.replace("MAIN_H", f"{main_h}px"), unsafe_allow_html=True)

        # Load data
        df_reviews = load_review(st.session_state["city"])
        df_listings = load_listings(st.session_state["city"])
        try:
            df_scrape = scrape_data()
            df_scrape = dict(list(df_scrape.items())[3:])
        except Exception:
            df_scrape = {DEFAULT_CITY: []}

        # Header
        h1, h2 = st.columns([2, 1], vertical_alignment="center")
        with h1:
            st.markdown(f"## :rainbow[THIS IS {st.session_state['city']}]")
        with h2:
            menu_col, reset_col = st.columns([5, 1])
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
                st.button("🔄", on_click=clear_data, use_container_width=True)

        with st.spinner("Creating map..."):
            m, fg = create_map(st.session_state["city"])

        col1, col2 = st.columns([2, 1])
        with col1.container(key="map_container", border=True, height=main_h):
            map_data = draw_map(m, fg, main_h)
            is_empty_dict = isinstance(map_data, dict) and len(map_data) == 0
            if not is_empty_dict and map_data != st.session_state["last_interaction"]:
                if isinstance(map_data, (str, int, float)):
                    map_data = _norm_id(map_data)
                st.session_state["data"] = map_data
                st.session_state["last_interaction"] = map_data
                st.rerun()
        st_data = st.session_state["data"]

        with col2:  # noqa: SIM117
            with st.container(border=True, key="stat_container", height=main_h):
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

        model = train_recommender(df_listings, 4)

        id_series = (
            df_listings["id"]
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )
        matched_rows = pd.DataFrame()

        if st_data is not None and not isinstance(st_data, dict):
            matched_rows = df_listings.loc[id_series == _norm_id(st_data)]
        elif isinstance(st_data, dict) and "Neighbourhood" in st_data:
            matched_rows = df_listings.loc[
                df_listings["neighbourhood_cleansed"] == st_data["Neighbourhood"]
            ]

        current_item = (
            matched_rows.iloc[0] if not matched_rows.empty else df_listings.iloc[0]
        )

        query = (
            current_item[
                [
                    "price",
                    "latitude",
                    "longitude",
                    "review_scores_rating",
                    "room_type",
                    "amenities",
                ]
            ]
            .to_frame()
            .T
        )
        transformed = model.named_steps["preprocessor"].transform(query)
        _, indices = model.named_steps["knn"].kneighbors(transformed)
        recommendations = df_listings.iloc[indices[0][1:]]

        st.space("small")
        left, right = st.columns([1, 3], gap="medium")
        with left:
            st.markdown(
                '<div class="sec-label current">Currently viewing</div>',
                unsafe_allow_html=True,
            )
            listing_card(current_item, "current", current=True)

        with right.container(key="similar_wrap"):
            st.markdown(
                '<div class="sec-label">Similar stays</div>', unsafe_allow_html=True
            )
            rec_cols = st.columns(3)
            for idx, col in enumerate(rec_cols):
                rec = recommendations.iloc[idx]
                try:
                    delta = float(rec["price"]) - float(current_item["price"])
                except (TypeError, ValueError):
                    delta = None
                with col:
                    listing_card(rec, f"rec_{idx}", delta=delta)
    except Exception as e:
        st.error("🚨 Error")
        st.code(f"{e}", language="text")
        time.sleep(1)
