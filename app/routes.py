# app/routes.py

from flask import render_template, request, current_app as app, send_file, url_for
from app.search_utils import perform_search
import io
import csv
import math
from collections import Counter

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    search_type = request.args.get('search_type', 'partial')
    columns = request.args.getlist('columns') or ['Description', 'Codelist_Name']
    page = int(request.args.get('page', 1))
    per_page = 20  # Number of results per page
    
    terms = [term.strip() for term in query.split(',') if term.strip()]
    
    results, total_count = perform_search(terms, columns, search_type, page, per_page)
    
    total_pages = math.ceil(total_count / per_page)
    
    # Prepare data for visualization
    codelist_counts = Counter(result['Codelist_Name'] for result in results)
    chart_data = {
        'labels': list(codelist_counts.keys()),
        'data': list(codelist_counts.values())
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
    
    terms = [term.strip() for term in query.split(',') if term.strip()]
    
    results = perform_search(terms, columns, search_type)
    
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
    
    terms = [term.strip() for term in query.split(',') if term.strip()]
    
    results = perform_search(terms, columns, search_type)
    
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