import streamlit as st 
from streamlit_folium import st_folium
import folium
import duckdb as dck
import plotly.express as px
import os
import pandas as pd
import jenkspy
import geojson
import numpy as np  


st.subheader("Tendances géographiques")
st.caption("""Comme pour les températures, ici nous comparons la médiane des dix premières années avec la médiane des dix dernières années, l'indicateur
        représenté par la couleur des points et la soustraction de ces deux valeurs pour chaque station disponible. 
        Cet indicateur nous permet de voir clairement quels sont les effets actuels du changement climatiques en lissant au maximum l'effet des valeurs extrêmes
        grâce à la médiane.""")
# Open a connection to DuckDB
con = dck.connect(database=':memory:', read_only=False)


with open('./data/result_diff_rr.geojson', 'r') as f:
    geojson_data = geojson.load(f)
    # Extract relevant properties from GeoJSON
features = geojson_data['features']
# Define a color gradient from wet to dry
dry_color =[0, 247, 255]    # Blue
wet_color =  [221, 0, 0 ]  # Red
num_colors = 5# Number of colors in the gradient
# print("MERGED ******* ", merged_df)

# Generate the gradient colors 
gradient_colors = []
for i in range(num_colors):
    ratio = i / num_colors
    color = [
        int(wet_color[j] * (1 - ratio) + dry_color[j] * ratio)
        for j in range(3)
    ]
    gradient_colors.append('#%02x%02x%02x' % tuple(color))
# Prepare the data for Jenks Natural Breaks Classification
differences = [feature['properties']['difference'] for feature in features if 'difference' in feature['properties']]

# Perform Jenks Natural Breaks Classification
breaks = jenkspy.jenks_breaks(differences, n_classes=4)

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
    # Convert differences to a pandas DataFrame
    differences_df = pd.DataFrame(differences, columns=['difference'])

    # Calculate the normalized difference using pandas methods
    normalized_difference = (properties['difference'] - differences_df['difference'].min()) / (differences_df['difference'].max() - differences_df['difference'].min())
    # Calculate the index in the gradient colors list
    gradient_color_index = int(normalized_difference * (num_colors - 1))
    folium.Circle(
        location=[coordinates[1], coordinates[0]],
        radius=5000,  # Adjust radius as needed
        popup=properties['difference'],
        color='transparent',  # Outline color
        fill=True,
        fill_color=gradient_colors[gradient_color_index],  # Fill color based on Jenks Natural Breaks Classification
        fill_opacity=0.7,
        # Je ne souhaite pas que l'utilisateur puisse zoomer/se déplacer sur la carte -> pour l'instant ne fonctionne pas
        zoom_control=False,
        scrollWheelZoom=False,
        dragging=False
    ).add_to(mymap)

# Add Legend
legend_html = """
    <div style="position: fixed; 
    bottom: 50px; left: 50px; width: 150px; height: 130px; 
    border:2px solid grey; z-index:9999; font-size:14px;
    background-color: white;
    ">&nbsp; <b>Legend</b> <br>
    &nbsp; Augmentation des précipitations &nbsp; <i class="fa fa-circle 
    fa-1x" style="color:{wet_color}"></i><br>
    &nbsp; Diminution des précipitations &nbsp; <i class="fa fa-circle 
    fa-1x" style="color:{dry_color}"></i>
    </div>
    """.format(wet_color=wet_color, dry_color=dry_color)
mymap.get_root().html.add_child(folium.Element(legend_html))

# Display the map using Streamlit
st_data = st_folium(mymap, width=725, returned_objects=[], key= "map3")


##########################
########### CHARTS 
# Lire le fichier de liste

st.subheader("Tendances annuelles et mensuelles")
st.caption("Si la somme des précipitations annuelle est un bon indicateur des tendances climatiques (lesquelles peuvent aussi varier spatialement), il peut aussi être intéressant de se pencher sur les tendances mensuelles.")
# Define a dictionary mapping month numbers to French month names
french_month_names = {1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril', 5: 'mai', 6: 'juin',
                    7: 'juillet', 8: 'août', 9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'}

# Define a checkbox for filtering the dataset
filter_checkbox = st.checkbox("Filtrer le jeu de donnée par station")

# Define a dropdown to select the file name
if filter_checkbox:
    file_list = dck.sql('select * from read_csv("./data/Liste_SH_RR_metro.csv")').df()
    file_names = file_list['nom_usuel'].unique()
    selected_file_name = st.selectbox("Selectionnez un nom de station", file_names)
else:
    selected_file_name = None

# Define a button to trigger chart computation
compute_button = st.button("Calcul des graphiques")

####### A FAIRE
## Si plot par station : 
# montrer la sommes des mois par ans pour le tout premier plot
## Si plot pour toute la france : 
# calculer la moyenne ou médiane de toutes les stations 


# Check if the button is clicked
if compute_button:
    # Display a spinner to indicate computation is in progress
    with st.spinner('Calcul en cours ...'):
        file_list = con.execute('select * from read_csv("./data/Liste_SH_RR_metro.csv")').fetchdf()
        dfs = []
        for index, row in file_list.iterrows():
            if selected_file_name is None or row['nom_usuel'] == selected_file_name:
                file_path = os.path.join("./data/SH_RR_metropole", row['nom_fichier'])
                query = f"SELECT * FROM read_csv('{file_path}')"
                df = con.execute(query).fetchdf()
                df['source_file'] = row['nom_fichier']
                df['date_debut'] = row['date_debut_serie(YYYYMM)']
                df['date_fin'] = row['date_fin_serie(YYYYMM)']
                dfs.append(df)
        final_df = pd.concat(dfs, ignore_index=True)
        final_df['YYYYMM'] = pd.to_datetime(final_df['YYYYMM'], format='%Y%m')
        final_df['Month'] = final_df['YYYYMM'].dt.month
        final_df['Year'] = final_df['YYYYMM'].dt.year
        final_df = final_df[final_df['Year'] > 1951]
        grouped_data = final_df.groupby(['Month', 'Year'])['VALEUR'].mean().reset_index()
    

####### A FAIRE
## Si plot par station : 
# montrer la sommes des mois par ans pour le tout premier plot
## Si plot pour toute la france : 
# calculer la moyenne ou médiane de toutes les stations 


        # Filter out non-numeric columns if necessary
        final_df_numeric = final_df.select_dtypes(include=[np.number])
        print("DATA : ",final_df_numeric.head())
        # Now perform the aggregation on the numeric DataFrame
        if filter_checkbox:
            yearly_data = final_df_numeric.groupby('Year')['VALEUR'].sum().reset_index()
            if selected_file_name:
                title = f"Somme annuelle des précipitations (mm) pour la station {selected_file_name}"
        else:
            yearly_data = final_df_numeric.groupby('Year').sum().reset_index()
            yearly_data = yearly_data.groupby('Year').mean().reset_index()

            title = "Moyenne annuelle des précipitations (mm) pour toutes les stations"
        
        # Plot yearly median precipitation
        print("DATA 2 : ", yearly_data)
        fig_median = px.scatter(yearly_data, x='Year', y='VALEUR', title=title,
                            trendline="ols", labels={'VALEUR': "Précipitations", "Year": "Années"})
        st.plotly_chart(fig_median, theme=None, use_container_width=True)
        

        #### Ensuite on montre les graphs par mois et leurs évolutions dans le temps
        # Plot each month with lines for each year
        for month in range(1, 13):
            data_month = grouped_data[grouped_data["Month"] == month]
            # Get the French month name
            month_name_fr = french_month_names[month]
            if filter_checkbox and selected_file_name:
                title = f'Précipitations moyennes (mm) par an pour le mois de {month_name_fr} pour la station {selected_file_name} + tendance'
            else:
                title = f'Précipitations moyennes (mm) par an pour le mois de {month_name_fr} pour toutes les données + tendance'
            
            # Calculate trendline using linear regression
            trend_slope, trend_intercept = np.polyfit(data_month['Year'], data_month['VALEUR'], 1)
            
            # Determine trend direction
            trend_direction = "augmentation" if trend_slope > 0 else "diminution"
            
            # Determine trend magnitude
            trend_magnitude = abs(trend_slope)
            
            st.write(f"### {title}")
            st.write(f"Ce graphique illustre les précipitations moyennes en millimètres pour le mois de {month_name_fr} au fil des années.")
            st.write(f"La tendance des précipitations pour le mois de {month_name_fr} est une {trend_direction} de {trend_magnitude:.2f} mm par an.")
            fig = px.scatter(data_month, x='Year', y='VALEUR',
                    color_discrete_sequence=px.colors.qualitative.Plotly, trendline="ols", labels={'VALEUR': "Précipitations",
                                                                                                    "Year": "Années"})
            st.plotly_chart(fig, theme="streamlit", use_container_width=True)
