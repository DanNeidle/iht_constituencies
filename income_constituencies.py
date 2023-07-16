# map data from https://geoportal.statistics.gov.uk/datasets/ons::westminster-parliamentary-constituencies-december-2022-uk-bgc/explore?location=55.233722%2C-3.316534%2C6.66
# 2020/21 income tax data from https://www.gov.uk/government/statistics/income-and-tax-by-parliamentary-constituency-2010-to-2011
# note that the per-constituency samples are small, and so we should be careful about reading too much into these figures
# in particular looks like an error for Fermanagh & South Tyrone - median self employment income of 4490 is half as much as Halifax (the next smallest). 
# So have deleted Fermanagh & South Tyrone data to prevent it messing up the chloropleth colouring

import plotly.graph_objects as go
import geopandas as gpd
import pandas as pd
from PIL import Image

# Constants
CONST_COL_NAME = "Parliamentary Constituency"
PCON22NM = "PCON22NM"
LOGO_PATH = "logo_full_white_on_blue.jpg"
GEOJSON_FILE = "constituencies.geojson"
EXCEL_FILE = 'income_by_constituency.xlsx'
EPSG = 4326
MAX_LEN = 8


datasets = [
    {"data_column": "Total income: Median", "title": "Median income"},
    {"data_column": "Total income: Mean", "title": "Mean income"}
]

"""
# to plot more datasets you can do e.g. 

datasets = [{"data_column": "Total income: Median", "title": "Median income"},
            {"data_column": "Total income: Mean", "title": "Mean income"},
            {"data_column": "Self-employment income: Median", "title": "Median self-employment income"},
            {"data_column": "Employment income: Median", "title": "Median employment income"},
            {"data_column": "Total tax: Median", "title": "Median total income tax"}]
"""


# Helper functions
def format_or_replace_na(series):
    return series.apply(lambda x: f'£{int(x):,}' if pd.notna(x) else "[missing data]")

def pad_string(s, total_length):
    return s + ' ' * (total_length - len(s))

def create_hovertext(merged_iht):
    # Prepare the hovertext data for each row
    hovertext_fields = ['Total tax: Median', 'Self-employment income: Median', 
                        'Employment income: Median', 'Total tax: Mean', 
                        'Self-employment income: Mean', 'Employment income: Mean', 
                        'Total income: Mean', 'Total income: Median']

    hovertext_data = {field: format_or_replace_na(merged_iht[field]) for field in hovertext_fields}

    hovertext = (merged_iht[PCON22NM] + '<br>' +
                 '                   Mean     Median<br>' +
                 'All income:      ' + hovertext_data['Total income: Mean'].apply(lambda x: pad_string(x, MAX_LEN)) + 
                 ' ' + hovertext_data['Total income: Median'].apply(lambda x: pad_string(x, MAX_LEN)) + '<br>' +
                 'All income tax:  ' + hovertext_data['Total tax: Mean'].apply(lambda x: pad_string(x, MAX_LEN)) + 
                 ' ' + hovertext_data['Total tax: Median'].apply(lambda x: pad_string(x, MAX_LEN)) + '<br>' +
                 'Self-emp income: ' + hovertext_data['Self-employment income: Mean'].apply(lambda x: pad_string(x, MAX_LEN)) + 
                 ' ' + hovertext_data['Self-employment income: Median'].apply(lambda x: pad_string(x, MAX_LEN)) + '<br>' +
                 'Emp income:      ' + hovertext_data['Employment income: Mean'].apply(lambda x: pad_string(x, MAX_LEN)) + 
                 ' ' + hovertext_data['Employment income: Median'].apply(lambda x: pad_string(x, MAX_LEN)))

    return hovertext

# Load logo
logo_jpg = Image.open(LOGO_PATH)

# Load GeoJSON file
gdf = gpd.read_file(GEOJSON_FILE)

# Ensure GeoDataFrame is using the correct Coordinate Reference System
gdf = gdf.to_crs(epsg=EPSG)

# Load the excel data
iht_df = pd.read_excel(EXCEL_FILE)

# Replace '&' with 'and' in the Parliamentary Constituency column
iht_df[CONST_COL_NAME] = iht_df[CONST_COL_NAME].str.replace('&', 'and')

# Create a simple dataframe that we will join with the GeoDataFrame
df = pd.DataFrame({
    PCON22NM: gdf[PCON22NM],
    'id': gdf.index
})

# Merge the dataframe with the GeoDataFrame
merged = gdf.merge(df, on=PCON22NM)

# Rename the column to match the GeoJSON file
iht_df = iht_df.rename(columns={CONST_COL_NAME: PCON22NM})

# Merge the IHT data with the GeoDataFrame and add a merge indicator
merged_iht = merged.merge(iht_df, on=PCON22NM, how='outer', indicator=True)

# Print the number of matched and unmatched constituencies
matched = merged_iht[merged_iht._merge == 'both']
unmatched = merged_iht[merged_iht._merge != 'both']
print(f"Number of matched constituencies: {len(matched)}")
print(f"Number of unmatched constituencies: {len(unmatched)}")

if len(unmatched) > 0:
    # Print the unmatched constituencies from the excel
    print("Unmatched constituencies from the excel file:")
    print(unmatched[unmatched._merge == 'right_only'][PCON22NM])

merged_iht['hovertext'] = create_hovertext(merged_iht)

# Prep logo
logo_layout = [dict(
    source=logo_jpg,
    xref="paper", yref="paper",
    x=0.99, y=0.89,
    sizex=0.1, sizey=0.1,
    xanchor="right", yanchor="bottom"
)]


for dataset in datasets:
    # Create the figure
    fig = go.Figure(go.Choroplethmapbox(
        geojson=merged_iht.geometry.__geo_interface__, 
        locations=merged_iht.id, 
        z=merged_iht[dataset["data_column"]],
        hovertext=merged_iht.hovertext, 
        hoverinfo='text',
        colorscale='Blues',
        marker_opacity=0.9, 
        marker_line_width=1, 
        marker_line_color='black', 
        showscale=False
    ))
    
    # Update layout
    fig.update_layout(
        images=logo_layout,
        mapbox_style="carto-positron", 
        mapbox_zoom=4.7, 
        mapbox_center={"lat": 55.3781, "lon": -3.4360},
        hoverlabel=dict(font_size=12, font_family="Courier New"),
        annotations=[
            go.layout.Annotation(
                showarrow=False,
                text=f"{dataset['title']}<br>by constituency in 2020/21",
                align='left',
                xanchor='left',
                x=0.05,
                yanchor='top',
                y=.95,
                font=dict(size=24, family='Arial Black')
            )
        ],
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    # Show the figure
    fig.show()
