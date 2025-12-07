import os
import time
from matplotlib import ticker
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import geopandas as gpd
from bs4 import BeautifulSoup
import requests
import pandas as pd
import polars as pl
from urllib.parse import quote
url = "https://insideairbnb.com/get-the-data/"
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, '../../raw/currency.csv')
currency_csv = pd.read_csv(file_path)



@st.cache_data
def scrape_data():
	response = requests.get(url, timeout=20)
	all_content = response.content
	soup = BeautifulSoup(all_content, 'lxml')
	all_cities_data = dict()
	cities = soup.find_all("h3")
	for city in cities:
		all_cities_data[city.get_text(strip=True)] = []
		table = city.find_next_sibling(class_=["data", "table", "table-hover", "table-striped"]).find_all("a")
		for link in table:
			all_cities_data[city.get_text(strip=True)].append(quote(link["href"], safe=':/?=&'))
	return all_cities_data




@st.cache_data 
def load_review(city = 'Singapore, Singapore, Singapore'):
	start_time = time.perf_counter()
	try:
		csv_reviews_path = scrape_data()[city][2]
	except Exception as e:
		st.error(f" NOT MY FAULT! Its error connection, wifi problem not code problem or {e} at review. So use this instead")
		if city == "Bangkok, Central Thailand, Thailand":
			csv_reviews_path = os.path.join(script_dir,"../../raw/bangkok/2025-06-24/data/reviews.csv.gz")
		elif city == "Taipei, Northern Taiwan, Taiwan":
			csv_reviews_path = os.path.join(script_dir,"raw/taipei/2025-06-29/data/reviews.csv.gz")
		else:
			csv_reviews_path = os.path.join(script_dir,"raw/singapore/2025-09-28/data/reviews.csv.gz")
	pf= pl.scan_csv(
		csv_reviews_path,
		low_memory = False,
	)
	pf = pf.with_columns(
		pl.col("comments").str.replace_all("<br/>", "\n"),
	)
	pf=pf.reverse()
	df = pf.collect().to_pandas()
	end_time = time.perf_counter()
	elapsed_time = end_time - start_time
	print(f"reviews executed in {elapsed_time:.4f} seconds.")
	return df
@st.cache_data 
def load_listings(city = 'Singapore, Singapore, Singapore'):
	start_time = time.perf_counter()
	country = city.split(',')[0].strip().upper()
	try:
		exchange_rate = currency_csv.loc[currency_csv['Country'] == country, 'Exchange_Rate'].item()
	except Exception as e:
		exchange_rate = 1

	try:
		csv_listings_path = scrape_data()[city][0]
	except Exception as e:
		st.error(f" NOT MY FAULT! Its error connection, wifi problem not code problem or {e} at listings. So use this instead")
		if city == "Bangkok, Central Thailand, Thailand":
			csv_listings_path = os.path.join(script_dir,"raw/bangkok/2025-06-24/data/listings.csv.gz")
		elif city == "Taipei, Northern Taiwan, Taiwan":
			csv_listings_path = os.path.join(script_dir,"raw/taipei/2025-06-29/data/listings.csv.gz")
		else:
			csv_listings_path = os.path.join(script_dir,"raw/singapore/2025-09-28/data/listings.csv.gz")
	pf = pl.scan_csv(csv_listings_path, schema_overrides={"id": pl.String, 'license': pl.String})
	pf = pf.with_columns(
		pl.col("price").str.replace_all(r"[\$,]", "").alias("price")
	).with_columns(
		pl.col("price").cast(pl.Float64).alias("price")
	).with_columns(
		(pl.col("price") / exchange_rate).alias("price")
	)
	df = pf.collect().to_pandas()

	end_time = time.perf_counter()
	elapsed_time = end_time - start_time
	print(f"listings executed in {elapsed_time:.4f} seconds.")
	return df


@st.cache_data 
def load_geojson(city = 'Singapore, Singapore, Singapore'):
	start_time = time.perf_counter()
	try:
		geojson_path = scrape_data()[city][6]
	except Exception as e:
		st.error(f" NOT MY FAULT! Its error connection, wifi problem not code problem or {e} at geojson. So use this instead pls 🥳")
		if city == "Bangkok, Central Thailand, Thailand":
			geojson_path = os.path.join(script_dir,"raw/bangkok/2025-06-24/visualisations/neighbourhoods.geojson")
		elif city == "Taipei, Northern Taiwan, Taiwan":
			geojson_path = os.path.join(script_dir,"raw/taipei/2025-06-29/visualisations/neighbourhoods.geojson")
		else:
			geojson_path = os.path.join(script_dir,"raw/singapore/2025-09-28/visualisations/neighbourhoods.geojson")
	

	geojson_data = gpd.read_file(geojson_path, encoding='utf-8')
	world_bounds = gpd.read_file("world.geojson",encoding='utf-8')
	end_time = time.perf_counter()
	elapsed_time = end_time - start_time
	print(f"geojson executed in {elapsed_time:.4f} seconds.")
	return geojson_data, world_bounds 


@st.cache_data 
def load_fig(listings):
	#fig1
	counts = listings['room_type'].value_counts()[::-1]
	room_type = listings['room_type'].unique()[::-1]
	bar_colors ={
				'Private room': 'blue', 
				'Entire home/apt': 'purple', 
				'Shared room': 'red', 
				'Hotel room': 'green'
	}
	colors = [bar_colors[i] for i in counts.index]
	fig1, ax1 = plt.subplots(figsize=(3, 4.5))
	fig1.patch.set_facecolor('#fbf7ed')
	ax1.set_facecolor("#fbf7ed")
	barhs = ax1.barh(room_type,counts,height=0.6,color=colors)
	ax1.tick_params(axis='y', labelleft=False)
	ax1.set_xlabel("listings",fontdict={'family': 'serif', 'color': 'darkblue', 'size': 18}, labelpad=10)
	for i, room in enumerate(room_type):
		ax1.text(
				sum(counts) / len(counts)/10, 
				i+0.5,            
				room,      
				horizontalalignment='left',     
				verticalalignment='center',   
				fontsize=17,
				fontweight= 400
		)
			
	
	plt.xticks(fontsize=12)
	ax1.spines['top'].set_visible(False)
	ax1.spines['right'].set_visible(False)
	#fig2

	# % of room_type
	room_type_counts = listings['room_type'].value_counts()
	room_type_counts=room_type_counts.rename(index={"Entire home/apt":"Entire homes/Apartments",})
  
  
  
	# top host table
	table_listings = listings[["host_name","room_type","host_total_listings_count"]]
	table_listings= pd.get_dummies(table_listings,columns=["room_type"], prefix='', prefix_sep='')
	table_listings = table_listings.groupby("host_name")
	top_host_table = table_listings.sum()
	top_host_table['host_total_listings_count'] = table_listings.count()['host_total_listings_count']
	top_host_table = top_host_table.sort_values(by='host_total_listings_count', ascending=False).head(100)
	top_host_table.rename(columns={"host_total_listings_count":"total_listings"},inplace=True)
	top_host_table.reset_index(inplace=True,col_level=0)


	# top_host_table = top_host_table.iloc[:, :0:-1]
	cols = top_host_table.columns.to_list()
	top_host_table = top_host_table[[cols[0]] + cols[1:][::-1]]


	# fig 2
	fig2_tick = [
					'0',
					'1-30',
					'31-60',
					'61-90',
					'91-120',
					'121-150',
					'151-180',
					'181-210',
					'211-240',
					'241-255+'
	]
	bins = [ -1, 0, 30, 60, 90, 120, 150, 180, 210, 240, 10*1000 ]
	binned_data = pd.Series(pd.cut(listings['estimated_occupancy_l365d'], bins = bins, labels=fig2_tick))
	binned_data = binned_data.value_counts()
	fig2, ax2 = plt.subplots(figsize=(12.5,4))
	bar2 = ax2.bar(fig2_tick, binned_data, width= 0.8)
	ax2.margins(0.03)  
	ax2.yaxis.set_major_locator(ticker.MultipleLocator(base=1000))
	ax2.tick_params(axis='y', left=False)
	ax2.set_xlabel("occupancy (last 12 months)",fontdict={'family': 'serif', 'color': 'darkblue', 'size': 20}, labelpad=10)
	ax2.set_ylabel("listings",fontdict={'family': 'serif', 'color': 'darkblue', 'size': 20}, labelpad=10)
	ax2.tick_params(axis='x', labelsize=12) 
	ax2.tick_params(axis='y', labelsize=14) 
	ax2.spines['top'].set_visible(False)
	ax2.spines['right'].set_visible(False)
	fig2.patch.set_facecolor('#fbf7ed')
	ax2.set_facecolor("#fbf7ed")
	for bar in bar2:
		height = bar.get_height()
		ax2.text(
					bar.get_x() + bar.get_width() / 2,
					height,
					s = f'{height}',
					horizontalalignment='center',     
					verticalalignment='bottom',   
					fontsize=16,
					fontweight= 400
				)

	#fig3
	limit_litings_host = listings
	limit_litings_host.loc[listings["calculated_host_listings_count"]>10,"calculated_host_listings_count"] = 10
	fig3, ax3 = plt.subplots(figsize=(12.5,4))
	data = limit_litings_host["calculated_host_listings_count"].value_counts()
	data_index = [item for item in range(1,11) if item not in data.index]
	new_s = pd.Series(0, index= data_index)
	if not new_s.empty:
		data = pd.concat([data, new_s])[::-1]
	
	data.sort_index(inplace=True)
	bar3 = ax3.bar(['1','2','3','4','5','6','7','8','9','10+'],list(data))
	ax3.margins(0.03)  
	ax3.yaxis.set_major_locator(ticker.MultipleLocator(base=1000))
	for bar in bar3:
		height = bar.get_height()
		ax3.text(
					bar.get_x() + bar.get_width() / 2,
					height,
					s = f'{height}',
					horizontalalignment='center',     
					verticalalignment='bottom',   
					fontsize=16,
					fontweight= 400
				)
	ax3.set_xlabel("listings per host",fontdict={'family': 'serif', 'color': 'darkblue', 'size': 18}, labelpad=10)
	ax3.set_ylabel("listings",fontdict={'family': 'serif', 'color': 'darkblue', 'size': 18}, labelpad=10)
	ax3.tick_params(axis='x', labelsize=14) 
	ax3.tick_params(axis='y', labelsize=16)
	ax3.spines['top'].set_visible(False)
	ax3.spines['right'].set_visible(False)
	fig3.patch.set_facecolor('#fbf7ed')
	ax3.set_facecolor("#fbf7ed")
	#fig4
	limit_data= listings
	limit_data.loc[listings['minimum_nights']>35,'minimum_nights'] = 35
	data= limit_data['minimum_nights'].value_counts()

	data_index = [item for item in range(1,36) if item not in data.index]
	new_row = pd.Series(0, index= data_index)
	if not new_row.empty:
		data = pd.concat([data, new_row])
	data.sort_index(inplace=True)
	fig4, ax4 = plt.subplots(figsize=(12.5,5),dpi=300)
	bar3 = ax4.bar([str(i) for i in range(1, 35)]+["35+"],list(data), width= 0.6)
	ax4.margins(0.02)  
	ax4.yaxis.set_major_locator(ticker.MultipleLocator(base=1000))
	ax4.set_xlabel("listings per host",fontdict={'family': 'serif', 'color': 'darkblue', 'size': 18}, labelpad=10)
	ax4.set_ylabel("listings",fontdict={'family': 'serif', 'color': 'darkblue', 'size': 18})
	ax4.tick_params(axis='x', labelsize=12) 
	ax4.tick_params(axis='y', labelsize=12)
	ax4.spines['top'].set_visible(False)
	ax4.spines['right'].set_visible(False)
	fig4.patch.set_facecolor('#fbf7ed')
	ax4.set_facecolor("#fbf7ed")
	xticks = ax4.get_xticklabels()
	for i in range(len(xticks)-1):
		if data[int(xticks[i].get_text())] == 0:
			xticks[i].set_visible(False)
	for bar in bar3:
		height = bar.get_height()
		if height != 0:
			ax4.text(
						bar.get_x() + bar.get_width() / 2,
						height,
						s = f'{height}',
						horizontalalignment='center',     
						verticalalignment='bottom',   
						color = 'red',
						fontsize=14,
						fontweight= 400
					)
	ax4.axvline(x=28.5, linestyle='--', linewidth=2, dashes=(5, 2), color = 'red')
	ax4.text(x= 28.5, y= data.max()//2,s = 'STR Threshold', rotation= -90, fontsize=19, color = 'b')
	return fig1, room_type_counts, top_host_table, fig2, fig3, fig4