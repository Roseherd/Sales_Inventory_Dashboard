import dash
from dash import dcc, html, dash_table
import pandas as pd
import os
from dash.dependencies import Input, Output
from twilio.rest import Client
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

# Twilio credentials from environment variables
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
PHARMACY_WHATSAPP_NUMBER = os.getenv("PHARMACY_WHATSAPP_NUMBER")

# File URL from environment variables
INVENTORY_FILE_URL = os.getenv("INVENTORY_FILE_URL")

# Function to download files from URLs
def download_file(url, local_path):
    """Download a file from a URL and save it locally."""
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
        
        # Search bar for filtering products
        dcc.Input(
            id="search-product",
            type="text",
            placeholder="Search for a medication...",
            debounce=True,
            style={'marginBottom': '10px', 'width': '300px'}
        ),

        # Low-stock filter checkbox
        dcc.Checklist(
            id='low-stock-filter',
            options=[{"label": "Show Only Low Stock Items", "value": "low_stock"}],
            value=[],
            style={'marginBottom': '10px'}
        ),

        # Alert message for low stock
        html.Div(id="low-stock-alert"),

        # DataTable to display inventory
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
        )
    ])

# Function to load inventory data
def load_inventory_data():
    local_inventory_path = "data/cleaned_inventory.csv"
    download_file(INVENTORY_FILE_URL, local_inventory_path)  # Download from Google Drive

    if os.path.exists(local_inventory_path):
        inventory_data = pd.read_csv(local_inventory_path)  # Load inventory data
    else:
        inventory_data = pd.DataFrame(columns=["PRODUCT", "LOCATION", "LOCATION TYPE", "CREATED", "BATCH", "EXPIRE", "UNIT", "QUANTITY LEFT", "BASE PRICE LIST"])

    # Define reorder threshold
    reorder_threshold = 5

    # Add "Reorder Status" column
    inventory_data["Reorder Status"] = inventory_data["QUANTITY LEFT"].apply(
        lambda x: "Needs Restock" if x < reorder_threshold else "In Stock"
    )

    return inventory_data

# Callback to update the inventory table dynamically
def register_inventory_callbacks(app):
    @app.callback(
        Output('inventory-table', 'data'),
        Output('inventory-table', 'columns'),
        Output('low-stock-alert', 'children'),
        Input('low-stock-filter', 'value'),
        Input('search-product', 'value')
    )
    def update_inventory(filter_value, search_value):
        inventory_data = load_inventory_data()

        # Apply low-stock filter
        if "low_stock" in filter_value:
            inventory_data = inventory_data[inventory_data["Reorder Status"] == "Needs Restock"]

        # Apply product search filter
        if search_value:
            inventory_data = inventory_data[inventory_data["PRODUCT"].str.contains(search_value, case=False, na=False)]

        # Generate alert if any item needs restocking
        alert_message = ""
        if "Needs Restock" in inventory_data["Reorder Status"].values:
            alert_message = html.Div("⚠️ Some products need restocking!", style={'color': 'red', 'fontWeight': 'bold'})

        return inventory_data.to_dict("records"), [{"name": col, "id": col} for col in inventory_data.columns], alert_message

# Function to send WhatsApp alerts
def send_whatsapp_alert(product_name, quantity_left):
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

    message = client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        body=f"🔔 *Reorder Alert*\n\n⚠️ *{product_name}* is running low!\nRemaining Stock: {quantity_left}\nPlease restock soon.",
        to=PHARMACY_WHATSAPP_NUMBER
    )

    print(f"WhatsApp alert sent for {product_name}: {message.sid}")

# Function to check for low stock and trigger WhatsApp alerts (max 10 messages)
def check_low_stock():
    inventory_data = load_inventory_data()

    low_stock_threshold = 5  # Set your reorder threshold
    low_stock_items = inventory_data[inventory_data["QUANTITY LEFT"] <= low_stock_threshold]

    # Send alerts for up to 10 products
    for i, (_, row) in enumerate(low_stock_items.iterrows()):
        if i >= 10:  # Limit to 10 messages
            break
        send_whatsapp_alert(row["PRODUCT"], row["QUANTITY LEFT"])