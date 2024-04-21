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
tab1, tab2, tab3, tab4 = st.tabs(["Bienvenue ! ", "Températures", "Précipitations", "Insolation"])

#######################################
############    TAB 1     ############
#######################################
with tab1 : 
    st.title("Weather warming")
    st.header("Bienvenue sur weather warming, cette appli vise à utiliser et valoriser les données ouvertes de [Météo-France](https://meteo.data.gouv.fr/).")
    st.caption("Compte-tenu de la prégnance de ce sujet dans notre quotidien ainsi que dans les médias et les travaux scientifiques, l'accent sera mis sur les séries temporelles de données climatologiques dites \"de référence pour l'étude du changement climatique\".")
    st.caption("Dans un premier temps nous souhaitons explorer ce que renferment ces données, quels sont les fichiers et les variables qu'ils contiennent afin de donner du contexte au reste de l'application et au traitements qui seront réalisés.")
    st.caption("""Le reste de l'application sera consacré à l'exploration de ces données ainsi qu'à des indicateurs tentant de mettre en exergue la prégnance du changement climatique, mais aussi les implications de ce dernier sur nos territoire. 
               En effet, que ce soit du point de vue des températures ou des précipitations, le réchauffement du climat ne semble pas avoir les mêmes conséquences selon les territoires.
               """)
#######################################
############    TAB 2     ############
#######################################
with tab2 : 
    df = con.execute('select "nom_usuel",  "altitude(m)", "date_debut_serie(YYYYMM)"::text as "date_debut_serie(YYYYMM)", "date_fin_serie(YYYYMM)"::text as "date_fin_serie(YYYYMM)" , "latitude(°)" ,"longitude(°)" from read_csv("./data/Liste_SH_TX_metro.csv")').fetchdf()

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
    

