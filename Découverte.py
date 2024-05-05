import streamlit as st 
from streamlit_folium import st_folium
import folium
import duckdb as dck
import plotly.express as px
import os
import pandas as pd
import jenkspy
import geojson
from branca.element import Template, MacroElement

st.title("Weather warming")

print('START')
# Open a connection to DuckDB
con = dck.connect(database=':memory:', read_only=False)
tab1, tab2, tab3, tab4 = st.tabs(["Accueil", "Températures", "Précipitations", "Insolation"])
####################################
#### GLOBAL
#############################
############
##### MAP
############
def assign_color(altitude, breaks, colors):
    for i in range(len(breaks) - 1):
        if breaks[i] <= altitude <= breaks[i + 1]:
            return colors[i]
    return colors[-1]

def create_map_with_altitude_colors(geojson_file):

    # Load GeoJSON data
    with open(geojson_file, 'r') as f:
        geojson_data = geojson.load(f)

    # Extract relevant properties from GeoJSON
    features = geojson_data['features']
    latitudes = [feature['geometry']['coordinates'][1] for feature in features]
    longitudes = [feature['geometry']['coordinates'][0] for feature in features]
    altitudes = [feature['properties']['altitude'] for feature in features]

    # Calculate average latitude and longitude
    average_latitude = sum(latitudes) / len(latitudes)
    average_longitude = sum(longitudes) / len(longitudes)

    # Create a map object centered around the mean of latitudes and longitudes
    mymap = folium.Map(location=[average_latitude, average_longitude], zoom_start=6)

    # Define altitude breaks using Jenks natural breaks classification
    breaks = jenkspy.jenks_breaks(altitudes, n_classes=4)
    colors = ['green', 'yellow', 'orange', 'red', 'brown']

    legend_template = """
    {% macro html(this, kwargs) %}
    <div id='maplegend' class='maplegend' 
        style='position: absolute; z-index: 9999; background-color: rgba(255, 255, 255, 0.5);
        border-radius: 6px; padding: 10px; font-size: 10.5px; right: 20px; top: 20px;'>     
    <div class='legend-scale'>Altitude des stations (m) :
    <ul class='legend-labels'>  
        <li><span style='background: green; opacity: 0.75;'></span>0</li>
        <li><span style='background: yellow; opacity: 0.75;'></span>500</li>
        <li><span style='background: orange; opacity: 0.75;'></span>1000</li>
        <li><span style='background: red; opacity: 0.75;'></span>1500</li>
        <li><span style='background: brown; opacity: 0.75;'></span>2000</li>
    </ul>
    </div>
    </div> 
    <style type='text/css'>
    .maplegend .legend-scale ul {margin: 0; padding: 0; color: #0f0f0f;}
    .maplegend .legend-scale ul li {list-style: none; line-height: 18px; margin-bottom: 1.5px;}
    .maplegend ul.legend-labels li span {float: left; height: 16px; width: 16px; margin-right: 4.5px;}
    </style>
    {% endmacro %}
    """
    # Add the legend to the map
    macro = MacroElement()
    macro._template = Template(legend_template)
    mymap.get_root().add_child(macro)

    # Add markers for each location
    for feature in features:
        properties = feature['properties']
        coordinates = feature['geometry']['coordinates']
        altitude = properties['altitude']

        # Assign color based on altitude using Jenks natural breaks
        color = assign_color(altitude, breaks, colors)

        folium.Circle(
            location=[coordinates[1], coordinates[0]],
            radius=5000,  # Adjust radius as needed
            popup=properties['nom'],
            color='transparent',  # Outline color
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            # Disable zooming and panning
            zoom_control=False,
            scrollWheelZoom=False,
            dragging=False
        ).add_to(mymap)

    return mymap
#########################
###### DATAFRAME dropdown filter
###########################
def process_data(file_path_liste, file_path_sh_rr, key_nb):
    file_list_1 = con.execute(f"""SELECT * FROM read_csv("{file_path_liste}")""").fetchdf()
    
    file_list_1 = file_list_1.sort_values(by=['nom_usuel'])

    # Allow user to choose the source file
    selected_file = st.selectbox("Sélectionnez une station : ", file_list_1['nom_usuel'], key=f"""sb{key_nb}""")

    # Get the corresponding num_serie for the selected file
    num_serie = file_list_1.loc[file_list_1['nom_usuel'] == selected_file, 'num_serie'].iloc[0]

    # Prepare SQL query to directly filter the CSV based on num_serie
    query = f"""SELECT "YYYYMM"::text AS Année_mois, "VALEUR" AS Precipitations
                FROM read_csv('{file_path_sh_rr}/SH_{num_serie}.csv')
                ORDER BY "YYYYMM" """

    # Execute the query to get the DataFrame
    df_filtered = con.execute(query).fetchdf()

    # Add 'nom_usuel' column to DataFrame
    df_filtered['nom_usuel'] = selected_file

    # Display the DataFrame
    st.dataframe(df_filtered[['Année_mois', 'Precipitations', 'nom_usuel']])
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')


    csv = convert_df(df_filtered)

    st.download_button(
    "Télécharger",
    csv,
    "file.csv",
    "text/csv",
    key=f"""dl-csv{key_nb}"""
    )
#### END GLOBAL

#######################################
############    TAB 1     ############
#######################################
with tab1 : 
    st.subheader("Bienvenue sur weather warming, cette appli vise à utiliser et valoriser les données ouvertes de [Météo-France](https://meteo.data.gouv.fr/).")
    st.caption("Compte-tenu de la prégnance du changement climatique dans notre quotidien ainsi que dans les médias et les travaux scientifiques, l'accent sera mis sur les séries temporelles de données climatologiques dites \"de référence pour l'étude du changement climatique\".")
    st.caption("Dans un premier temps nous souhaitons explorer ce que renferment ces données, quels sont les fichiers et les variables qu'ils contiennent afin de donner du contexte au reste de l'application et au traitements qui seront réalisés.")
    st.caption("""Le reste de l'application sera consacré à l'exploration de ces données ainsi qu'à des indicateurs tentant de mettre en exergue le changement climatique, mais aussi les implications de ce dernier sur nos territoires. 
               En effet, que ce soit du point de vue des températures ou des précipitations, le réchauffement du climat ne semble pas avoir les mêmes conséquences selon les territoires.
               """)
    st.subheader("warnings")
    st.caption("""Une première mise en garde doit être faite concernant cette série temporelle au regard de son objectif. En effet, le changement climatique
               ou tout du moins ses origines et ses causes prennent racine dans la période de la révolution industrielle et le début de l'emploi massif de ressources fossiles 
               comme sources d'énergie. Si l'on sait que les quantités de gaz à effet de serre n'ont fait qu'augmenter depuis cette période, le jeu de données étudié au travers de 
               cette application ne permettra pas d'observer l'évolution du climat jusqu'à cette période puisque les séries commencent à partir des années 50 (vous le verrez, chaque série a sa date de début / fin)
               """)
#######################################
############    TAB 2     ############
#######################################
with tab2 : 
    df = con.execute('select "nom_usuel",  "altitude(m)", "date_debut_serie(YYYYMM)"::text as "date_debut_serie(YYYYMM)", "date_fin_serie(YYYYMM)"::text as "date_fin_serie(YYYYMM)" , "latitude(°)" ,"longitude(°)" from read_csv("./data/Liste_SH_TX_metro.csv")').fetchdf()

    st.dataframe(df[["nom_usuel", "altitude(m)", "date_debut_serie(YYYYMM)", "date_fin_serie(YYYYMM)"]], 1000, 200)
    
    # Example usage:
    map_with_altitude_colors_temp = create_map_with_altitude_colors('./data/geo_station.geojson')
    st_data = st_folium(map_with_altitude_colors_temp, width = 725, returned_objects=[], key="map1")
    
        ###############//
    #######//   DROPDOWN 
    ###############//
        # Lire le fichier de liste

    process_data("./data/Liste_SH_TX_metro.csv", "./data/SH_TX_metropole", 1)

    print('TAB 2 OK')
#######################################
############    TAB 3     ############
#######################################
with tab3 : 
    df = con.execute('select "nom_usuel",  "altitude(m)", "date_debut_serie(YYYYMM)"::text as "date_debut_serie(YYYYMM)", "date_fin_serie(YYYYMM)"::text as "date_fin_serie(YYYYMM)" , "latitude(°)" ,"longitude(°)" from read_csv("./data/Liste_SH_TX_metro.csv")').fetchdf()

    st.dataframe(df[["nom_usuel", "altitude(m)", "date_debut_serie(YYYYMM)", "date_fin_serie(YYYYMM)"]], 1000, 200)
    # Create a map object centered around the mean of latitudes and longitudes
    # Load GeoJSON data
    map_with_altitude_colors_precip = create_map_with_altitude_colors('./data/result_diff_rr.geojson')
    st_data = st_folium(map_with_altitude_colors_precip, width = 725, returned_objects=[], key="map2")


        ###############//
    #######// DATAFRAME 

    process_data("./data/Liste_SH_RR_metro.csv", "./data/SH_RR_metropole", 2)

    print('TAB 3 OK')
        
        
