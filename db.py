import mysql.connector
from config import DB_CONFIG

def execute_sql(sql: str) -> dict:
    ":""Execute SQL and return a dict: {columns: [...], rows: [[...], ...]}"""
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        cursor.close()
        return {"columns": cols, "rows": rows}
    finally:
        if conn:
            conn.close()
