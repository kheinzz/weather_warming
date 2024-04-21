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
# Load GeoJSON data
with open('./data/result_diff_tx.geojson', 'r') as f:
    geojson_data = geojson.load(f)

# Extract relevant properties from GeoJSON
features = geojson_data['features']

# Prepare the data for Jenks Natural Breaks Classification
data = [float(feature['properties']['difference']) for feature in features if 'difference' in feature['properties']]

# Perform Jenks Natural Breaks Classification
breaks = jenkspy.jenks_breaks(data, n_classes=4)

# Define color scale
colors = ["yellow", "orange", "red", "purple"]
# Assuming you have a list of features called 'features'
# Extract latitude and longitude from each feature
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
    if 'difference' in properties:
        # Determine color index based on Jenks Natural Breaks Classification
        for i in range(len(breaks) - 1):
            if breaks[i] <= properties['difference'] < breaks[i + 1]:
                color_index = i
                break
    
    folium.Circle(
        location=[coordinates[1], coordinates[0]],
        radius=5000,  # Adjust radius as needed
        popup="Nom de la station : "+ str(properties['nom']) + "\n "+"Différence : " + str(properties['difference']) ,  # Concatenating string with value
        color='transparent',  # Outline color
        fill=True,
        fill_color=colors[color_index],  # Fill color based on Jenks Natural Breaks Classification
        fill_opacity=0.7,
        # Je ne souhaite pas que l'utilisateur puisse zoomer/se déplacer sur la carte -> pour l'instant ne fonctionne pas
        zoom_control=False,
        scrollWheelZoom=False,
        dragging=False
    ).add_to(mymap)

print("La différence de t° minimum observée entre les deux périodes:", min(data), '\n', "La différence de t° maximum observée entre les deux périodes:", max(data))



st_data = st_folium(mymap, width = 725, returned_objects=[], key="map2")
    ######################
####  CHART

# Lire le fichier de liste
file_list_1 = con.execute('select * from read_csv("./data/Liste_SH_TX_metro.csv")').fetchdf()

# Allow user to choose the source file
selected_file = st.selectbox("Sélectionnez une station : ", file_list_1['nom_usuel'])

# Liste pour stocker les DataFrames de chaque fichier CSV
dfs = []
with st.spinner('Calcul en cours ...'):
    # Parcourir chaque fichier dans la liste
    for index, row in file_list_1.iterrows():
        # Chemin complet vers le fichier CSV
        file_path = os.path.join("./data/SH_TX_metropole", row['nom_fichier'])

        # Connectez-vous à votre base de données DuckDB
        con = dck.connect(database=':memory:', read_only=False)

        # Utiliser la variable dans la fonction read_csv()
        query = f"SELECT * FROM read_csv('{file_path}')"

        # Exécuter la requête et obtenir le DataFrame
        df = con.execute(query).fetchdf()
        # Charger le fichier CSV dans un DataFrame
        # Ajouter une colonne supplémentaire pour stocker le nom du fichier d'origine
        df['source_file'] = row['nom_fichier']
        df['date_debut'] = row['date_debut_serie(YYYYMM)']
        df['date_fin'] = row['date_fin_serie(YYYYMM)']
        df['nom_usuel'] = row['nom_usuel']

        # Ajouter le DataFrame à la liste
        dfs.append(df)

    # Concaténer tous les DataFrames en un seul
    final_df = pd.concat(dfs, ignore_index=True)

    # Filtrer les données pour le fichier sélectionné par l'utilisateur
    df_filtered = final_df[final_df['nom_usuel'] == selected_file]

    # Convert 'YYYYMM' column to datetime
    df_filtered['YYYYMM'] = pd.to_datetime(df_filtered['YYYYMM'], format='%Y%m')

    # Extract month and year from 'YYYYMM' column
    df_filtered['Month'] = df_filtered['YYYYMM'].dt.month
    df_filtered['Year'] = df_filtered['YYYYMM'].dt.year

    # Plotly scatter plot
    # Plotly scatter plot with specified color scale
    scatter_fig = px.scatter(df_filtered, x='Month', y='VALEUR', color='Year',
                            color_continuous_scale='viridis', labels={'Month': 'Mois', 'VALEUR': 'Température', 'YYYYMM': 'Année'})



    # Update layout
    scatter_fig.update_layout(title=f'Evolution des température pour la station {selected_file}', xaxis_title='Month', yaxis_title='Temperature', boxmode='overlay')

    # Show combined plot
    st.plotly_chart(scatter_fig, theme="streamlit", use_container_width=True)
