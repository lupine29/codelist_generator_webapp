# app/search_utils.py

import sqlite3
import re
from typing import List, Dict, Any, Tuple

def get_db_connection():
    conn = sqlite3.connect('instance/medical_codelists.db')
    conn.row_factory = sqlite3.Row
    return conn

def build_search_query(terms: List[str], columns: List[str], search_type: str, use_fuzzy: bool = False) -> Tuple[str, List[str]]:
    query_parts = []
    params = []
    
    for term in terms:
        term_query = []
        if ' AND ' in term.upper():
            and_terms = term.split(' AND ')
            and_query, and_params = build_term_query(and_terms, columns, search_type, use_fuzzy, operator='AND')
            term_query.append(and_query)
            params.extend(and_params)
        elif ' OR ' in term.upper():
            or_terms = term.split(' OR ')
            or_query, or_params = build_term_query(or_terms, columns, search_type, use_fuzzy, operator='OR')
            term_query.append(or_query)
            params.extend(or_params)
        elif term.upper().startswith('NOT '):
            not_term = term[4:].strip()
            not_query, not_params = build_term_query([not_term], columns, search_type, use_fuzzy, operator='NOT')
            term_query.append(not_query)
            params.extend(not_params)
        else:
            single_query, single_params = build_term_query([term], columns, search_type, use_fuzzy)
            term_query.append(single_query)
            params.extend(single_params)
        
        query_parts.append('(' + ' OR '.join(term_query) + ')')
    
    where_clause = ' AND '.join(query_parts)
    sql_query = f"SELECT * FROM codelists WHERE {where_clause}"
    
    return sql_query, params

def build_term_query(terms: List[str], columns: List[str], search_type: str, use_fuzzy: bool, operator: str = 'OR') -> Tuple[str, List[str]]:
    query_parts = []
    params = []
    
    for term in terms:
        term_parts = []
        for column in columns:
            if search_type == 'exact':
                term_parts.append(f"LOWER({column}) = LOWER(?)")
                params.append(term)
            elif search_type == 'starts_with':
                term_parts.append(f"LOWER({column}) LIKE LOWER(? || '%')")
                params.append(term)
            elif search_type == 'ends_with':
                term_parts.append(f"LOWER({column}) LIKE LOWER('%' || ?)")
                params.append(term)
            else:  # partial
                if use_fuzzy:
                    # Simple fuzzy matching: allow for one character difference
                    term_parts.append(f"LOWER({column}) LIKE LOWER('%' || ? || '%') OR LOWER({column}) LIKE LOWER('%' || ? || '%') OR LOWER({column}) LIKE LOWER('%' || ? || '%')")
                    params.extend([term[:-1] if len(term) > 1 else term, term, term + '_'])
                else:
                    term_parts.append(f"LOWER({column}) LIKE LOWER('%' || ? || '%')")
                    params.append(term)
        
        if operator == 'NOT':
            query_parts.append(f"NOT ({' OR '.join(term_parts)})")
        else:
            query_parts.append(f"({' OR '.join(term_parts)})")
    
    return f" {operator} ".join(query_parts), params

def perform_search(terms: List[str], columns: List[str], search_type: str, page: int, per_page: int, sort_by: str = None, use_fuzzy: bool = False) -> tuple:
    conn = get_db_connection()
    
    if not terms:
        # If no search terms, return all results
        sql_query = "SELECT * FROM codelists"
        params = []
    else:
        sql_query, params = build_search_query(terms, columns, search_type, use_fuzzy)
    
    if sort_by == 'snomed':
        sql_query += " GROUP BY SNOMED_CT_Concept_ID"
    
    sql_query += " ORDER BY SNOMED_CT_Concept_ID"
    
    # Add pagination
    sql_query += " LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])
    
    results = conn.execute(sql_query, params).fetchall()
    
    # Get total count for pagination
    count_query = f"SELECT COUNT(*) as count FROM ({sql_query.split('LIMIT')[0]})"
    total_count = conn.execute(count_query, params[:-2]).fetchone()['count']
    
    conn.close()
    
    return [dict(row) for row in results], total_count

def get_overall_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get total count of codes
    cursor.execute("SELECT COUNT(*) FROM codelists")
    total_codes = cursor.fetchone()[0]

    # Get count of unique SNOMED codes
    cursor.execute("SELECT COUNT(DISTINCT SNOMED_CT_Concept_ID) FROM codelists")
    unique_snomed = cursor.fetchone()[0]

    # Get top 5 sources
    cursor.execute("""
        SELECT Source_Codelist, COUNT(*) as count
        FROM codelists
        GROUP BY Source_Codelist
        ORDER BY count DESC
        LIMIT 5
    """)
    top_sources = cursor.fetchall()

    # Get top 5 largest codelists
    cursor.execute("""
        SELECT Codelist_Name, COUNT(*) as count
        FROM codelists
        GROUP BY Codelist_Name
        ORDER BY count DESC
        LIMIT 5
    """)
    top_codelists = cursor.fetchall()

    conn.close()

    return {
        'total_codes': total_codes,
        'unique_snomed': unique_snomed,
        'top_sources': top_sources,
        'top_codelists': top_codelists
    }