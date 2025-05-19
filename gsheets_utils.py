# Purpose of this function: Open the google sheet, analyst_overrides_short
# Find the tab based on selected_name
# Within that tab, filter by year. If this is present get it out as a df so that we can stick it to short_table_df
# IF empty, then we just stick an empty df with the col names "short_name", "Adjustment", "Analyst Comment"

def load_override_from_gsheet(sheet, selected_name, selected_year):
    import pandas as pd
    import gspread

    """Loads analyst overrides for a specific Country-Year from a country-named tab."""
    try:
        worksheet = sheet.worksheet(selected_name)  # open the country tab
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)

        filtered = df[df["year"] == selected_year]

        if filtered.empty:
            return pd.DataFrame(columns=["short_name", "Adjustment", "Analyst Comment"])
        else:
            return filtered[["short_name", "Adjustment", "Analyst Comment"]].reset_index(drop=True)

    except gspread.exceptions.WorksheetNotFound:
        print(f"⚠️ Worksheet for {selected_name} not found.")
        return pd.DataFrame(columns=["short_name", "Adjustment", "Analyst Comment"])


# Purpose of this function: Open the google sheet and push over analyst edits into the relevant country tab
# First drops rows for the relevant year so we get a blank slate
# takes updated_df which is just "short_name", "Adjustment", "Analyst Comment" post manual input by our analysts
# appends the "year" column to this which is just populated by selected_year eg. 2024
# this is then vertical joined to the df object we first pulled from google sheets
# finally we push this update back to google sheets to write it in on google cloud

def save_override_to_gsheet(sheet, updated_df, selected_name, selected_year):
    import pandas as pd
    import gspread

    """
    Overwrites analyst overrides in a single tab (per country) for a given Year.
    """

    try:
        worksheet = sheet.worksheet(selected_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"❌ Worksheet for {selected_name} not found. Cannot save.")
        return

    # Load existing records from the tab
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)

    # Drop rows for that year only (not the entire tab)
    df = df[df["year"] != selected_year]

    # Prepare new override rows to add
    new_rows = updated_df.copy()
    new_rows["year"] = selected_year

    # Ensure column order matches the sheet
    columns_order = ["year", "short_name", "Adjustment", "Analyst Comment"]
    df_final = pd.concat([df, new_rows[columns_order]], ignore_index=True)

    # Upload everything back to the worksheet
    data_to_push = [df_final.columns.tolist()] + df_final.values.tolist()
    worksheet.update("A1", data_to_push)
