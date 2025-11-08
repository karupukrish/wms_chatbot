import re
from config import client
from dbschema import get_db_schema, filter_schema

def smart_fuzzy_fix(sql_query: str) -> str:
    fuzzy_columns = ["item_name", "product_name", "description", "name"]
    for col in fuzzy_columns:
        sql_query = re.sub(
            rf"(WHERE\s+[\w\.]*{col}\s*=\s*['\"]([^'\"]+)['\"])" ,
            lambda m: f"WHERE LOWER({col}) LIKE '%{m.group(2).lower()}%'",
            sql_query,
            flags=re.IGNORECASE,
        )
    return sql_query

def generate_sql(user_question: str) -> str:
    schema = get_db_schema()
    filtered_schema = filter_schema(schema, user_question)

    prompt = f"""You are an expert MySQL query generator. Follow these rules:
- Use LOWER(column) and LIKE for matching text (e.g., WHERE LOWER(item_name) LIKE '%rin%').
- Use ISO-style dates if needed (YYYY-MM-DD).
- For aggregations (monthly/weekly totals), prefer SUM(amount) and proper WHERE date filters.
- Only output the SQL query (no prose). If you cannot generate a query, output exactly: NO_SQL.

Schema:
{filtered_schema}

User question: {user_question}

Generate only the SQL query to answer the user question.
"""

    try:
        response = client.chat.completions.create(
            # model="mistralai/mistral-7b-instruct",
                    model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Convert natural language to MySQL queries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0
        )
    except Exception as e:
        print("❌ LLM call error in generate_sql():", e)
        return "SELECT 'NO_SQL_RETURNED' AS result;"

    print("🧠 Raw SQL generation response:", response)

    sql_query = ""
    if hasattr(response, "choices") and len(response.choices) > 0:
        msg = response.choices[0].message
        if isinstance(msg, dict):
            sql_query = msg.get("content", "") or ""
        else:
            sql_query = getattr(msg, "content", "") or ""

    if not sql_query:
        print("⚠️ Model returned empty SQL.")
        return "SELECT 'NO_SQL_RETURNED' AS result;"

    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
    sql_query = smart_fuzzy_fix(sql_query)

    if not re.match(r"^(SELECT|WITH|UPDATE|INSERT|DELETE)\b", sql_query, flags=re.IGNORECASE):
        print("⚠️ Generated text doesn't look like SQL. Returning NO_SQL.")
        print("Generated content:", sql_query[:300])
        return "SELECT 'NO_SQL_RETURNED' AS result;"

    print("🧠 Final SQL:", sql_query)
    return sql_query
