from datetime import datetime, timedelta
import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
from database import (get_connection, get_customer_locations, get_manager_names, get_customer_names, get_data)
import plotly.express as px
import dash_leaflet as dl

current_date = datetime.today()
first_day_of_month = datetime(current_date.year, current_date.month, 1)
last_day_of_month = datetime(current_date.year, current_date.month + 1, 1) - timedelta(days=1)


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Sales Dashboard"), className="block")),
    dbc.Row([
        dbc.Col(dcc.DatePickerRange(
            id='date-picker-range',
            start_date=first_day_of_month,
            end_date=last_day_of_month,
            display_format='YYYY-MM-DD'
        ), className="block"),
        dbc.Col(dcc.Dropdown(
            id='manager-dropdown',
            options=[{'label': name, 'value': name} for name in get_manager_names()],
            placeholder="Select a Manager"
        ), className="block"),
        dbc.Col(dcc.Dropdown(
            id='customer-dropdown',
            options=[{'label': name, 'value': name} for name in get_customer_names()],
            placeholder="Select a Customer"
        ), className="block"),
    ]),
    dbc.Row(dbc.Col(dcc.Graph(id='sales-graph'), className="graph")),
    dbc.Row([
        dbc.Col(dcc.Graph(id='traffic-chanel-pie'), className="block"),
        dbc.Col(dcc.Graph(id='customer-type-pie'), className="block")
    ]),
    dbc.Row(dbc.Col(dl.Map(id='customer-map', children=[dl.TileLayer()], center=[50, 0], zoom=10), className="block")),
    dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Total Sales", className="card-title"),
                    html.H3(id="total-sales", className="card-text"),
                    html.P("Total number of sales in the period", className="card-text")
                ])
            ], color="warning", outline=True), className="block"),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Total Revenue", className="card-title"),
                    html.H3(id="total-revenue", className="card-text"),
                    html.P("Total revenue from orders in the period", className="card-text")
                ])
            ], color="warning", outline=True), className="block"),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Average Order Value", className="card-title"),
                    html.H3(id="average-check", className="card-text"),
                    html.P("Average value of orders in the period", className="card-text")
                ])
            ], color="warning", outline=True), className="block")
        ]),
    ], className="container")


@app.callback(
    Output('traffic-chanel-pie', 'figure'),
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')])

def update_traffic_chanel_pie(start_date, end_date):
    conn = get_connection()
    query = f"""
    SELECT mk.TrafficChanel, COUNT(*) as count
    FROM Sale s
    JOIN Marketing mk ON s.IDTraffic = mk.IDTraffic
    WHERE s.SaleDate BETWEEN '{start_date}' AND '{end_date}'
    GROUP BY mk.TrafficChanel
    """
    df = pd.read_sql(query, conn)
    fig = px.pie(df, values='count', names='TrafficChanel', title='Distribution of Traffic Chanels')
    return fig

@app.callback(
    Output('customer-type-pie', 'figure'),
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_customer_type_pie(start_date, end_date):
    conn = get_connection()
    query = f"""SELECT c.CustomerType, COUNT(*) AS Count
    FROM Sale s
    JOIN Customer c ON s.IDCustomer = c.IDCustomer
    WHERE s.SaleDate BETWEEN '{start_date}' AND '{end_date}'
    GROUP BY c.CustomerType
    """
    df = pd.read_sql(query, conn)
    fig = px.pie(df, values='Count', names='CustomerType', title='Distribution of Customer Types')
    return fig

@app.callback(
    Output('customer-map', 'children'),
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_customer_map(start_date, end_date):
    df = get_customer_locations(start_date, end_date)
    max_order_count = df['OrderCount'].max() if not df.empty else 1  # Защита от деления на ноль
    markers = [
        dl.CircleMarker(
            center=[float(row['Latitude']), float(row['Longitude'])],
            radius=5 + 20 * (row['OrderCount'] / max_order_count),  # Масштабируем радиус
            color='blue',
            fill=True,
            fillOpacity=0.5,
            children=dl.Tooltip(f"Orders: {row['OrderCount']}")
        )
        for index, row in df.iterrows()
        if row['Latitude'] and row['Longitude']
    ]
    map_center = [float(df.iloc[0]['Latitude']), float(df.iloc[0]['Longitude'])] if not df.empty else [50, 0]
    return dl.Map([dl.TileLayer()] + markers, center=map_center, zoom=4,
                  style={'width': '100%', 'height': '50vh', 'margin': "auto", "display": "block"})

@app.callback(
    [Output('total-sales', 'children'),
     Output('total-revenue', 'children'),
     Output('average-check', 'children'),
     Output('sales-graph', 'figure')],
    [Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('manager-dropdown', 'value'),
     Input('customer-dropdown', 'value')]
)
def update_financial_and_sales_metrics(start_date, end_date, manager, customer):
    conn = get_connection()
    query = f"""
    SELECT s.*, m.Name, c.FirstName, c.LastName, c.Phone
    FROM (Sale s
    JOIN Manager m ON s.IDManager = m.IDManager)
    JOIN Customer c ON s.IDCustomer = c.IDCustomer
    WHERE s.SaleDate BETWEEN '{start_date}' AND '{end_date}'
    """
    if manager:
        query += f" AND m.Name = '{manager}'"
    if customer:
        query += f" AND CONCAT(c.FirstName, c.LastName, c.Phone) = '{customer}'"
    query += " ORDER BY s.SaleDate"
    df = pd.read_sql(query, conn)
    total_sales = df['TotalAmount'].sum()

    total_sales_count, total_revenue = get_data(start_date, end_date)
    average_check = total_revenue / total_sales_count if total_sales_count else 0

    figure = {
        'data': [{'x': df['SaleDate'], 'y': df['TotalAmount'], 'type': 'line'}],
        'layout': {'title': 'Sales Over Time'}
    }
    return f"{total_sales_count:,}", f"${total_revenue:,.2f}", f"${average_check:,.2f}", figure

if __name__ == '__main__':
    app.run_server(debug=True)