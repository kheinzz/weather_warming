import streamlit as st 
from streamlit_folium import st_folium
import folium
import duckdb as dck
import plotly.express as px
import os
import pandas as pd
import jenkspy
import geojson
import pathlib

# Open a connection to DuckDB
con = dck.connect(database=':memory:', read_only=False)
# tab1, tab2, tab3 = st.tabs(["Découverte", "Evolution des températures", "Evolution des précipitations"])

#######################################
############    TAB 1     ############
#######################################
with tab1 :
    df = con.execute('select "nom_usuel",  "altitude(m)", "date_debut_serie(YYYYMM)"::text as "date_debut_serie(YYYYMM)", "date_fin_serie(YYYYMM)"::text as "date_fin_serie(YYYYMM)" , "latitude(°)" ,"longitude(°)" from read_csv("..\data\Liste_SH_TX_metro.csv")').fetchdf()

    st.dataframe(df[["nom_usuel", "altitude(m)", "date_debut_serie(YYYYMM)", "date_fin_serie(YYYYMM)"]], 1000, 200)
    # Create a map object centered around the mean of latitudes and longitudes
    # Load GeoJSON data
    with open('./data/geo_station.geojson', 'r') as f:
        geojson_data = geojson.load(f)
        
    # Extract relevant properties from GeoJSON
    features = geojson_data['features']
    latitudes = [feature['geometry']['coordinates'][1] for feature in features]
    longitudes = [feature['geometry']['coordinates'][0] for feature in features]

    # Calculate average latitude and longitude
    average_latitude = sum(latitudes) / len(latitudes)
    average_longitude = sum(longitudes) / len(longitudes)
    # Creat a map object centered around the mean of latitudes and longitudes
    mymap = folium.Map(location=[average_latitude, average_longitude], zoom_start=6)
 # Add markers for each location
    for feature in features:
        properties = feature['properties']
        coordinates = feature['geometry']['coordinates']
        
        # Assign color based on 'difference' value
        color_index = 0  # Default color index
        
        folium.Circle(
            location=[coordinates[1], coordinates[0]],
            radius=5000,  # Adjust radius as needed
            popup=properties['nom'],
            color='blue',  # Outline color
            fill=True,
            fill_color='transparent',  
            fill_opacity=0.7,
            # Je ne souhaite pas que l'utilisateur puisse zoomer/se déplacer sur la carte -> pour l'instant ne fonctionne pas
            zoom_control=False,
            scrollWheelZoom=False,
            dragging=False
        ).add_to(mymap)
    # Extract relevant properties from GeoJSON
    features = geojson_data['features']
    st_data = st_folium(mymap, width = 725, returned_objects=[], key="map1")
    

