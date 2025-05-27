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

# map each short_var to a Python format‐string for its value
format_map = {
    "ngdp_pc":"${value:,.0f}",
    "ngdp":"${value:,.1f} bil",
    "growth_avg": "{value:.1f}%",
    "inf_avg":    "{value:.1f}%",
    "default_hist": "{value:.0f}",
    "default_decay": "{value:.2f}",
    "voice_acct": "{value:.2f}",
    "pol_stab": "{value:.2f}",
    "gov_eff": "{value:.2f}",
    "reg_qual":"{value:.2f}",
    "rule_law":"{value:.2f}",
    "cont_corrupt": "{value:.2f}",
    "fb_avg": "{value:.1f}% of GDP",
    "gov_rev_gdp": "{value:.1f}% of GDP",
    "ir_rev": "{value:.1f}% of revenue",
    "gov_debt_gdp": "{value:.1f}% of GDP",
    "cab_avg": "{value:.1f}% of GDP",
    "reserve_gdp": "{value:.1f}% of GDP",
    "import_cover": "{value:.1f} months of imports",
    "reserve_fx": "{value:.0f}"}

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

####----Define histogram function for rapid chart building---####

def build_variable_histogram(
    short_var: str,
    df_peers: pd.DataFrame,
    selected_row: pd.Series,
    selected_name: str,
    selected_bucket: str,
    variable_dict: dict,
    bins_rule: str = "fd", #or "sturges"
    format_map = dict #custom formatting dict
):
    """
    Plots a histogram of `short_var` for peers (df_peers),
    with FD‐optimal bins, dotted percentile lines, a red line for the selected country,
    and a two‐line HTML title including the country’s value & percentile.
    """
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    import streamlit as st

    # 1) Data & label lookup
    vals = df_peers[short_var].dropna()
    long_var = variable_dict.get(short_var, short_var)

    # 2) Compute bin edges via the chosen rule (e.g. "fd" or "sturges")
    edges   = np.histogram_bin_edges(vals, bins=bins_rule)
    bin_size = edges[1] - edges[0]
    start, end = edges[0], edges[-1]

    # 3) Percentiles
    p5, p25, p50, p75, p95 = np.percentile(vals, [5,25,50,75,95])

    # 4) Build the figure
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=vals,
        xbins=dict(start=start, end=end, size=bin_size),
        marker_color="#DAEEF3",
        opacity=0.75,
        name="Peers"
    ))

    # 5) Dotted percentile lines
    for x_val, label in [(p5,"5th"), (p25,"25th"), (p50,"Median"),
                         (p75,"75th"), (p95,"95th")]:
        fig.add_vline(
            x=x_val,
            line=dict(color="gray", dash="dot", width=2),
            annotation_text=label,
            annotation_position="top left"
        )

    # 6) Red country line
    my_val = selected_row[short_var]
    fig.add_vline(
        x=my_val,
        line=dict(color="red", width=3),
        annotation_text=selected_name,
        annotation_position = "bottom right",
        annotation_font_color = "red"
    )

    # 7) Axis styling
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

    # 8) Compute country percentile
    percentile = np.mean(vals <= my_val) * 100

    # 9) Title with inline red line

    # then, given your short_var & my_val:
    fmt = format_map.get(short_var, "{value}")
    formatted_val = fmt.format(value=my_val)
    
    # and in your title line:
    title_text = (
    f"{selected_name} vs {selected_bucket} peers<br>"
    f"<span style='color:red'>{selected_name}: "
    f"{formatted_val} ({percentile:.0f}th percentile)</span>")

    fig.update_layout(
        title=title_text,
        template="simple_white",
        margin=dict(t=80, b=40, l=40, r=20),
        showlegend=False)
    
    # 10) return a fig object, which we then input into st.plotly to plot where we want it!
    return fig

def build_dummy_histogram(
    short_var: str,
    df_peers,
    selected_row,
    selected_name: str,
    selected_bucket: str,
    variable_dict: dict,
    bins_rule: str = "fd",
    format_map: dict = None
) -> go.Figure:
    """
    Builds a Plotly histogram figure for a given variable.
    
    Parameters:
    - short_var: column name to plot (short code)
    - df_peers: peers DataFrame, already filtered
    - selected_row: pd.Series for the selected country (one row)
    - selected_name: displayed country name
    - selected_bucket: bucket label (e.g. "BBB", "ALL")
    - variable_dict: mapping short_var -> long display name
    - bins_rule: "fd" (Freedman–Diaconis), "sturges", or "dummy"
    - format_map: mapping short_var -> Python format string
    
    Returns:
    - Plotly Figure
    """
   
    # Extract peers values and display name
    vals = df_peers[short_var].dropna()
    long_var = variable_dict.get(short_var, short_var)

    # Start a new figure
    fig = go.Figure()

    if bins_rule.lower() == "dummy":
        # Two-bin histogram for 0/1 dummy
        fig.add_trace(go.Histogram(
            x=vals,
            xbins=dict(start=0, end=2, size=1),
            marker_color="#DAEEF3",
            opacity=0.75,
            name="Peers"
        ))
    elif bins_rule.lower() == "ten":
        # Fixed 10-bin histogram
        fig.add_trace(go.Histogram(
        x=vals,
        nbinsx=10,
        marker_color="#DAEEF3",
        opacity=0.75,
        name="Peers"
        ))
    else:
        # Continuous histogram with FD or Sturges rule
        edges = np.histogram_bin_edges(vals, bins=bins_rule)
        bin_size = edges[1] - edges[0]
        start, end = edges[0], edges[-1]
        fig.add_trace(go.Histogram(
            x=vals,
            xbins=dict(start=start, end=end, size=bin_size),
            marker_color="#DAEEF3",
            opacity=0.75,
            name="Peers"
        ))
        
    # Reference line for the selected country
    my_val = selected_row[short_var]
    fig.add_vline(
        x=my_val,
        line=dict(color="red", width=3),
        annotation_text=selected_name,
        annotation_position="bottom right",
        annotation_font_color="red"
    )

    # Style axes uniformly
    fig.update_xaxes(
        title_text=long_var,
        title_font_color="black",
        tickfont_color="black",
        showline=True,
        linecolor="black",
        tickmode="array" if bins_rule.lower() == "dummy" else "auto",
        tickvals=[0, 1] if bins_rule.lower() == "dummy" else None
    )
    fig.update_yaxes(
        title_text="Count",
        title_font_color="black",
        tickfont_color="black",
        showline=True,
        linecolor="black"
    )

    # Compute and format the selected country’s value & percentile
    percentile = np.mean(vals <= my_val) * 100
    fmt_str = format_map.get(short_var, "{value}")
    formatted_val = fmt_str.format(value=my_val)

    # Build two-line HTML title
    title_text = (
        f"{selected_name} vs {selected_bucket} peers<br>"
        f"<span style='color:red'>{selected_name}: {formatted_val} "
        f"({percentile:.0f}th percentile)</span>"
    )
    fig.update_layout(
        title=title_text,
        template="simple_white",
        margin=dict(t=80, b=40, l=40, r=20),
        showlegend=False
    )

    return fig

####----Wealth----####
st.subheader("Wealth Factor")

fig_ngdp_pc = build_variable_histogram(
    short_var="ngdp_pc",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

st.plotly_chart(fig_ngdp_pc,use_container_width=True)

####----Size----####
st.subheader("Size Factor")

fig_ngdp = build_variable_histogram(
    short_var="ngdp",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

st.plotly_chart(fig_ngdp,use_container_width=True)

####----Growth----####
st.subheader("Growth Factor")

fig_growth_avg = build_variable_histogram(
    short_var="growth_avg",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

st.plotly_chart(fig_growth_avg,use_container_width=True)

####----Inflation----####
st.subheader("Inflation Factor")

fig_inf_avg = build_variable_histogram(
    short_var="inf_avg",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

st.plotly_chart(fig_inf_avg,use_container_width=True)

####----Default----####
st.subheader("Default History Factor")

fig_default = build_dummy_histogram(
    short_var="default_hist",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "dummy",
    format_map = format_map)

fig_decay = build_dummy_histogram(
    short_var="default_decay",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "ten",
    format_map = format_map)

col1, col2 = st.columns(2)
col1.plotly_chart(fig_default, use_container_width=True)
col2.plotly_chart(fig_decay, use_container_width=True)

####----Governance----####
st.subheader("Governance Factor")

fig_voice = build_variable_histogram(
    short_var="voice_acct",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

fig_pol = build_variable_histogram(
    short_var="pol_stab",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

fig_gov = build_variable_histogram(
    short_var="gov_eff",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

fig_reg = build_variable_histogram(
    short_var="reg_qual",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

fig_law = build_variable_histogram(
    short_var="rule_law",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

fig_corrupt = build_variable_histogram(
    short_var="cont_corrupt",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

col1, col2 = st.columns(2)
col1.plotly_chart(fig_voice, use_container_width=True)
col2.plotly_chart(fig_pol, use_container_width=True)

col3, col4 = st.columns(2)
col3.plotly_chart(fig_gov, use_container_width=True)
col4.plotly_chart(fig_reg, use_container_width=True)

col5, col6 = st.columns(2)
col5.plotly_chart(fig_law, use_container_width=True)
col6.plotly_chart(fig_corrupt, use_container_width=True)

####----Fiscal Performance----####
st.subheader("Fiscal Performance Factor")

fig_fb = build_variable_histogram(
    short_var="fb_avg",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

fig_rev = build_variable_histogram(
    short_var="gov_rev_gdp",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

fig_ir = build_variable_histogram(
    short_var="ir_rev",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

st.plotly_chart(fig_fb,use_container_width=True)

col1, col2 = st.columns(2)
col1.plotly_chart(fig_rev, use_container_width=True)
col2.plotly_chart(fig_ir, use_container_width=True)

###----Government Debt----####
st.subheader("Government Debt Factor")

fig_debt = build_variable_histogram(
    short_var="gov_debt_gdp",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

st.plotly_chart(fig_debt,use_container_width=True)

####----External Performance----####
st.subheader("External Performance Factor")

fig_cab = build_variable_histogram(
    short_var="cab_avg",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

st.plotly_chart(fig_cab,use_container_width=True)

####----FX Reserves----####
st.subheader("FX Reserves Factor")

fig_reserve = build_variable_histogram(
    short_var="reserve_gdp",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

fig_import = build_variable_histogram(
    short_var="import_cover",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "fd",
    format_map = format_map)

col1, col2 = st.columns(2)
col1.plotly_chart(fig_reserve, use_container_width=True)
col2.plotly_chart(fig_import, use_container_width=True)

####----Reserve Currency Status----####
st.subheader("Reserve Currency Factor")

fig_status = build_dummy_histogram(
    short_var="reserve_fx",
    df_peers = df_raw_filter,
    selected_row = selected_row_raw.iloc[0],
    selected_name = selected_name,
    selected_bucket = selected_bucket,
    variable_dict = variable_dict,
    bins_rule = "dummy",
    format_map = format_map)

col1, col2 = st.columns(2)
col1.plotly_chart(fig_status, use_container_width=True)
