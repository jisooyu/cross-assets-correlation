# app.py
"""
Dash + Plotly Cross-Asset Dashboard
Includes:
- 2Y, 10Y, 30Y Treasury yields
- Nasdaq
- Gold
- Bitcoin, Ethereum

Includes date range selector and auto-refresh every 15 minutes.
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.colors import qualitative
from dash import Dash, html, dcc
from dash.dependencies import Input, Output
from datetime import datetime, UTC

from data_fetching import fetch_cross_asset_data

# -----------------------------------------------------------
# App Setup
# -----------------------------------------------------------

app = Dash(__name__)
app.title = "Cross-Asset Correlation Dashboard"

DATE_OPTIONS = {
    "180d": ("180d", "1d"),
    "1y": ("1y", "1d"),
}

app.layout = html.Div(
    style={"fontFamily": "Arial", "margin": "25px"},
    children=[
        html.H2("📊 Cross-Asset Live Dashboard"),

        # ----- Date Range Selector -----
        html.Label("Select Date Range:"),
        dcc.Dropdown(
            id="date-range",
            options=[{"label": k, "value": k} for k in DATE_OPTIONS.keys()],
            value="1y",   # or "180d"
            clearable=False
        ),
        html.Div(id="last-update", style={"marginBottom": "20px"}),

        dcc.Graph(id="normalized-chart"),
        dcc.Graph(id="correlation-heatmap"),

        # auto-refresh every 15 minutes
        dcc.Interval(
            id="interval-component",
            interval=900_000,
            n_intervals=0,
        ),
    ],
)

# -----------------------------------------------------------
# Callback
# -----------------------------------------------------------
@app.callback(
    [
        Output("normalized-chart", "figure"),
        Output("correlation-heatmap", "figure"),
        Output("last-update", "children"),
    ],
    [
        Input("interval-component", "n_intervals"),
        Input("date-range", "value"),
    ],
)
def update_dashboard(n, date_key):
    if date_key is None:
        date_key = "1y"

    period, interval = DATE_OPTIONS[date_key]

    df = fetch_cross_asset_data(period=period, interval=interval)

    if df.empty:
        empty_fig = go.Figure().update_layout(title="No data loaded")
        return empty_fig, empty_fig, "⚠ No data returned"

    # -----------------------------------------------------------
    # ---------- Dual-Axis Normalized Chart ----------
    # -----------------------------------------------------------

    # yields = ["3M_Yield", "1Y_Yield", "2Y_Yield", "10Y_Yield", "30Y_Yield"]
    yields = ["3M_Yield",  "10Y_Yield"]
    assets = ["BTC", "ETH", "SOL", "XRP"]

    df_norm = df / df.iloc[0]

    fig_norm = go.Figure()

    # Left axis (Treasury yields)
    yield_colors = ["#1f77b4",  "#0f2a44"]

    for col, color in zip(yields, yield_colors):
        if col in df_norm.columns:
            fig_norm.add_trace(
                go.Scatter(
                    x=df_norm.index,
                    y=df_norm[col],
                    mode="lines",
                    name=col,
                    yaxis="y1",
                    line=dict(color=color, width=2.2),
                )
            )

    # Right axis (Risk assets)
    asset_colors = {
        # "Gold": "#DAA520",
        # "Nasdaq": "#FF7F0E",
        "BTC": "#BF1A1A",
        "ETH": "#F5AD18",
        "SOL": "#9E1C60",
        "XRP": "#DC143C",
    }

    for col in assets:
        if col in df_norm.columns:
            fig_norm.add_trace(
                go.Scatter(
                    x=df_norm.index,
                    y=df_norm[col],
                    mode="lines",
                    name=col,
                    yaxis="y2",
                    line=dict(color=asset_colors[col], width=2.2),
                )
            )
    fig_norm.update_layout(
        title=f"Normalized Cross-Asset Movement ({period}, interval={interval})",
        hovermode="x unified",

        # Left axis (yields)
        yaxis=dict(
            title="Treasury Yields (Normalized)",
            color="#1f77b4",      # tick labels color
        ),

        # Right axis (risk assets)
        yaxis2=dict(
            title="Risk Assets (Normalized)",
            overlaying="y",
            side="right",
            color="#FF7F0E",      # tick labels color
        ),

        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
    )

    # left axis title color
    fig_norm.update_layout(
        yaxis_title_font=dict(color="#1f77b4")
    )

    # right axis title color
    fig_norm.update_layout(
        yaxis2_title_font=dict(color="#FF7F0E")
    )


    # -----------------------------------------------------------
    # ---------- Correlation Matrix ----------
    # -----------------------------------------------------------

    df_clean = df.ffill().bfill()
    returns = df_clean.pct_change(fill_method=None).dropna()
    corr = returns.corr().round(3)

    fig_corr = px.imshow(
        corr,
        color_continuous_scale="RdYlGn",
        zmin=-1,
        zmax=1,
        aspect="auto",
    )

    fig_corr.update_traces(
        text=corr.values,
        texttemplate="%{text:.3f}",
        textfont=dict(size=16),
    )

    fig_corr.update_layout(
        title="Return Correlation Matrix",
        width=900,
        height=900,
        xaxis=dict(tickfont=dict(size=16)),
        yaxis=dict(tickfont=dict(size=16)),
    )

    timestamp = f"Last updated: {datetime.now(UTC):%Y-%m-%d %H:%M UTC}"

    return fig_norm, fig_corr, timestamp

# -----------------------------------------------------------
# Run Server
# -----------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
