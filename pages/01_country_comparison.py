import streamlit as st
import pandas as pd
from pathlib import Path


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

## Make country and year selection boxes

st.markdown("""
<style>
/* 🔹 Limit the max width of selectboxes */
div[data-baseweb="select"] {
    max-width: 300px !important;
}
</style>
""", unsafe_allow_html=True)

# Dropdown to select Country,year, and peer group

country_name = df_transform['name'].unique()
selected_name = st.selectbox("Select Country", sorted(country_name))

# Dropdown to select years

filtered_year = df_transform[df_transform['name'] == selected_name]['year'].unique()
selected_year = st.selectbox("Select Year", sorted(filtered_year, reverse=True))

# Dropdown to select peer group

rating_ranges = {
    "ALL": ( -float("inf"), float("inf") ),
    "IG": (13, 22),
    "HY": (1, 12),
    "AAA": (22, 22),
    "AA":  (19, 21),
    "A":   (16, 18),
    "BBB": (13, 15),
    "BB":  (10, 12),
    "B":  (7, 9),
    "CCC-C": (2,6),
    "D": (0,1)      }

#user selects key from rating_ranges dictionary
selected_bucket = st.selectbox("Peer Group", list(rating_ranges.keys())) 
#Lookup up lower and upper bound based on rating category selected (tuple unpacking)
low, high = rating_ranges[selected_bucket] 
#Filter raw_df and transform_df by that numeric range
filtered_df_transform = df_transform[df_transform['rating'].between(low, high)]
filtered_df_raw = df_raw[df_raw['rating'].between(low, high)]
#writes out how many countreis are in the selected bucket
st.write(f"{len(filtered_df_raw)} countries in bucket {selected_bucket}")

## to do. add rounded rating to both dfs
## tweak code to reflect new name dfs for both

# Sub Header --> 11 rating factors
st.subheader("Percentile Ranking Across 11 Standardized Rating Factors")

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