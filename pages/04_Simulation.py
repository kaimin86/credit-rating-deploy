import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode, ColumnsAutoSizeMode
import os #--> helps to save user edits on to pc
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import json
import gspread
from google.oauth2.service_account import Credentials
from gsheets_utils_sim import load_override_from_gsheet, save_override_to_gsheet
from pathlib import Path

## Page content. how it shows up on the side bar. how the page is laid out. wide in this case.
st.set_page_config(
    page_title="Country Simulation",
    layout="wide",
)

## Page title
st.title("Country Simulation")

## Instructions
st.markdown(
    """
    **Instructions:** Use this simulation tool to help you with your rating adjustments.
    Key in custom values into the **Custom Value** column.
    Hit **Save Analyst Input**.
    The rating impact (in notches) will appear in
    <span style="color:#FF0000; font-weight:600;">red</span>
    in the last column.
    """,
    unsafe_allow_html=True
)

## Load the data. Cache so user only loads once upon use.

BASE_DIR = Path(__file__).resolve().parent.parent #file --> refers to where current py lives. parent parent goes up two levels

@st.cache_data
def load_all_excels():
    return (
        pd.read_excel(BASE_DIR/"transform_data.xlsx"),
        pd.read_excel(BASE_DIR/"raw_data.xlsx"),
        pd.read_excel(BASE_DIR/"coefficients_2024_WGI_new.xlsx"),
        pd.read_excel(BASE_DIR/"index_rating_scale.xlsx"),
        pd.read_excel(BASE_DIR/"index_variable_name.xlsx"),
        pd.read_excel(BASE_DIR/"index_country.xlsx"),
        pd.read_excel(BASE_DIR/"index_bbg_rating_live.xlsx", sheet_name="hard_code"),
        pd.read_excel(BASE_DIR/"scaler_stats_2024_v3.xlsx")
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

# Force Z-score cols and raw value cols to numeric to avoid annoying mixed type error
long_table_df["Raw Value"] = pd.to_numeric(long_table_df["Raw Value"],errors="coerce")
long_table_df["Z-score Value"] = pd.to_numeric(long_table_df["Z-score Value"],errors="coerce")

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
#note i edit at the load_override_from_gsheet that lives in gsheets_util_sim.py to convert "" to nan at the pull step..

override_df_sim = fetch_overrides_sim(selected_name, selected_year)

## override_df_long = load_override_from_gsheet(sheet_long, selected_name, selected_year)
#what this function does is looks at the google sheet object (sheet_long in this case)
#uses selected_name to find the relevant country tab (cos i named each tab with a different country name)
#within the country tab, searches for overrides in a specific year (selected_year) "short_name", "Adjustment", "Analyst Comment"
#calls this out as a df called override_df_long

### Merge overrides into the main df
long_table_df = pd.merge(long_table_df, override_df_sim, on="short_name", how="left")
long_table_df["Custom Value"] = pd.to_numeric(long_table_df["Custom Value"], errors="coerce")

### COMPUTE AND THEN MERGE RATINGS IMPACT INTO MAIN DF. THIS IS A MULTI STEP PROCESS!! ###

### This block of code calculates the ratings impact from raw user input ###

# create a copy of scalar stats

scalar_stats_rename = scalar_stats.copy()
scalar_stats_rename.columns.values[0] = "short_name" #rename the first col which was default "Unnamed 0"

scalar_stats_rename['short_name'] = scalar_stats_rename['short_name'].replace({
    'ngdp_pc': 'wealth_factor',
    'ngdp': 'size_factor',
    'growth_avg': 'growth_factor',
    'inf_avg': 'inflation_factor',
    'gov_debt_gdp': 'govdebt_factor',
    'cab_avg': 'extperf_factor',
    'reserve_fx': 'reservestatus_factor'
})

### standardize the custom value inputs variable by variable.

# define helper functions to grab scalars from tables!

def get_scalar_small(df, row, col,default=np.nan):
    # use to grab scalars from small dfs
    s = df.loc[df["short_name"] == row, col] #grab pandas series based on short_name value and col name
    if s.empty: #if cannot find anything, return default which is equals to nan
        return default
    v = s.iloc[0] #converts pandas series into a scalar
    return default if pd.isna(v) else v

def get_scalar_big(df, col, name, year, default=np.nan):
    # use to grab scalars from big dfs like transform_df
    s = df.loc[
        (df["name"] == name) &
        (df["year"] == year),
        col
    ]

    if s.empty: #if cannot find anything, return default which is equals to nan
        return default
    
    v = s.iloc[0] #converts pandas series into a scalar

    return default if pd.isna(v) else v

## wealth_factor / ngdp_pc

#call out single value as scalar
wealth_factor = get_scalar_small(df=override_df_sim,row="wealth_factor",col="Custom Value")
#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(wealth_factor):
    wealth_factor = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #guard against zero edge case
    zero_wealth = 0.01
    wealth_factor = max(wealth_factor,zero_wealth)
    #log it
    wealth_factor = np.log(wealth_factor) # first we log it
    #detrend it
    wealth_factor_trend = get_scalar_big(df_transform,col="trend_median_ngdp_pc",name=selected_name,year=selected_year)
    wealth_factor = wealth_factor - wealth_factor_trend
    #z-score it with the scalar stats
    wealth_mean = get_scalar_small(df=scalar_stats_rename,row="wealth_factor",col="mean")
    wealth_std = get_scalar_small(df=scalar_stats_rename,row="wealth_factor",col="std")
    wealth_factor = (wealth_factor - wealth_mean) / wealth_std
#print(wealth_factor)
    
## size_factor / ngdp

#call out single value as scalar
size_factor = get_scalar_small(df=override_df_sim,row="size_factor",col="Custom Value")
#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(size_factor):
    size_factor = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #guard against zero edge case
    zero_size = 0.01
    size_factor = max(size_factor,zero_size)
    #log it
    size_factor = np.log(size_factor) # first we log it
    #detrend it
    size_factor_trend = get_scalar_big(df_transform,col="trend_median_ngdp",name=selected_name,year=selected_year)
    size_factor = size_factor - size_factor_trend
    #z-score it with the scalar stats
    size_mean = get_scalar_small(df=scalar_stats_rename,row="size_factor",col="mean")
    size_std = get_scalar_small(df=scalar_stats_rename,row="size_factor",col="std")
    size_factor = (size_factor - size_mean) / size_std
#print(size_factor)

## growth_factor / growth_avg

#call out single value as scalar
growth_factor = get_scalar_small(df=override_df_sim,row="growth_factor",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(growth_factor):
    growth_factor = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    growth_mean = get_scalar_small(df=scalar_stats_rename,row="growth_factor",col="mean")
    growth_std = get_scalar_small(df=scalar_stats_rename,row="growth_factor",col="std")
    growth_factor = (growth_factor - growth_mean) / growth_std
    #Windsorize growth avg to + / - 4 sd. max
    growth_factor = np.clip(growth_factor, -4, 4) #use numpy to clip a scalar value.
#print(growth_factor)

## inflation_factor / inflation_avg

#call out single value as scalar
inflation_factor = get_scalar_small(df=override_df_sim,row="inflation_factor",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(inflation_factor):
    inflation_factor = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #compute the 99th percentile for inflation
    percentile_99_inf_avg = np.nanpercentile(df_raw['inf_avg'], 99)
    #Replace values above the 99th percentile with the 99th percentile value
    inflation_factor = min(inflation_factor, percentile_99_inf_avg)
    #if inflation is below zero, force it to a small number 0.01
    zero = 0.01
    inflation_factor = max(inflation_factor,zero)
    #z-score it with the scalar stats
    inflation_mean = get_scalar_small(df=scalar_stats_rename,row="inflation_factor",col="mean")
    inflation_std = get_scalar_small(df=scalar_stats_rename,row="inflation_factor",col="std")
    inflation_factor = (inflation_factor - inflation_mean) / inflation_std
    #change sign by *-1 to aid interpretation
    inflation_factor = inflation_factor*(-1)
#print(inflation_factor)

### default_factor --> Combination factor

## default_hist

#call out single value as scalar
default_hist = get_scalar_small(df=override_df_sim,row="default_hist",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(default_hist):
    default_hist = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    default_hist_mean = get_scalar_small(df=scalar_stats_rename,row="default_hist",col="mean")
    default_hist_std = get_scalar_small(df=scalar_stats_rename,row="default_hist",col="std")
    default_hist = (default_hist - default_hist_mean) / default_hist_std
     #change sign by *-1 to aid interpretation
    #default_hist = default_hist*(-1)
#print(default_hist)

## default_decay

#call out single value as scalar
default_decay = get_scalar_small(df=override_df_sim,row="default_decay",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(default_decay):
    default_decay = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    default_decay_mean = get_scalar_small(df=scalar_stats_rename,row="default_decay",col="mean")
    default_decay_std = get_scalar_small(df=scalar_stats_rename,row="default_decay",col="std")
    default_decay = (default_decay - default_decay_mean) / default_decay_std
    #change sign by *-1 to aid interpretation
    #default_decay = default_decay*(-1)
#print(default_decay)

## Combining into default_factor for reference
#default_factor = ((default_hist + default_decay)/2)*-1 #multiply by -1 to aid interpretation

### governance_factor --> Combination factor

## voice_acct

#call out single value as scalar
voice_acct = get_scalar_small(df=override_df_sim,row="voice_acct",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(voice_acct):
    voice_acct = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    voice_acct_mean = get_scalar_small(df=scalar_stats_rename,row="voice_acct",col="mean")
    voice_acct_std = get_scalar_small(df=scalar_stats_rename,row="voice_acct",col="std")
    voice_acct = (voice_acct - voice_acct_mean) / voice_acct_std
#print(voice_acct)

## pol_stab

#call out single value as scalar
pol_stab = get_scalar_small(df=override_df_sim,row="pol_stab",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(pol_stab):
    pol_stab = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    pol_stab_mean = get_scalar_small(df=scalar_stats_rename,row="pol_stab",col="mean")
    pol_stab_std = get_scalar_small(df=scalar_stats_rename,row="pol_stab",col="std")
    pol_stab = (pol_stab - pol_stab_mean) / pol_stab_std
#print(pol_stab)

## gov_eff

#call out single value as scalar
gov_eff = get_scalar_small(df=override_df_sim,row="gov_eff",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(gov_eff):
    gov_eff = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    gov_eff_mean = get_scalar_small(df=scalar_stats_rename,row="gov_eff",col="mean")
    gov_eff_std = get_scalar_small(df=scalar_stats_rename,row="gov_eff",col="std")
    gov_eff = (gov_eff - gov_eff_mean) / gov_eff_std
#print(gov_eff)

## reg_qual

#call out single value as scalar
reg_qual = get_scalar_small(df=override_df_sim,row="reg_qual",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(reg_qual):
    reg_qual = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    reg_qual_mean = get_scalar_small(df=scalar_stats_rename,row="reg_qual",col="mean")
    reg_qual_std = get_scalar_small(df=scalar_stats_rename,row="reg_qual",col="std")
    reg_qual = (reg_qual - reg_qual_mean) / reg_qual_std
#print(reg_qual)

## rule_law

#call out single value as scalar
rule_law = get_scalar_small(df=override_df_sim,row="rule_law",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(rule_law):
    rule_law = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    rule_law_mean = get_scalar_small(df=scalar_stats_rename,row="rule_law",col="mean")
    rule_law_std = get_scalar_small(df=scalar_stats_rename,row="rule_law",col="std")
    rule_law = (rule_law - rule_law_mean) / rule_law_std
#print(rule_law)

## cont_corrupt

#call out single value as scalar
cont_corrupt = get_scalar_small(df=override_df_sim,row="cont_corrupt",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(cont_corrupt):
    cont_corrupt = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    cont_corrupt_mean = get_scalar_small(df=scalar_stats_rename,row="cont_corrupt",col="mean")
    cont_corrupt_std = get_scalar_small(df=scalar_stats_rename,row="cont_corrupt",col="std")
    cont_corrupt = (cont_corrupt - cont_corrupt_mean) / cont_corrupt_std
#print(cont_corrupt)

## Combining into governance_factor for reference
#governance_factor = (voice_acct + pol_stab + gov_eff + reg_qual + rule_law + cont_corrupt)/6 #multiply by -1 to aid interpretation

### fiscalperf_factor --> Combination Factor

## fb_avg

#call out single value as scalar
fb_avg = get_scalar_small(df=override_df_sim,row="fb_avg",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(fb_avg):
    fb_avg = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    fb_avg_mean = get_scalar_small(df=scalar_stats_rename,row="fb_avg",col="mean")
    fb_avg_std = get_scalar_small(df=scalar_stats_rename,row="fb_avg",col="std")
    fb_avg = (fb_avg - fb_avg_mean) / fb_avg_std
#print(fb_avg)

## gov_rev_gdp

#call out single value as scalar
gov_rev_gdp = get_scalar_small(df=override_df_sim,row="gov_rev_gdp",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(gov_rev_gdp):
    gov_rev_gdp = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    gov_rev_gdp_mean = get_scalar_small(df=scalar_stats_rename,row="gov_rev_gdp",col="mean")
    gov_rev_gdp_std = get_scalar_small(df=scalar_stats_rename,row="gov_rev_gdp",col="std")
    gov_rev_gdp = (gov_rev_gdp - gov_rev_gdp_mean) / gov_rev_gdp_std
#print(gov_rev_gdp)

## ir_rev

#call out single value as scalar
ir_rev = get_scalar_small(df=override_df_sim,row="ir_rev",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(ir_rev):
    ir_rev = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    ir_rev_mean = get_scalar_small(df=scalar_stats_rename,row="ir_rev",col="mean")
    ir_rev_std = get_scalar_small(df=scalar_stats_rename,row="ir_rev",col="std")
    ir_rev = (ir_rev - ir_rev_mean) / ir_rev_std
    #change sign by *-1 to aid interpretation
    ir_rev = ir_rev*(-1)
#print(ir_rev)

## Combining into fiscalperf_factor for reference
#fiscalperf_factor = (fb_avg+gov_rev_gdp+ir_rev)/3

## govdebt_factor/gov_debt_gdp

#call out single value as scalar
govdebt_factor = get_scalar_small(df=override_df_sim,row="govdebt_factor",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(govdebt_factor):
    govdebt_factor = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #guard against zero edge case
    zero_debt = 0.01
    govdebt_factor = max(govdebt_factor,zero_debt)
    #compute the 99th percentile for govdebt_factor
    percentile_99_gov_debt_gdp = np.nanpercentile(df_raw['gov_debt_gdp'], 99)
    #Replace values above the 99th percentile with the 99th percentile value
    govdebt_factor = min(govdebt_factor, percentile_99_gov_debt_gdp)
    #z-score it with the scalar stats
    govdebt_mean = get_scalar_small(df=scalar_stats_rename,row="govdebt_factor",col="mean")
    govdebt_std = get_scalar_small(df=scalar_stats_rename,row="govdebt_factor",col="std")
    govdebt_factor = (govdebt_factor - govdebt_mean) / govdebt_std
    #change sign by *-1 to aid interpretation
    govdebt_factor = govdebt_factor*(-1)
#print(govdebt_factor)

## extperf_factor / cab
#call out single value as scalar
extperf_factor = get_scalar_small(df=override_df_sim,row="extperf_factor",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(extperf_factor):
    extperf_factor = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #compute the 1st percentile for cab_avg/extperf_factor
    percentile_1_cab_avg = np.nanpercentile(df_raw['cab_avg'],1)
    #compute the 99th percentile for cab_avg/extperf_factor
    percentile_99_cab_avg = np.nanpercentile(df_raw['cab_avg'],99)
    # Windsorize cab_avg to + / - 30% of GDP max
    extperf_factor = np.clip(extperf_factor, -30, 30) #use numpy to clip a scalar value.
    #z-score it with the scalar stats
    extperf_mean = get_scalar_small(df=scalar_stats_rename,row="extperf_factor",col="mean")
    extperf_std = get_scalar_small(df=scalar_stats_rename,row="extperf_factor",col="std")
    extperf_factor = (extperf_factor - extperf_mean) / extperf_std
#print(extperf_factor)


### reservebuffer_factor --> Composite factor

## reserve_gdp

#call out single value as scalar
reserve_gdp = get_scalar_small(df=override_df_sim,row="reserve_gdp",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(reserve_gdp):
    reserve_gdp = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #guard against zero edge case
    zero_reserve = 0.01
    reserve_gdp = max(reserve_gdp,zero_reserve)
    #log it
    reserve_gdp = np.log(reserve_gdp) # first we log it
    #z-score it with the scalar stats
    reserve_gdp_mean = get_scalar_small(df=scalar_stats_rename,row="reserve_gdp",col="mean")
    reserve_gdp_std = get_scalar_small(df=scalar_stats_rename,row="reserve_gdp",col="std")
    reserve_gdp = (reserve_gdp - reserve_gdp_mean) / reserve_gdp_std
#print(reserve_gdp)

## import_cover

#call out single value as scalar
import_cover = get_scalar_small(df=override_df_sim,row="import_cover",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(import_cover):
    import_cover = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #force negative values to a small number
    zero_import = 0.01
    import_cover = max(import_cover,zero_import)
    #log it
    import_cover = np.log(import_cover) # first we log it
    #z-score it with the scalar stats
    import_cover_mean = get_scalar_small(df=scalar_stats_rename,row="import_cover",col="mean")
    import_cover_std = get_scalar_small(df=scalar_stats_rename,row="import_cover",col="std")
    import_cover = (import_cover - import_cover_mean) / import_cover_std
#print(import_cover)

## Combining into reservebuffer_factor for reference
#reservebuffer_factor = (reserve_gdp + import_cover)/2

## reservestatus_factor / reserve_fx

#call out single value as scalar
reservestatus_factor = get_scalar_small(df=override_df_sim,row="reservestatus_factor",col="Custom Value")

#check if its a na value. happens if its blank. if so. returns na. if not run transformation.
if pd.isna(reservestatus_factor):
    reservestatus_factor = np.nan
else:
    #else we start to transform it the way we do when building our model#
    #z-score it with the scalar stats
    reservestatus_factor_mean = get_scalar_small(df=scalar_stats_rename,row="reservestatus_factor",col="mean")
    reservestatus_factor_std = get_scalar_small(df=scalar_stats_rename,row="reservestatus_factor",col="std")
    reservestatus_factor = (reservestatus_factor - reservestatus_factor_mean) / reservestatus_factor_std
#print(reservestatus_factor)

### Start Building out calc_df to input intermediate calculations in

# make a copy of long_table_df and then drop the informative columns.
# the goal here is to keep just what is needed to input the calculated variables and to check our work 
calc_df = long_table_df.copy().drop(columns=["Factor", "Constituent Variables"],errors="ignore")
calc_df["Custom Z-score"] = np.nan

# drop my computed custom Z-score values (if any) into calc_df
# create a dictionary mapping short_name to custom computed z score value
custom_z_map = {
    "wealth_factor": wealth_factor,
    "size_factor": size_factor,
    "growth_factor": growth_factor,
    "inflation_factor": inflation_factor,
    "default_hist": default_hist,
    "default_decay": default_decay,
    "voice_acct": voice_acct,
    "pol_stab": pol_stab,
    "gov_eff": gov_eff,
    "reg_qual": reg_qual,
    "rule_law": rule_law,
    "cont_corrupt": cont_corrupt,
    "fb_avg": fb_avg,
    "gov_rev_gdp": gov_rev_gdp,
    "ir_rev": ir_rev,
    "govdebt_factor": govdebt_factor,
    "extperf_factor": extperf_factor,
    "reserve_gdp": reserve_gdp,
    "import_cover": import_cover,
    "reservestatus_factor": reservestatus_factor,
}
#use a for loop to loop through my custom dict and input the custom values in based on short_name into "Custom Z-score" column
for k, v in custom_z_map.items():
    calc_df.loc[calc_df["short_name"] == k, "Custom Z-score"] = v

## work out the ratings impact by multiplying by the appropriate discount factor and coefficient

# create a copy of coeff_index

coeff_index_rename = coeff_index.copy()
coeff_index_rename.columns.values[0] = "short_name" #rename the first col which was default "Unnamed 0"

# Merge it into the calc table as a "Coefficient" column
calc_df = calc_df.merge(coeff_index_rename[["short_name", "coefficient"]],on="short_name",how="left")

# define function(s) to make your life easier when finding values
def get_calc_input(df,row,col,default=np.nan):
    s = df.loc[df["short_name"] == row, col]
    if s.empty:
        return default
    return s.iloc[0]

# work out the ratings impacts line by line
wealth_factor_r = (wealth_factor - get_calc_input(calc_df,"wealth_factor","Z-score Value"))*get_calc_input(calc_df,"wealth_factor","coefficient")

size_factor_r = (size_factor - get_calc_input(calc_df,"size_factor","Z-score Value"))*get_calc_input(calc_df,"size_factor","coefficient")

growth_factor_r = (growth_factor - get_calc_input(calc_df,"growth_factor","Z-score Value"))*get_calc_input(calc_df,"growth_factor","coefficient")

inflation_factor_r = (inflation_factor - get_calc_input(calc_df,"inflation_factor","Z-score Value"))*get_calc_input(calc_df,"inflation_factor","coefficient")

default_hist_r = (default_hist - get_calc_input(calc_df,"default_hist","Z-score Value"))*get_calc_input(calc_df,"default_factor","coefficient")*-1/2
default_decay_r = (default_decay - get_calc_input(calc_df,"default_decay","Z-score Value"))*get_calc_input(calc_df,"default_factor","coefficient")*-1/2
default_factor_r = np.nansum([default_hist_r,default_decay_r])

voice_acct_r = (voice_acct - get_calc_input(calc_df,"voice_acct","Z-score Value"))*get_calc_input(calc_df,"governance_factor","coefficient")*1/6
pol_stab_r = (pol_stab - get_calc_input(calc_df,"pol_stab","Z-score Value"))*get_calc_input(calc_df,"governance_factor","coefficient")*1/6
gov_eff_r = (gov_eff - get_calc_input(calc_df,"gov_eff","Z-score Value"))*get_calc_input(calc_df,"governance_factor","coefficient")*1/6
reg_qual_r = (reg_qual - get_calc_input(calc_df,"reg_qual","Z-score Value"))*get_calc_input(calc_df,"governance_factor","coefficient")*1/6
rule_law_r = (rule_law - get_calc_input(calc_df,"rule_law","Z-score Value"))*get_calc_input(calc_df,"governance_factor","coefficient")*1/6
cont_corrupt_r = (cont_corrupt - get_calc_input(calc_df,"cont_corrupt","Z-score Value"))*get_calc_input(calc_df,"governance_factor","coefficient")*1/6
governance_factor_r = np.nansum([voice_acct_r,pol_stab_r,gov_eff_r,reg_qual_r,rule_law_r,cont_corrupt_r])

fb_avg_r = (fb_avg - get_calc_input(calc_df,"fb_avg","Z-score Value"))*get_calc_input(calc_df,"fiscalperf_factor","coefficient")*1/3
gov_rev_gdp_r = (gov_rev_gdp - get_calc_input(calc_df,"gov_rev_gdp","Z-score Value"))*get_calc_input(calc_df,"fiscalperf_factor","coefficient")*1/3
ir_rev_r = (ir_rev - get_calc_input(calc_df,"ir_rev","Z-score Value"))*get_calc_input(calc_df,"fiscalperf_factor","coefficient")*1/3
fiscalperf_factor_r = np.nansum([fb_avg_r,gov_rev_gdp_r,ir_rev_r])

govdebt_factor_r = (govdebt_factor - get_calc_input(calc_df,"govdebt_factor","Z-score Value"))*get_calc_input(calc_df,"govdebt_factor","coefficient")

extperf_factor_r = (extperf_factor - get_calc_input(calc_df,"extperf_factor","Z-score Value"))*get_calc_input(calc_df,"extperf_factor","coefficient")

reserve_gdp_r = (reserve_gdp - get_calc_input(calc_df,"reserve_gdp","Z-score Value"))*get_calc_input(calc_df,"reservebuffer_factor","coefficient")*1/2
import_cover_r = (import_cover - get_calc_input(calc_df,"import_cover","Z-score Value"))*get_calc_input(calc_df,"reservebuffer_factor","coefficient")*1/2
reservebuffer_factor_r = np.nansum([reserve_gdp_r,import_cover_r])

reservestatus_factor_r = (reservestatus_factor - get_calc_input(calc_df,"reservestatus_factor","Z-score Value"))*get_calc_input(calc_df,"reservestatus_factor","coefficient")

## append the "ratings impact" into a calc_df with short_name as reference

# create a blank "Rating Impact" column
calc_df["Rating Impact"] = np.nan

# create a custom map to map the rating impact in notches to corresponding short_name row

custom_r_map = {
    "wealth_factor": wealth_factor_r,
    "size_factor": size_factor_r,
    "growth_factor": growth_factor_r,
    "inflation_factor": inflation_factor_r,
    "default_factor": default_factor_r,
    "default_hist": default_hist_r,
    "default_decay": default_decay_r,
    "governance_factor": governance_factor_r,
    "voice_acct": voice_acct_r,
    "pol_stab": pol_stab_r,
    "gov_eff": gov_eff_r,
    "reg_qual": reg_qual_r,
    "rule_law": rule_law_r,
    "cont_corrupt": cont_corrupt_r,
    "fiscalperf_factor": fiscalperf_factor_r,
    "fb_avg": fb_avg_r,
    "gov_rev_gdp": gov_rev_gdp_r,
    "ir_rev": ir_rev_r,
    "govdebt_factor": govdebt_factor_r,
    "extperf_factor": extperf_factor_r,
    "reservebuffer_factor":reservebuffer_factor_r,
    "reserve_gdp": reserve_gdp_r,
    "import_cover": import_cover_r,
    "reservestatus_factor": reservestatus_factor_r,
}

# use a for loop to append computed rating impact values to column called "Rating Impact"

for k, v in custom_r_map.items():
    calc_df.loc[calc_df["short_name"] == k, "Rating Impact"] = v

### Merge Ratings impact into the main df
long_table_df = long_table_df.merge(
    calc_df[["short_name", "Rating Impact"]],
    on="short_name",
    how="left"
)

# Initialize AgGrid to create interactive table in 

## Basic column options
gb_long = GridOptionsBuilder.from_dataframe(long_table_df)

## Apply to all columns
gb_long.configure_default_column(
    editable=False, #cannot edit
    sortable=False, #cannot sort
    filter=False, #cannot filter
    resizable=False, #cannot resize
    suppressHeaderMenuButton=True #hide the 3 dots button for me. FINALLY!
)

## Define formatters which basically controls how values display in the column
## Define styles which basically shows how values look in a column (bold etc etc)
## editable call_back (restrictions) that i can pass into the editable arg to control which cells can or cannot be edited

combined_formatter_long = JsCode("""
function(params) {
  const v = params.value;
  // 1) Blank out null/undefined/empty
  if (v === undefined || v === null || v === '') {
    return '';
  }
  // 2) If numeric, show one decimal
  if (!isNaN(v)) {
    return parseFloat(v).toFixed(2);
  }
  // 3) Otherwise (e.g. letter ratings), just display as string
  return v.toString();
}
""")

rawvalue_formatter_long = JsCode("""
function(params) {
  const v  = params.value;
  const id = params.data.short_name;

  // 1) Handle null/undefined/empty
  if (v === undefined || v === null || v === '') {
    // show “–” for these specific headers
    const dashRows = [
      'default_factor',
      'governance_factor',
      'fiscalperf_factor',
      'reservebuffer_factor'
    ];
    return dashRows.includes(id) ? '–' : '';
  }

  // 2) Parse number
  const num = parseFloat(v);
  if (isNaN(num)) {
    // if it wasn’t numeric, just show it as text
    return v.toString();
  }

  // 3) Formatting by row key
  switch (id) {
    case 'wealth_factor':
      // comma thousands, no decimals
      return num.toLocaleString(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      });

    case 'default_hist':
    case 'reservestatus_factor':
      // integer (0 or 1)
      return num.toFixed(0);

    default:
      // everything else: one decimal place
      return num.toFixed(1);
  }
}
""")

hide_na_formatter_long = JsCode("""
function(params) {
    return params.value === undefined || params.value === null ? '' : params.value.toString();
}
""") ### “If the value is missing, show blank. If it’s a letter like 'A', just display it as-is — don't try to force into a numeric”

hide_zero_formatter_long = JsCode("""
function(params) {
  const v = params.value;
  // 1) blank out null/undefined and zero
  if (v === undefined || v === null || v === 0) {
    return '';
  }
  // 2) if it’s numeric, show two decimals
  if (!isNaN(v)) {
    return parseFloat(v).toFixed(2);
  }
  // 3) otherwise (e.g. letter), just render as string
  return v.toString();
}
""")

customvalue_formatter_long = JsCode("""
function(params) {
  const v  = params.value;
  const id = params.data.short_name;

  // -----------------------------
  // 1) Handle null / undefined / empty
  // -----------------------------
  if (v === undefined || v === null || v === '') {
    const dashRows = [
      'default_factor',
      'governance_factor',
      'fiscalperf_factor',
      'reservebuffer_factor'
    ];
    return dashRows.includes(id) ? '–' : '';
  }

  // -----------------------------
  // 2) Try numeric parsing
  // -----------------------------
  const num = parseFloat(v);
  if (isNaN(num)) {
    // non-numeric text → show as-is
    return v.toString();
  }

  // -----------------------------
  // 3) Formatting by row key
  // -----------------------------
  switch (id) {

    case 'wealth_factor':
      // comma thousands, no decimals
      return num.toLocaleString(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      });

    case 'default_hist':
    case 'reservestatus_factor':
      // integer flags (0 / 1)
      return num.toFixed(0);

    default:
      // everything else: one decimal
      return num.toFixed(1);
  }
}
""")


purple_values_style = JsCode("""
function(params) {
  const id = params.data.short_name;
  const purpleIds = [
    'default_hist',
    'default_decay',
    'voice_acct',
    'pol_stab',
    'gov_eff',
    'reg_qual',
    'rule_law',
    'cont_corrupt',
    'fb_avg',
    'gov_rev_gdp',
    'ir_rev',
    'reserve_gdp',
    'import_cover'
  ];
  if (purpleIds.includes(id)) {
    return { color: '#B21740' };
  }
  return null;
}
""")

purple_description_style = JsCode("""
function(params) {
  const id = params.data.short_name;
  const purpleIds = [
    'default_hist',
    'default_decay',
    'voice_acct',
    'pol_stab',
    'gov_eff',
    'reg_qual',
    'rule_law',
    'cont_corrupt',
    'fb_avg',
    'gov_rev_gdp',
    'ir_rev',
    'reserve_gdp',
    'import_cover'
  ];
  if (purpleIds.includes(id)) {
    // purple, normal weight
    return { color: '#B21740', 'font-weight': 'normal' };
  }
  // all other rows: black, bold
  return { color: 'black', 'font-weight': 'bold' };
}
""")

adjustment_style = JsCode("""
function(params) {
  const id = params.data.short_name;
  // list of rows to render in blue + bold
  const blueIds = [
    'wealth_factor',
    'size_factor',
    'growth_factor',
    'inflation_factor',
    'default_factor',
    'governance_factor',
    'fiscalperf_factor',
    'govdebt_factor',
    'extperf_factor',
    'reservebuffer_factor',
    'reservestatus_factor'
  ];
  if (blueIds.includes(id)) {
    return {
      color: '#0000FF',
      'font-weight': 'bold'
    };
  }
  // everything else: maroon-ish, normal weight
  return {
    color: '#B21740',
    'font-weight': 'normal'
  };
}
""")

customvalue_style = JsCode("""
function(params) {
  const id = params.data.short_name;
  // list of rows to render in blue + bold
  const blueIds = [
    'wealth_factor',
    'size_factor',
    'growth_factor',
    'inflation_factor',
    'default_factor',
    'governance_factor',
    'fiscalperf_factor',
    'govdebt_factor',
    'extperf_factor',
    'reservebuffer_factor',
    'reservestatus_factor'
  ];
  if (blueIds.includes(id)) {
    return {
      color: '#0000FF',
      'font-weight': 'bold'
    };
  }
  // everything else: blue, normal weight
  return {
    color: '#0000FF',
    'font-weight': 'normal'
  };
}
""")

ratingimpact_style = JsCode("""
function(params) {
  const id = params.data.short_name;
  // list of rows to render in red + bold
  const blueIds = [
    'wealth_factor',
    'size_factor',
    'growth_factor',
    'inflation_factor',
    'default_factor',
    'governance_factor',
    'fiscalperf_factor',
    'govdebt_factor',
    'extperf_factor',
    'reservebuffer_factor',
    'reservestatus_factor'
  ];
  if (blueIds.includes(id)) {
    return {
      color: '#FF0000',
      'font-weight': 'bold'
    };
  }
  // everything else: red, normal weight
  return {
    color: '#FF0000',
    'font-weight': 'normal'
  };
}
""")

analyst_style = JsCode("""
function(params) {
  const id = params.data.short_name;
  const blueIds = [
    'wealth_factor',
    'size_factor',
    'growth_factor',
    'inflation_factor',
    'default_factor',
    'governance_factor',
    'fiscalperf_factor',
    'govdebt_factor',
    'extperf_factor',
    'reservebuffer_factor',
    'reservestatus_factor'
  ];
  if (blueIds.includes(id)) {
    return { color: '#0000FF' };      // blue, no bold
  }
  return { color: '#B21740' };        // maroon-ish, no bold
}
""")

factor_style_long = JsCode("""
function(params) {
  const style = {};
  // header sentinels to skip
  const headers = [
    "eco_header",
    "insti_header",
    "fiscal_header",
    "ext_header",
    "final_header"
  ];
  // Shade every non-header row
  if (!headers.includes(params.data.short_name)) {
    style['background-color'] = '#DAEEF3';
  }
  // Bold all text
  style['font-weight'] = 'bold';
  return style;
}
""")

editable_criteria_adjustment = JsCode("""
function(params) {
  const id = params.data.short_name;
  // list of short_name values that should NOT be editable
  const locked = [
    '',                  // blank header rows
    'const',
    'default_factor',
    'governance_factor',
    'fiscalperf_factor',
    'reservebuffer_factor',
    'eco_header',
    'insti_header',
    'fiscal_header',
    'ext_header'                                                                   
  ];
  // return false (lock) when id is in our locked list; true otherwise
  return !locked.includes(id);
}
""")

editable_criteria_analyst = JsCode("""
function(params) {
  const id = params.data.short_name;
  // lock only blank header rows and the 'const' row
  if (id === '' || id === 'const') {
    return false;
  }
  return true;
}
""")

## Apply column by column configuration in df...

gb_long.configure_column("short_name", hide=True)
gb_long.configure_column("Factor", valueFormatter=combined_formatter_long, cellStyle=factor_style_long,maxWidth=320,minWidth=320)
gb_long.configure_column("Constituent Variables", valueFormatter=combined_formatter_long, cellStyle=purple_description_style,
                         maxWidth=420,minWidth=420)
gb_long.configure_column("Raw Value", valueFormatter=rawvalue_formatter_long, filter=False, cellStyle = purple_values_style,maxWidth=120,minWidth=120)
gb_long.configure_column("Z-score Value", valueFormatter=combined_formatter_long, filter=False, cellStyle = purple_values_style,maxWidth=140,minWidth=140)

## Make Custom Value columns editable

gb_long.configure_column("Custom Value",valueFormatter=customvalue_formatter_long, cellStyle = customvalue_style,
                         editable = editable_criteria_adjustment, filter=False, headerClass="ag-header-cell-label-left",
                         cellClass="ag-left-aligned-cell",maxWidth=120,minWidth=120)

## Make Configuration for Rating Impact column
gb_long.configure_column("Rating Impact",valueFormatter=combined_formatter_long, cellStyle = ratingimpact_style,
                         filter=False, headerClass="ag-header-cell-label-left",
                         cellClass="ag-left-aligned-cell",maxWidth=140,minWidth=140)

## Now we apply the color schemes to the grid

custom_css_override_long = {
    # header cell label (the text container)
    ".ag-header-cell-label": {
        "background-color": "#1A3B73 !important",
        "color":            "white !important",
        "font-weight":      "bold !important",
        #"font-size":        "16px !important"
    },
    # the very header row wrapper (fills behind the labels)
    ".ag-header": {
        "background-color": "#1A3B73 !important"
    },
}

LS_gridOptions_long = gb_long.build()
LS_gridOptions_long["getRowStyle"] = JsCode("""
  function(params) {
    // list of the exact Factor values you want to style
    const headers = [
      "REAL ECONOMY PILLAR (25%)",
      "MONETARY & INSTITUTIONS PILLAR (44%)",
      "FISCAL PILLAR (17%)",
      "EXTERNAL PILLAR (14%)",
      "SOVEREIGN CREDIT RATING"
    ];
    // if this row’s Factor is one of the headers, return a style object
    if (headers.includes(params.data.Factor)) {
      return {
        "font-weight":      "bold",
        "background-color": "#B6CEE4"   // light tint—change as you like
      };
    }
    return null;  // otherwise use default styling
  }
""")

## Finally we initialize the grid

grid_response_long = AgGrid(
    long_table_df,
    gridOptions=LS_gridOptions_long,
    custom_css = custom_css_override_long,
    allow_unsafe_jscode=True,
    update_mode='VALUE_CHANGED',  #necessary to capture edits
    fit_columns_on_grid_load=False,# we’re sizing to contents instead
    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS, #columns size to fit contents
    suppressColumnVirtualisation=True,    # measure off-screen columns too
    theme='alpine',
    height=500,  # manually control table height without scrolling
    )


## Captures edits made by user in grid
updated_df_long = grid_response_long["data"] #extracts the updated DataFrame after user edits from AgGrid (Custom Value col)
updated_df_long["Custom Value"] = pd.to_numeric(updated_df_long["Custom Value"], errors="coerce") #safety layer to ensure only numeric captured
#errors = coerce means you dont crash the app if non numeric. just input nan value. which we then turn to zero!

# Put the Save + Export buttons side by side
# carve the page into 3 chunks: 
#  • 1 unit for btn1 
#  • 1 unit for blank space
#  • 6 units of blank space

save_col_long, blank_col_1, blank_col_2= st.columns([2, 2, 6])

with save_col_long:
    if st.button("💾 Save Analyst Input",key="sim_save"):

      # Save only the override columns (factor-level edits) to a file
      columns_to_save_long = ["short_name", "Custom Value"]
      updated_subset_long = updated_df_long[columns_to_save_long]

      # this is a fail safe as google sheets does not recognize nan values, so we convert it to blank ""
      to_save = updated_subset_long.copy()
      to_save["Custom Value"] = pd.to_numeric(to_save["Custom Value"], errors="coerce")
      to_save["Custom Value"] = to_save["Custom Value"].where(to_save["Custom Value"].notna(), "")

      # Use the full Google Sheet, then pass selected_name to target the right tab
      save_override_to_gsheet(sheet_sim, to_save, selected_name, selected_year)

      # clear only the cache for fetch_overrides
      fetch_overrides_sim.clear()

      st.success("✅ Overrides saved and rating updated.")
      st.rerun() #rerun entire script from top to bottom so analyst can see update immediately


#### STOP HERE FOR NOW ###

# turn off filter for raw and z-score
# fix col widths
# change custom value fonts to blue
# allow for zero values in custom value
# change rating impact fonts to red


## keep in mind the zero / na problem in the custom value col. we will get to it again.

# create custom column for value
#long_table_df["Custom Value"] = np.nan


## here you visualize tables to check things in streamlit

#long_table_df
#override_df_sim 
#scalar_stats_rename
#calc_df
#coeff_index

#st.write(long_table_df["short_name"].dtype)

# create coefficient column. merge it with the coeff df via left join. hide it later in streamlit
#coeff_index = coeff_index.reset_index(names="short_name")
#long_table_df = pd.merge(long_table_df,coeff_index,on="short_name", how="left")

### TEST
#print(long_table_df["short_name"].dtype)
#print(coeff_index["short_name"].dtype)

#print(long_table_df["short_name"].head())
#print(coeff_index["short_name"].head())

# create mean column & sd column via merge from scalar_stats


# create adj. Z-score column --> this one have to think about it? maybe jump straight to the delta?

# create rating impact column

# implied rating computed below
# analyst comment column (redundant?)

