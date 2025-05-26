import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
import numpy as np

## Page content. how it shows up on the side bar. how the page is laid out. wide in this case.
st.set_page_config(
    page_title="Country Comparison",
    layout="wide",
)

## Page title
st.title("Country Comparison")

## Load the data. Cache so user only loads once upon use.

BASE_DIR = Path(__file__).resolve().parent.parent #file --> refers to where current py lives. parent parent goes up two levels


@st.cache_data
def load_all_excels():
    return (
        pd.read_excel(BASE_DIR/"transform_data.xlsx"),
        pd.read_excel(BASE_DIR/"raw_data.xlsx"),
        pd.read_excel(BASE_DIR/"coefficients_apr2024.xlsx"),
        pd.read_excel(BASE_DIR/"index_rating_scale.xlsx"),
        pd.read_excel(BASE_DIR/"index_variable_name.xlsx"),
        pd.read_excel(BASE_DIR/"index_country.xlsx"),
        pd.read_excel(BASE_DIR/"index_bbg_rating_live.xlsx", sheet_name="hard_code"),
    )
df_transform, df_raw, coeff_index, rating_index, variable_index, country_index, public_rating_index = load_all_excels()
#.. to go up one level in the folder

## Make copies of df_transform and df_raw. Add rounded rating col to help with fitering.

rounded_transform = df_transform['rating'].round()
df_transform.insert(3,'round_rating',rounded_transform)

rounded_raw = df_raw['rating'].round()
df_raw.insert(3,'round_rating',rounded_raw)

## Make country and year selection boxes

st.markdown("""
<style>
/* 🔹 Limit the max width of selectboxes */
div[data-baseweb="select"] {
    max-width: 300px !important;
}
</style>
""", unsafe_allow_html=True)

## Dropdown to select Country,year, and peer group

country_name = df_transform['name'].unique()
selected_name = st.selectbox("Select Country", sorted(country_name))

## Dropdown to select years

filtered_year = df_transform[df_transform['name'] == selected_name]['year'].unique()
selected_year = st.selectbox("Select Year", sorted(filtered_year, reverse=True))

## Dropdown to select peer group

rating_ranges = {
    "ALL": (0, 22),
    "IG": (13, 22),
    "HY": (1, 12),
    "AAA": (22, 22),
    "AA":  (19, 21),
    "A":   (16, 18),
    "BBB": (13, 15),
    "BB":  (10, 12),
    "B":  (7, 9),
    "CCC to C": (2,6),
    "D": (0,1),            }

#user selects key from rating_ranges dictionary
selected_bucket = st.selectbox("Peer Group", list(rating_ranges.keys())) 
#Lookup up lower and upper bound based on rating category selected (tuple unpacking)
low, high = rating_ranges[selected_bucket] 

## Now that selections are in place. Let us begin the filtering process to cut down our df to size

#filter both raw and transform dfs based on year

df_transform_filter = df_transform[df_transform["year"] == selected_year]
df_raw_filter = df_raw[df_raw["year"] == selected_year]

#and then filter further (note new df names w _filter) by narrowing down the rating range
df_transform_filter = df_transform_filter[df_transform_filter['round_rating'].between(low, high)]
df_raw_filter = df_raw_filter[df_raw_filter['round_rating'].between(low, high)]

#select Row based on year and country
selected_row_transform = df_transform[(df_transform['name'] == selected_name) & (df_transform['year'] == selected_year)]
selected_row_raw = df_raw[(df_raw['name'] == selected_name) & (df_raw['year'] == selected_year)]

#check to see if selected row is in the filtered dfs, if not apppend it in
#we do this because sometimes we want to compare a country against a group that higher / lower rated than it

mask_transform = (
    (df_transform_filter['name'] == selected_name) &
    (df_transform_filter['year'] == selected_year)
)
if not mask_transform.any():
    df_transform_filter = pd.concat([df_transform_filter, selected_row_transform], ignore_index=True)

mask_raw = (
    (df_raw_filter['name'] == selected_name) &
    (df_raw_filter['year'] == selected_year)
)
if not mask_raw.any():
    df_raw_filter = pd.concat([df_raw_filter, selected_row_raw], ignore_index=True)


df_transform_filter = df_transform_filter.reset_index(drop=True)
df_raw_filter = df_raw_filter.reset_index(drop=True)

#writes out how many countriss are in the selected bucket
st.write(f"{len(df_raw_filter)} countries in bucket {selected_bucket}")

#st.dataframe(df_transform_filter) #unlock the if you wanna test to see the df rendering properly
#st.dataframe(df_raw_filter)

## Sub Header --> 11 rating factors
st.subheader("Percentile Ranking Across 11 Standardized Rating Factors")

factors = ["wealth_factor",
           "size_factor",
           "growth_factor",
           "inflation_factor",
           "default_factor",
           "governance_factor",
           "fiscalperf_factor",
           "govdebt_factor",
           "extperf_factor",
           "reservebuffer_factor",
           "reservestatus_factor",
           ]
# Build the figure
fig_factor = go.Figure()

# 0) Peers as grey dots (so they render *behind* the boxes) --> see if you want to unlock infuture
#peer_x, peer_y = [], []
#for factor in factors:
    #peer_x += [factor] * len(df_transform_filter)
    #peer_y += df_transform_filter[factor].tolist()

#fig_factor.add_trace(go.Scatter(
    #x=peer_x, y=peer_y, mode="markers",
    #marker=dict(color="lightgrey", size=6, opacity=0.3),
    #showlegend=False, hoverinfo="skip"
#))

#1) Add one box plot per factor

for factor in factors:
    vals = df_transform_filter[factor]
    p5, p25, p50, p75, p95 = np.percentile(vals, [5,25,50,75,95])

    fig_factor.add_trace(go.Box(
        x=[factor],          # ← assign the box to the factor category
        lowerfence=[p5],
        q1=[p25],
        median=[p50],
        q3=[p75],
        upperfence=[p95],
        marker_color="lightblue",
        whiskerwidth=0.5,
        boxpoints=False,
        name=factor
    ))

#2a) Optional overlay the grey dots to showcase other countries



#2) Overlay the selected country as a red dot
#We take the value for each factor from selected_row.iloc[0]

fig_factor.add_trace(go.Scatter(
    x=factors,
    y=[selected_row_transform.iloc[0][f] for f in factors],
    mode="markers",
    marker=dict(color="crimson", size=10),
    hovertemplate=(
        "Country: " + selected_name + "<br>" +
        "Year: "    + str(selected_year)  + "<br>" +
        "Factor: %{x}<br>" +
        "Value: %{y:.2f}<extra></extra>"
    )
))

#3) Layout tweaks
fig_factor.update_layout(
    title=f"How does {selected_name} compare against {selected_bucket} peers across rating factors?",
    yaxis_title="Z-score Value",
    xaxis_tickangle=-45,
    showlegend=False,
    margin=dict(b=150, t=80)
)

#4) In Streamlit, render full-width
st.plotly_chart(fig_factor, use_container_width=True)

# Wealth
st.subheader("Wealth Factor")

# Size
st.subheader("Size Factor")

# Growth
st.subheader("Growth Factor")

# Inflation
st.subheader("Inflation Factor")

# Default
st.subheader("Default History Factor")

# Governance
st.subheader("Governance Factor")

# Fiscal Performance
st.subheader("Fiscal Performance Factor")

# Government Debt
st.subheader("Government Debt Factor")

# External Performance
st.subheader("External Performance Factor")

# FX Reserves
st.subheader("FX Reserves Factor")

# Reserve Currency Status
st.subheader("Reserve Currency Factor")