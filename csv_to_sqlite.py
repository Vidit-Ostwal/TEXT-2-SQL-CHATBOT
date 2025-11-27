import pandas as pd
import sqlite3
import os

# 1. Define the CSV files you need to load
csv_files = [
    "territory_dim.csv",
    "rep_dim.csv",
    "fact_rx.csv",
    "fact_payor_mix.csv",
    "date_dim.csv",
    "fact_ln_metrics.csv",
    "fact_rep_activity.csv",
    "account_dim.csv",
    "hcp_dim.csv"
]

# 2. Define the database file name
db_file = "pharma_data.db"

def load_csv_to_sqlite():
    """
    Loads a list of CSV files into a single SQLite database, 
    creating a table for each file.
    """

    csv_files = [
    "territory_dim.csv",
    "rep_dim.csv",
    "fact_rx.csv",
    "fact_payor_mix.csv",
    "date_dim.csv",
    "fact_ln_metrics.csv",
    "fact_rep_activity.csv",
    "account_dim.csv",
    "hcp_dim.csv"]

    # 2. Define the database file name
    db_file = "pharma_data.db"

    print(f"Connecting to database: {db_file}")
    
    # Connect to the SQLite database (it will be created if it doesn't exist)
    conn = sqlite3.connect(db_file)
    
    for file_name in csv_files:
        # Check if the file exists before attempting to load
        full_path = os.path.join("data", file_name)
        if not os.path.exists(full_path):
            print(f"⚠️ Warning: File not found: {file_name}. Skipping.")
            continue
            
        # Create a clean table name from the file name
        table_name = file_name.replace(".csv", "")
        
        try:
            print(f"Loading '{file_name}' into table '{table_name}'...")
            
            # Read the CSV into a pandas DataFrame
            # Assuming the first row contains headers.
            df = pd.read_csv(full_path)
            
            # Write the DataFrame to the SQL database
            # 'replace' will overwrite the table if it already exists
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            print(f"   ✅ Successfully loaded {len(df)} rows.")

        except pd.errors.EmptyDataError:
            print(f"   ❌ Error: {file_name} is empty. Skipping.")
        except Exception as e:
            print(f"   ❌ An error occurred while processing {file_name}: {e}")

    # Close the connection
    conn.close()
    print("\nAll files processed. Database connection closed.")
    print(f"Database '{db_file}' is ready!")