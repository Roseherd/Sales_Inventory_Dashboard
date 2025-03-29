import dash
from dash import dcc, html, Input, Output, dash_table, ctx
import pandas as pd
import plotly.express as px
from components.sales_trends import sales_trend_component, register_sales_trend_callbacks
from components.alt_inventory_tracking import inventory_component, register_inventory_callbacks
from components.sales_forecasting import forecast_component, register_forecast_callbacks

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Load Data
sales_data = pd.read_csv("data/daily_sales.csv", parse_dates=["DATE"])
forecast_data = pd.read_csv("data/forecasted_sales.csv")
forecast_data["DATE"] = pd.to_datetime(forecast_data["DATE"])
inventory_data = pd.read_csv("data/cleaned_inventory.csv")

# Sales Trend Plot
fig_sales = px.line(sales_data, x="DATE", y="TOTAL AMOUNT", title="Daily Sales Trend")

# Layout with Tabs
app.layout = html.Div(children=[
    html.H1("Oddaremma Chemists - Sales & Inventory Dashboard", style={'textAlign': 'center'}),
    
    dcc.Tabs(id="tabs", value='sales', children=[
        dcc.Tab(label='Sales Trends', value='sales'),
        dcc.Tab(label='Inventory', value='inventory'),
        dcc.Tab(label='Sales Forecasting', value='forecasting')
    ]),
    
    html.Div(id='tabs-content'),

    # Download Buttons (Always Present)
    html.Div(id="download-buttons", children=[
        html.Button("Download Sales Data", id="btn_sales_csv", n_clicks=0, style={"marginTop": "20px", "display": "none"}),
        html.Button("Download Inventory Data", id="btn_inventory_csv", n_clicks=0, style={"marginTop": "20px", "display": "none"}),
        html.Button("Download Forecast Data", id="btn_forecast_csv", n_clicks=0, style={"marginTop": "20px", "display": "none"}),
    ]),

    # Hidden download component
    dcc.Download(id="download_data")
])

# Callback to switch tabs and show relevant download button
@app.callback(
    Output('tabs-content', 'children'),
    Output("btn_sales_csv", "style"),
    Output("btn_inventory_csv", "style"),
    Output("btn_forecast_csv", "style"),
    Input('tabs', 'value')
)
def update_tab(tab_name):
    hidden = {"display": "none"}
    visible = {"marginTop": "20px"}

    if tab_name == 'sales':
        return sales_trend_component(), visible, hidden, hidden
    elif tab_name == 'inventory':
        return inventory_component(), hidden, visible, hidden
    elif tab_name == 'forecasting':
        return forecast_component(), hidden, hidden, visible
    return html.Div(), hidden, hidden, hidden

# Callback for downloading CSV based on button click
@app.callback(
    Output("download_data", "data"),
    Input("btn_sales_csv", "n_clicks"),
    Input("btn_inventory_csv", "n_clicks"),
    Input("btn_forecast_csv", "n_clicks"),
    prevent_initial_call=True
)
def generate_csv(n_sales, n_inventory, n_forecast):
    triggered_id = ctx.triggered_id
    if triggered_id == "btn_sales_csv":
        return dcc.send_data_frame(sales_data.to_csv, "daily_sales.csv", index=False)
    elif triggered_id == "btn_inventory_csv":
        return dcc.send_data_frame(inventory_data.to_csv, "inventory_data.csv", index=False)
    elif triggered_id == "btn_forecast_csv":
        return dcc.send_data_frame(forecast_data.to_csv, "forecasted_sales.csv", index=False)
    return None

# Register callbacks
register_inventory_callbacks(app)
register_sales_trend_callbacks(app)
register_forecast_callbacks(app)

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
    
