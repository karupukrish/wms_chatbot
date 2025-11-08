import mysql.connector
from config import DB_CONFIG

def get_db_schema():
    """Return a dict of {table: [columns]} for all tables in DB."""
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]
        schema = {}
        for t in tables:
            cursor.execute(f"SHOW COLUMNS FROM `{t}`")
            cols = [r[0] for r in cursor.fetchall()]
            schema[t] = cols
        cursor.close()
        return schema
    finally:
        if conn:
            conn.close()

def filter_schema(schema: dict, question: str) -> str:
    """Return a compact textual schema filtered by keywords found in the question.
    If filtering finds nothing, return a short summary of common tables and columns."""
    q = question.lower()
    matches = {}
    for table, cols in schema.items():
        for c in cols:
            if c.lower() in q or any(word in q for word in [table.lower(), c.lower()]):
                matches.setdefault(table, []).append(c)
    if matches:
        lines = []
        for t, cols in matches.items():
            lines.append(f"TABLE {t}: {', '.join(cols)}")
        return '\n'.join(lines)
    # fallback: return small sample of schema (first 10 tables)
    lines = []
    i = 0
    for t, cols in schema.items():
        lines.append(f"TABLE {t}: {', '.join(cols[:8])}")
        i += 1
        if i >= 10:
            break
    return '\n'.join(lines)
