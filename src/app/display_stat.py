import os
from load_data import load_fig
import streamlit as st
from streamlit_extras.stylable_container import stylable_container
import glob
import random

script_dir = os.path.dirname(os.path.abspath(__file__))
roblox_files = glob.glob(os.path.join(script_dir,"../../roblox_profile_pic/*.png"))
random.seed(42)
def city_display_data(listings):
    with st.container(border=True,key='1', horizontal_alignment="left",height=100):
        col1, col2 = st.columns([1,1])
        with col1:
            citi = st.session_state['city'].split(',')
            st.title(f":rainbow[{citi[0]}]")
        with col2:
            number = f"{len(listings):,} listings "
            st.title(f":rainbow[{number}]")
    st.space()
    display_stat(listings)





def neibourhood_display_data(listings, st_data):
    neibourhood_listings = listings.loc[listings['neighbourhood_cleansed'] == st_data['Neighbourhood']]
    with st.container(border=True,key='1', horizontal_alignment="left",height=100):
        col1, col2 = st.columns([1,1])
        with col1:
            citi = st.session_state['city'].split(',')
            st.title(f":blue[{st_data['Neighbourhood']}]")
        with col2:
            number = f"{len(neibourhood_listings):,} listings "
            st.title(f":rainbow[{number}]")
    display_stat(neibourhood_listings)





def listings_display_data(df_reviews,df_listings,data):
    with st.spinner("load comment"):
        listings_data = df_listings.loc[df_listings["id"] == data]
        listings_data = listings_data.fillna("unknown")
        name = listings_data['name']
        url = listings_data['listing_url']
        st.markdown(
            f"""
            <h2 class="listings-name">
                <a href="Hosted by {url.iloc[0]}">
                    {str(name.iloc[0])}
                </a>
            </h2>
            """, 
            unsafe_allow_html=True
        )
        
        st.header('', divider='rainbow')
        col1, col2 = st.columns([1,6])
        with col1:
            host_image = listings_data['host_picture_url']
            st.space('small')
            st.markdown(f'<img src="{host_image.iloc[0]}" alt="0" style="width: 40px;\
                        max-width: 100%; margin-left: 2rem; margin-top: 8px; border-radius: 50%;">'
                            , unsafe_allow_html= True)
        with col2:
            host_name = listings_data['host_name']
            host_url = listings_data['host_url']
            st.markdown(
                f"""
                <h3 class="listings-host" style="font-size: 18.4px;margin: 0px;">
                    Hosted by
                    <a href=" {host_url.iloc[0]}" target="_blank" style="font-size: 18.4px;margin: 0px;">
                        {str(host_name.iloc[0])}
                    </a>
                </h3>
                """, 
                unsafe_allow_html=True
            )
            host_since = listings_data['host_since']
            st.markdown(f'<p class="listings-host">Host since {host_since.iloc[0]}</p>', unsafe_allow_html= True)


        st.header('', divider='rainbow')
        st.space("small") 
        with st.container(key= 'airbnb_detail'):
            _, col2 = st.columns([1,15])
            col2.header("ABOUT THIS PLACE: ") 
            st.space("small") 
            st.markdown("<p  style = ' margin-left: 30px; margin-right: 30px;'>" +\
                            listings_data['description'].iloc[0] +"</p>", unsafe_allow_html= True)

        _, center,_ = st.columns([1,20,1])
        center.space('medium')
        center.image(str(listings_data['picture_url'].iloc[0]))
        center.markdown(f'<h1 style="text-align:center;">{str(listings_data["review_scores_rating"].iloc[0]).upper()}🌟</h1>', unsafe_allow_html= True)
        center.markdown(f'<p style="text-align:center;">This home is a guest favorite based on ratings, reviews, and reliability</p>', unsafe_allow_html= True)
        center.space('medium')
        cols = center.columns([1.2,1,1,1.8,1.2,1], gap='small')
        items = [
            {"label": "Cleanliness", "score": f'{listings_data["review_scores_cleanliness"].iloc[0]}🌟', "icon": "🧼"},
            {"label": "Accuracy", "score": f'{listings_data["review_scores_accuracy"].iloc[0]}🌟', "icon": "✅"},
            {"label": "Check-in", "score": f'{listings_data["review_scores_checkin"].iloc[0]}🌟', "icon": "🔑"},
            {"label": "Communication", "score": f'{listings_data["review_scores_communication"].iloc[0]}🌟', "icon": "💬"},
            {"label": "Location", "score": f'{listings_data["review_scores_location"].iloc[0]}🌟', "icon": "🗺️"},
            {"label": "Value", "score": f'{listings_data["review_scores_value"].iloc[0]}🌟', "icon": "🏷️"}
        ]
        for i, col in enumerate(cols):
            item = items[i]
            with col:
                st.write(f'**{item["label"]}**')
                st.write(item['score'])
                st.write(item['icon'])



        reviews = df_reviews[df_reviews["listing_id"] == int(data)]
        with st.container():

            if(listings_data['number_of_reviews'] is not None):
                st.subheader(f'{listings_data["number_of_reviews"].iloc[0]} reviews')
            else:
                st.subheader('0 reviews')

            st.markdown('<div class="review-marker"/>', unsafe_allow_html=True)

            with st.container(width='stretch', key= 'review_section', border= False):
                if reviews.empty:
                    st.write("This listing has no comments.")
                else:
                    for _, review in reviews.iterrows():
                        st.divider()
                        col1, col2 = st.columns([1,7])
                        with col1.container():
                            st.image(random.choice(roblox_files), width= 45)
                        with col2.container():
                            st.space(12)
                            st.markdown(f":rainbow[**{review['reviewer_name']}**]")
                            st.caption(f":red[{review['date']}]")
                        st.markdown("<br/>",unsafe_allow_html=True)
                        st.write(review["comments"])
        



def display_stat(listings):
    if listings.empty:
        st.write("No listings match the current filters.")
        return
    fig1, room_type_counts, top_host_table, fig2, fig3, fig4 = load_fig(listings=listings)
    with st.container(height=570,border=False):
        _,aligncenter,_=st.columns([1.5,17,1])
        with aligncenter:
            st.header("Room Type",divider="rainbow")
            st.space("small")
            c1, c2, c3 = st.columns([155.2,120,130],gap= None)
            with c1:
                st.space("small")
                st.write("Airbnb hosts can list entire homes/apartments, private, shared rooms, and more recently hotel rooms. \n\n Depending on the room type and activity, a residential airbnb listing could be more like a hotel, disruptive for neighbours, taking away housing, and illegal.")
            with c2:
                st.space("small")
                st.pyplot(fig1, width = 'content')
            with c3:
                st.space("small")
                with stylable_container(
                        key=f"dynamic_button_1",
                        css_styles=["""
                        h1{
                            text-align: right;
                            font-family: Lato, sans-serif;
                            font-size: 25px;
                            font-weight: 800;
                            line-height: 1em;
                            padding-bottom: 5;
                            padding-top: 2;
                            float: right;
                            margin-top: 3px;
                            text-align: right;
                            width: 130px;
                        }
                        """,
                        """
                        p{
                            font-family: Arial, Helvetica Neue, Helvetica, sans-serif;
                            text-align: right;
                            font-size: .8em;
                            line-height: 1.3
                        }
                        """]
                    ):
                        st.title(f"{round(room_type_counts.iloc[0]/len(listings)*100,1)}%")
                        st.space("small")
                        st.write(f"{room_type_counts.index[0]}")
                        st.space("small")

                for type, counts in room_type_counts.items():
                    with stylable_container(
                        key=f"dynamic_button_{type}",
                        css_styles=["""
                        h2{
                            text-align: right;
                            font-family: Lato, sans-serif;
                            font-size: 15.5px;
                            font-weight: 800;
                            line-height: 1em;
                            padding-bottom: 5;
                            padding-top: 2;
                            float: right;
                            margin-top: 3px;
                            text-align: right;
                            width: 130px;
                        }
                        """,
                        """
                        p{
                            text-align: right;
                            padding-right: 0em;
                            font-size: 10.25px;
                        }
                        """]
                    ):
                        st.header(f"**{counts} ({round(counts/len(listings)*100,1)}%)**")
                        st.space("small")
                        st.write(f"{str(type)}")
                        st.space("small")
            st.header("Activity",divider="rainbow")
            c1,c2 = st.columns([1.7,1],gap="large")
            with c1:
                st.space("small")
                st.write("""The minimum stay, price and number of  
                            reviews have been used to estimate the 
                            number of **nights booked** and the **income** for  
                            each listing, for the last 12 months. """)
                st.space("small")
                st.write("""
                            Is the home, apartment or room rented
                            frequently and displacing units of housing and 
                            residents?  Does the income from Airbnb 
                            incentivise short-term rentals vs long-term housing?""")
            with c2:
                pass
            st.space("medium")
            st.pyplot(fig2)
            st.header("Short-Term Rentals",divider="rainbow")
            c1,c2 = st.columns([1.7,1],gap="large")
            with c1: 
                st.space("small")
                st.write("""Some Airbnb hosts have multiple listings.""")

                st.space("small")
                st.write("""A host may list separate rooms in the same
                            apartment, or multiple apartments or homes
                            available in their entirity.""")
        
                st.space("small")
                st.write("""Hosts with multiple listings are more likely to
                            be running a business, are unlikely to be living
                            in the property, and in violation of most short 
                            term rental laws designed to protect
                            residential housing.""")
                st.space("small")
            st.pyplot(fig4)
            st.header("Listings per Host",divider="rainbow")
            c1,c2 = st.columns([1.7,1],gap="large")
            with c1: 
                st.space("small")
                st.write("""Some Airbnb hosts have multiple listings.""")

                st.space("small")
                st.write("""A host may list separate rooms in the same 
                            apartment, or multiple apartments or homes
                            available in their entirity.""")
        
                st.space("small")
                st.write("""Hosts with multiple listings are more likely to be running a business, are unlikely to be living in the property, and in violation of most short term rental laws designed to protect residential housing.  """)
                st.space("small")
            st.pyplot(fig3)
            st.header("Top Hosts",divider="rainbow")
            def col_pretty(col):
                if col.name == 'total_listings' or col.name == "host_name":
                    return ["font-weight: bold"] * len(col)
                return [''] * len(col)
            def row_pretty(row):
                if (int(row.name) % 2) :
                    return ['background-color: lightgray; color: black'] * len(row)
                else:
                    return ['background-color: white; color: black'] * len(row)

            st.write(top_host_table.style\
                                    .apply(col_pretty, axis=0).hide(axis="index")\
                                    .apply(row_pretty, axis=1).to_html(), unsafe_allow_html=True)
