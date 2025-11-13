# app.py
"""
Dash + Plotly Cross-Asset Dashboard
Includes:
- Volatility
- Maximum Drawdown
- Rolling Correlation Stress
Always displays correlation heatmap.
"""

import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc
from dash.dependencies import Input, Output
from datetime import datetime, UTC
import pandas as pd

from data_fetching import fetch_cross_asset_data

# -----------------------------------------------------------
# App Setup
# -----------------------------------------------------------

app = Dash(__name__)
app.title = "Crypto Risk Dashboard"

DATE_OPTIONS = {
    "180d": ("180d", "1d"),
    "1y": ("1y", "1d"),
}

app.layout = html.Div(
    style={"fontFamily": "Arial", "margin": "25px"},
    children=[
        html.H2("📊 Crypto Risk Dashboard"),

        # ----- Date Range Selector -----
        html.Label("Select Date Range:"),
        dcc.Dropdown(
            id="date-range",
            options=[{"label": k, "value": k} for k in DATE_OPTIONS.keys()],
            value="1y",
            clearable=False,
        ),

        html.Br(),

        # ----- RISK BUTTONS -----
        html.Div(
            [
                html.Button("Annualized Volatility", id="btn-vol", n_clicks=0),
                html.Button("Max Drawdown", id="btn-dd", n_clicks=0, style={"marginLeft": "10px"}),
                html.Button("Correlation Stress", id="btn-corr", n_clicks=0, style={"marginLeft": "10px"}),
            ],
            style={"marginBottom": "15px"},
        ),

        html.Div(id="last-update", style={"marginBottom": "20px"}),

        # Single risk chart
        dcc.Graph(id="risk-chart"),

        # Always-visible correlation heatmap
        dcc.Graph(id="correlation-heatmap"),

        # Auto-refresh
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
        Output("risk-chart", "figure"),
        Output("correlation-heatmap", "figure"),
        Output("last-update", "children"),
    ],
    [
        Input("interval-component", "n_intervals"),
        Input("date-range", "value"),
        Input("btn-vol", "n_clicks"),
        Input("btn-dd", "n_clicks"),
        Input("btn-corr", "n_clicks"),
    ],
)
def update_dashboard(n, date_key, n_vol, n_dd, n_corr):

    # Determine last clicked button
    buttons = {"vol": n_vol, "dd": n_dd, "corr": n_corr}
    selected = max(buttons, key=buttons.get)

    if date_key is None:
        date_key = "1y"

    period, interval = DATE_OPTIONS[date_key]

    # -------- FULL DATASET (yields + Nasdaq + cryptos) --------
    df = fetch_cross_asset_data(period=period, interval=interval).dropna()

    if df.empty:
        empty = go.Figure().update_layout(title="No data loaded")
        return empty, empty, "⚠ No data returned"

    # Crypto subset for crypto-specific risk
    cryptos = ["BTC", "ETH", "SOL", "XRP"]
    df_crypto = df[cryptos].dropna()

    # Returns for all assets (for full correlation matrix)
    returns_all = df.pct_change().dropna()

    # Returns for crypto-only (for vol/dd/corr stress)
    returns_crypto = df_crypto.pct_change().dropna()

    # -----------------------------------------------------------
    # 1) ANNUALIZED VOLATILITY
    # -----------------------------------------------------------
    if selected == "vol":
        ann_vol = returns_crypto.std() * (365 ** 0.5)

        fig = go.Figure()
        fig.add_bar(
            x=ann_vol.index,
            y=ann_vol.values,
            marker_color=["#BF1A1A", "#F5AD18", "#9E1C60", "#DC143C"],
        )
        fig.update_layout(title="Annualized Volatility (Crypto)", yaxis_title="Vol")

    # -----------------------------------------------------------
    # 2) MAXIMUM DRAWDOWN
    # -----------------------------------------------------------
    elif selected == "dd":
        running_max = df_crypto.cummax()
        drawdowns = df_crypto / running_max - 1
        maxdd = drawdowns.min()

        fig = go.Figure()
        fig.add_bar(
            x=maxdd.index,
            y=maxdd.values,
            marker_color=["#BF1A1A", "#F5AD18", "#9E1C60", "#DC143C"],
        )
        fig.update_layout(title="Maximum Drawdown (Crypto)", yaxis_title="Drawdown")

    # -----------------------------------------------------------
    # 3) CORRELATION STRESS — Rolling 30-day vs Nasdaq
    # -----------------------------------------------------------
    else:  # selected == "corr"
        fig = go.Figure()

        if "Nasdaq" in df.columns:
            nasdaq_ret = df["Nasdaq"].pct_change().dropna()

            for c in cryptos:
                series = returns_crypto[c]

                rolling_corr = series.rolling(30).corr(nasdaq_ret)

                fig.add_trace(
                    go.Scatter(
                        x=rolling_corr.index,
                        y=rolling_corr,
                        mode="lines",
                        name=c,
                    )
                )

        fig.update_layout(
            title="Rolling 30-Day Correlation vs Nasdaq",
            yaxis_title="Correlation",
        )

    # -----------------------------------------------------------
    # CORRELATION MATRIX (Always Visible)
    # Includes yields + Nasdaq + all cryptos
    # -----------------------------------------------------------

    corr = returns_all.corr().round(3)

    fig_corr = px.imshow(
        corr,
        color_continuous_scale="RdYlGn",
        zmin=-1,
        zmax=1,
        aspect="auto",
        title="Full Cross-Asset Correlation Matrix",
    )
    fig_corr.update_traces(
        text=corr.values,
        texttemplate="%{text:.3f}",
        textfont=dict(size=14),
    )

    timestamp = f"Last updated: {datetime.now(UTC):%Y-%m-%d %H:%M UTC}"

    return fig, fig_corr, timestamp

# -----------------------------------------------------------
# Run Server
# -----------------------------------------------------------

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=True)
