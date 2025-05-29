import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
import numpy as np
import re

## Page content. how it shows up on the side bar. how the page is laid out. wide in this case.
st.set_page_config(
    page_title="Historical Comparison",
    layout="wide",
)

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
    "fb_avg": "{value:.1f}%",
    "gov_rev_gdp": "{value:.1f}%",
    "ir_rev": "{value:.1f}%",
    "gov_debt_gdp": "{value:.1f}%",
    "cab_avg": "{value:.1f}%",
    "reserve_gdp": "{value:.1f}%",
    "import_cover": "{value:.1f}",
    "reserve_fx": "{value:.0f}"}

# Create Gap Variable

df_transform.insert(
    loc=5, 
    column="gap", 
    value=df_transform["predicted_rating"] - df_transform["rating"])

# calculate gap and insert it as the 6th column (index position 5)
#interpret this as, if predicted rating > rating. shade green. positive rating pressure.
#if predicted rating < rating. shade red. negative rating pressure.

## Make country and year selection boxes

st.markdown("""
<style>
/* 🔹 Limit the max width of selectboxes */
div[data-baseweb="select"] {
    max-width: 300px !important;
}
</style>
""", unsafe_allow_html=True)

## Dropdown to select Country

country_name = df_transform['name'].unique()
selected_name = st.selectbox("Select Country", sorted(country_name))

## Filter both df_transform and df_raw to include only the selected country

df_transform_filter = df_transform[df_transform["name"] == selected_name]
df_raw_filter = df_raw[df_raw["name"] == selected_name]

## Define Loomis Colors for use later

LS_darkblue = "#1A3B73"
LS_lightblue = "#B6CEE4"
LS_faintblue = "#DAEEF3"
LS_darkgrey = "#91929B"
LS_lightgrey = "#E9E9EB"
LS_orange = "#EF7622"

#st.dataframe(df_transform_filter)  ---> unlock if you want to check if your df is filtering properly
#st.dataframe(df_raw_filter)  ---> unlock if you want to check if your df is filtering properly

####----Historical Credit Rating----####
st.subheader("Sovereign Credit Rating Over The Years")

# Initialize the Figure
fig_rating = go.Figure()

# Define x and y values
x = df_transform_filter["year"]
gaps = df_transform_filter["gap"]
rating = df_transform_filter["rating"]
model_rating = df_transform_filter["predicted_rating"]

# 1) Predicted rating as line + markers
fig_rating.add_trace(go.Scatter(
    x=x,
    y=model_rating,
    mode="lines+markers",
    name="Model Rating",
    marker=dict(symbol="diamond", size=8, color = LS_darkblue),
    line=dict(width=2, color = LS_darkblue),
    hovertemplate="Predicted Rating: %{y:.2f}<extra></extra>"
))

# 2) Actual rating as line + markers
fig_rating.add_trace(go.Scatter(
    x=x,
    y=rating,
    mode="lines+markers",
    name="Public Rating",
    marker=dict(symbol="circle", size=8, color = LS_darkgrey),
    line=dict(width=2, color = LS_darkgrey, dash = "dash")
))

# 3) Gap as bars

# build a color per bar
bar_colors = ['green' if g >= 0 else 'red' for g in gaps]

fig_rating.add_trace(go.Bar(
    x=x,
    y=gaps,
    name="Gap (Model Rating - Actual Rating)",
    marker=dict(color=bar_colors),
    opacity=0.6,
    hovertemplate='Gap: %{y:.2f}<extra></extra>'
))

# A) annotation for Upgrade Pressure in that right margin above the x‐axis
fig_rating.add_annotation(
    xref="paper", x=1.15,    # 5% into right margin
    yref="y", y=0,    # just above top of plot
    text="⬆ Upgrade Pressure",
    showarrow=False,
    font=dict(color="green", size=14),
    align="left",
    yshift=10
)

# B) annotation for Downgrade Pressure in that right margin below the x‐axis
fig_rating.add_annotation(
    xref="paper", x=1.173,    # 5% into right margin
    yref="y", y=-0,    # just above top of plot
    text="⬇ Downgrade Pressure",
    showarrow=False,
    font=dict(color="red", size=14),
    align="left",
    yshift=-10
)

# Layout tweaks
fig_rating.update_layout(
    title=f"How does {selected_name}'s model rating differ from its public rating?",
    barmode="overlay",             # bars behind lines
    template="plotly_white"
)

fig_rating.update_xaxes(
    # keep your ticks & label styling
    title_text="Year",
    tickfont=dict(color="black"),
    title=dict(text="Year", font=dict(color="black")),
    showline=False,
    mirror=False
)

fig_rating.update_yaxes(
    title_text="Rating (1 = D, 22 = AAA)",
    title_font=dict(color="black"),
    tickfont=dict(color="black"),
    showline=True,
    linecolor="black",
    mirror=False
)

# Plot the chart finally!
st.plotly_chart(fig_rating, use_container_width=True)

####----Historical Macro Fundamentals ----####
st.subheader("How Have Macro Fundamentals Evolved Over The Years?")

####----Define line chart function for rapid chart building---####

def plot_line_series(
    data: pd.DataFrame,
    country: str,
    column: str,
    name_map: dict,
    hover_format_map: dict,
    base_color: str
) -> go.Figure:
    """
    Plot a time series line+markers for one macro variable with custom styling,
    using hover_format_map for numeric formatting and labeling the last point.

    Parameters
    ----------
    data : pd.DataFrame
        DataFrame with a 'year' column and the target series column.
    column : str
        Name of the column in `data` to plot.
    name_map : Dict[str, str]
        Maps column names to descriptive titles for chart headings.
    hover_format_map : Dict[str, str]
        Maps column names to Python-format strings for hover text, e.g. "${value:,.1f}".
    base_color : str
        Hex code for the series color, e.g. '#0A2342'.

    Returns
    -------
    fig : plotly.graph_objects.Figure
        A Plotly figure object ready for display.
    """
    # Derive the chart title
    title = f"{country} {name_map.get(column, column)}"

    # Extract x/y
    x_vals = data['year']
    y_vals = data[column]

    # Build hover template from map
    fmt = hover_format_map.get(column, '{value:.2f}')
    hover_template = re.sub(r'\{value:([^}]*)\}', lambda m: f'%{{y:{m.group(1)}}}', fmt) + '<extra></extra>'

    # Create figure
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='lines+markers',
            name=title,
            line=dict(color=base_color, width=2),
            marker=dict(symbol='circle', size=6, color=base_color),
            hovertemplate=hover_template
        )
    )

    # Annotate last data point
    last_x = x_vals.iloc[-1]
    last_y = y_vals.iloc[-1]
    label = fmt.format(value=last_y)
    fig.add_trace(
        go.Scatter(
            x=[last_x],
            y=[last_y],
            mode='text',
            text=[label],
            textposition='top right',
            showlegend=False,
            textfont=dict(color=base_color, size=12)
        )
    )

    # Layout styling
    fig.update_layout(
        title=title,
        template='plotly_white',
        xaxis=dict(
            title=dict(text='Year', font=dict(color='black')),
            tickfont=dict(color='black'),
            showline=True,
            linecolor='black'
        ),
        yaxis=dict(
            showline=True,
            linecolor='black',
            tickfont=dict(color='black')
        ),
        margin=dict(l=60, r=40, t=80, b=60),
        showlegend=False
    )

    return fig

####----Wealth----####
st.subheader("Wealth Factor")

fig_ngdp_pc = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "ngdp_pc",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

st.plotly_chart(fig_ngdp_pc,use_container_width=True)

####----Size----####
st.subheader("Size Factor")

fig_ngdp = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "ngdp",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

st.plotly_chart(fig_ngdp,use_container_width=True)

####----Growth----####
st.subheader("Growth Factor")

fig_growth = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "growth_avg",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

st.plotly_chart(fig_growth,use_container_width=True)

####----Inflation----####
st.subheader("Inflation Factor")

fig_inf = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "inf_avg",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

st.plotly_chart(fig_inf,use_container_width=True)

####----Default----####
st.subheader("Default History Factor")

fig_default = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "default_hist",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

fig_decay = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "default_decay",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

col1, col2 = st.columns(2)
col1.plotly_chart(fig_default, use_container_width=True)
col2.plotly_chart(fig_decay, use_container_width=True)

####----Governance----####
st.subheader("Governance Factor")

fig_voice = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "voice_acct",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

fig_pol = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "pol_stab",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

fig_gov = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "gov_eff",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

fig_reg = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "reg_qual",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

fig_law = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "rule_law",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

fig_corrupt = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "cont_corrupt",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

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

fig_fb = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "fb_avg",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

fig_rev = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "gov_rev_gdp",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

fig_ir = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "ir_rev",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

st.plotly_chart(fig_fb,use_container_width=True)

col1, col2 = st.columns(2)
col1.plotly_chart(fig_rev, use_container_width=True)
col2.plotly_chart(fig_ir, use_container_width=True)

###----Government Debt----####
st.subheader("Government Debt Factor")

fig_debt = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "gov_debt_gdp",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

st.plotly_chart(fig_debt,use_container_width=True)

####----External Performance----####
st.subheader("External Performance Factor")

fig_cab = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "cab_avg",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

st.plotly_chart(fig_cab,use_container_width=True)

####----FX Reserves----####
st.subheader("FX Reserves Factor")

fig_reserve = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "reserve_gdp",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

fig_import = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "import_cover",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

col1, col2 = st.columns(2)
col1.plotly_chart(fig_reserve, use_container_width=True)
col2.plotly_chart(fig_import, use_container_width=True)

####----Reserve Currency Status----####
st.subheader("Reserve Currency Factor")

fig_status = plot_line_series(
    data = df_raw_filter,
    country = selected_name,
    column = "reserve_fx",
    name_map = variable_dict,
    hover_format_map = format_map,
    base_color = LS_darkblue
)

col1, col2 = st.columns(2)
col1.plotly_chart(fig_status, use_container_width=True)
