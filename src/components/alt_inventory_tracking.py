import dash
from dash import dcc, html, dash_table
import pandas as pd
import os
from dash.dependencies import Input, Output
from twilio.rest import Client
import plotly.express as px
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

# Twilio credentials from environment variables
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
PHARMACY_WHATSAPP_NUMBER = os.getenv("PHARMACY_WHATSAPP_NUMBER")

# File URLs from environment variables
INVENTORY_FILE_URL = os.getenv("INVENTORY_FILE_URL")
SALES_FILE_URL = os.getenv("SALES_FILE_URL")

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

# Function to create inventory component
def inventory_component():
    return html.Div([
        html.H3("Inventory Overview"),
        
        # Search bar for inventory table
        dcc.Input(
            id="search-product",
            type="text",
            placeholder="Search for a medication...",
            debounce=True,
            style={'marginBottom': '10px', 'width': '300px'}
        ),

        # Filter for low stock items
        dcc.Checklist(
            id='low-stock-filter',
            options=[{"label": "Show Only Low Stock Items", "value": "low_stock"}],
            value=[],
            style={'marginBottom': '10px'}
        ),

        html.Div(id="low-stock-alert"),

        # Inventory Data Table
        dash_table.DataTable(
            id='inventory-table',
            columns=[],
            data=[],
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Reorder Status} eq "Needs Restock"'},
                    'backgroundColor': '#ffdddd',
                    'color': 'red'
                }
            ]
        ),

        html.H3("Predicted Reorder Dates"),

        # Search bar for reorder dates table
        dcc.Input(
            id="search-reorder-product",
            type="text",
            placeholder="Search for a product in reorder dates...",
            debounce=True,
            style={'marginBottom': '10px', 'width': '300px'}
        ),

        # Reorder Dates Data Table
        dash_table.DataTable(
            id='reorder-dates-table',
            columns=[],
            data=[],
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'}
        )
    ])

# Function to load inventory data
def load_inventory_data():
    local_inventory_path = "data/cleaned_inventory.csv"
    download_file(INVENTORY_FILE_URL, local_inventory_path)  # Download from Google Drive
    inventory_data = pd.read_csv(local_inventory_path)
    if inventory_data.empty:
        raise ValueError("The inventory data file is empty.")

    reorder_threshold = 5
    inventory_data["Reorder Status"] = inventory_data["QUANTITY LEFT"].apply(
        lambda x: "Needs Restock" if x < reorder_threshold else "In Stock"
    )
    return inventory_data

# Function to predict reorder dates
def predict_reorder_dates(lead_time=1):
    local_sales_path = "data/cleaned_sales.csv"
    download_file(SALES_FILE_URL, local_sales_path)  # Download from Google Drive
    sales_data = pd.read_csv(local_sales_path)
    inventory_data = load_inventory_data()
    
    reorder_predictions = []

    for _, row in inventory_data.iterrows():
        product_name = row['PRODUCT']
        product_sales = sales_data[sales_data['PRODUCT'] == product_name]

        if not product_sales.empty:
            daily_avg_sales = product_sales['QTY'].mean()

            if pd.notna(daily_avg_sales) and daily_avg_sales > 0:
                days_until_reorder = row['QUANTITY LEFT'] / daily_avg_sales
                reorder_date = pd.Timestamp.today() + pd.Timedelta(days=days_until_reorder - lead_time)  # Subtract lead time

                reorder_predictions.append({
                    'PRODUCT': product_name,
                    'Days Until Reorder': max(0, round(days_until_reorder - lead_time)),  # Prevent negative days
                    'Predicted Reorder Date': reorder_date.strftime('%Y-%m-%d')
                })

    return pd.DataFrame(reorder_predictions)

# Precompute data
inventory_data = load_inventory_data()
reorder_data = predict_reorder_dates()

# Callback to update inventory table, alerts, and reorder prediction
def register_inventory_callbacks(app):
    @app.callback(
        Output('inventory-table', 'data'),
        Output('inventory-table', 'columns'),
        Output('low-stock-alert', 'children'),
        Output('reorder-dates-table', 'data'),
        Output('reorder-dates-table', 'columns'),
        Input('low-stock-filter', 'value'),
        Input('search-product', 'value'),
        Input('search-reorder-product', 'value')  # New input for searching reorder dates
    )
    def update_inventory(filter_value, search_value, search_reorder_value):
        filtered_inventory = inventory_data.copy()
        filtered_reorder = reorder_data.copy()

        # Apply low stock filter
        if "low_stock" in filter_value:
            filtered_inventory = filtered_inventory.query("`Reorder Status` == 'Needs Restock'")

        # Apply search filter for inventory data
        if search_value:
            filtered_inventory = filtered_inventory[filtered_inventory["PRODUCT"].str.contains(search_value, case=False, na=False)]

        # Apply search filter for reorder data
        if search_reorder_value:
            filtered_reorder = filtered_reorder[filtered_reorder["PRODUCT"].str.contains(search_reorder_value, case=False, na=False)]

        # Handle empty inventory data
        if filtered_inventory.empty:
            alert_message = html.Div("No products match the current filters.", style={'color': 'blue', 'fontWeight': 'bold'})
            return [], [], alert_message, [], []

        # Handle empty reorder data
        if filtered_reorder.empty:
            filtered_reorder = pd.DataFrame(columns=["PRODUCT", "Days Until Reorder", "Predicted Reorder Date"])

        # Generate alert message
        alert_message = ""
        if "Needs Restock" in filtered_inventory["Reorder Status"].values:
            alert_message = html.Div("⚠️ Some products need restocking!", style={'color': 'red', 'fontWeight': 'bold'})

        # Prepare outputs
        columns = [{"name": col, "id": col} for col in filtered_inventory.columns]
        reorder_columns = [{"name": col, "id": col} for col in filtered_reorder.columns]

        return (
            filtered_inventory.to_dict("records"),
            columns,
            alert_message,
            filtered_reorder.to_dict("records"),
            reorder_columns
        )

# Function to send WhatsApp alerts
def send_whatsapp_alert(product_name, quantity_left):
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        body=f"🔔 *Reorder Alert*\n\n⚠️ *{product_name}* is running low!\nRemaining Stock: {quantity_left}\nPlease restock soon.",
        to=PHARMACY_WHATSAPP_NUMBER
    )
    print(f"WhatsApp alert sent for {product_name}: {message.sid}")

# Function to check for low stock and trigger WhatsApp alerts
def check_low_stock():
    inventory_data = load_inventory_data()
    low_stock_threshold = 5
    low_stock_items = inventory_data[inventory_data["QUANTITY LEFT"] <= low_stock_threshold]
    for i, (_, row) in enumerate(low_stock_items.iterrows()):
        if i >= 10:
            break
        send_whatsapp_alert(row["PRODUCT"], row["QUANTITY LEFT"])
