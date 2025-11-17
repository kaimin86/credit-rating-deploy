import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode, ColumnsAutoSizeMode
import os #--> helps to save user edits on to pc
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import json
import gspread
from google.oauth2.service_account import Credentials
from gsheets_utils import load_override_from_gsheet, save_override_to_gsheet
from pathlib import Path

## Page content. how it shows up on the side bar. how the page is laid out. wide in this case.
st.set_page_config(
    page_title="Country Simulation",
    layout="wide",
)

## Page title
st.title("Country Simulation")

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
        pd.read_excel(BASE_DIR/"scaler_stats_2024_v2.xlsx")
    )
df_transform, df_raw, coeff_index, rating_index, variable_index, country_index, public_rating_index, scalar_stats = load_all_excels()
#.. to go up one level in the folder

## Make copies of df_transform and df_raw. Add rounded rating col to help with fitering.

rounded_transform = df_transform['rating'].round()
df_transform.insert(3,'round_rating',rounded_transform)

rounded_raw = df_raw['rating'].round()
df_raw.insert(3,'round_rating',rounded_raw)

#Inject the width-limiting CSS before your selectbox calls
#else they appeared to be too wide!

st.markdown("""
<style>
/* 🔹 Limit the max width of selectboxes */
div[data-baseweb="select"] {
    max-width: 300px !important;
}
</style>
""", unsafe_allow_html=True)

# Dropdown to select Country

country_name = df_transform['name'].unique()
selected_name = st.selectbox("Select Country", sorted(country_name))

# Dropdown to select years

filtered_year = df_transform[df_transform['name'] == selected_name]['year'].unique()
selected_year = st.selectbox("Select Year", sorted(filtered_year, reverse=True))

## Recreate the long table for the Simulator

# Select Row based on year and country
selected_row_raw = df_raw[(df_raw['name'] == selected_name) & (df_raw['year'] == selected_year)]
selected_row_transform = df_transform[(df_transform['name'] == selected_name) & (df_transform['year'] == selected_year)]

# Use variable_index (variable name file from excel) to form LHS of long_table_df

variable_index_long = variable_index.copy()
long_table_df = variable_index_long

# Transpose the selected country / year row from both the raw and transform data frames

long_table_df_raw = selected_row_raw.T.reset_index() #T is transpose. Reset Index just prevents variable name from being index
long_table_df_raw.columns = ['short_name', 'Raw Value'] #rename columns

long_table_df_transform = selected_row_transform.T.reset_index() #T is transpose. Reset Index just prevents variable name from being index
long_table_df_transform.columns = ['short_name', 'Z-score Value'] #rename columns

# Have to tweak the row names in long_table_raw first col so that single variable factors get renamed as factor for LHS join

long_table_df_raw['short_name'] = long_table_df_raw['short_name'].replace({
    'ngdp_pc': 'wealth_factor',
    'ngdp': 'size_factor',
    'growth_avg': 'growth_factor',
    'inf_avg': 'inflation_factor',
    'gov_debt_gdp': 'govdebt_factor',
    'cab_avg': 'extperf_factor',
    'reserve_fx': 'reservestatus_factor'
})

# merge all 3 table into a single long_table_df using left join

# merge long_table_df with long_table_df_raw
long_table_df = pd.merge(long_table_df, long_table_df_raw, on = 'short_name', how='left')

# then merge the combined table with long_table_df_transform to get the final table
long_table_df = pd.merge(long_table_df, long_table_df_transform, on = 'short_name', how='left')

# Manually Insert Section Headers

## Build section header rows
economy_pillar = pd.DataFrame([{
    'short_name': 'eco_header',
    'long_name': 'REAL ECONOMY PILLAR (25%)',
    'description': '',
    'Raw Value': '',
    'Z-score Value': ''
}])

institutions_pillar = pd.DataFrame([{
    'short_name': 'insti_header',
    'long_name': 'MONETARY & INSTITUTIONS PILLAR (44%)',
    'description': '',
    'Raw Value': '',
    'Z-score Value': ''
}])

fiscal_pillar = pd.DataFrame([{
    'short_name': 'fiscal_header',
    'long_name': 'FISCAL PILLAR (17%)',
    'description': '',
    'Raw Value': '',
    'Z-score Value': ''
}])

external_pillar = pd.DataFrame([{
    'short_name': 'ext_header',
    'long_name': 'EXTERNAL PILLAR (14%)',
    'description': '',
    'Raw Value': '',
    'Z-score Value': ''
}])

## Slice DataFrame based on where the insertions should go
df1 = long_table_df.iloc[:1]   # includes const row
df2 = long_table_df.iloc[1:4]  # economy factors. includes rows 1-3, excludes 4
df3 = long_table_df.iloc[4:15]  # institutional factors, includes rows 4-14, excludes 15
df4 = long_table_df.iloc[15:20]   # fiscal factors, includes rows 15-19, excludes 20
df5 = long_table_df.iloc[20:25]   # external factors, includes rows 20-24, excludes 25

## Combine everything in order to make long_table_df once again

long_table_df = pd.concat(
    [df1, economy_pillar, df2, institutions_pillar, df3, fiscal_pillar, df4, external_pillar, df5],
    ignore_index=True
)

# Change column names to make more presentable

long_table_df = long_table_df.rename(columns={'long_name':'Factor','description': 'Constituent Variables'})

# Connect to google sheets

@st.cache_resource
def init_gsheets_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_info = dict(st.secrets["gcp_service_account"])
    creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

client = init_gsheets_client()

## (the below segment is the old code along with explainers...)

## scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#Defines the authorization scopes — i.e., what permissions your app is requesting from Google. 
#Allows access to read/write Google Sheets data
#Allows access to open the sheet (via Google Drive), even if it's not explicitly listed in your Drive UI
#These are required for gspread to function correctly.

## creds_info = dict(st.secrets["gcp_service_account"]) #--> config object st.secrets. need to convert to a DICT

## creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n") # Repair the escaped-newline issue

#Pulls your service account credentials from Streamlit’s secrets.toml file, where you’ve stored the [gcp_service_account] block.

#creds_dict is now a Python dictionary containing your private key, client email, etc.

##creds = Credentials.from_service_account_info(creds_info, scopes = scope) #important to put scopes = " ". otherwise position wrong

#Converts the credentials dictionary into a usable OAuth2 credentials object that gspread can use to authenticate
#Think of it as logging in with the service account and telling Google what scopes (permissions) your app wants.

## client = gspread.authorize(creds)
#Uses the credentials to create a gspread client — this is your authenticated connection to Google Sheets
#You’ll use client to open any sheet, read, write, or update data.

## sheet_short = client.open("analyst_overrides_short")
#Opens the Google Sheet named "analyst_overrides_short"
#Note that streamlit "sees" this as the entire spreadsheet since we didn't specify specific tab
#Now sheet_short is a live object that lets you read from or write to that google sheet

#With the connection established. Let us load the analyst overrides into our short_table_df
## override_df = load_override_from_gsheet(sheet_short, selected_name, selected_year)
#what this function does is looks at the google sheet object (sheet_short in this case)
#uses selected_name to find the relevant country tab (cos i named each tab with a different country name)
#within the country tab, searches for overrides in a specific year (selected_year) "short_name", "Adjustment", "Analyst Comment"
#calls this out as a df called override_df

# load saved simulations from the g sheet as a dataframe

#already ran the authorization block of code to google sheets above. now we just use client object to open a new sheet
sheet_sim = client.open("analyst_overrides_sim")

## With the connection established. Let us load the analyst overrides into our long_table_df

# Do similar caching to short_table above. only load unique country year combination once unless there is edit.
@st.cache_data
def fetch_overrides_sim(country: str, year: int):
    sheet_sim = client.open("analyst_overrides_sim")
    return load_override_from_gsheet(sheet_sim, country, year)

override_df_sim = fetch_overrides_sim(selected_name, selected_year)

## override_df_long = load_override_from_gsheet(sheet_long, selected_name, selected_year)
#what this function does is looks at the google sheet object (sheet_long in this case)
#uses selected_name to find the relevant country tab (cos i named each tab with a different country name)
#within the country tab, searches for overrides in a specific year (selected_year) "short_name", "Adjustment", "Analyst Comment"
#calls this out as a df called override_df_long

#### STOP HERE FOR NOW ###



### Merge overrides into the main df
long_table_df = pd.merge(long_table_df, override_df_long, on="short_name", how="left")
long_table_df["Adjustment"] = pd.to_numeric(long_table_df["Adjustment"], errors="coerce").fillna(0)
long_table_df["Analyst Comment"] = long_table_df["Analyst Comment"].fillna("")

# custom column for value
# Z-score impact column
# implied rating computed below
# analyst comment column (redundant?)

long_table_df