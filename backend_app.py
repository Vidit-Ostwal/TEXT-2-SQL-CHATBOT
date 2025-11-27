import os
import time
import json
import sqlite3
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI, APIError
from system_prompt import SYSTEM_PROMPT 
import re
from csv_to_sqlite import load_csv_to_sqlite


# --- Configuration ---
# NOTE: The OpenAI client will automatically look for the OPENAI_API_KEY 
# environment variable.
try:
    client = OpenAI()
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    print("Please ensure OPENAI_API_KEY environment variable is set.")

DB_FILE = "pharma_data.db"
GPT_MODEL = "gpt-4o-mini" # Using gpt-4o-mini as the intended model

load_csv_to_sqlite()

# --- Retry Logic Configuration ---
MAX_RETRIES = 5
INITIAL_DELAY = 2  # Seconds
RETRY_DELAY = lambda attempt: INITIAL_DELAY * (2 ** attempt) # Exponential backoff

# --- Pydantic Models for FastAPI ---
class QueryRequest(BaseModel):
    """Model for the incoming user query."""
    user_question: str

class QueryResponse(BaseModel):
    """Model for the final response."""
    status: str
    final_answer: str
    generated_sql: str
    sql_result: str
    model_used: str


# --- LLM Helper: Detailed Prompt Context ---

def get_db_schema_and_relationships():
    """
    Returns the detailed schema and relationship text for the LLM prompt.
    """
    return SYSTEM_PROMPT
    schema = """
    CREATE TABLE territory_dim (territory_id INTEGER, name TEXT, geo_type TEXT, parent_territory_id INTEGER);
    CREATE TABLE rep_dim (rep_id INTEGER, first_name TEXT, last_name TEXT, region TEXT);
    CREATE TABLE fact_rx (hcp_id INTEGER, date_id INTEGER, brand_code TEXT, trx_cnt INTEGER, nrx_cnt INTEGER);
    CREATE TABLE fact_payor_mix (account_id INTEGER, date_id INTEGER, payor_type TEXT, pct_of_volume REAL);
    CREATE TABLE date_dim (date_id INTEGER, calendar_date TEXT, year INTEGER, quarter TEXT, week_num INTEGER, day_of_week TEXT);
    CREATE TABLE fact_ln_metrics (entity_type TEXT, entity_id INTEGER, quarter_id TEXT, ln_patient_cnt INTEGER, est_market_share REAL);
    CREATE TABLE fact_rep_activity (activity_id INTEGER, rep_id INTEGER, hcp_id INTEGER, account_id INTEGER, date_id INTEGER, activity_type TEXT, status TEXT, time_of_day TEXT, duration_min REAL);
    CREATE TABLE account_dim (account_id INTEGER, name TEXT, account_type TEXT, address TEXT, territory_id INTEGER);
    CREATE TABLE hcp_dim (hcp_id INTEGER, full_name TEXT, specialty TEXT, tier TEXT, territory_id INTEGER);

    -- Explicit Foreign Key Relationships (CRITICAL FOR JOINS):
    -- 1. Date Joins: fact_rx.date_id <-> date_dim.date_id, fact_payor_mix.date_id <-> date_dim.date_id, fact_rep_activity.date_id <-> date_dim.date_id
    -- 2. Territory Joins: hcp_dim.territory_id <-> territory_dim.territory_id, account_dim.territory_id <-> territory_dim.territory_id
    -- 3. Rep/Territory: rep_dim.region <-> territory_dim.name (name-based join for territory)
    -- 4. HCP/Account Joins: fact_rx.hcp_id <-> hcp_dim.hcp_id, fact_rep_activity.hcp_id <-> hcp_dim.hcp_id/account_dim.account_id
    -- 5. Longitudinal Metrics: fact_ln_metrics.entity_id joins to hcp_dim.hcp_id when entity_type = 'H'.
    """
    return schema


def build_sql_prompt(user_question: str) -> str:
    """Builds the full prompt used to generate the SQL query."""
    schema = get_db_schema_and_relationships()
    # return f"""
    # -- ROLE: Data Analyst SQL Expert
    # -- TASK: You are a highly accurate SQLite database expert. Your sole function is to translate a user's natural language question into a single, valid, and executable SQLite query. 
    # -- You MUST only output the raw SQL query. DO NOT include any explanatory text, conversational filler, or markdown formatting (e.g., no ```sql...```).

    # -- DATABASE CONTEXT:
    # -- The database is named 'pharma_data.db' and uses the SQLite dialect.

    # -- SCHEMA DEFINITION:
    # {schema}

    # -- INSTRUCTIONS & RULES:
    # -- 1. **SQL DIALECT:** Use standard SQLite syntax.
    # -- 2. **Aliasing:** Always use table aliases (e.g., T1, T2) for readability.
    # -- 3. **Aggregation:** Use appropriate aggregate functions (SUM, AVG, COUNT) and GROUP BY clauses when needed.
    # -- 4. **HCP/Account Names:** Names are typically full strings. Use LIKE '%%' or '=' as appropriate.
    # -- 5. **Date Filtering:** Use the appropriate columns in the `date_dim` table for filtering by year, quarter, etc.

    # -- USER QUESTION START:
    # {user_question}
    # -- USER QUESTION END
    # """

    return f"""
    -- ROLE: Data Analyst SQL Expert
    -- TASK: You are a highly accurate SQLite database expert. Your sole function is to translate a user's natural language question into a single, valid, and executable SQLite query.

    -- OUTPUT FORMAT (required, exact):
    -- 1) A short, high-level, non-sensitive explanation enclosed in <explanation>...</explanation>.
    --    - This should be a concise rationale (2–3 short bullet points or <= 40 words) describing the approach and any key assumptions (do NOT reveal internal chain-of-thought or step-by-step hidden reasoning).
    -- 2) The final SQL enclosed in <sql>...</sql>.
    --    - The <sql> section must contain only the single, executable SQLite query (no surrounding backticks, no commentary).
    -- Example correct output:
    -- <explanation>Use date_dim.year filter for 2024; aggregate prescriptions by doctor; exclude null names.</explanation>
    -- <sql>SELECT ...;</sql>

    -- DATABASE CONTEXT:
    -- The database is named 'pharma_data.db' and uses the SQLite dialect.

    -- SCHEMA DEFINITION:
    {schema}

    -- INSTRUCTIONS & RULES:
    -- 1. **SQL DIALECT:** Use standard SQLite syntax.
    -- 2. **Aliasing:** Always use table aliases (e.g., T1, T2) for readability.
    -- 3. **Aggregation:** Use appropriate aggregate functions (SUM, AVG, COUNT) and GROUP BY clauses when needed.
    -- 4. **HCP/Account Names:** Names are typically full strings. Use LIKE '%%' or '=' as appropriate.
    -- 5. **Date Filtering:** Use the appropriate columns in the `date_dim` table for filtering by year, quarter, etc.
    -- 6. **Single Query:** Return exactly one valid, executable SQL statement inside <sql>...</sql>.
    -- 7. **No Extra Output:** Do NOT include any other text, markup, or commentary outside the two tags.
    -- 8. **Safety:** Do NOT output internal chain-of-thought or verbatim reasoning. Only provide the short, high-level explanation in <explanation> as described above.

    -- USER QUESTION START:
    {user_question}
    -- USER QUESTION END
    """


def parse_response(text: str):
    expl = re.search(r"<explanation>(.*?)</explanation>", text, re.DOTALL)
    sql  = re.search(r"<sql>(.*?)</sql>", text, re.DOTALL)

    if not expl or not sql:
        raise ValueError("Missing <explanation> or <sql> tags in model output")

    return {
        "explanation": expl.group(1).strip(),
        "sql": sql.group(1).strip()
    }


def generate_sql_query(user_question: str) -> str:
    """Generates a SQL query from the user question using the LLM with retry logic."""
    prompt = build_sql_prompt(user_question)
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            # The LLM is instructed to only output the SQL query
            response = response.choices[0].message.content.strip()
            parsed = parse_response(response)
            return parsed
            
        except APIError as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY(attempt)
                print(f"OpenAI API Error (Attempt {attempt + 1}/{MAX_RETRIES}): {e}. Retrying in {delay:.2f}s...")
                time.sleep(delay)
            else:
                raise HTTPException(status_code=500, detail=f"OpenAI API failed after {MAX_RETRIES} attempts: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred during SQL generation: {e}")
            
    # Should not be reached, but needed for type completeness
    raise HTTPException(status_code=500, detail="Failed to generate SQL query after all retries.")


def generate_final_answer(question: str, sql_query: str, sql_result: str) -> str:
    """Translates the raw SQL result into a natural language answer."""
    prompt = f"""
    You are a friendly, concise data analyst.
    The user asked the question: "{question}"
    The SQL query executed was: "{sql_query}"
    The raw result from the database was: "{sql_result}"
    
    Please provide the final answer in a single, concise, human-readable sentence. 
    If the result is an empty set, state that no data was found.
    """
    
    # Simple single-attempt LLM call for translation
    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error translating result: {e}"


def execute_sql(sql_query: str) -> str:
    """Executes the SQL query against the SQLite database and formats the result."""
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        
        # Fetch results
        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]
        
        if not rows:
            return "[]" # Return an empty JSON string for no data
            
        # Format results as a list of dictionaries (JSON format)
        result_list = []
        for row in rows:
            result_list.append(dict(zip(column_names, row)))
            
        # Use json.dumps to handle complex types and structure for LLM context
        return json.dumps(result_list, indent=2)

    except sqlite3.OperationalError as e:
        # This is a critical error (e.g., bad syntax, misspelled table/column)
        print(f"SQL Execution Error: {e}")
        return f"SQL_ERROR: {e}"
        
    except Exception as e:
        print(f"General Execution Error: {e}")
        return f"GENERAL_ERROR: {e}"
        
    finally:
        if conn:
            conn.close()


def process_query(user_question: str) -> dict:
    """
    Processes a natural language query, generates SQL, executes it, and provides a final answer.
    """
    user_question = user_question.strip()
    
    # 1. Generate SQL Query (with Retries)
    generated_sql = generate_sql_query(user_question)
    
    # 2. Execute SQL Query
    sql_result = execute_sql(generated_sql.get('sql'))

    # 3. Handle SQL Errors or Success
    if sql_result.startswith("SQL_ERROR") or sql_result.startswith("GENERAL_ERROR"):
        # The prompt is designed to self-correct, but for a fast prototype, we halt here.
        # In a production system, you would feed this error back to the LLM for correction.
        error_message = f"SQL generation was successful, but execution failed. The error was: {sql_result.split(': ', 1)[1]}"
        return {
            "status": "error",
            "final_answer": error_message,
            "generated_sql": generated_sql['sql'],
            "sql_result": sql_result,
            "model_used": GPT_MODEL,
            "explanation": generated_sql['explanation']

        }

    # 4. Generate Final Answer
    final_answer = generate_final_answer(user_question, generated_sql, sql_result)
    
    return {
        "status": "success",
        "final_answer": final_answer,
        "generated_sql": generated_sql['sql'],
        "sql_result": sql_result,
        "model_used": GPT_MODEL,
        "explanation": generated_sql['explanation']
    }
