from flask import render_template, request, current_app as app, send_file, url_for
from app.search_utils import perform_search, get_overall_stats
import io
import csv
import math
from collections import Counter
import re

@app.route('/')
@app.route('/index')
def index():
    stats = get_overall_stats()
    return render_template('index.html', stats=stats)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').strip()
    search_type = request.args.get('search_type', 'partial')
    columns = request.args.getlist('columns') or ['Description', 'Codelist_Name']
    page = int(request.args.get('page', 1))
    per_page = 20
    sort_by = request.args.get('sort_by')
    use_fuzzy = request.args.get('use_fuzzy', 'false').lower() == 'true'
    
    if query:
        terms = re.findall(r'"[^"]*"|\S+', query)
        terms = [term.strip('"') for term in terms]
    else:
        terms = []
    
    results, total_count = perform_search(terms, columns, search_type, page, per_page, sort_by, use_fuzzy)
    
    if not results:
        no_results_message = ("We apologize, but no results were found matching your search criteria. "
                              "Please try again with different terms or adjust your search parameters.")
        return render_template('results.html', 
                               query=query, 
                               search_type=search_type, 
                               columns=columns,
                               no_results_message=no_results_message)
    
    total_pages = math.ceil(total_count / per_page)
    
    codelist_counts = Counter(result['Codelist_Name'] for result in results)
    source_counts = Counter(result['Source_Codelist'] for result in results)

    chart_data = {
        'codelist': {
            'labels': list(codelist_counts.keys()),
            'data': list(codelist_counts.values())
        },
        'source': {
            'labels': list(source_counts.keys()),
            'data': list(source_counts.values())
        }
    }
    
    return render_template('results.html', 
                           results=results, 
                           query=query, 
                           search_type=search_type, 
                           columns=columns,
                           page=page,
                           total_pages=total_pages,
                           total_count=total_count,
                           chart_data=chart_data)

@app.route('/export', methods=['GET'])
def export():
    query = request.args.get('query', '')
    search_type = request.args.get('search_type', 'partial')
    columns = request.args.getlist('columns') or ['Description', 'Codelist_Name']
    use_fuzzy = request.args.get('use_fuzzy', 'false').lower() == 'true'
    
    terms = [term.strip() for term in re.split(r'\s+(?=(?:[^"]*"[^"]*")*[^"]*$)', query) if term.strip()]
    
    results, _ = perform_search(terms, columns, search_type, page=1, per_page=1000000, use_fuzzy=use_fuzzy)  # Large per_page to get all results
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=results[0].keys() if results else [])
    writer.writeheader()
    writer.writerows(results)
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='search_results.csv'
    )

@app.route('/export_unique', methods=['GET'])
def export_unique():
    query = request.args.get('query', '')
    search_type = request.args.get('search_type', 'partial')
    columns = request.args.getlist('columns') or ['Description', 'Codelist_Name']
    use_fuzzy = request.args.get('use_fuzzy', 'false').lower() == 'true'
    
    terms = [term.strip() for term in re.split(r'\s+(?=(?:[^"]*"[^"]*")*[^"]*$)', query) if term.strip()]
    
    results, _ = perform_search(terms, columns, search_type, page=1, per_page=1000000, use_fuzzy=use_fuzzy)  # Large per_page to get all results
    
    # Get unique results based on SNOMED_CT_Concept_ID
    unique_results = {row['SNOMED_CT_Concept_ID']: row for row in results}.values()
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=results[0].keys() if results else [])
    writer.writeheader()
    writer.writerows(unique_results)
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='unique_results.csv'
    )