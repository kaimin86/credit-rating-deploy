# Import require Packages

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

# Set up to connect to google sheets
# note this is a simpler configuration as we are just hooking up form my pc to google sheets
# if we were to do it via streamlit web app it becomes more complex

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_service_account.json", scope)
client = gspread.authorize(creds)

# Load list of countries
# Adjust path and column name as needed
country_list = pd.read_excel("index_country.xlsx")["name"].dropna().unique().tolist()

# --- Open your master sheet (must be created manually and shared first) ---
sheet = client.open("analyst_overrides_short")

# --- Create tabs for each country ---

existing_tabs = [ws.title for ws in sheet.worksheets()]
#sheet is the google sheet object
#.worksheets() is a method that returns a list of all worksheet objects (tabs) inside that heet
#ws.title extrats the name of each tab

for country in country_list:
    if country in existing_tabs:
        print(f"⏭️ Skipping {country} — tab already exists")
        continue

    try:
        sheet.add_worksheet(title=country, rows="1000", cols="4")
        ws = sheet.worksheet(country)
        ws.append_row(["year", "short_name", "Adjustment", "Analyst Comment"])
        print(f"✅ Created tab: {country}")
        time.sleep(1.5)  # prevent quota errors
    except gspread.exceptions.APIError as e:
        print(f"⚠️ Error with {country}: {e}")

# Count how many unique countries you attempted to create
num_countries = len(country_list)

# Count how many tabs (worksheets) actually exist in the sheet
num_tabs = len(sheet.worksheets())

print(f"\n📊 Summary:")
print(f"🌍 Unique countries from list: {num_countries}")
print(f"📄 Total tabs in Google Sheet: {num_tabs}")