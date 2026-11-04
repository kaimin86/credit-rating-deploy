import streamlit as st
from pathlib import Path

st.title("Help Page")

# Folder containing this script; adjust if your files sit elsewhere in the repo
BASE_DIR = Path(__file__).parent.parent #this goes up to level. .parent means still in pages folder. .parent again goes into main folder
guide_path = BASE_DIR / "Analyst Guide To Ratings Model.pdf"     # <- your actual file name
changes_path = BASE_DIR / "LS_rating_oct_26.xlsx"         # <- your actual file name

st.write("Download the Analyst Guide to the Ratings Model Here")

with open(guide_path, "rb") as f:
    st.download_button(
        label="📄 Download Analyst Guide",
        data=f,
        file_name=guide_path.name,
        mime="application/pdf",
    )


st.write("Download this spreadsheet to see what changed compared to the previous update")

with open(changes_path, "rb") as f:
    st.download_button(
        label="📊 Download Changes Spreadsheet",
        data=f,
        file_name=changes_path.name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

