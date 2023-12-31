# map data from https://geoportal.statistics.gov.uk/datasets/ons::westminster-parliamentary-constituencies-december-2022-uk-bgc/explore?location=55.233722%2C-3.316534%2C6.66
# 2019/20 IHT data from https://www.gov.uk/government/statistics/inheritance-tax-statistics-table-1212-estimated-numbers-of-estates-liable-to-tax-on-death-by-parliamentary-constituency
# note that, where there are five or fewer estates paying IHT in a constituency, no data is shown (data privacy reasons)


import plotly.graph_objects as go
import geopandas as gpd
import pandas as pd
import numpy as np
from PIL import Image

#load logo
logo_jpg = Image.open("logo_full_white_on_blue.jpg")

# Load GeoJSON file
gdf = gpd.read_file("constituencies.geojson")

datasets = [{"data_column": "Amount (£ million)", "title": "Inheritance tax £ paid"},
            {"data_column": "Number", "title": "Number of inheritance tax estates"}]

# prep logo
logo_layout = [dict(
            source=logo_jpg,
            xref="paper", yref="paper",
            x=0.99, y=0.89,
            sizex=0.1, sizey=0.1,
            xanchor="right", yanchor="bottom"
        )]


# Ensure GeoDataFrame is using the correct Coordinate Reference System
gdf = gdf.to_crs(epsg=4326)


for x in datasets:

    # Create a simple dataframe that we will join with the GeoDataFrame
    df = pd.DataFrame({
        'PCON22NM': gdf['PCON22NM'],
        'id': gdf.index
    })

    # Merge the dataframe with the GeoDataFrame
    merged = gdf.merge(df, on='PCON22NM')

    # Load the excel data
    iht_df = pd.read_excel('iht_by_constituency.xlsx')

    # Rename the column to match the GeoJSON file
    iht_df.rename(columns={"Parliamentary Constituency": "PCON22NM"}, inplace=True)

    # Merge the IHT data with the GeoDataFrame and add a merge indicator
    merged_iht = merged.merge(iht_df, on='PCON22NM', how='outer', indicator=True)

    # Print the number of matched and unmatched constituencies
    matched = merged_iht[merged_iht._merge == 'both']
    unmatched = merged_iht[merged_iht._merge != 'both']
    print(f"Number of matched constituencies: {len(matched)}")
    print(f"Number of unmatched constituencies: {len(unmatched)}")

    if len(unmatched) > 0:
        # Print the unmatched constituencies from the excel
        print("Unmatched constituencies from the excel file:")
        print(unmatched[unmatched._merge == 'right_only']['PCON22NM'])

    # Create a separate hovertext for constituencies with no data
    no_data_mask = merged_iht['Number'].isnull() | merged_iht[x["data_column"]].isnull()
    merged_iht.loc[no_data_mask, 'hovertext'] = merged_iht.loc[no_data_mask, 'PCON22NM'] + ': no data'

    # For the other constituencies, use the existing formula to create hovertext
    data_mask = ~no_data_mask
    merged_iht.loc[data_mask, 'hovertext'] = merged_iht.loc[data_mask, 'PCON22NM'] + '<br>' + '£' + merged_iht.loc[data_mask, 'Amount (£ million)'].astype(int).astype(str) + 'm IHT (' + merged_iht.loc[data_mask, 'Number'].astype(int).astype(str) + ' estates)'

    # Apply square root transformation to datacolumn
    merged_iht['sqrt_amount'] = np.where(merged_iht[x["data_column"]].isnull(), -1, np.sqrt(merged_iht[x["data_column"]]))

    # Create the figure
    fig = go.Figure(go.Choroplethmapbox(geojson=merged_iht.geometry.__geo_interface__, 
                                        locations=merged_iht.id, 
                                        z=merged_iht['sqrt_amount'],  # Use the square root-transformed amount for coloring
                                        hovertext=merged_iht.hovertext, 
                                        hoverinfo='text',
                                        colorscale='Blues',  # Use the standard 'Blues' color scale
                                        marker_opacity=0.9, 
                                        marker_line_width=1, 
                                        marker_line_color='black', 
                                        showscale=False))

    # Set mapbox style, center and zoom level
    fig.update_layout(images=logo_layout,
                    mapbox_style="carto-positron", 
                    mapbox_zoom=4.7, 
                    mapbox_center = {"lat": 55.3781, "lon": -3.4360})

    # Add title annotation
    fig.update_layout(
        annotations=[
            go.layout.Annotation(
                showarrow=False,
                text=f"{x['title']}<br>per constituency in 2019/20", 
                align='left',  # left alignment
                xanchor='left',
                x=0.05,  
                yanchor='top',
                y=.95,  
                font=dict(
                    size=24,  # font size
                    family='Arial Black'  # bold font
                )
            )
        ]
    )


    # Update layout
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    # Show the figure
    fig.show()
