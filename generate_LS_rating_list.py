import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gsheets_utils import load_override_from_gsheet, save_override_to_gsheet
import os #--> helps to save user edits on to pc
from openpyxl import Workbook
import streamlit as st
import time

## set the references year that you want
choose_year = 2025

## get the relevant excel files in. Transform into df and dictionary where relevant

# get the name, rating, and predicted rating into a df
df_transform = pd.read_excel("transform_data.xlsx")
df_rating = df_transform.loc[
    df_transform['year'] == choose_year,
    ['name', 'rating', 'predicted_rating']
].reset_index(drop=True)

# get the ratings scale into an excel, and then into a dictonary
rating_index = pd.read_excel("index_rating_scale.xlsx")
#zip pairs the two columns row by row to help make into a dict
rating_dict = dict(zip(rating_index['Numeric'], rating_index['Credit Rating'])) 

# Extract list of unique countries
countries = df_rating['name'].unique().tolist()

## create a connection to google sheets

def init_gsheets_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_info = dict(st.secrets["gcp_service_account"])
    creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

client = init_gsheets_client()

sheet_short = client.open("analyst_overrides_short")

## pull out rating adjustments into a df

adjustment_records = []

for country in countries:
    try:
        print(f"⏳ Reading overrides for {country}…", end="", flush=True)
        ws = sheet_short.worksheet(country)
        records = ws.get_all_records()
        print(" done")                # shows you it finished
        time.sleep(1)
        df_sheet = pd.DataFrame(records)
        
        # ── DROP THE PREDICTED/FINAL ROWS ── 
        if "short_name" in df_sheet.columns:
            df_sheet = df_sheet.loc[
                ~df_sheet["short_name"].isin(["predicted_rating", "final_rating"])
            ]

        # If sheet is empty or no 'year' column, assume zero adjustment
        if 'year' not in df_sheet.columns or df_sheet.empty:
            total_adj = 0.0
        else:
            total_adj = (
                df_sheet.loc[df_sheet['year'] == choose_year, 'Adjustment']
                .sum()
            )
        adjustment_records.append({'name': country, 'Adjustment': total_adj})
    except gspread.exceptions.WorksheetNotFound:
        # If the tab is missing, treat adjustment as zero
        print(f"⚠️ {country} tab not found; assuming 0 adjustment")
        adjustment_records.append({'name': country, 'Adjustment': 0.0})
    time.sleep(1) # throttle before next iteration

df_adjustment = pd.DataFrame(adjustment_records)

## Merge main ratings df and the adjustment df
df_LS_rating = pd.merge(
    df_rating,
    df_adjustment,
    on='name',
    how='left'
)
df_LS_rating['Adjustment'] = df_LS_rating['Adjustment'].fillna(0.0)

#calculate LS_ratings
df_LS_rating['LS_rating'] = df_LS_rating['predicted_rating'] + df_LS_rating['Adjustment']
#force a min max to the LS_ratings
df_LS_rating['LS_rating'] = df_LS_rating['LS_rating'].clip(lower=1,upper=22)

#rename columns
df_LS_rating.rename(columns={
    "rating":"public_rating",
    "predicted_rating":"model_rating"
}, inplace=True)

#map LS_ratings to letter

def rating_to_letter(x):
    key = int(round(x))
    return rating_dict.get(key, "Unknown")

df_LS_rating["LS_letter"] = df_LS_rating["LS_rating"].apply(rating_to_letter)

## export fhe file into excel for sharing
output_path = "LS_rating.xlsx"
df_LS_rating.to_excel(output_path, index = False, engine="openpyxl")
print(f"Exported LS Ratings to {output_path}")
