from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import ChatRequest
from embeddings import vectorstore
from decision import decide_mode
from sql_generator import generate_sql
from db import execute_sql
from config import client
import traceback
import re
import os

app = FastAPI()

# CORS for front-end (React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_sql_result(result: dict, user_question: str) -> str:
    """Formats MySQL result into a human-friendly response."""
    cols = result.get("columns", [])
    rows = result.get("rows", [])

    if not rows:
        return "No records found."

    # Single scalar (one row, one column)
    if len(cols) == 1 and len(rows) == 1:
        val = rows[0][0]
        try:
            formatted = f"{float(val):,.2f}"
            if re.search(r"(price|sales price|rate|cost|rupee|₹|rs|rs\.)", user_question, re.IGNORECASE):
                return f"The sales price is {formatted}"
            else:
                return f"Result: {formatted}"
        except Exception:
            return f"Result: {val}"

    # Single row, multiple columns
    if len(rows) == 1 and len(cols) >= 1:
        vals = rows[0]
        if all(isinstance(v, (int, float)) for v in vals):
            formatted_vals = [f"{float(v):,.2f}" for v in vals]
            if len(formatted_vals) == 1:
                return f"The value is {formatted_vals[0]}"
            return f"Values: {', '.join(formatted_vals)}"

    # Multiple rows: preview
    preview_rows = rows[:5]
    lines = []
    header = " | ".join(cols)
    lines.append(header)
    for r in preview_rows:
        lines.append(" | ".join(str(x) for x in r))
    if len(rows) > 5:
        lines.append(f"... and {len(rows)-5} more rows")
    return "\n".join(lines)


@app.post("/chat")
def chat(req: ChatRequest):
    try:
        q = req.message.strip()
        print("\n🔎 Incoming question:", q)

        print("🔑 OPENROUTER key present:", bool(os.getenv("OPENROUTER_API_KEY")))

        # ========================
        # 1) Retrieve RAG Context
        # ========================
        context = ""
        debug_docs = []
        if vectorstore:
            try:
                retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
                if hasattr(retriever, "get_relevant_documents"):
                    docs = retriever.get_relevant_documents(q)
                elif hasattr(retriever, "get_relevant_texts"):
                    docs = retriever.get_relevant_texts(q)
                else:
                    docs = retriever.invoke(q)

                normalized = []
                if isinstance(docs, list):
                    for d in docs:
                        if hasattr(d, "page_content"):
                            normalized.append({"page_content": d.page_content, "meta": getattr(d, "metadata", None)})
                        elif isinstance(d, dict):
                            normalized.append({
                                "page_content": d.get("page_content") or d.get("content") or "",
                                "meta": d.get("metadata")
                            })
                        elif isinstance(d, str):
                            normalized.append({"page_content": d})
                        else:
                            normalized.append({"page_content": str(d)})
                elif isinstance(docs, str):
                    normalized = [{"page_content": docs}]
                else:
                    normalized = [{"page_content": str(docs)}]

                normalized = [d for d in normalized if d.get("page_content") and d.get("page_content").strip()]
                context = "\n\n".join([d["page_content"] for d in normalized])
                debug_docs = normalized

                print(f"📚 Retrieved {len(debug_docs)} doc(s) from vectorstore.")
                for i, dd in enumerate(debug_docs, 1):
                    snippet = dd["page_content"][:200].replace("\n", " ")
                    print(f"  doc{i} snippet: {snippet!r}")

            except Exception as e:
                print("⚠️ Retriever error:", e)
                context = ""
        else:
            print("⚠️ No vectorstore available (RAG disabled).")

        # ========================
        # 2) Decide Mode (SQL/TEXT)
        # ========================
        mode = decide_mode(q)
        print("🧠 Initial decision:", mode)

        if mode == "SQL":
            print("💾 SQL intent detected; locking SQL mode.")
        else:
            if debug_docs and len(debug_docs) > 0:
                print("📝 Relevant docs found -> TEXT (RAG).")
                mode = "TEXT"
            else:
                print("🧾 No docs found -> TEXT fallback.")
                mode = "TEXT"

        print("📝 Final decision:", mode)

        # ========================
        # 3) Execute Mode
        # ========================
        if mode == "SQL":
            print("➡️ Running SQL flow")
            sql_query = generate_sql(q)
            print("🧠 Generated SQL:", sql_query)

            if sql_query.strip().upper().startswith("SELECT 'NO_SQL_RETURNED'"):
                return {"type": "SQL", "query": sql_query, "answer": "I couldn't generate a valid SQL query for that question."}
            try:
                result = execute_sql(sql_query)
                friendly = format_sql_result(result, q)
                return {
                    "type": "SQL",
                    "query": sql_query,
                    "raw": result,
                    "answer": friendly
                }
            except Exception as e:
                print("⚠️ SQL execution error:", e)
                return {"type": "SQL", "query": sql_query, "answer": f"SQL Execution Error: {str(e)}"}

        else:
            print("➡️ Running TEXT (RAG) flow")
            prompt_text = f"Question: {q}\n\nContext:\n{context}" if context else f"Question: {q}\n\nContext:\n"

            try:
                completion = client.chat.completions.create(
                    # model="mistralai/mistral-7b-instruct",
                    # model="mistralai/mistral-7b-instruct",
                    model="gpt-4o-mini",

                    messages=[
                        {"role": "system", "content": "You are a helpful WMS assistant. Use the RAG context if relevant."},
                        {"role": "user", "content": prompt_text},
                    ],
                )

                # 🧾 Debug print — see full structure
                print("🧠 RAW completion object:", completion)

                # ✅ Flexible parsing: handles both OpenAI and OpenRouter style
                reply = ""

                if hasattr(completion, "choices") and len(completion.choices) > 0:
                    choice = completion.choices[0]

                    # Case 1: OpenAI style
                    if hasattr(choice, "message") and getattr(choice.message, "content", None):
                        reply = choice.message.content

                    # Case 2: OpenRouter style
                    elif hasattr(choice, "text") and choice.text:
                        reply = choice.text

                    # Case 3: dict style
                    elif isinstance(choice, dict):
                        reply = choice.get("message", {}).get("content", "") or choice.get("text", "")

                if not reply or not reply.strip():
                    print("⚠️ Model returned empty content (after parsing). Full object:", completion)
                    reply = "⚠️ The model didn't return any message. Please try again."

                print("🧾 Final reply:", reply)
                return {"type": "TEXT", "answer": reply}

            except Exception as e:
                print("❌ LLM API Error:", e)
                return {"type": "TEXT", "answer": f"Model error: {str(e)}"}

    except Exception as e:
        print("❌ Unexpected chat error:", traceback.format_exc())
        return {"type": "ERROR", "answer": f"Internal Server Error: {str(e)}"}
