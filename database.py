import pyodbc
import pandas as pd

def get_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-AKE911M;'
        'DATABASE=Trotuarka;'
        'Trusted_Connection=yes;')

def test_connection():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Sale')
    for row in cursor.fetchall():
        print(row)
    conn.close()

def get_unique_values(column_name):
    conn = get_connection()
    query = f"SELECT DISTINCT {column_name} FROM Sale ORDER BY {column_name}"
    cursor = conn.cursor()
    cursor.execute(query)
    values = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return values

def get_manager_names():
    conn = get_connection()
    query = "SELECT DISTINCT [Name] FROM Manager ORDER BY [Name]"
    cursor = conn.cursor()
    cursor.execute(query)
    manager_names = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return manager_names

def get_customer_names():
    conn = get_connection()
    query = "SELECT CONCAT(FirstName , LastName , Phone) FROM Customer ORDER BY FirstName"
    cursor = conn.cursor()
    cursor.execute(query)
    customer_names = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return customer_names

def get_customer_locations(start_date, end_date):
    conn = get_connection()
    query = f"""
    SELECT c.AddressMap, COUNT(*) as OrderCount
    FROM Customer c
    JOIN Sale s ON c.IDCustomer = s.IDCustomer
    WHERE s.SaleDate BETWEEN '{start_date}' AND '{end_date}'
    GROUP BY c.AddressMap
    """
    df = pd.read_sql(query, conn)
    lat, lon = [], []
    for index, row in df.iterrows():
        parts = row['AddressMap'].split(',')
        if len(parts) == 2:
            lat.append(parts[0])
            lon.append(parts[1])
        else:
            lat.append(None)
            lon.append(None)
    df['Latitude'] = lat
    df['Longitude'] = lon
    return df


def get_data(start_date, end_date):
    conn = get_connection()
    query = f"""
    SELECT
        COUNT(IDSale) AS TotalSales,
        SUM(TotalAmount) AS TotalRevenue
    FROM Sale
    WHERE SaleDate BETWEEN '{start_date}' AND '{end_date}'
    """
    df = pd.read_sql(query, conn)
    conn.close()

    # Обработка значений None
    total_sales = int(df.loc[0, 'TotalSales']) if not pd.isnull(df.loc[0, 'TotalSales']) else 0
    total_revenue = float(df.loc[0, 'TotalRevenue']) if not pd.isnull(df.loc[0, 'TotalRevenue']) else 0.0

    return total_sales, total_revenue

if __name__ == '__main__':
    test_connection()