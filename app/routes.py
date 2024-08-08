from flask import render_template, request, current_app as app, send_file, url_for
from app.search_utils import perform_search, get_overall_stats
import io
import csv
import math
from collections import Counter

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
    unique_snomed = request.args.get('unique_snomed', 'false').lower() == 'true'

    # Perform search without pagination to get all results
    all_results, total_count = perform_search(query, columns, search_type, 1, None, sort_by, use_fuzzy)

    if unique_snomed:
        # Filter for unique SNOMED codes from all results
        unique_results = {result['SNOMED_CT_Concept_ID']: result for result in all_results}.values()
        results = list(unique_results)
        total_count = len(results)
    else:
        results = all_results

    # Apply pagination after filtering
    total_pages = math.ceil(total_count / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_results = results[start:end]

    # Prepare data for visualizations using all results
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
    
    if not results:
        no_results_message = ("We apologize, but no results were found matching your search criteria. "
                              "Please try again with different terms or adjust your search parameters.")
        return render_template('results.html', 
                               query=query, 
                               search_type=search_type, 
                               columns=columns,
                               no_results_message=no_results_message)
    
    return render_template('results.html', 
                           results=paginated_results, 
                           query=query, 
                           search_type=search_type, 
                           columns=columns,
                           page=page,
                           total_pages=total_pages,
                           total_count=total_count,
                           chart_data=chart_data,
                           unique_snomed=unique_snomed)

@app.route('/export', methods=['GET'])
def export():
    query = request.args.get('query', '')
    search_type = request.args.get('search_type', 'partial')
    columns = request.args.getlist('columns') or ['Description', 'Codelist_Name']
    use_fuzzy = request.args.get('use_fuzzy', 'false').lower() == 'true'
    unique_snomed = request.args.get('unique_snomed', 'false').lower() == 'true'
    
    results, _ = perform_search(query, columns, search_type, page=1, per_page=None, use_fuzzy=use_fuzzy, unique_snomed=unique_snomed)
    
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
    
    results, _ = perform_search(query, columns, search_type, page=1, per_page=1000000, use_fuzzy=use_fuzzy)
    
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