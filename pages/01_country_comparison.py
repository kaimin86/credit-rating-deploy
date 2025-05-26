import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
import numpy as np

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

rounded_transform = df_transform['rating'].round()
df_transform.insert(3,'round_rating',rounded_transform)

rounded_raw = df_raw['rating'].round()
df_raw.insert(3,'round_rating',rounded_raw)

## Make country and year selection boxes

st.markdown("""
<style>
/* 🔹 Limit the max width of selectboxes */
div[data-baseweb="select"] {
    max-width: 300px !important;
}
</style>
""", unsafe_allow_html=True)

## Dropdown to select Country,year, and peer group

country_name = df_transform['name'].unique()
selected_name = st.selectbox("Select Country", sorted(country_name))

## Dropdown to select years

filtered_year = df_transform[df_transform['name'] == selected_name]['year'].unique()
selected_year = st.selectbox("Select Year", sorted(filtered_year, reverse=True))

## Dropdown to select peer group

rating_ranges = {
    "ALL": (0, 22),
    "IG": (13, 22),
    "HY": (1, 12),
    "AAA": (22, 22),
    "AA":  (19, 21),
    "A":   (16, 18),
    "BBB": (13, 15),
    "BB":  (10, 12),
    "B":  (7, 9),
    "CCC to C": (2,6),
    "D": (0,1),            }

#user selects key from rating_ranges dictionary
selected_bucket = st.selectbox("Peer Group", list(rating_ranges.keys())) 
#Lookup up lower and upper bound based on rating category selected (tuple unpacking)
low, high = rating_ranges[selected_bucket] 

## Now that selections are in place. Let us begin the filtering process to cut down our df to size

#filter both raw and transform dfs based on year

df_transform_filter = df_transform[df_transform["year"] == selected_year]
df_raw_filter = df_raw[df_raw["year"] == selected_year]

#and then filter further (note new df names w _filter) by narrowing down the rating range
df_transform_filter = df_transform_filter[df_transform_filter['round_rating'].between(low, high)]
df_raw_filter = df_raw_filter[df_raw_filter['round_rating'].between(low, high)]

#select Row based on year and country
selected_row_transform = df_transform[(df_transform['name'] == selected_name) & (df_transform['year'] == selected_year)]
selected_row_raw = df_raw[(df_raw['name'] == selected_name) & (df_raw['year'] == selected_year)]

#check to see if selected row is in the filtered dfs, if not apppend it in
#we do this because sometimes we want to compare a country against a group that higher / lower rated than it

mask_transform = (
    (df_transform_filter['name'] == selected_name) &
    (df_transform_filter['year'] == selected_year)
)
if not mask_transform.any():
    df_transform_filter = pd.concat([df_transform_filter, selected_row_transform], ignore_index=True)

mask_raw = (
    (df_raw_filter['name'] == selected_name) &
    (df_raw_filter['year'] == selected_year)
)
if not mask_raw.any():
    df_raw_filter = pd.concat([df_raw_filter, selected_row_raw], ignore_index=True)


df_transform_filter = df_transform_filter.reset_index(drop=True)
df_raw_filter = df_raw_filter.reset_index(drop=True)

#writes out how many countriss are in the selected bucket
st.write(f"{len(df_raw_filter)} countries in bucket {selected_bucket}")

#st.dataframe(df_transform_filter) #unlock the if you wanna test to see the df rendering properly
#st.dataframe(df_raw_filter)

## Sub Header --> 11 rating factors
st.subheader("Percentile Ranking Across 11 Standardized Rating Factors")

factors = ["wealth_factor",
           "size_factor",
           "growth_factor",
           "inflation_factor",
           "default_factor",
           "governance_factor",
           "fiscalperf_factor",
           "govdebt_factor",
           "extperf_factor",
           "reservebuffer_factor",
           "reservestatus_factor",
           ]

factors_dict = {
    "wealth_factor":       "Wealth",
    "size_factor":         "Size",
    "growth_factor":       "Growth",
    "inflation_factor":    "Inflation",
    "default_factor":      "Default History",
    "governance_factor":   "Governance",
    "fiscalperf_factor":   "Fiscal Performance",
    "govdebt_factor":      "Government Debt",
    "extperf_factor":      "External Performance",
    "reservebuffer_factor":"FX Reserves",
    "reservestatus_factor":"Reserve Currency Status"
}

variable_dict = {
    "ngdp_pc":       "Nominal GDP per capita (US$)",
    "ngdp":         "Nominal GDP (bil US$)",
    "growth_avg":       "Avg 10Yr GDP Growth t-5 to t+4 (%)",
    "inf_avg":    "Average 10Yr Inflation t-5 to t+4 (%)",
    "default_hist":      "Default History Dummy (1=Yes, 0=No)",
    "default_decay":   "Default Decay (1 at incidence)",
    "voice_acct":   "Voice and Accountability (Z-score)",
    "pol_stab":      "Political Stability (Z-score)",
    "gov_eff":      "Government Effectiveness (Z-score)",
    "reg_qual":"Regulatory Quality (Z-score)",
    "rule_law":"Rule of Law (Z-score)",
    "cont_corrupt": "Control of Corruption (Z-score)",
    "fb_avg": "Avg 10Yr Fiscal Balance t-5 to t+4 (% of GDP)",
    "gov_rev_gdp": "Government Revenue (% of GDP)",
    "ir_rev": "Interest Payment (% of Revenue)",
    "gov_debt_gdp": "Government Debt (% of GDP)",
    "cab_avg": "Avg 10Yr Current Account Balance t-5 to t+4 (% of GDP)",
    "reserve_gdp": "FX Reserves (% of GDP)",
    "import_cover": "FX Reserves (months of imports)",
    "reserve_fx": "Reserve Currency Status (1 = Yes, 0 = No)"

}

# Build the figure
fig_factor = go.Figure()

# 0) Peers as grey dots (so they render *behind* the boxes) --> see if you want to unlock infuture
#peer_x, peer_y = [], []
#for factor in factors:
    #peer_x += [factor] * len(df_transform_filter)
    #peer_y += df_transform_filter[factor].tolist()

#fig_factor.add_trace(go.Scatter(
    #x=peer_x, y=peer_y, mode="markers",
    #marker=dict(color="lightgrey", size=6, opacity=0.3),
    #showlegend=False, hoverinfo="skip"
#))

#1) Add one box plot per factor

for factor in factors:
    # look up the long label once
    long_label = factors_dict[factor]
    vals = df_transform_filter[factor]
    p5, p25, p50, p75, p95 = np.percentile(vals, [5,25,50,75,95])

    fig_factor.add_trace(go.Box(
        x=[long_label], # ← assign the box to the factor category
        name = long_label,                    
        lowerfence=[p5],
        q1=[p25],
        median=[p50],
        q3=[p75],
        upperfence=[p95],
        marker_color="#DAEEF3",
        whiskerwidth=0.5,
        boxpoints=False
        
    ))

#2) Overlay the selected country as a red dot
#We take the value for each factor from selected_row.iloc[0]

fig_factor.add_trace(go.Scatter(
    x=[factors_dict[f] for f in factors],
    y=[selected_row_transform.iloc[0][f] for f in factors],
    mode="markers",
    marker=dict(color="#1A3B73", size=10),
    hovertemplate=(
        "Country: " + selected_name + "<br>" +
        "Year: "    + str(selected_year)  + "<br>" +
        "Factor: %{x}<br>" +
        "Value: %{y:.2f}<extra></extra>"
    )
))

#3) Layout tweaks
fig_factor.update_layout(
    title=f"How does {selected_name} compare against {selected_bucket} peers across rating factors?",
    yaxis_title="Z-score Value",
    xaxis_tickangle=-45,
    showlegend=False,
    margin=dict(b=150, t=80)
)

#4) Tweak Axes
# Make axis titles & tick labels black, and draw black axis lines
fig_factor.update_xaxes(
    title_font_color="black",
    tickfont_color="black",
    showline=True,
    linecolor="black",
    mirror=False   # if you only want the bottom line
)
fig_factor.update_yaxes(
    title_font_color="black",
    tickfont_color="black",
    showline=True,
    linecolor="black",
    mirror=False   # if you only want the left line
)

#5) In Streamlit, render full-width
st.plotly_chart(fig_factor, use_container_width=True)

# Wealth
st.subheader("Wealth Factor")

# 1) Your data
short_var = "ngdp_pc"
vals = df_raw_filter[short_var].dropna()

# 2) Compute FD‐optimal edges
edges   = np.histogram_bin_edges(vals, bins="fd")
bin_size = edges[1] - edges[0]
start, end = edges[0], edges[-1]

# 3) Compute percentiles
p5, p25, p50, p75, p95 = np.percentile(vals, [5,25,50,75,95])

# 4) Build the figure
fig = go.Figure()

# Histogram with FD bins
fig.add_trace(go.Histogram(
    x=vals,
    xbins=dict(
        start=start,
        end=end,
        size=bin_size
    ),
    marker_color="#DAEEF3",
    opacity=0.75,
    name="Peers"
))

# 5) Dotted percentile lines
for x_val, label in [
    (p5,  "5th"),
    (p25, "25th"),
    (p50, "Median"),
    (p75, "75th"),
    (p95, "95th"),
]:
    fig.add_vline(
        x=x_val,
        line=dict(color="gray", dash="dot", width=2),
        annotation_text=label,
        annotation_position="top left"
    )

# 6) Country line & label
my_val = selected_row_raw.iloc[0][short_var]
fig.add_vline(
    x=my_val,
    line=dict(color="red", width=3),
    annotation_text=selected_name,
    annotation_position="bottom right",
    annotation_font_color="red"
)

# 7) Style axes
long_var = variable_dict[short_var]
fig.update_xaxes(
    title_text=long_var,
    title_font_color="black",
    tickfont_color="black",
    showline=True,
    linecolor="black"
)
fig.update_yaxes(
    title_text="Count",
    title_font_color="black",
    tickfont_color="black",
    showline=True,
    linecolor="black"
)

#A) Compute the country’s percentile
percentile = np.mean(vals <= my_val) * 100  # gives a value between 0–100

#B) Build a multi-line HTML title
title_text = (
    f"{selected_name} vs {selected_bucket} peers<br>"
    # second line in red:
    f"<span style='color:red'>{selected_name}: ${my_val:,.0f} "
    f"({percentile:.1f}th percentile)</span>"
)

# 8) Final layout & render
fig.update_layout(
    title=title_text,
    template="simple_white",
    margin=dict(t=80, b=40, l=40, r=20),
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

#st.plotly_chart(fig, use_container_width=True)

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