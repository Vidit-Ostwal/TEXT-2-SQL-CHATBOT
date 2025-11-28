import json
import sqlite3
from pydantic import BaseModel
from openai import OpenAI
from system_prompt import SYSTEM_PROMPT 
import re
from csv_to_sqlite import load_csv_to_sqlite


try:
    client = OpenAI()
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    print("Please ensure OPENAI_API_KEY environment variable is set.")

DB_FILE = "pharma_data.db"
GPT_MODEL = "gpt-4o-mini"

load_csv_to_sqlite()

MAX_RETRIES = 5

class QueryRequest(BaseModel):
    """Model for the incoming user query."""
    user_question: str


def build_sql_prompt(user_question: str) -> str:
    """Builds the full prompt used to generate the SQL query."""

    return f"""
    -- ROLE: Data Analyst SQL Expert
    -- TASK: You are a highly accurate SQLite database expert. Your sole function is to translate a user's natural language question into a single, valid, and executable SQLite query.

    -- OUTPUT FORMAT (required, exact):
    -- 1) A short, high-level, non-sensitive explanation enclosed in <explanation>...</explanation>.
    --    - This should be a concise rationale describing the approach and any key assumptions (reveal internal chain-of-thought or step-by-step hidden reasoning).
    -- 2) The final SQL enclosed in <sql>...</sql>.
    --    - The <sql> section must contain only the single, executable SQLite query (no surrounding backticks, no commentary).
    -- Example correct output:
    -- <explanation>Use date_dim.year filter for 2024; aggregate prescriptions by doctor; exclude null names.</explanation>
    -- <sql>SELECT ...;</sql>

    -- DATABASE CONTEXT:
    -- The database is named 'pharma_data.db' and uses the SQLite dialect.

    -- SCHEMA DEFINITION:
    {SYSTEM_PROMPT}

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


def generate_sql_query(messages: list = [], max_retry: int = 3) -> dict | None:
    """Generates a SQL query from the user question using the LLM with retry logic."""
    retry_count = 0
    while retry_count < max_retry:
        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                temperature=0.0
            )
            response = response.choices[0].message.content.strip()
            parsed = parse_response(response)
            return parsed
        except Exception:
            retry_count += 1
    
    print(f"Failed to generate valid SQL after {max_retry} retries.")
    return {}


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
    messages = []
    user_question = user_question.strip()
    prompt = build_sql_prompt(user_question)
    messages.append({"role": "user", "content": prompt})

    final_answer = ""
    sql_query = ""
    sql_result = ""
    explanation = ""


    for attempt in range(MAX_RETRIES):
        print(f"Attempt {attempt + 1} of {MAX_RETRIES} to generate valid SQL query...")
        generated_response = generate_sql_query(messages)

        sql_query = generated_response.get('sql')
        explanation = generated_response.get('explanation')
        error_message = None

        if sql_query is None:
            error_message = "Failed to generate valid SQL query."
        else:
            sql_result = execute_sql(sql_query)
            if sql_result.startswith("SQL_ERROR") or sql_result.startswith("GENERAL_ERROR"):
                error_message = f"SQL generation was successful, but execution failed. The error was: {sql_result.split(': ', 1)[1]}"
            elif sql_result == "[]": # Check for exact empty array string
                error_message = "No data found for the given query, try another query."
            else:
                # If no error and data found, break the retry loop
                break
        
        # If an error occurred, append messages for retry and continue loop
        if error_message:
            messages.append({"role": "assistant", "content": generated_response})
            messages.append({"role": "user", "content": f"The previous attempt resulted in an error: {error_message}. Please try again."})
            print(f"Error encountered: {error_message}. Retrying...")
            continue

    if sql_query is None or error_message:
        # If loop finished without success due to persistent errors or max retries
        final_answer = "I was unable to generate a valid SQL query or execute it successfully. Please try rephrasing your question."
        return {
            "status": "failure",
            "final_answer": final_answer,
            "generated_sql": sql_query if sql_query else "N/A",
            "sql_result": sql_result if sql_result else "N/A",
            "model_used": GPT_MODEL,
            "explanation": explanation if explanation else "N/A"
        }

    final_answer = generate_final_answer(user_question, sql_query, sql_result)
    
    return {
        "status": "success",
        "final_answer": final_answer,
        "generated_sql": sql_query,
        "sql_result": sql_result,
        "model_used": GPT_MODEL,
        "explanation": explanation
    }
