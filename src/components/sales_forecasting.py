import pandas as pd
import plotly.express as px
from dash import dcc, html, Input, Output, dash_table
from dotenv import load_dotenv
import os
import requests

# Load environment variables from .env file
load_dotenv()

# File URL from environment variables
FORECAST_FILE_URL = os.getenv("FORECAST_FILE_URL")

# Function to download files from URLs
def download_file(url, local_path):
    """Download a file from a URL and save it locally."""
    response = requests.get(url)
    if response.status_code == 200:
        with open(local_path, "wb") as f:
            f.write(response.content)
    else:
        raise Exception(f"Failed to download file from {url}. Status code: {response.status_code}")

# Preload forecasted sales data once when the app starts
def preload_forecast_data():
    local_forecast_path = "data/forecasted_sales.csv"
    download_file(FORECAST_FILE_URL, local_forecast_path)  # Download from Google Drive
    forecast_data = pd.read_csv(local_forecast_path, parse_dates=["DATE"])
    return forecast_data

# Preload forecasted sales data globally
forecast_data = preload_forecast_data()

def forecast_component():
    return html.Div([
        html.H3("Sales Forecasting", style={"textAlign": "center"}),

        # Date Picker
        dcc.DatePickerRange(
            id="forecast_date_picker",
            start_date=forecast_data["DATE"].min(),
            end_date=forecast_data["DATE"].max(),
            display_format="YYYY-MM-DD"
        ),

        # Total Forecast Text Box
        html.Div(id="total_forecast_text", style={"marginTop": "20px", "fontSize": "18px", "textAlign": "center"}),

        # Forecast Graph
        dcc.Graph(id="forecast_graph", config={"doubleClick": "reset"}),  # Enable zoom reset on double-click

        # Forecast Data Table
        dash_table.DataTable(
            id='forecast-data-table',
            columns=[{"name": i, "id": i} for i in forecast_data.columns],
            data=forecast_data.to_dict('records'),
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'}
        )
    ])

# Callback (Register globally)
def register_forecast_callbacks(app):
    @app.callback(
        [
            Output("forecast_graph", "figure"),
            Output("forecast-data-table", "data"),
            Output("total_forecast_text", "children")
        ],
        [
            Input("forecast_date_picker", "start_date"),
            Input("forecast_date_picker", "end_date")
        ]
    )
    def update_forecast(start_date, end_date):
        # Use preloaded forecasted sales data instead of reloading it
        global forecast_data

        # Filter data based on date range
        filtered_data = forecast_data[(forecast_data["DATE"] >= start_date) & (forecast_data["DATE"] <= end_date)]

        # Update line plot
        fig = px.line(filtered_data, x="DATE", y="Forecasted Sales",
                      title="Sales Forecasting Trends")

        # Update data table
        table_data = filtered_data.to_dict('records')

        # Calculate total forecast
        total_forecast = filtered_data["Forecasted Sales"].sum()
        total_forecast_text = f"Total Forecasted Sales for Selected Date Range: GHS{total_forecast:,.2f}"

        return fig, table_data, total_forecast_text