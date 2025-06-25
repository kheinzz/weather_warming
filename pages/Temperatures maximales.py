import streamlit as st 
from streamlit_folium import st_folium
import folium
import duckdb as dck
import plotly.express as px
import pandas as pd
import jenkspy
import geojson
from pathlib import Path

st.set_page_config(
    page_title=None,
    page_icon=None,
    layout=None,
    initial_sidebar_state="expanded",
    menu_items=None
)

st.subheader("Données des températures mensuelles maximales")
st.caption("""Dans cette partie nous allons essayer d'explorer les données disponibles pour essayer d'observer
             des changements dans le temps (en l'occurrence une augmentation), et comment ceux-ci se manifestent spatialement""")
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

# Extract latitude and longitude from each feature
coordinates = [(feature['geometry']['coordinates'][1], feature['geometry']['coordinates'][0]) for feature in features]

# Calculate average latitude and longitude
average_latitude = sum(lat for lat, _ in coordinates) / len(coordinates)
average_longitude = sum(lon for _, lon in coordinates) / len(coordinates)

# Create a map object centered around the mean of latitudes and longitudes
mymap = folium.Map(location=[average_latitude, average_longitude], zoom_start=6)

# Define constants
RADIUS = 5000
COLORS = ["yellow", "orange", "red", "purple"]
DEFAULT_COLOR = "gray"

# Iterate over GeoJSON features
for feature, (lat, lon) in zip(features, coordinates):
    properties = feature['properties']
    
    # Assign color based on 'difference' value
    color_index = next((i for i, b in enumerate(breaks) if b > properties.get('difference', 0)), len(breaks) - 1)
    
    # Handle color index out of range gracefully
    if color_index >= len(COLORS):
        color_index = len(COLORS) - 1
    
    # Create circle markers
    folium.Circle(
        location=[lat, lon],
        radius=RADIUS,
        popup=f"Nom de la station : {properties.get('nom', '')}\nDifférence : {properties.get('difference', '')}",
        color='transparent',
        fill=True,
        fill_color=COLORS[color_index],
        fill_opacity=0.7,
        zoom_control=False,
        scrollWheelZoom=False,
        dragging=False
    ).add_to(mymap)

# Improved file path handling
file_path = Path("./data/SH_TX_metropole")
print("La différence de t° minimum observée entre les deux périodes:", min(data), '\n', "La différence de t° maximum observée entre les deux périodes:", max(data))

st_data = st_folium(mymap, width=725, returned_objects=[], key="map2")

# Read the list file
file_list_1 = con.execute('select * from read_csv("./data/Liste_SH_TX_metro.csv")').fetchdf()

# Allow user to choose the source file
selected_file = st.selectbox("Sélectionnez une station : ", file_list_1['nom_usuel'])

# List to store the DataFrames of each CSV file
dfs = []
# Append DataFrames to a list for efficient concatenation
dfs = []
with st.spinner('Calcul en cours ...'):
    for index, row in file_list_1.iterrows():
        query = f"SELECT * FROM read_csv('{file_path / row['nom_fichier']}')"
        df = con.execute(query).fetchdf()
        df['source_file'] = row['nom_fichier']
        df['date_debut'] = row['date_debut_serie(YYYYMM)']
        df['date_fin'] = row['date_fin_serie(YYYYMM)']
        df['nom_usuel'] = row['nom_usuel']
        dfs.append(df)

final_df = pd.concat(dfs, ignore_index=True)

df_filtered = final_df[final_df['nom_usuel'] == selected_file]
df_filtered['YYYYMM'] = pd.to_datetime(df_filtered['YYYYMM'], format='%Y%m')
df_filtered['Month'] = df_filtered['YYYYMM'].dt.month
df_filtered['Year'] = df_filtered['YYYYMM'].dt.year

scatter_fig = px.scatter(df_filtered, x='Month', y='VALEUR', color='Year',
                        color_continuous_scale='viridis', labels={'Month': 'Mois', 'VALEUR': 'Température', 'YYYYMM': 'Année'})

scatter_fig.update_layout(title=f'Evolution des température pour la station {selected_file}', xaxis_title='Month', yaxis_title='Temperature', boxmode='overlay')

st.plotly_chart(scatter_fig, theme="streamlit", use_container_width=True)
