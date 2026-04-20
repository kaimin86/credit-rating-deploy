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

# --- Open your sheet (must be created manually and shared first) --- #

# toggle the sheet that you want here. analyst_overrides_short or analyst_overrides_long

spreadsheet = client.open("analyst_overrides_long")

# ========================
# PARAMETERS TO CHANGE WITH EACH NEW YEAR ####
# ========================
SOURCE_YEAR = 2025
TARGET_YEAR = 2026

# ========================
# LOOP THROUGH ALL SHEETS
# ========================
for worksheet in spreadsheet.worksheets():

    sheet_name = worksheet.title
    print(f"Processing: {sheet_name}")

    # Get data
    data = worksheet.get_all_records()
    time.sleep(1)

    if not data:
        print("  -> Empty sheet, skipping")
        continue

    df = pd.DataFrame(data)

    # Safety check: ensure 'year' exists
    if "year" not in df.columns:
        print("  -> No 'year' column, skipping")
        continue

    # ========================
    # CHECK CONDITIONS
    # ========================
    has_old = (df["year"] == SOURCE_YEAR).any()
    has_new = (df["year"] == TARGET_YEAR).any()

    if not has_old:
        print(f"  -> No {SOURCE_YEAR} data in {sheet_name}, skipping")
        continue

    if has_new:
        print(f"  -> {TARGET_YEAR} data already in {sheet_name}, skipping")
        continue

    # ========================
    # COPY PREVIOUS YEAR ROWS
    # ========================
    df_old = df[df["year"] == SOURCE_YEAR].copy()

    # Change year
    df_old["year"] = TARGET_YEAR

    # Replace NaN with empty string (important for Sheets)
    df_old = df_old.fillna("")

    # ========================
    # APPEND TO SHEET
    # ========================
    rows_to_append = df_old.values.tolist()

    worksheet.append_rows(rows_to_append)
    time.sleep(1)

    print(f"  -> Added {len(rows_to_append)} rows for {TARGET_YEAR}")
    time.sleep(0.5)

print("Done.")