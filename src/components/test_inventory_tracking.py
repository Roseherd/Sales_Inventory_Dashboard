import dash
from dash import dcc, html, dash_table
import pandas as pd
import os
from dash.dependencies import Input, Output
from twilio.rest import Client
import plotly.express as px

# Twilio credentials (replace with your actual credentials)
TWILIO_SID = "ACae94609e7397a9ca34fd938f6efaf256"
TWILIO_AUTH_TOKEN = "219bef0c23cce3dabde58686789e6e6d"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"
PHARMACY_WHATSAPP_NUMBER = "whatsapp:+233539681341"

# Function to create inventory component
def inventory_component():
    return html.Div([
        html.H3("Inventory Overview"),
        
        dcc.Input(
            id="search-product",
            type="text",
            placeholder="Search for a medication...",
            debounce=True,
            style={'marginBottom': '10px', 'width': '300px'}
        ),

        dcc.Checklist(
            id='low-stock-filter',
            options=[{"label": "Show Only Low Stock Items", "value": "low_stock"}],
            value=[],
            style={'marginBottom': '10px'}
        ),

        # dcc.Slider(
        #     id='lead-time-slider',
        #     min=1,
        #     max=30,
        #     step=1,
        #     value=7,
        #     marks={i: str(i) for i in range(1, 31, 5)},
        #     tooltip= {"placement": "bottom", "always_visible": True},
        #     #debounce=True  # Ensure callback fires only after user stops sliding
        #         ),

        #html.Div("Adjust Reorder Lead Time (Days)", style={'marginBottom': '10px'}),

        html.Div(id="low-stock-alert"),

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

        #dcc.Graph(id='stock-depletion-graph', config={"doubleClick": "reset"}),

        html.H3("Predicted Reorder Dates"),

        dcc.Input(
            id="search-reorder",
            type="text",
            placeholder="Search for a medication...",
            debounce=True,
            style={'marginBottom': '10px', 'width': '300px'}
        ),

        dash_table.DataTable(id='reorder-dates-table', columns=[],
         page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'})
    ])

# Function to load inventory data
def load_inventory_data():
    file_path = '../data/cleaned_inventory.csv'
    if os.path.exists(file_path):
        inventory_data = pd.read_csv(file_path)
        if inventory_data.empty:
            raise ValueError("The inventory data file is empty.")
    else:
        raise FileNotFoundError(f"Inventory data file not found at {file_path}")

    reorder_threshold = 5
    inventory_data["Reorder Status"] = inventory_data["QUANTITY LEFT"].apply(
        lambda x: "Needs Restock" if x < reorder_threshold else "In Stock"
    )
    return inventory_data

# Function to predict reorder dates
def predict_reorder_dates(lead_time=1):
    sales_data = pd.read_csv('../data/cleaned_sales.csv')
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

# Callback to update inventory table, alerts, and reorder prediction
def register_inventory_callbacks(app):
    @app.callback(
        Output('inventory-table', 'data'),
        Output('inventory-table', 'columns'),
        Output('low-stock-alert', 'children'),
        #Output('stock-depletion-graph', 'figure'),
        Output('reorder-dates-table', 'data'),
        Output('reorder-dates-table', 'columns'),
        Input('low-stock-filter', 'value'),
        Input('search-reorder', 'value'),
        Input('search-product', 'value'),
        #Input('lead-time-slider', 'value')
    )
    def update_inventory(filter_value, search_value):
        inventory_data = load_inventory_data()
        reorder_data = predict_reorder_dates()

        # Apply filters
        if "low_stock" in filter_value:
            inventory_data = inventory_data[inventory_data["Reorder Status"] == "Needs Restock"]

        if search_value:
            inventory_data = inventory_data[inventory_data["PRODUCT"].str.contains(search_value, case=False, na=False)]
            reorder_data = reorder_data[reorder_data["PRODUCT"].str.contains(search_value, case=False, na=False)]

        # Handle empty inventory data
        if inventory_data.empty:
            alert_message = html.Div("No products match the current filters.", style={'color': 'blue', 'fontWeight': 'bold'})
            return [], [], alert_message, px.bar(title="No Data Available"), [], []

        # # Handle empty reorder data
        # if reorder_data.empty:
        #     figure = px.bar(title="No Reorder Data Available")
        #     reorder_data = pd.DataFrame(columns=["PRODUCT", "Days Until Reorder", "Predicted Reorder Date"])
        # else:
        #     figure = px.bar(reorder_data, x='PRODUCT', y='Days Until Reorder', title="Stock Depletion Forecast", range_y=[0, 100])

        # Generate alert message
        alert_message = ""
        if "Needs Restock" in inventory_data["Reorder Status"].values:
            alert_message = html.Div("⚠️ Some products need restocking!", style={'color': 'red', 'fontWeight': 'bold'})

        # Prepare outputs
        columns = [{"name": col, "id": col} for col in inventory_data.columns]
        reorder_columns = [{"name": col, "id": col} for col in reorder_data.columns]

        return (
            inventory_data.to_dict("records"),
            columns,
            alert_message,
            #figure,
            reorder_data.to_dict("records"),
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
