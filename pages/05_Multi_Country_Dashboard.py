import streamlit as st

URL = "https://loomiscountry-comparison-dtz4lhrti7a5vd3onxcgzx.streamlit.app/"

st.title("Multi-Country Comparison Dashboard")

st.write("""
A dashboard that allows you to compare the macro vitals multiple countries across time. 

Click the link below to access the web-based tool.

Created by Mike Brice.
""")

#st.markdown(
    #f'<a href="{URL}" target="_blank" rel="noopener noreferrer">'
    #f'<button style="padding:0.5rem 1rem; font-size:1rem; cursor:pointer;">'
    #f'Open Comparison Tool ↗</button></a>',
    #unsafe_allow_html=True,
#)

st.markdown((f"{URL}"))
