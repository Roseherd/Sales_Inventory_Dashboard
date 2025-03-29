import pandas as pd
import plotly.express as px
from dash import dcc, html, Input, Output, dash_table
from dotenv import load_dotenv
import os
import requests

# Load environment variables from .env file
load_dotenv()

# File URL from environment variables
DAILY_SALES_FILE_URL = os.getenv("DAILY_SALES_FILE_URL")

# Function to download files from URLs
def download_file(url, local_path):
    """Download a file from a URL and save it locally."""
    response = requests.get(url)
    if response.status_code == 200:
        with open(local_path, "wb") as f:
            f.write(response.content)
    else:
        raise Exception(f"Failed to download file from {url}. Status code: {response.status_code}")

# Preload sales data once when the app starts
def preload_sales_data():
    local_sales_path = "data/daily_sales.csv"
    download_file(DAILY_SALES_FILE_URL, local_sales_path)  # Download from Google Drive
    sales_data = pd.read_csv(local_sales_path, parse_dates=["DATE"])
    return sales_data

# Preload sales data globally
sales_data = preload_sales_data()

def sales_trend_component():
    return html.Div([
        html.H3("Sales Trends", style={"textAlign": "center"}),

        # Date Picker
        dcc.DatePickerRange(
            id="sales_date_picker",
            start_date=sales_data["DATE"].min(),
            end_date=sales_data["DATE"].max(),
            display_format="YYYY-MM-DD"
        ),

        # Total Sales Text Box
        html.Div(id="total_sales_text", style={"marginTop": "20px", "fontSize": "18px", "textAlign": "center"}),

        # Sales Trend Graph
        dcc.Graph(id="sales_trend_graph", config={"doubleClick": "reset"}),  # Enable zoom reset on double-click

        # Sales Data Table
        dash_table.DataTable(
            id='sales-data-table',
            columns=[{"name": i, "id": i} for i in sales_data.columns],
            data=sales_data.to_dict('records'),
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'}
        )
    ])

# Callback (Register globally)
def register_sales_trend_callbacks(app):
    @app.callback(
        [
            Output("sales_trend_graph", "figure"),
            Output("sales-data-table", "data"),
            Output("total_sales_text", "children")
        ],
        [
            Input("sales_date_picker", "start_date"),
            Input("sales_date_picker", "end_date")
        ]
    )
    def update_sales_trend(start_date, end_date):
        # Use preloaded sales data instead of reloading it
        global sales_data

        # Filter data based on date range
        filtered_data = sales_data[(sales_data["DATE"] >= start_date) & (sales_data["DATE"] <= end_date)]

        # Update line plot
        fig = px.line(filtered_data, x="DATE", y="TOTAL AMOUNT",
                      title="Sales Trends Over Time")

        # Update data table
        table_data = filtered_data.to_dict('records')

        # Calculate total sales
        total_sales = filtered_data["TOTAL AMOUNT"].sum()
        total_sales_text = f"Total Sales for Selected Date Range: GHS{total_sales:,.2f}"

        return fig, table_data, total_sales_text

