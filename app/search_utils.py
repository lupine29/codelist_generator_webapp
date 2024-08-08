import sqlite3
import re
from typing import List, Tuple, Dict, Any, Optional

def get_db_connection():
    conn = sqlite3.connect('instance/medical_codelists.db')
    conn.row_factory = sqlite3.Row
    return conn

def build_search_query(query: str, columns: List[str], search_type: str, use_fuzzy: bool = False) -> Tuple[str, List[str]]:
    terms = parse_query(query)
    query_parts = []
    params = []
    
    for term in terms:
        if isinstance(term, str):
            term_query, term_params = build_term_query(term, columns, search_type, use_fuzzy)
            query_parts.append(term_query)
            params.extend(term_params)
        elif isinstance(term, list):
            sub_query_parts = []
            for sub_term in term:
                sub_query, sub_params = build_term_query(sub_term, columns, search_type, use_fuzzy)
                sub_query_parts.append(sub_query)
                params.extend(sub_params)
            query_parts.append('(' + ' OR '.join(sub_query_parts) + ')')
    
    where_clause = ' AND '.join(query_parts)
    sql_query = f"SELECT * FROM codelists WHERE {where_clause}"
    
    return sql_query, params

def parse_query(query: str) -> List[Any]:
    terms = re.findall(r'([()]|\S+)', query)
    parsed = []
    current_group = []
    stack = [parsed]
    
    for term in terms:
        if term == '(':
            new_group = []
            stack[-1].append(new_group)
            stack.append(new_group)
        elif term == ')':
            if len(stack) > 1:
                stack.pop()
        elif term.upper() == 'OR':
            if current_group:
                stack[-1].append(current_group)
                current_group = []
        else:
            current_group.append(term)
    
    if current_group:
        stack[-1].append(current_group)
    
    return flatten(parsed)

def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            if len(item) == 1:
                result.append(item[0])
            else:
                result.append(flatten(item))
        else:
            result.append(item)
    return result

def build_term_query(term: str, columns: List[str], search_type: str, use_fuzzy: bool) -> Tuple[str, List[str]]:
    query_parts = []
    params = []
    
    if term.upper().startswith('NOT '):
        negation = True
        term = term[4:]
    else:
        negation = False
    
    for column in columns:
        if search_type == 'exact':
            query_parts.append(f"LOWER({column}) = LOWER(?)")
            params.append(term)
        elif search_type == 'starts_with':
            query_parts.append(f"LOWER({column}) LIKE LOWER(? || '%')")
            params.append(term)
        elif search_type == 'ends_with':
            query_parts.append(f"LOWER({column}) LIKE LOWER('%' || ?)")
            params.append(term)
        else:  # partial
            if use_fuzzy:
                query_parts.append(f"LOWER({column}) LIKE LOWER('%' || ? || '%') OR LOWER({column}) LIKE LOWER('%' || ? || '%') OR LOWER({column}) LIKE LOWER('%' || ? || '%')")
                params.extend([term[:-1] if len(term) > 1 else term, term, term + '_'])
            else:
                query_parts.append(f"LOWER({column}) LIKE LOWER('%' || ? || '%')")
                params.append(term)
    
    term_query = '(' + ' OR '.join(query_parts) + ')'
    if negation:
        term_query = f"NOT {term_query}"
    
    return term_query, params

def perform_search(query: str, columns: List[str], search_type: str, page: int, per_page: Optional[int], sort_by: str = None, use_fuzzy: bool = False, unique_snomed: bool = False) -> Tuple[List[Dict[str, Any]], int]:
    conn = get_db_connection()
    
    if not query.strip():
        sql_query = "SELECT * FROM codelists"
        params = []
    else:
        sql_query, params = build_search_query(query, columns, search_type, use_fuzzy)
    
    if sort_by == 'snomed':
        sql_query += " ORDER BY SNOMED_CT_Concept_ID"
    else:
        sql_query += " ORDER BY Codelist_Name"
    
    # Get total count
    count_query = f"SELECT COUNT(*) as count FROM ({sql_query})"
    total_count = conn.execute(count_query, params).fetchone()['count']
    
    # Add pagination only if per_page is not None
    if per_page is not None:
        sql_query += " LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
    
    results = conn.execute(sql_query, params).fetchall()
    
    conn.close()
    
    results = [dict(row) for row in results]
    
    if unique_snomed:
        results = list({result['SNOMED_CT_Concept_ID']: result for result in results}.values())
        total_count = len(results)
    
    return results, total_count

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