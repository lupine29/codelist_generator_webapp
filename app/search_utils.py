# app/search_utils.py

import sqlite3
from typing import List, Dict, Any

def get_db_connection():
    conn = sqlite3.connect('instance/medical_codelists.db')
    conn.row_factory = sqlite3.Row
    return conn

def build_search_query(terms: List[str], columns: List[str], search_type: str) -> tuple:
    """
    Build the SQL query based on search terms, columns, and search type.
    """
    query_parts = []
    params = []
    
    for term in terms:
        term_query = []
        for column in columns:
            if search_type == 'exact':
                term_query.append(f"LOWER({column}) = LOWER(?)")
                params.append(term)
            elif search_type == 'starts_with':
                term_query.append(f"LOWER({column}) LIKE LOWER(? || '%')")
                params.append(term)
            elif search_type == 'ends_with':
                term_query.append(f"LOWER({column}) LIKE LOWER('%' || ?)")
                params.append(term)
            else:  # partial
                term_query.append(f"LOWER({column}) LIKE LOWER('%' || ? || '%')")
                params.append(term)
        query_parts.append("(" + " OR ".join(term_query) + ")")
    
    where_clause = " AND ".join(query_parts)
    sql_query = f"""
        SELECT * FROM codelists
        WHERE {where_clause}
    """
    
    return sql_query, params

def perform_search(terms: List[str], columns: List[str], search_type: str, page: int, per_page: int) -> tuple:
    """
    Perform the search based on the given terms, columns, and search type, with pagination.
    """
    conn = get_db_connection()
    sql_query, params = build_search_query(terms, columns, search_type)
    
    # Add pagination
    sql_query += " LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])
    
    results = conn.execute(sql_query, params).fetchall()
    
    # Get total count for pagination
    count_query = f"SELECT COUNT(*) as count FROM codelists WHERE {sql_query.split('WHERE')[1].split('LIMIT')[0]}"
    total_count = conn.execute(count_query, params[:-2]).fetchone()['count']
    
    conn.close()
    
    return [dict(row) for row in results], total_count