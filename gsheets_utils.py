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

        # ————————————————————————————————
        # If the sheet is empty *or* this year has never been used,
        # return an empty override DataFrame:
        if df.empty or selected_year not in df["year"].values:
            return pd.DataFrame(columns=["short_name", "Adjustment", "Analyst Comment"])
        # ————————————————————————————————

        # At this point we know df has at least one row for selected_year
        filtered = df[df["year"] == selected_year]
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
    - If the tab is empty, just writes the new rows.
    - If selected_year is not in existing data, appends new rows.
    - Otherwise, drops old rows for that year and appends new ones.
    """
    try:
        worksheet = sheet.worksheet(selected_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"❌ Worksheet for {selected_name} not found. Cannot save.")
        return

    records = worksheet.get_all_records()
    df = pd.DataFrame(records)

    # Prepare new rows
    new_rows = updated_df.copy()
    new_rows["year"] = selected_year
    columns_order = ["year", "short_name", "Adjustment", "Analyst Comment"]
    new_rows = new_rows[columns_order]

    # Case 1: completely empty tab (no data beyond headers)
    if df.empty:
        df_final = new_rows

    # Case 2: tab has data but not for this year
    elif selected_year not in df["year"].values:
        df_final = pd.concat([df, new_rows], ignore_index=True)

    # Case 3: tab has data for this year already
    else:
        df_remaining = df[df["year"] != selected_year]
        df_final = pd.concat([df_remaining, new_rows], ignore_index=True)

    # Push back to the sheet
    data_to_push = [df_final.columns.tolist()] + df_final.values.tolist()
    worksheet.update("A1", data_to_push)
