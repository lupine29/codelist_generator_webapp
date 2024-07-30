import pandas as pd
import sqlite3

def setup_database():
    # Define the data types for each column
    dtypes = {
        'Description': str,
        'SNOMED_CT_Concept_ID': str,
        'Med_Code_ID': str,
        'Source_Codelist': str,
        'Codelist_Name': str,
        'Original_Source': str,
        'Codelist_Description': str
    }

    # Read the CSV file with specified dtypes
    df = pd.read_csv(r"C:\Users\Micheal\Desktop\Work\CPRD\Codelists\Sources\Complete_Repo\Entire_Repository_2024_07_26.csv", dtype=dtypes)

    # Create a connection to the SQLite database
    conn = sqlite3.connect('medical_codelists.db')
    cursor = conn.cursor()

    # Drop existing tables if they exist
    cursor.execute("DROP TABLE IF EXISTS codelists")
    cursor.execute("DROP TABLE IF EXISTS codelists_fts")

    # Write the dataframe to SQLite
    df.to_sql('codelists', conn, if_exists='replace', index=False)

    # Create indexes for faster searching
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_description ON codelists(Description)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_codelist_name ON codelists(Codelist_Name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_snomed_ct_concept_id ON codelists(SNOMED_CT_Concept_ID)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_med_code_id ON codelists(Med_Code_ID)')

    # Set up Full-Text Search
    cursor.execute('CREATE VIRTUAL TABLE IF NOT EXISTS codelists_fts USING fts5(Description, Codelist_Name, Codelist_Description)')
    cursor.execute('DELETE FROM codelists_fts')  # Clear existing data if any
    cursor.execute('''
        INSERT INTO codelists_fts(Description, Codelist_Name, Codelist_Description)
        SELECT Description, Codelist_Name, Codelist_Description FROM codelists
    ''')

    conn.commit()
    conn.close()

    print("Database setup completed successfully.")

if __name__ == "__main__":
    setup_database()