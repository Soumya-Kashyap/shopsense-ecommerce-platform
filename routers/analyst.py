import os
import re
from typing import Any
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
import models
import schemas

load_dotenv()

router = APIRouter(
    tags=["AI Data Analyst Text-to-SQL (Milestone 3)"]
)

# Complete SQLite Schema Context provided to Groq LLM
DB_SCHEMA_CONTEXT = """
-- SQLite Database Schema for ShopSense E-Commerce Platform:

CREATE TABLE vendors (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    role VARCHAR(50),      -- 'admin' or 'vendor'
    status VARCHAR(50)     -- 'active', 'pending', or 'suspended'
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    vendor_id INTEGER REFERENCES vendors(id),
    name VARCHAR(255),
    price FLOAT,           -- Unit price in ₹ INR
    stock_qty INTEGER,     -- Stock quantity
    category VARCHAR(255), -- Product category
    tags VARCHAR(255),
    description TEXT
);

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER,      -- Units sold in this order
    total_amount FLOAT,    -- Total revenue in ₹ INR
    created_at DATETIME    -- Order timestamp
);

CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255)
);
"""


def sanitize_and_validate_sql(sql_str: str) -> tuple[str, bool, str]:
    """
    Multi-layer safety net validating LLM-generated SQL query:
    1. Removes markdown code block markers.
    2. Enforces strict read-only SELECT constraints.
    3. Blacklists destructive keywords (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, ATTACH, DETACH, ;).
    """
    # Remove markdown formatting if present
    clean_sql = re.sub(r"```sql|```", "", sql_str, flags=re.IGNORECASE).strip()

    # Reject multi-statement query tricks via semicolon
    if ";" in clean_sql:
        clean_sql = clean_sql.split(";")[0].strip()

    sql_upper = clean_sql.upper()

    # Blacklist destructive keywords
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "ATTACH", "DETACH", "PRAGMA", "EXEC"]
    for word in forbidden:
        # Match whole keyword or sub-word
        if re.search(r'\b' + word + r'\b', sql_upper):
            return "", False, f"Security Violation: Query contained forbidden operation keyword '{word}'."

    # Must be a SELECT or WITH statement
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return "", False, "Security Violation: Query must start with SELECT or WITH statement."

    return clean_sql, True, ""


@router.post("/vendor/{vendor_id}/ai-analyst", response_model=schemas.AIAnalystResponse)
def run_vendor_ai_analyst(
    vendor_id: int,
    payload: schemas.AIAnalystRequest,
    db: Session = Depends(get_db)
):
    """
    POST /vendor/{vendor_id}/ai-analyst (Milestone 3 Text-to-SQL Feature):
    1. Converts natural language vendor questions into valid, vendor-scoped SQLite queries.
    2. Validates SQL for strict read-only safety (blacklists INSERT, UPDATE, DELETE, DROP, ALTER).
    3. Executes query safely via SQLAlchemy.
    4. Uses Groq LLM to synthesize natural language business answers in ₹ INR.
    """
    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found."
        )

    question_text = payload.question.strip()
    groq_api_key = os.getenv("GROQ_API_KEY")

    # Step 1: Text-to-SQL Prompting
    sql_prompt_system = (
        "You are an expert SQLite Text-to-SQL generator for the ShopSense e-commerce platform.\n"
        f"Database Schema:\n{DB_SCHEMA_CONTEXT}\n\n"
        f"CRITICAL SAFETY & SCOPING RULES:\n"
        f"1. You MUST generate ONLY a valid, executable SQLite SELECT query.\n"
        f"2. You MUST NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, or any write operations.\n"
        f"3. TENANT ISOLATION: The vendor asking this question has vendor_id = {vendor_id}.\n"
        f"   You MUST ALWAYS filter by products.vendor_id = {vendor_id} (or join products and filter by products.vendor_id = {vendor_id}).\n"
        f"   Never allow querying data belonging to other vendors.\n"
        f"4. Return ONLY the raw SQL code wrapped in ```sql ... ``` block or plain text without explanations."
    )

    sql_prompt_user = f"Vendor '{vendor.name}' asks: \"{question_text}\""

    generated_sql = ""
    if groq_api_key:
        try:
            import groq
            client = groq.Groq(api_key=groq_api_key)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": sql_prompt_system},
                    {"role": "user", "content": sql_prompt_user}
                ],
                temperature=0.1,
                max_tokens=250
            )
            if completion.choices and completion.choices[0].message.content:
                generated_sql = completion.choices[0].message.content.strip()
        except Exception as err:
            print(f"Groq Text-to-SQL API warning: {err}")

    # Fallback SQL query generation if Groq call is unavailable
    if not generated_sql:
        q_lower = question_text.lower()
        if "top" in q_lower or "best" in q_lower:
            generated_sql = (
                f"SELECT p.name AS product_name, p.price, SUM(t.quantity) AS units_sold, SUM(t.total_amount) AS revenue "
                f"FROM products p JOIN transactions t ON p.id = t.product_id "
                f"WHERE p.vendor_id = {vendor_id} "
                f"GROUP BY p.id, p.name, p.price ORDER BY units_sold DESC LIMIT 5"
            )
        elif "order" in q_lower or "total" in q_lower:
            generated_sql = (
                f"SELECT COUNT(t.id) AS total_orders, SUM(t.quantity) AS total_units, SUM(t.total_amount) AS total_revenue "
                f"FROM products p JOIN transactions t ON p.id = t.product_id "
                f"WHERE p.vendor_id = {vendor_id}"
            )
        else:
            generated_sql = (
                f"SELECT p.name AS product_name, p.price, p.stock_qty, p.category "
                f"FROM products p WHERE p.vendor_id = {vendor_id} ORDER BY p.stock_qty ASC"
            )

    # Step 2: Safety Validation
    clean_sql, is_safe, err_msg = sanitize_and_validate_sql(generated_sql)

    if not is_safe:
        return {
            "answer": f"⚠️ Query security rejection: {err_msg} Only safe SELECT queries are permitted.",
            "sql_query": generated_sql,
            "data": [],
            "query_success": False
        }

    # Step 3: Execute SQL Query safely via SQLAlchemy
    raw_data = []
    try:
        query_result = db.execute(text(clean_sql), {"vendor_id": vendor_id})
        # Extract rows as dictionaries
        mappings = query_result.mappings().all()
        for r in mappings[:50]:  # Limit max 50 rows
            row_dict = {}
            for k, v in r.items():
                if isinstance(v, (float, int, str)) or v is None:
                    row_dict[k] = v
                else:
                    row_dict[k] = str(v)
            raw_data.append(row_dict)
    except Exception as exec_err:
        print(f"SQL execution error: {exec_err}")
        return {
            "answer": f"I couldn't execute the generated SQL query directly ({str(exec_err)}). Please try rephrasing your question!",
            "sql_query": clean_sql,
            "data": [],
            "query_success": False
        }

    # Step 4: Synthesize Natural Language Answer using Groq LLM
    answer_synthesis_prompt = (
        "You are ShopSense AI Data Analyst, a sharp business intelligence advisor for vendor merchants.\n"
        f"Vendor Name: '{vendor.name}'\n"
        f"Original Question: \"{question_text}\"\n"
        f"Executed SQL Query: {clean_sql}\n"
        f"Query Data Results: {raw_data}\n\n"
        "Instructions:\n"
        "1. Write a clear, concise, and helpful 2-3 sentence answer explaining the findings to the vendor.\n"
        "2. Format prices in Indian Rupees (₹ INR) using standard formatting.\n"
        "3. Highlight top metrics, units sold, or key product insights directly."
    )

    natural_answer = ""
    if groq_api_key:
        try:
            import groq
            client = groq.Groq(api_key=groq_api_key)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are ShopSense AI Data Analyst."},
                    {"role": "user", "content": answer_synthesis_prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            if completion.choices and completion.choices[0].message.content:
                natural_answer = completion.choices[0].message.content.strip()
        except Exception as err:
            print(f"Groq synthesis warning: {err}")

    if not natural_answer:
        if raw_data:
            first_row = raw_data[0]
            summary_parts = [f"{k}: {v}" for k, v in first_row.items()]
            natural_answer = f"Based on your sales database analysis for '{vendor.name}': " + ", ".join(summary_parts) + "."
        else:
            natural_answer = f"No sales transaction records matched your query criteria for {vendor.name}."

    return {
        "answer": natural_answer,
        "sql_query": clean_sql,
        "data": raw_data,
        "query_success": True
    }
