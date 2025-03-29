import dash
from dash import dcc, html, Input, Output, dash_table, ctx
import pandas as pd
import plotly.express as px
from components.sales_trends import sales_trend_component, register_sales_trend_callbacks
from components.alt_inventory_tracking import inventory_component, register_inventory_callbacks
from components.sales_forecasting import forecast_component, register_forecast_callbacks
import dash_auth
from dotenv import load_dotenv
import os
import requests

# Load environment variables from .env file
load_dotenv()

# File URLs from environment variables
INVENTORY_FILE_URL = os.getenv("INVENTORY_FILE_URL")
SALES_FILE_URL = os.getenv("DAILY_SALES_FILE_URL")
FORECAST_FILE_URL = os.getenv("FORECAST_FILE_URL")

# Function to download files from URLs
def download_file(url, local_path):
    """Download a file from a URL and save it locally."""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    # Download the file
    response = requests.get(url)
    if response.status_code == 200:
        with open(local_path, "wb") as f:
            f.write(response.content)
    else:
        raise Exception(f"Failed to download file from {url}. Status code: {response.status_code}")

# Download and load data
def load_data():
    # Download inventory data
    inventory_path = "data/cleaned_inventory.csv"
    download_file(INVENTORY_FILE_URL, inventory_path)
    inventory_data = pd.read_csv(inventory_path)

    # Download sales data
    sales_path = "data/daily_sales.csv"
    download_file(SALES_FILE_URL, sales_path)
    sales_data = pd.read_csv(sales_path, parse_dates=["DATE"])

    # Download forecast data
    forecast_path = "data/forecasted_sales.csv"
    download_file(FORECAST_FILE_URL, forecast_path)
    forecast_data = pd.read_csv(forecast_path)
    forecast_data["DATE"] = pd.to_datetime(forecast_data["DATE"])

    return inventory_data, sales_data, forecast_data

# Load all data
inventory_data, sales_data, forecast_data = load_data()

# Load credentials from environment variables
DASH_USERNAME = os.getenv("DASH_USERNAME")
DASH_PASSWORD = os.getenv("DASH_PASSWORD")

VALID_USERNAME_PASSWORD_PAIRS = {
    DASH_USERNAME: DASH_PASSWORD
}

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Basic Authentication
auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)

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

