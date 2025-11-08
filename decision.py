import re

def decide_mode(user_question: str) -> str:
    q = user_question.lower().strip()

    # definition-like -> TEXT
    if re.search(r"^(what is|who is|define|explain|describe|meaning of|tell me about|how to)", q):
        return "TEXT"

    sql_patterns = [
        r"\b(price|sale price|purchase price|sales_price|cost|rate|amount|value)\b",
        r"\b(stock|quantity|qty|how many|total stock|inventory)\b",
        r"\b(list|get|show|fetch|display)\s+(items|products|stock|inventory)\b",
        r"\b(count|number of|how many)\b",
        r"\b(sales|revenue|total sales|this month sales|last month sales|monthly sales)\b"
    ]

    for p in sql_patterns:
        if re.search(p, q):
            return "SQL"
    return "TEXT"
