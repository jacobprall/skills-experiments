#!/usr/bin/env python3
"""
HTML Wave Migration Report Generator

Generates comprehensive interactive HTML report from dependency analysis outputs.
Includes: analysis summary, wave statistics, object details, and hour estimations.
Uses AI to generate contextual benefits and purpose sections based on project characteristics.
"""
import csv
import json
import argparse
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

# Import data loading functions from separate module
from load_data_html_report import (
    load_issues_estimation,
    load_toplevel_code_units,
    load_partition_membership,
    parse_graph_summary,
    parse_cycles,
    parse_excluded_edges,
    load_toplevel_objects_estimation,
    find_estimation_reports,
    load_estimation_grand_totals,
    estimate_hours_for_object,
    load_missing_object_references
)


def load_missing_dependencies_json(json_path):
    """Load missing dependencies JSON file.
    
    The JSON has structure {"_metadata": {...}, "objects": {obj_name: {...}, ...}}.
    Returns just the 'objects' dict for direct lookup by object name.
    """
    if not json_path or not json_path.exists():
        return {}
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract the objects dict; fall back to raw data for legacy format
    return data.get('objects', data)


def load_object_references(reports_dir):
    """Load ObjectReferences CSV to build dependency graph."""
    references = []
    
    # Search for ObjectReferences CSV
    search_path = Path(reports_dir)
    matches = list(search_path.glob('ObjectReferences.*.csv'))
    
    if not matches:
        return references
    
    csv_path = matches[0]
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            caller = row.get('Caller_CodeUnit_FullName', '').strip()
            referenced = row.get('Referenced_Element_FullName', '').strip()
            
            if caller and referenced:
                references.append({
                    'caller': caller,
                    'referenced': referenced
                })
    
    return references


def load_dependency_counts(analysis_dir):
    """Load object dependency counts from object_dependencies.csv."""
    counts = {}
    
    csv_path = Path(analysis_dir) / 'object_dependencies.csv'
    
    if not csv_path.exists():
        return counts
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            obj_name = row.get('object', '').strip()
            if obj_name:
                counts[obj_name] = {
                    'direct_dependencies': int(row.get('direct_dependencies_count', 0)),
                    'direct_dependents': int(row.get('direct_dependents_count', 0)),
                    'total_dependencies': int(row.get('total_dependencies', 0)),
                    'total_dependents': int(row.get('total_dependents', 0))
                }
    
    return counts


def generate_ai_wave_benefits(waves_data, graph_summary, total_objects, total_waves, cycles, excluded_edges):
    """Generate AI-powered wave benefits analysis based on project characteristics.
    
    This function uses Snowflake Cortex Complete to analyze the migration project
    and generate contextual benefits of wave-based migration.
    """
    try:
        # Try to use Snowflake Cortex Complete for AI generation
        import snowflake.connector
        
        conn_name = os.getenv("SNOWFLAKE_CONNECTION_NAME")
        if not conn_name:
            return generate_static_wave_benefits()
        
        # Analyze project characteristics
        categories = Counter()
        technologies = Counter()
        total_with_missing = 0
        
        for wave_num, objects in waves_data.items():
            for obj in objects:
                categories[obj.get('category', 'Unknown')] += 1
                tech = obj.get('technology', '')
                if tech:
                    technologies[tech] += 1
                if obj.get('has_missing_dependencies', False):
                    total_with_missing += 1
        
        # Build analysis context
        context = {
            'total_objects': total_objects,
            'total_waves': total_waves,
            'categories': dict(categories.most_common(5)),
            'technologies': dict(technologies.most_common(3)),
            'has_cycles': len(cycles) > 0,
            'cycle_count': len(cycles),
            'excluded_count': excluded_edges.get('total_excluded', 0),
            'missing_deps_count': total_with_missing,
            'avg_objects_per_wave': total_objects / total_waves if total_waves > 0 else 0
        }
        
        prompt = f"""You are analyzing a database migration project with the following characteristics:

- Total objects to migrate: {context['total_objects']}
- Number of deployment waves: {context['total_waves']}
- Average objects per wave: {context['avg_objects_per_wave']:.1f}
- Object categories: {', '.join(f"{k}: {v}" for k, v in context['categories'].items())}
- Technologies involved: {', '.join(f"{k}: {v}" for k, v in context['technologies'].items()) if context['technologies'] else 'SQL'}
- Circular dependencies detected: {context['cycle_count']}
- Objects with missing dependencies: {context['missing_deps_count']}
- Excluded dependencies (temp tables, etc.): {context['excluded_count']}

Generate a concise explanation (4-6 key benefits, each 2-3 sentences) of why wave-based migration is beneficial for THIS SPECIFIC PROJECT. Focus on:
1. The actual complexity and scale of this migration
2. Specific risks based on the dependency patterns observed
3. How the wave structure addresses this project's challenges
4. Practical deployment considerations for this workload

Format as HTML with benefit cards. Each benefit should have:
- An emoji icon
- A short title (4-6 words)
- A description (2-3 sentences) tailored to this project

Return ONLY the HTML content for the benefit cards (div elements), no markdown formatting."""

        conn = snowflake.connector.connect(connection_name=conn_name)
        cursor = conn.cursor()
        
        sql = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large2',
            [{{'role': 'user', 'content': {json.dumps(prompt)}}}],
            {{'temperature': 0.3, 'max_tokens': 1500}}
        ) AS response
        """
        
        cursor.execute(sql)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result and result[0]:
            response_data = json.loads(result[0])
            ai_content = response_data.get('choices', [{}])[0].get('messages', '')
            if ai_content:
                return ai_content
        
        return generate_static_wave_benefits()
        
    except Exception as e:
        print(f"Note: AI generation not available ({str(e)}), using static content")
        return generate_static_wave_benefits()


def generate_static_wave_benefits():
    """Generate static wave benefits content as fallback."""
    return """
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 3px solid #28a745;">
                    <h4 style="margin-top: 0; color: #005C8F; font-size: 1em;">Dependency Management</h4>
                    <p style="margin: 0; font-size: 0.9em;">Each wave contains objects that only depend on objects from earlier waves, ensuring no deployment failures due to missing dependencies.</p>
                </div>
                
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 3px solid #17a2b8;">
                    <h4 style="margin-top: 0; color: #005C8F; font-size: 1em;">Incremental Validation</h4>
                    <p style="margin: 0; font-size: 0.9em;">Test and validate each wave independently before proceeding to the next, reducing risk and enabling faster issue identification.</p>
                </div>
                
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 3px solid #ffc107;">
                    <h4 style="margin-top: 0; color: #005C8F; font-size: 1em;">Progress Tracking</h4>
                    <p style="margin: 0; font-size: 0.9em;">Clearly defined milestones make it easy to track migration progress, estimate effort, and report status to stakeholders.</p>
                </div>
                
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 3px solid #dc3545;">
                    <h4 style="margin-top: 0; color: #005C8F; font-size: 1em;">Risk Mitigation</h4>
                    <p style="margin: 0; font-size: 0.9em;">Isolate complex dependencies and problematic objects in separate waves, allowing focused attention where needed most.</p>
                </div>
                
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 3px solid #6610f2;">
                    <h4 style="margin-top: 0; color: #005C8F; font-size: 1em;">Parallel Execution</h4>
                    <p style="margin: 0; font-size: 0.9em;">Multiple teams can work on different waves simultaneously once their dependencies are met, accelerating overall timeline.</p>
                </div>
                
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 3px solid #e83e8c;">
                    <h4 style="margin-top: 0; color: #005C8F; font-size: 1em;">Resource Optimization</h4>
                    <p style="margin: 0; font-size: 0.9em;">Allocate team resources based on wave complexity and size, ensuring efficient use of personnel and time.</p>
                </div>
"""


def generate_ai_wave_purpose(wave_num, objects, waves_data):
    """Generate AI-powered purpose statement for a specific wave."""
    try:
        import snowflake.connector
        
        conn_name = os.getenv("SNOWFLAKE_CONNECTION_NAME")
        if not conn_name:
            return generate_static_wave_purpose(wave_num, objects)
        
        # Analyze wave composition
        categories = Counter(obj['category'] for obj in objects)
        technologies = Counter(obj.get('technology', '') for obj in objects if obj.get('technology', ''))
        with_missing = sum(1 for obj in objects if obj.get('has_missing_dependencies', False))
        success_rate = sum(1 for obj in objects if obj.get('conversion_status') == 'Success') / len(objects) * 100
        
        prompt = f"""You are analyzing Wave {wave_num} of a database migration deployment plan.

Wave Characteristics:
- Total objects: {len(objects)}
- Categories: {', '.join(f"{k}: {v}" for k, v in categories.most_common())}
- Technologies: {', '.join(f"{k}: {v}" for k, v in technologies.most_common()) if technologies else 'SQL'}
- Objects with missing dependencies: {with_missing}
- Conversion success rate: {success_rate:.1f}%
- Wave position: {"Early" if wave_num <= 2 else "Middle" if wave_num <= max(waves_data.keys()) // 2 else "Later"} in deployment sequence

Generate a concise purpose statement (2-4 sentences) that explains:
1. The primary role of this wave in the migration sequence
2. What types of objects it contains and why they're grouped together
3. Any special considerations or dependencies for this wave

Be specific and actionable. Return ONLY plain text, no markdown formatting."""

        conn = snowflake.connector.connect(connection_name=conn_name)
        cursor = conn.cursor()
        
        sql = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large2',
            [{{'role': 'user', 'content': {json.dumps(prompt)}}}],
            {{'temperature': 0.3, 'max_tokens': 300}}
        ) AS response
        """
        
        cursor.execute(sql)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result and result[0]:
            response_data = json.loads(result[0])
            ai_content = response_data.get('choices', [{}])[0].get('messages', '')
            if ai_content:
                return ai_content.strip()
        
        return generate_static_wave_purpose(wave_num, objects)
        
    except Exception as e:
        print(f"Note: AI generation not available for wave {wave_num}, using static content")
        return generate_static_wave_purpose(wave_num, objects)


def generate_static_wave_purpose(wave_num, objects):
    """Generate static wave purpose as fallback."""
    categories = Counter(obj['category'] for obj in objects)
    dominant = categories.most_common(1)[0][0] if categories else 'objects'
    
    if wave_num == 1:
        return f"Foundation wave containing {len(objects)} {dominant.lower()}s that have minimal dependencies. These objects form the base layer and must be deployed first to satisfy dependencies for subsequent waves."
    else:
        return f"Deployment wave containing {len(objects)} objects including {', '.join(f'{v} {k}' for k, v in categories.most_common(3))}. This wave depends on earlier waves and should be deployed after Wave {wave_num - 1} is validated."


def generate_html_report(analysis_dir, issues_json_path, output_path=None, reports_dir=None):
    """Generate comprehensive HTML wave report with accurate analysis data."""
    
    analysis_path = Path(analysis_dir)
    
    # Load all analysis files
    partition_membership_path = analysis_path / 'partition_membership.csv'
    graph_summary_path = analysis_path / 'graph_summary.txt'
    cycles_path = analysis_path / 'cycles.txt'
    excluded_edges_path = analysis_path / 'excluded_edges_analysis.txt'
    wave_deployment_order_path = analysis_path / 'wave_deployment_order.json'
    
    # Find TopLevelCodeUnits CSV (can be .NA.csv or .<TIMESTAMP>.csv)
    toplevel_csv_path = None
    missing_deps_json_path = None
    
    # Search directories for TopLevelCodeUnits files
    search_dirs = [
        analysis_path.parent.parent.parent,
        analysis_path.parent.parent.parent / 'Reports',
        analysis_path.parent.parent.parent / 'out' / 'Reports',
        analysis_path.parent,
        analysis_path,
        Path(analysis_dir).parent / 'Reports',
        Path(analysis_dir).parent / 'out' / 'Reports'
    ]
    
    # Add reports_dir if provided
    if reports_dir:
        search_dirs.insert(0, Path(reports_dir))
    
    for search_dir in search_dirs:
        if search_dir.exists():
            # Look for TopLevelCodeUnits.*.csv pattern
            matches = list(search_dir.glob('TopLevelCodeUnits.*.csv'))
            if matches:
                toplevel_csv_path = matches[0]
                break
    
    # Search for missing_dependencies.json
    missing_deps_search_paths = [
        analysis_path / 'missing_dependencies.json',
        analysis_path.parent.parent.parent / 'missing_dependencies.json',
        analysis_path.parent.parent.parent / 'Reports' / 'missing_dependencies.json',
        analysis_path.parent.parent.parent / 'out' / 'Reports' / 'missing_dependencies.json'
    ]
    
    for path in missing_deps_search_paths:
        if path.exists():
            missing_deps_json_path = path
            break
    
    if toplevel_csv_path is None:
        print(f"Error: TopLevelCodeUnits CSV not found in expected locations")
        return
    
    if not partition_membership_path.exists():
        print(f"Error: partition_membership.csv not found at {partition_membership_path}")
        return
    
    # Try to find estimation reports in the same directory as TopLevelCodeUnits
    estimation_data = None
    grand_totals_data = None
    estimation_source = "Baseline (issues-estimation.json)"
    
    if toplevel_csv_path:
        reports_dir = toplevel_csv_path.parent
        estimation_files = find_estimation_reports(reports_dir)
        
        if 'toplevel_estimation' in estimation_files:
            print(f"Found estimation report: {estimation_files['toplevel_estimation']}")
            estimation_data = load_toplevel_objects_estimation(estimation_files['toplevel_estimation'])
            estimation_source = f"Estimation Reports ({estimation_files['toplevel_estimation'].name})"
            
            # Load grand totals from estimation reports
            grand_totals_data = load_estimation_grand_totals(estimation_files)
    
    # Load all data
    issue_map, severity_map = load_issues_estimation(issues_json_path)
    objects_data = load_toplevel_code_units(toplevel_csv_path)
    membership = load_partition_membership(partition_membership_path)
    missing_deps_data = load_missing_dependencies_json(missing_deps_json_path) if missing_deps_json_path else {}
    graph_summary = parse_graph_summary(graph_summary_path)
    cycles = parse_cycles(cycles_path)
    excluded_edges = parse_excluded_edges(excluded_edges_path)
    
    # Load wave deployment order from JSON
    wave_deployment_order_data = {}
    if wave_deployment_order_path.exists():
        with open(wave_deployment_order_path, 'r', encoding='utf-8') as f:
            deployment_json = json.load(f)
            wave_deployment_order_data = deployment_json.get('waves', {})
    
    # Load object references for dependency search
    object_references = load_object_references(toplevel_csv_path.parent) if toplevel_csv_path else []
    
    # Load missing object references for blocked objects section
    missing_obj_refs = load_missing_object_references(toplevel_csv_path.parent) if toplevel_csv_path else {
        'missing_objects': set(),
        'dependents': {},
        'details': []
    }
    
    # Load dependency counts
    dependency_counts = load_dependency_counts(analysis_path)
    
    # Calculate wave statistics
    waves_data = defaultdict(list)
    for obj_name, mem_info in membership.items():
        partition = mem_info['partition']
        obj_info = objects_data.get(obj_name, {})
        
        # Use data from partition_membership first, fallback to TopLevelCodeUnits
        category = mem_info.get('category', obj_info.get('category', 'Unknown'))
        file_name = mem_info.get('file_name', obj_info.get('file_name', ''))
        technology = mem_info.get('technology', obj_info.get('technology', ''))
        conversion_status = mem_info.get('conversion_status', obj_info.get('conversion_status', 'Unknown'))
        subtype = mem_info.get('subtype', '')
        
        estimated_hours = estimate_hours_for_object(obj_name, objects_data, issue_map, severity_map, estimation_data, conversion_status)
        
        # Get missing dependencies for this object
        obj_missing_deps = missing_deps_data.get(obj_name, {})
        missing_deps_list = obj_missing_deps.get('missing_dependencies', [])
        has_missing = obj_missing_deps.get('has_missing_dependencies', False)
        
        # Get dependency counts
        dep_counts = dependency_counts.get(obj_name, {})
        
        # Get EWI, FDM, PRF counts from TopLevelCodeUnits (objects_data)
        ewi_count = 0
        fdm_count = 0
        prf_count = 0
        highest_ewi_severity = ''
        if obj_info:
            ewi_count = obj_info.get('ewi_count', 0)
            fdm_count = obj_info.get('fdm_count', 0)
            prf_count = obj_info.get('prf_count', 0)
            highest_ewi_severity = obj_info.get('highest_ewi_severity', '')
        
        waves_data[partition].append({
            'name': obj_name,
            'category': category,
            'file_name': file_name,
            'has_missing_dependencies': has_missing,
            'conversion_status': conversion_status,
            'estimated_hours': estimated_hours,
            'is_root': mem_info['is_root'],
            'is_leaf': mem_info['is_leaf'],
            'is_picked_scc': mem_info.get('is_picked_scc', False),
            'missing_dependencies': missing_deps_list,
            'dependency_count': dep_counts.get('total_dependencies', 0),
            'dependent_count': dep_counts.get('dependent_count', 0),
            'technology': technology,
            'subtype': subtype,
            'partition_type': mem_info.get('partition_type', 'regular'),
            'ewi_count': ewi_count,
            'fdm_count': fdm_count,
            'prf_count': prf_count,
            'highest_ewi_severity': highest_ewi_severity
        })
    
    # Calculate totals
    total_objects = len(membership)
    total_waves = len(waves_data)
    total_with_missing = sum(1 for obj_name in membership.keys() 
                            if missing_deps_data.get(obj_name, {}).get('has_missing_dependencies', False))
    total_without_missing = total_objects - total_with_missing
    total_estimated_hours = sum(
        estimate_hours_for_object(
            obj_name, 
            objects_data, 
            issue_map, 
            severity_map, 
            estimation_data,
            membership[obj_name].get('conversion_status', objects_data.get(obj_name, {}).get('conversion_status', 'Unknown'))
        ) 
        for obj_name in membership.keys()
    )
    
    success_count = sum(1 for obj_name in membership.keys() 
                       if membership[obj_name].get('conversion_status', objects_data.get(obj_name, {}).get('conversion_status', '')) == 'Success')
    conversion_percentage = (success_count / total_objects * 100) if total_objects > 0 else 0
    
    # Calculate EWI grand totals from TopLevelCodeUnits (objects_data)
    total_objects_with_ewis = sum(1 for obj_name in membership.keys() 
                                  if objects_data.get(obj_name, {}).get('ewi_count', 0) > 0)
    total_ewis = sum(objects_data.get(obj_name, {}).get('ewi_count', 0) 
                     for obj_name in membership.keys())
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if output_path is None:
        output_path = analysis_path / f'wave_report_{timestamp}.html'
    
    # Generate HTML
    html_content = generate_html_content(
        graph_summary, cycles, excluded_edges, waves_data, 
        total_objects, total_waves, total_with_missing, total_without_missing,
        total_estimated_hours, conversion_percentage, timestamp, estimation_source, grand_totals_data,
        object_references, missing_obj_refs, total_objects_with_ewis, total_ewis, wave_deployment_order_data
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML report generated: {output_path}")
    return output_path


def generate_wave_name_and_summary(wave_num, objects):
    """Generate a descriptive name and key procedures for a wave based on its objects.
    
    Args:
        wave_num: The wave number
        objects: List of object dictionaries in the wave
    
    Returns:
        tuple: (wave_name, key_procedures_list)
    """
    from collections import Counter
    
    # Analyze object composition
    categories = Counter(obj['category'] for obj in objects)
    technologies = Counter(obj.get('technology', '') for obj in objects if obj.get('technology', ''))
    
    # Get dominant category
    dominant_category = categories.most_common(1)[0][0] if categories else 'Mixed'
    dominant_tech = technologies.most_common(1)[0][0] if technologies else ''
    
    # Get key objects (prioritize picked_scc objects, then by category importance)
    priority_objects = [obj for obj in objects if obj.get('is_picked_scc', False)]
    if not priority_objects:
        # Priority order: PROCEDURE > FUNCTION > VIEW > TABLE > ETL
        category_priority = {'PROCEDURE': 1, 'FUNCTION': 2, 'VIEW': 3, 'TABLE': 4, 'ETL': 5}
        sorted_objects = sorted(objects, key=lambda x: category_priority.get(x['category'], 99))
        priority_objects = sorted_objects[:5]
    else:
        priority_objects = priority_objects[:5]
    
    # Generate wave name based on composition
    if len(categories) == 1:
        # Single category wave
        category_names = {
            'TABLE': 'Table Foundation',
            'VIEW': 'View Layer',
            'PROCEDURE': 'Stored Procedures',
            'FUNCTION': 'Functions',
            'ETL': 'ETL Pipelines'
        }
        wave_name = category_names.get(dominant_category, dominant_category)
        if dominant_tech:
            wave_name += f" ({dominant_tech})"
    elif dominant_category in ['PROCEDURE', 'ETL']:
        # Procedure/ETL-heavy wave
        wave_name = f"{dominant_category.title()} Pipeline"
        if dominant_tech:
            wave_name += f" ({dominant_tech})"
    elif 'TABLE' in categories and 'VIEW' in categories:
        # Mixed data structures
        wave_name = "Data Structures Layer"
    elif categories.get('TABLE', 0) > len(objects) * 0.6:
        # Table-dominant
        wave_name = "Core Tables"
    elif categories.get('VIEW', 0) > len(objects) * 0.6:
        # View-dominant
        wave_name = "View Definitions"
    else:
        # Mixed wave
        wave_name = "Mixed Objects"
    
    # Add wave number
    wave_name = f"Wave {wave_num}: {wave_name}"
    
    # Generate key procedures list with category breakdown
    key_procedures = []
    for category, count in categories.most_common():
        key_procedures.append(f"{category}: {count} object{'s' if count > 1 else ''}")
    
    # Add top priority object names
    if priority_objects:
        key_procedures.append("---")
        key_procedures.append("Key Objects:")
        for obj in priority_objects[:3]:
            key_procedures.append(f"  • {obj['name']} ({obj['category']})")
    
    return wave_name, key_procedures


def generate_html_content(graph_summary, cycles, excluded_edges, waves_data, 
                         total_objects, total_waves, total_with_missing, total_without_missing,
                         total_estimated_hours, conversion_percentage, timestamp, estimation_source, grand_totals_data=None,
                         object_references=None, missing_obj_refs=None, total_objects_with_ewis=0, total_ewis=0,
                         wave_deployment_order=None):
    """Generate complete HTML content with AI-generated benefits and purposes."""
    
    if object_references is None:
        object_references = []
    
    if missing_obj_refs is None:
        missing_obj_refs = {
            'missing_objects': set(),
            'dependents': {},
            'details': [],
            'data_source': 'none',
            'warning': None
        }
    
    if wave_deployment_order is None:
        wave_deployment_order = {}
    
    # Generate AI-powered wave benefits
    ai_benefits_html = generate_ai_wave_benefits(waves_data, graph_summary, total_objects, total_waves, cycles, excluded_edges)
    
    # Generate wave names, summaries, and AI purposes
    wave_names = {}
    wave_summaries = {}
    wave_purposes = {}
    wave_types = {}
    for wave_num, objects in waves_data.items():
        name, summary = generate_wave_name_and_summary(wave_num, objects)
        wave_names[wave_num] = name
        wave_summaries[wave_num] = summary
        wave_purposes[wave_num] = generate_ai_wave_purpose(wave_num, objects, waves_data)
        # Determine wave type from first object's partition_type
        wave_types[wave_num] = objects[0].get('partition_type', 'regular') if objects else 'regular'
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wave Migration Report - {timestamp}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
            background-color: #EEF6F7;
            color: #333;
            line-height: 1.6;
            display: flex;
            min-height: 100vh;
        }}
        
        /* Side Navigation Panel */
        .side-nav {{
            position: fixed;
            left: 0;
            top: 0;
            width: 280px;
            height: 100vh;
            background: linear-gradient(180deg, #005C8F 0%, #003D5C 100%);
            padding: 20px 0;
            overflow-y: auto;
            box-shadow: 4px 0 12px rgba(0, 0, 0, 0.15);
            z-index: 1000;
        }}
        
        .side-nav-header {{
            padding: 0 20px 20px 20px;
            border-bottom: 2px solid rgba(182, 213, 243, 0.3);
            margin-bottom: 20px;
        }}
        
        .side-nav-title {{
            color: #FCFFFE;
            font-size: 1.3em;
            font-weight: 700;
            margin-bottom: 5px;
        }}
        
        .side-nav-subtitle {{
            color: #CFECEF;
            font-size: 0.85em;
        }}
        
        .side-nav-section {{
            margin-bottom: 8px;
        }}
        
        .side-nav-link {{
            display: block;
            padding: 12px 20px;
            color: #CFECEF;
            text-decoration: none;
            font-size: 0.9em;
            transition: all 0.2s;
            border-left: 3px solid transparent;
        }}
        
        .side-nav-link:hover {{
            background-color: rgba(182, 213, 243, 0.15);
            color: #FCFFFE;
            border-left-color: #B6D5F3;
        }}
        
        .side-nav-link.active {{
            background-color: rgba(182, 213, 243, 0.25);
            color: #FCFFFE;
            border-left-color: #FCFFFE;
            font-weight: 600;
        }}
        
        .side-nav-subsection {{
            padding-left: 40px;
        }}
        
        .side-nav-subsection .side-nav-link {{
            font-size: 0.85em;
            padding: 8px 20px;
        }}
        
        /* Main Content Area */
        .main-content {{
            margin-left: 280px;
            flex: 1;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background-color: #FCFFFE;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 40px;
        }}
        
        /* Scroll behavior */
        html {{
            scroll-behavior: smooth;
            scroll-padding-top: 20px;
        }}
        
        h1 {{
            color: #005C8F;
            font-size: 2.2em;
            margin-bottom: 10px;
            border-bottom: 3px solid #B6D5F3;
            padding-bottom: 15px;
        }}
        
        h2 {{
            color: #005C8F;
            font-size: 1.6em;
            margin-top: 40px;
            margin-bottom: 20px;
            border-left: 4px solid #B6D5F3;
            padding-left: 15px;
            scroll-margin-top: 20px;
        }}
        
        h3 {{
            color: #005C8F;
            font-size: 1.2em;
            margin-top: 25px;
            margin-bottom: 15px;
        }}
        
        
        .info-tooltip:hover .tooltip-content {{
            display: block !important;
        }}
        .info-tooltip svg {{
            transition: all 0.2s;
        }}
        .info-tooltip:hover svg {{
            transform: scale(1.1);
        }}
        
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin: 16px 0;
        }}
        
        .metric-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border: 1px solid #E2E8F0;
            transition: all 0.2s;
        }}
        
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        
        .metric-card .metric-label {{
            font-size: 0.85rem;
            font-weight: 600;
            color: #64748B;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
            line-height: 1.2;
        }}
        
        .metric-card .metric-value {{
            font-size: 2rem;
            font-weight: 800;
            color: #102E46;
            margin-top: 4px;
        }}
        
        .metric-card .metric-description {{
            font-size: 0.875rem;
            color: #8A999E;
            margin-top: 0.5rem;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #CFECEF 0%, #B6D5F3 100%);
            border-radius: 8px;
            padding: 25px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .stat-label {{
            font-size: 0.9em;
            color: #005C8F;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }}
        
        .stat-value {{
            font-size: 2.2em;
            font-weight: 700;
            color: #005C8F;
        }}
        
        .stat-value.large {{
            font-size: 2.8em;
        }}
        
        .filters {{
            background-color: #EEF6F7;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
            border: 1px solid #CFECEF;
        }}
        
        .filter-group {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            align-items: flex-start;
        }}
        
        .filter-item {{
            display: flex;
            flex-direction: column;
            gap: 5px;
            min-width: 180px;
        }}
        
        .filter-item-input-wrapper {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        
        .filter-item label {{
            font-size: 0.85em;
            font-weight: 600;
            color: #005C8F;
        }}
        
        .filter-item input,
        .filter-item select {{
            padding: 8px 12px;
            border: 1px solid #B6D5F3;
            border-radius: 4px;
            font-size: 0.9em;
            background-color: #FCFFFE;
            transition: border-color 0.2s;
        }}
        
        .filter-item input:focus,
        .filter-item select:focus {{
            outline: none;
            border-color: #005C8F;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            background-color: #FCFFFE;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        thead {{
            background-color: #005C8F;
            color: #FCFFFE;
        }}
        
        th {{
            padding: 14px 12px;
            text-align: left;
            font-weight: 600;
            font-size: 0.95em;
            cursor: pointer;
            user-select: none;
            transition: background-color 0.2s;
        }}
        
        th:hover {{
            background-color: #004570;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #EEF6F7;
            font-size: 0.9em;
        }}
        
        tbody tr:hover {{
            background-color: #EEF6F7;
        }}
        
        tbody tr:last-child td {{
            border-bottom: none;
        }}
        
        .object-row {{
            cursor: pointer;
            transition: background-color 0.2s;
        }}
        
        .object-row:hover {{
            background-color: #CFECEF !important;
        }}
        
        .picked-scc-row {{
            background-color: #FFFACD !important;
            border-left: 4px solid #FFD700 !important;
        }}
        
        .picked-scc-row:hover {{
            background-color: #FFF4B0 !important;
        }}
        
        .expandable-row {{
            display: none;
            background-color: #F8FBFC;
        }}
        
        .expandable-row.show {{
            display: table-row;
        }}
        
        .expandable-content {{
            padding: 15px 20px;
            max-height: 300px;
            overflow-y: auto;
            border-left: 4px solid #005C8F;
            background-color: #FCFFFE;
            border-radius: 4px;
        }}
        
        .expandable-content h4 {{
            color: #005C8F;
            margin-bottom: 10px;
            font-size: 0.95em;
        }}
        
        .missing-dep-item {{
            padding: 8px 12px;
            margin: 5px 0;
            background-color: #FFF3CD;
            border-left: 3px solid #856404;
            border-radius: 3px;
            font-size: 0.85em;
        }}
        
        .missing-dep-item strong {{
            color: #856404;
        }}
        
        .no-info-text {{
            color: #666;
            font-style: italic;
            padding: 10px;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 14px;
            font-size: 0.8em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .badge-success {{
            background-color: #D4EDDA;
            color: #155724;
        }}
        
        .badge-warning {{
            background-color: #FFF3CD;
            color: #856404;
        }}
        
        .badge-danger {{
            background-color: #F8D7DA;
            color: #721C24;
        }}
        
        .badge-info {{
            background-color: #D1ECF1;
            color: #0C5460;
        }}
        
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 92, 143, 0.4);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            backdrop-filter: blur(3px);
        }}
        
        .modal-overlay.show {{
            display: flex;
            animation: fadeIn 0.3s ease-out;
        }}
        
        .modal-content {{
            background-color: #FCFFFE;
            border-radius: 12px;
            width: 95%;
            max-width: 1400px;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 40px rgba(0, 92, 143, 0.3);
            animation: slideUp 0.3s ease-out;
            border: 3px solid #005C8F;
        }}
        
        .modal-header {{
            padding: 20px 25px;
            background: linear-gradient(135deg, #005C8F 0%, #0074A8 100%);
            border-radius: 9px 9px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid #CFECEF;
        }}
        
        .modal-title {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .modal-wave-label {{
            font-weight: 700;
            color: #FCFFFE;
            font-size: 1.3em;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
        }}
        
        .modal-wave-badge {{
            background-color: #FDF9DC;
            color: #005C8F;
            padding: 6px 16px;
            border-radius: 18px;
            font-size: 0.9em;
            font-weight: 700;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }}
        
        .modal-nav-btn {{
            background-color: transparent;
            border: 1px solid #FCFFFE;
            color: #FCFFFE;
            font-size: 0.9em;
            cursor: pointer;
            padding: 4px 10px;
            border-radius: 4px;
            font-weight: 600;
            transition: all 0.2s;
        }}
        
        .modal-nav-btn:hover:not(:disabled) {{
            background-color: #FCFFFE;
            color: #005C8F;
        }}
        
        .modal-nav-btn:disabled {{
            opacity: 0.3;
            cursor: not-allowed;
        }}
        
        .modal-close {{
            background-color: transparent;
            border: 1px solid #FCFFFE;
            color: #FCFFFE;
            font-size: 1.1em;
            cursor: pointer;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: 600;
            transition: all 0.2s;
        }}
        
        .modal-close:hover {{
            background-color: #FCFFFE;
            color: #005C8F;
        }}
        
        .modal-body {{
            padding: 25px;
            overflow-y: auto;
            overflow-x: auto;
            flex: 1;
        }}
        
        .modal-body table {{
            width: 100%;
            min-width: 800px;
            table-layout: fixed;
        }}
        
        .modal-body table th,
        .modal-body table td {{
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .modal-body table th:nth-child(1),
        .modal-body table td:nth-child(1) {{
            width: 8%;
        }}
        
        .modal-body table th:nth-child(2),
        .modal-body table td:nth-child(2) {{
            width: 10%;
        }}
        
        .modal-body table th:nth-child(3),
        .modal-body table td:nth-child(3) {{
            width: 22%;
        }}
        
        .modal-body table th:nth-child(4),
        .modal-body table td:nth-child(4) {{
            width: 20%;
        }}
        
        .modal-body table th:nth-child(5),
        .modal-body table td:nth-child(5) {{
            width: 8%;
        }}
        
        .modal-body table th:nth-child(6),
        .modal-body table td:nth-child(6) {{
            width: 14%;
        }}
        
        .modal-body table th:nth-child(7),
        .modal-body table td:nth-child(7) {{
            width: 13%;
        }}
        
        @keyframes fadeIn {{
            from {{
                opacity: 0;
            }}
            to {{
                opacity: 1;
            }}
        }}
        
        @keyframes slideUp {{
            from {{
                transform: translateY(50px);
                opacity: 0;
            }}
            to {{
                transform: translateY(0);
                opacity: 1;
            }}
        }}
        
        .wave-dropdown {{
            background-color: #FCFFFE;
            border: 2px solid #B6D5F3;
            border-radius: 8px;
            margin-bottom: 16px;
            overflow: hidden;
            transition: all 0.3s;
            box-shadow: 0 2px 6px rgba(0, 92, 143, 0.1);
        }}
        
        .wave-dropdown:hover {{
            box-shadow: 0 4px 12px rgba(0, 92, 143, 0.15);
            border-color: #005C8F;
        }}
        
        .wave-header {{
            padding: 16px 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(135deg, #005C8F 0%, #0074A8 100%);
            transition: all 0.2s;
            position: relative;
        }}
        
        .wave-header:hover {{
            background: linear-gradient(135deg, #004570 0%, #005C8F 100%);
        }}
        
        .wave-header-title {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .wave-label {{
            font-weight: 700;
            color: #FCFFFE;
            font-size: 1.1em;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
        }}
        
        .wave-badge {{
            background-color: #FDF9DC;
            color: #005C8F;
            padding: 5px 14px;
            border-radius: 16px;
            font-size: 0.85em;
            font-weight: 700;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
        }}
        
        
        @keyframes slideDown {{
            from {{
                opacity: 0;
                max-height: 0;
            }}
            to {{
                opacity: 1;
                max-height: 5000px;
            }}
        }}
        
        .object-table {{
            width: 100%;
            margin-top: 15px;
        }}
        
        .object-table th {{
            background-color: #B6D5F3;
            color: #005C8F;
            font-size: 0.9em;
        }}
        
        .scrollable-table-container {{
            max-height: 350px;
            overflow-y: auto;
            overflow-x: hidden;
            border: 1px solid #B6D5F3;
            border-top: none;
            border-radius: 0 0 6px 6px;
            margin: 0 0 20px 0;
            position: relative;
        }}
        
        .scrollable-waves-container {{
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #B6D5F3;
            border-radius: 6px;
            padding: 10px;
            margin: 20px 0;
        }}
        
        .filter-buttons {{
            display: flex;
            gap: 8px;
            margin-top: 10px;
        }}
        
        .filter-btn {{
            padding: 8px 16px;
            border: 1px solid #B6D5F3;
            background-color: #005C8F;
            color: #FCFFFE;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.85em;
            transition: all 0.2s;
        }}
        
        .filter-btn:hover {{
            background-color: #003D5C;
        }}
        
        .filter-btn.secondary {{
            background-color: #FCFFFE;
            color: #005C8F;
        }}
        
        .filter-btn.secondary:hover {{
            background-color: #EEF6F7;
        }}
        
        .copy-icon {{
            cursor: pointer;
            display: inline-block;
            margin-left: 6px;
            padding: 2px 6px;
            background: #EEF6F7;
            border-radius: 3px;
            font-size: 0.85em;
            color: #005C8F;
            transition: all 0.2s;
            vertical-align: middle;
        }}
        
        .copy-icon:hover {{
            background: #B6D5F3;
            transform: scale(1.1);
        }}
        
        .copy-icon:active {{
            transform: scale(0.95);
        }}
        
        .copy-success {{
            display: inline-block;
            margin-left: 6px;
            padding: 2px 6px;
            background: #D4EDDA;
            color: #155724;
            border-radius: 3px;
            font-size: 0.75em;
            animation: fadeOut 2s forwards;
        }}
        
        @keyframes fadeOut {{
            0% {{ opacity: 1; }}
            70% {{ opacity: 1; }}
            100% {{ opacity: 0; }}
        }}
        
        .cycle-item {{
            background-color: #FFF3CD;
            border-left: 3px solid #FFC107;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }}
        
        .cycle-item h4 {{
            color: #856404;
            margin-bottom: 8px;
        }}
        
        .cycle-nodes {{
            font-size: 0.9em;
            color: #666;
            margin-top: 8px;
            max-height: 200px;
            overflow-y: auto;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }}
        
        .cycle-nodes ul {{
            list-style-type: none;
            padding-left: 0;
            margin: 0;
        }}
        
        .cycle-nodes li {{
            padding: 4px 0;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .cycle-nodes li:last-child {{
            border-bottom: none;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        
        .info-item {{
            background-color: #EEF6F7;
            padding: 15px;
            border-radius: 6px;
            border-left: 3px solid #B6D5F3;
        }}
        
        .info-item strong {{
            color: #005C8F;
            display: block;
            margin-bottom: 5px;
        }}
        
        /* Blocked Objects Section Styles */
        .blocked-objects-section {{
            background: #FFF8E1;
            border: 2px solid #FFAB00;
            border-radius: 8px;
            padding: 20px;
            margin: 30px 0;
            max-height: 400px;
        }}
        
        .blocked-section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            position: sticky;
            top: 0;
            background: #FFF8E1;
            z-index: 10;
            padding-bottom: 10px;
        }}
        
        .blocked-section-title {{
            color: #005C8F;
            font-size: 1.6em;
            margin: 0;
            border-left: 4px solid #B6D5F3;
            padding-left: 15px;
        }}
        
        .blocked-objects-list-container {{
            max-height: 300px;
            overflow-y: auto;
            padding-right: 10px;
        }}
        
        .blocked-objects-list-container::-webkit-scrollbar {{
            width: 8px;
        }}
        
        .blocked-objects-list-container::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 4px;
        }}
        
        .blocked-objects-list-container::-webkit-scrollbar-thumb {{
            background: #FFAB00;
            border-radius: 4px;
        }}
        
        .blocked-objects-list-container::-webkit-scrollbar-thumb:hover {{
            background: #FF9800;
        }}
        
        .blocked-filter-toggle {{
            display: flex;
            align-items: center;
            gap: 10px;
            background: white;
            padding: 10px 15px;
            border-radius: 6px;
            border: 1px solid #ddd;
        }}
        
        .blocked-filter-toggle label {{
            font-size: 0.9em;
            color: #333;
            cursor: pointer;
            margin: 0;
        }}
        
        .blocked-filter-toggle input[type="checkbox"] {{
            cursor: pointer;
            width: 18px;
            height: 18px;
        }}
        
        .blocked-object-card {{
            background: white;
            border: 1px solid #FFAB00;
            border-radius: 6px;
            margin-bottom: 10px;
            overflow: hidden;
        }}
        
        .blocked-object-header {{
            background: linear-gradient(135deg, #FFAB00 0%, #FFD54F 100%);
            color: #333;
            padding: 12px 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
        }}
        
        .blocked-object-header:hover {{
            background: linear-gradient(135deg, #FF9800 0%, #FFAB00 100%);
        }}
        
        .blocked-dependents-list {{
            padding: 15px;
            display: none;
        }}
        
        .blocked-dependents-list.active {{
            display: block;
        }}
        
        .blocked-dependent-item {{
            background: #F5F5F5;
            border-left: 3px solid #005C8F;
            padding: 10px 12px;
            margin-bottom: 8px;
            border-radius: 4px;
        }}
        
        .blocked-dependent-name {{
            font-weight: 600;
            color: #005C8F;
            margin-bottom: 4px;
        }}
        
        .blocked-dependent-wave {{
            display: inline-block;
            background: #005C8F;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            margin-right: 8px;
        }}
        
        .blocked-no-objects {{
            background: #E8F5E9;
            border: 2px solid #4CAF50;
            border-radius: 6px;
            padding: 20px;
            text-align: center;
            color: #2E7D32;
            font-size: 1.1em;
        }}
    </style>
</head>
<body>
    <!-- Side Navigation Panel -->
    <nav class="side-nav" id="sideNav">
        <div class="side-nav-header">
            <div class="side-nav-title">Report Navigation</div>
            <div class="side-nav-subtitle">Wave Migration Analysis</div>
        </div>
        
        <div class="side-nav-section">
            <a href="#overview" class="side-nav-link">Overview</a>
        </div>
        
        <div class="side-nav-section">
            <a href="#wave-recommendations" class="side-nav-link">Migration Waves</a>
        </div>
        
        <div class="side-nav-section">
            <div class="side-nav-subsection" id="waveLinksContainer">
                <!-- Wave links will be dynamically inserted here -->
            </div>
        </div>
        
        <div class="side-nav-section">
            <a href="#hour-estimation" class="side-nav-link">Hour Estimation Methodology</a>
        </div>
    </nav>
    
    <!-- Main Content Area -->
    <div class="main-content">
        <div class="container">
            <div style="margin-bottom: 32px;">
                <h1 id="overview" style="font-size: 1.875rem; font-weight: 800; color: #102E46; margin-bottom: 12px;">Wave Migration Report</h1>
                <p style="color: #64748B; font-size: 1.1rem;">Dependency-based migration schedule with objects grouped into sequential waves for valid deployment order.</p>
            </div>
            
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-label">Total Objects to Migrate</div>
                    <div class="metric-value">{total_objects}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Total Waves</div>
                    <div class="metric-value">{total_waves}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Objects With Missing Dependencies</div>
                    <div class="metric-value">{total_with_missing}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Cyclic Dependencies</div>
                    <div class="metric-value">{graph_summary.get('cyclic_dependencies', 0)}</div>
                </div>
            </div>
            
'''

    # Circular Dependencies warning — above Dependency Information
    cycle_count = len(cycles) if cycles else 0
    if cycle_count > 0:
        html += f'''
            <details style="margin: 16px 0; background: #FFF8E1; border: 1px solid #FFD54F; border-radius: 6px; padding: 4px 12px;">
                <summary style="cursor: pointer; font-weight: 600; color: #856404; font-size: 0.95em; padding: 8px 0;">&#9888; {cycle_count} Circular {"Dependency" if cycle_count == 1 else "Dependencies"} Detected</summary>
                <div style="margin-top: 8px; padding-bottom: 8px;">
'''
        for cycle in cycles:
            nodes_list = '<ul style="margin-top: 4px; margin-bottom: 4px;">'
            for node in cycle['nodes']:
                nodes_list += f'<li>{node}</li>'
            nodes_list += '</ul>'
            html += f'''
                    <div class="cycle-item">
                        <h4>Cycle {cycle['cycle_num']}: {cycle['node_count']} objects</h4>
                        <div class="cycle-nodes">{nodes_list}</div>
                    </div>
'''
        html += '''
                </div>
            </details>
'''

    html += f'''
            <details style="margin: 16px 0;">
                <summary style="cursor: pointer; font-weight: 600; color: #005C8F; font-size: 0.95em;">Dependency Information</summary>
                <div style="margin-top: 10px;">
                    <table>
                        <thead>
                            <tr>
                                <th>Metric</th>
                                <th>Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td>Max Dependencies</td><td>{graph_summary.get('max_dependencies', 0)}</td></tr>
                            <tr><td>Max Dependents</td><td>{graph_summary.get('max_dependents', 0)}</td></tr>
                            <tr><td>Cyclic Dependencies</td><td>{graph_summary.get('cyclic_dependencies', 0)}</td></tr>
                            <tr><td>Total Dependencies</td><td>{graph_summary.get('total_edges', 0)}</td></tr>
                            <tr><td>Avg Dependencies / Object</td><td>{graph_summary.get('avg_dependencies', '0.0')}</td></tr>
                        </tbody>
                    </table>
                </div>
            </details>
'''

    # Add Top Undefined Referenced Objects (Temp Tables) as collapsed section
    top_undefined = excluded_edges.get('top_undefined_referenced', [])
    if top_undefined:
        html += '''
            <details style="margin: 8px 0;">
                <summary style="cursor: pointer; font-weight: 600; color: #005C8F; font-size: 0.95em;">Top Undefined Referenced Objects (Temp Tables)</summary>
                <div style="margin-top: 10px;">
                    <p style="margin-bottom: 12px; color: #666; font-size: 0.9em;">Frequently referenced objects not defined in the migration scope, typically temporary tables or dynamically created objects.</p>
                    <table>
                        <thead>
                            <tr>
                                <th>Object Name</th>
                                <th>Reference Count</th>
                            </tr>
                        </thead>
                        <tbody>
'''
        for obj in top_undefined:
            html += f'''
                            <tr>
                                <td><code>{obj['object']}</code></td>
                                <td>{obj['count']}</td>
                            </tr>
'''
        html += '''
                        </tbody>
                    </table>
                </div>
            </details>
'''
    
    # Add collapsed info sections and wave details
    html += f'''
        <details style="margin-bottom: 20px;">
            <summary style="cursor: pointer; font-weight: 600; color: #005C8F; font-size: 1em; padding: 8px 0;">Why Break Down Migration into Waves?</summary>
            <div style="background: linear-gradient(135deg, #F5FAFC 0%, #EAF3F7 100%); border-left: 4px solid #005C8F; padding: 20px; margin-top: 10px; border-radius: 6px;">
                <p style="margin-bottom: 12px;">Wave-based migration provides a structured, dependency-aware approach to moving your data and processes to Snowflake. Here are the key benefits for this project:</p>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-top: 15px;">
                    {ai_benefits_html}
                </div>
                
                <p style="margin-top: 15px; margin-bottom: 0; font-weight: 600; color: #005C8F; font-size: 0.95em;">
                    Best Practice: Deploy waves sequentially in order. Each wave contains objects that depend only on objects in earlier waves.
                </p>
            </div>
        </details>
        
        <h2 id="wave-recommendations" style="font-size: 1.5rem; font-weight: 700; color: #102E46; margin-bottom: 20px; margin-top: 24px;">Migration Waves</h2>
        
        <div class="filters" style="padding: 12px 16px;">
            <div style="display: flex; align-items: flex-end; gap: 12px; flex-wrap: nowrap;">
                <div style="display: flex; flex-direction: column; min-width: 120px;">
                    <label for="searchWaveDetails" style="font-size: 0.8em; font-weight: 600; color: #005C8F; margin-bottom: 4px;">Wave Number:</label>
                    <input type="text" id="searchWaveDetails" placeholder="e.g., 1 or 2" style="padding: 6px 10px; font-size: 0.85em;">
                </div>
                <div style="display: flex; flex-direction: column; min-width: 180px;">
                    <label for="searchObject" style="font-size: 0.8em; font-weight: 600; color: #005C8F; margin-bottom: 4px;">Object Name:</label>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <input type="text" id="searchObject" placeholder="Search by name..." style="padding: 6px 10px; font-size: 0.85em; flex: 1;">
                        <div style="display: flex; align-items: center; gap: 4px; white-space: nowrap;">
                            <input type="checkbox" id="exactMatchToggle" style="cursor: pointer; width: 14px; height: 14px;">
                            <label for="exactMatchToggle" style="font-size: 0.7em; color: #666; cursor: pointer; font-weight: normal; margin: 0;">
                                Exact
                            </label>
                        </div>
                    </div>
                </div>
                <div style="display: flex; flex-direction: column; min-width: 130px;">
                    <label for="filterCategory" style="font-size: 0.8em; font-weight: 600; color: #005C8F; margin-bottom: 4px;">Category:</label>
                    <select id="filterCategory" style="padding: 6px 10px; font-size: 0.85em;">
                        <option value="">All</option>
                        <option value="TABLE">TABLE</option>
                        <option value="VIEW">VIEW</option>
                        <option value="PROCEDURE">PROCEDURE</option>
                        <option value="FUNCTION">FUNCTION</option>
                        <option value="ETL">ETL</option>
                    </select>
                </div>
                <div style="display: flex; flex-direction: column; min-width: 150px;">
                    <label for="filterMissing" style="font-size: 0.8em; font-weight: 600; color: #005C8F; margin-bottom: 4px;">Missing Dependencies:</label>
                    <select id="filterMissing" style="padding: 6px 10px; font-size: 0.85em;">
                        <option value="">All</option>
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                    </select>
                </div>
                <div style="display: flex; flex-direction: column; min-width: 110px;">
                    <label for="filterStatus" style="font-size: 0.8em; font-weight: 600; color: #005C8F; margin-bottom: 4px;">Status:</label>
                    <select id="filterStatus" style="padding: 6px 10px; font-size: 0.85em;">
                        <option value="">All</option>
                        <option value="Success">Success</option>
                        <option value="Failed">Failed</option>
                    </select>
                </div>
                <div style="display: flex; gap: 8px; margin-left: auto;">
                    <button class="filter-btn" onclick="applyWaveFilters()" style="padding: 8px 16px; font-size: 0.85em; white-space: nowrap;">Apply</button>
                    <button class="filter-btn secondary" onclick="clearWaveFilters()" style="padding: 8px 16px; font-size: 0.85em; white-space: nowrap;">Clear</button>
                </div>
            </div>
        </div>
        
        <div class="pipeline-search-section" style="margin-top: 20px;">
            <div class="filters">
                <div id="pipelineSearchLoading" style="display: none; margin-bottom: 10px; padding: 10px 12px; background: #E8F4F8; border-radius: 4px; border-left: 3px solid #005C8F; font-size: 0.85em; color: #005C8F;">
                    <strong>⏳ Searching dependencies...</strong> Please wait while we analyze the dependency tree.
                </div>
                <div id="pipelineSearchResults" style="display: none; margin-bottom: 10px; padding: 10px 12px; background: #D4EDDA; border-radius: 4px; border-left: 3px solid #28a745; font-size: 0.85em;">
                    <div style="margin-bottom: 8px; font-weight: 600; color: #155724;">Active Search</div>
                    <div style="margin-bottom: 10px; padding: 8px; background: white; border-radius: 4px;">
                        <div style="margin-bottom: 4px; color: #666; font-size: 0.75em; font-weight: 600; text-transform: uppercase;">Searched Objects:</div>
                        <div id="pipelineObjectsList" style="display: flex; flex-wrap: wrap; gap: 6px;"></div>
                    </div>
                    <div id="pipelineStats" style="font-size: 0.9em; color: #155724; padding: 8px; background: rgba(255,255,255,0.5); border-radius: 4px;"></div>
                </div>
                <div style="display: flex; align-items: flex-end; gap: 12px; flex-wrap: nowrap;">
                    <div style="display: flex; flex-direction: column; flex: 1; min-width: 200px;">
                        <label for="searchPipeline" style="font-size: 0.8em; font-weight: 600; color: #005C8F; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
                            Search for object dependencies
                            <span class="info-tooltip" style="position: relative; display: inline-flex; align-items: center; cursor: help;">
                                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style="display: block;">
                                    <circle cx="8" cy="8" r="7" stroke="#005C8F" stroke-width="1.5" fill="none"/>
                                    <text x="8" y="11.5" text-anchor="middle" fill="#005C8F" font-size="11" font-weight="600" font-family="Arial">i</text>
                                </svg>
                                <span class="tooltip-content" style="position: absolute; left: 50%; transform: translateX(-50%); bottom: calc(100% + 8px); background: #102E46; color: white; padding: 12px; border-radius: 6px; font-size: 0.8em; font-weight: normal; width: 320px; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.2); display: none; pointer-events: none;">
                                    <div style="margin-bottom: 8px; font-weight: 600;">Traces the complete dependency chain for any object:</div>
                                    <ul style="margin: 0 0 8px 16px; padding: 0; line-height: 1.6;">
                                        <li><strong>Dependencies:</strong> Objects deployed first (earlier waves)</li>
                                        <li><strong>Dependents:</strong> Objects deployed after (later waves)</li>
                                    </ul>
                                    <div style="font-size: 0.85em; opacity: 0.9; font-style: italic;">
                                        💡 Only CREATE objects are tracked in deployment waves.
                                    </div>
                                    <div style="position: absolute; left: 50%; bottom: -6px; transform: translateX(-50%); width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-top: 6px solid #102E46;"></div>
                                </span>
                            </span>
                        </label>
                        <input type="text" id="searchPipeline" placeholder="Enter object name..." style="font-size: 0.85em; padding: 6px 10px;">
                    </div>
                    <div style="display: flex; flex-direction: column; min-width: 220px;">
                        <label for="pipelineView" style="font-size: 0.8em; font-weight: 600; color: #005C8F; margin-bottom: 4px;">View:</label>
                        <select id="pipelineView" style="font-size: 0.85em; padding: 6px 10px;">
                            <option value="all">All (Direct + Transitive)</option>
                            <option value="dependencies">All Direct Dependencies</option>
                            <option value="dependents">All Direct Dependents</option>
                        </select>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="filter-btn" onclick="searchPipeline()" style="background-color: #005C8F; font-size: 0.85em; padding: 8px 16px; white-space: nowrap;">
                            Search
                        </button>
                        <button class="filter-btn" onclick="addToPipeline()" style="background-color: #28a745; display: none; font-size: 0.85em; padding: 8px 16px; white-space: nowrap;" id="addToPipelineBtn">
                            Add to Search
                        </button>
                        <button class="filter-btn secondary" onclick="clearPipelineSearch()" style="display: none; font-size: 0.85em; padding: 8px 16px; white-space: nowrap;" id="clearPipelineBtn">
                            Clear
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="scrollable-waves-container" id="waveDetailsContainer">
'''
    
    # Add Missing Dependencies Wave (Wave 0) - Always first
    missing_objects_count = len(missing_obj_refs.get('missing_objects', []))
    has_missing_deps = missing_objects_count > 0
    missing_deps_warning = missing_obj_refs.get('warning')
    
    if missing_deps_warning:
        # Data source unavailable - show warning
        status_text = "⚠️ Data Unavailable"
        composition_text = "Check Required"
        description_text = "Could not load missing dependencies data. This does not mean there are no missing dependencies - please verify the data source."
    elif has_missing_deps:
        status_text = f"{missing_objects_count} Missing Dependencies"
        composition_text = "Review Required"
        description_text = "Objects with unresolved dependencies that may require attention before deployment."
    else:
        status_text = "No Missing Dependencies"
        composition_text = "✓ All Clear"
        description_text = "Great news! All dependencies are resolved. No missing references detected."
    
    html += f'''
        <div class="wave-dropdown" data-wave="0" id="wave-0" style="margin-bottom: 12px;">
            <div class="wave-header" onclick="openMissingDepsModal()" style="cursor: pointer; display: flex; justify-content: space-between; align-items: center; padding: 24px 28px; border-radius: 8px; background: linear-gradient(135deg, #FFF9E6 0%, #FFE082 100%); box-shadow: 0 2px 8px rgba(255, 193, 7, 0.15); transition: all 0.2s ease; border: 1px solid #FFD54F;">
                <div style="display: flex; flex-direction: column; gap: 8px; flex: 1;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 1.15em; font-weight: 600; color: #856404; letter-spacing: 0.3px;">Missing Dependencies Overview</span>
                        <span style="font-size: 0.8em; color: #856404; background-color: rgba(255, 193, 7, 0.2); padding: 4px 12px; border-radius: 12px; font-weight: 500;">{status_text}</span>
                    </div>
                    <div style="font-size: 0.88em; color: #856404; font-weight: 400; line-height: 1.5; max-width: 90%;">
                        {description_text}
                    </div>
                </div>
                <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px; min-width: 180px; padding-left: 24px;">
                    <div style="font-size: 0.72em; color: #856404; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; opacity: 0.7;">Status</div>
                    <div style="font-size: 0.85em; color: #856404; text-align: right; line-height: 1.4;">
                        {composition_text}
                    </div>
                </div>
            </div>
        </div>
'''
    
    # Add wave details dropdowns
    for wave_num in sorted(waves_data.keys()):
        objects = waves_data[wave_num]
        wave_display_name = wave_names.get(wave_num, f"Wave {wave_num}")
        wave_summary_list = wave_summaries.get(wave_num, [])
        wave_purpose = wave_purposes.get(wave_num, "")
        wave_type = wave_types.get(wave_num, "regular")
        
        # Calculate wave hours and EWI stats
        wave_hours = sum(obj['estimated_hours'] for obj in objects)
        objects_with_ewis = sum(1 for obj in objects if obj.get('ewi_count', 0) > 0)
        total_ewis_in_wave = sum(obj.get('ewi_count', 0) for obj in objects)
        
        # Format wave type for display
        wave_type_display_map = {
            'simple_object': 'Simple Objects',
            'user_prioritized': 'User Prioritized',
            'regular': 'Regular'
        }
        wave_type_display = wave_type_display_map.get(wave_type, wave_type.title())
        
        # Build compact composition for header (right side) with EWI stats
        composition_lines = []
        if wave_summary_list:
            # Take first 3 items, make them very compact
            for item in wave_summary_list[:3]:
                if item != "---":
                    # Extract just the key part (e.g., "15 Tables" from "• 15 Tables")
                    clean_item = item.replace('•', '').strip()
                    composition_lines.append(clean_item)
        
        # Add EWI stats to composition
        if total_ewis_in_wave > 0:
            composition_lines.append(f"{objects_with_ewis} objs w/ EWIs")
            composition_lines.append(f"{total_ewis_in_wave} total EWIs")
        
        composition_compact = '<br>'.join(composition_lines)
        
        # Format summary for display (below the header) - remove this as it's now in header
        summary_html = '<div style="font-size: 0.85em; color: #333; margin-top: 12px; display: none;">'
        summary_html += '</div>'
        
        html += f'''
            <div class="wave-dropdown" data-wave="{wave_num}" id="wave-{wave_num}" style="margin-bottom: 12px;">
                <div class="wave-header" onclick="openWaveModal({wave_num})" style="cursor: pointer; display: flex; justify-content: space-between; align-items: center; padding: 24px 28px; border-radius: 8px; background: linear-gradient(135deg, #005C8F 0%, #0074A8 100%); box-shadow: 0 2px 8px rgba(0, 92, 143, 0.15); transition: all 0.2s ease;">
                    <div style="display: flex; flex-direction: column; gap: 8px; flex: 1;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-size: 1.15em; font-weight: 600; color: white; letter-spacing: 0.3px;">{wave_display_name}</span>
                            <span style="font-size: 0.75em; color: #29B5E8; background-color: rgba(41, 181, 232, 0.2); padding: 4px 10px; border-radius: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border: 1px solid rgba(41, 181, 232, 0.4);">{wave_type_display}</span>
                            <span id="wave-badge-{wave_num}" style="font-size: 0.8em; color: rgba(255, 255, 255, 0.85); background-color: rgba(255, 255, 255, 0.15); padding: 4px 12px; border-radius: 12px; font-weight: 500;">{len(objects)} objects · {wave_hours:.1f}h</span>
                        </div>
                        {'<div style="font-size: 0.88em; color: rgba(255, 255, 255, 0.9); font-weight: 400; line-height: 1.5; max-width: 90%;">' + wave_purpose + '</div>' if wave_purpose else ''}
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px; min-width: 200px; padding-left: 24px;">
                        <div style="font-size: 0.72em; color: rgba(255, 255, 255, 0.7); text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Composition</div>
                        <div style="font-size: 0.85em; color: white; text-align: right; line-height: 1.5;">
                            {composition_compact}
                        </div>
                    </div>
                </div>
            </div>
'''
    
    html += '''
        </div>
        
        <!-- Modal container -->
        <div id="waveModal" class="modal-overlay" onclick="closeWaveModal(event)">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <button class="modal-nav-btn" id="prevWaveBtn" onclick="navigateWave(-1)">◀</button>
                    <div class="modal-title">
                        <span class="modal-wave-label" id="modalWaveLabel"></span>
                        <span class="modal-wave-badge" id="modalWaveBadge"></span>
                    </div>
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <button class="modal-nav-btn" id="nextWaveBtn" onclick="navigateWave(1)">▶</button>
                        <button class="modal-close" onclick="closeWaveModal(event)">✕</button>
                    </div>
                </div>
                <div class="modal-body" id="modalWaveBody">
                </div>
            </div>
        </div>
'''
    
    # Store wave data in JavaScript for modal display
    html += '''
        <script>
        const waveNames = {
'''
    
    # Add wave names to JavaScript
    for wave_num in sorted(waves_data.keys()):
        wave_name = wave_names.get(wave_num, f"Wave {wave_num}").replace("'", "\\'")
        html += f"            {wave_num}: '{wave_name}',\n"
    
    html += '''
        };
        
        const wavesData = {
'''
    
    for wave_num in sorted(waves_data.keys()):
        objects = waves_data[wave_num]
        
        # Use pre-computed deployment order from JSON if available
        if wave_deployment_order and str(wave_num) in wave_deployment_order:
            deployment_order_names = wave_deployment_order[str(wave_num)].get('deployment_order', [])
            # Create name-to-object mapping
            name_to_obj = {obj['name']: obj for obj in objects}
            # Sort objects based on deployment order
            sorted_objects = [name_to_obj[name] for name in deployment_order_names if name in name_to_obj]
            # Add any remaining objects not in deployment order
            remaining = [obj for obj in objects if obj['name'] not in deployment_order_names]
            remaining.sort(key=lambda x: x['name'])
            sorted_objects.extend(remaining)
        else:
            # Fallback to alphabetical if no deployment order available
            sorted_objects = sorted(objects, key=lambda x: x['name'])
        
        html += f'''
            {wave_num}: [
'''
        for idx, obj in enumerate(sorted_objects, 1):
            missing_badge = '<span class="badge badge-warning">Yes</span>' if obj['has_missing_dependencies'] else '<span class="badge badge-success">No</span>'
            status_badge_class = 'badge-success' if obj['conversion_status'] == 'Success' else 'badge-danger'
            status_badge = f'<span class="badge {status_badge_class}">{obj["conversion_status"]}</span>'
            
            # Prepare missing dependencies data (escape and format properly)
            missing_deps_list = obj.get('missing_dependencies', [])
            missing_deps_json = json.dumps(missing_deps_list)
            
            # Escape backslashes, quotes, and newlines for JavaScript
            escaped_name = obj['name'].replace('\\', '\\\\').replace('"', '&quot;').replace('\n', '\\n').replace('\r', '\\r')
            escaped_file_name = obj['file_name'].replace('\\', '\\\\').replace('"', '&quot;').replace('\n', '\\n').replace('\r', '\\r')
            escaped_technology = obj.get('technology', '').replace('\\', '\\\\').replace('"', '&quot;').replace('\n', '\\n').replace('\r', '\\r')
            escaped_subtype = obj.get('subtype', '').replace('\\', '\\\\').replace('"', '&quot;').replace('\n', '\\n').replace('\r', '\\r')
            
            ewi_count = obj.get('ewi_count', 0)
            fdm_count = obj.get('fdm_count', 0)
            prf_count = obj.get('prf_count', 0)
            highest_ewi_severity = obj.get('highest_ewi_severity', '')
            
            html += f'''
                {{
                    deployment_position: {idx},
                    category: "{obj['category']}",
                    name: "{escaped_name}",
                    file_name: "{escaped_file_name}",
                    has_missing: {str(obj['has_missing_dependencies']).lower()},
                    missing_badge: '{missing_badge}',
                    conversion_status: "{obj['conversion_status']}",
                    status_badge: '{status_badge}',
                    estimated_hours: {obj['estimated_hours']:.1f},
                    is_picked_scc: {str(obj.get('is_picked_scc', False)).lower()},
                    missing_dependencies: {missing_deps_json},
                    dependency_count: {obj.get('dependency_count', 0)},
                    dependent_count: {obj.get('dependent_count', 0)},
                    technology: "{escaped_technology}",
                    subtype: "{escaped_subtype}",
                    ewi_count: {ewi_count},
                    fdm_count: {fdm_count},
                    prf_count: {prf_count},
                    highest_ewi_severity: "{highest_ewi_severity}"
                }},
'''
        html += '''
            ],
'''
    
    html += '''
        };
        
        // Object references for dependency search
        const objectReferences = [
'''
    
    for ref in object_references:
        caller = ref['caller'].replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
        referenced = ref['referenced'].replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
        html += f'''            {{caller: "{caller}", referenced: "{referenced}"}},
'''
    
    html += '''
        ];
        </script>
'''

    
    # Add Hour Estimation Methodology section (outside script tags)
    html += f'''
        
        <h2 id="hour-estimation">Hour Estimation Methodology</h2>
        <div class="analysis-info">
            <p><strong>Estimation Source:</strong> {estimation_source}</p>
            
            <h3 style="margin-top: 20px;">Estimation Logic:</h3>
            <p style="margin-top: 10px;">The tool prioritizes estimation data as follows:</p>
            <ol style="margin-left: 20px; margin-top: 10px;">
                <li><strong>Estimation Reports (if provided):</strong> Uses per-object manual effort data from TopLevelObjectsEstimation.NA.csv
                    <ul style="margin-left: 20px; margin-top: 5px;">
                        <li>Files detected: TopLevelObjectsEstimation.*.csv (NA or timestamp pattern)</li>
                        <li>Effort values are in minutes and converted to hours for display</li>
                        <li>Each object has specific manual effort based on complexity and issues</li>
                    </ul>
                </li>
                <li style="margin-top: 10px;"><strong>Baseline (fallback):</strong> Uses severity-based estimates from issues-estimation.json when reports unavailable
                    <ul style="margin-left: 20px; margin-top: 5px;">
                        <li><strong>Critical:</strong> 120 minutes (2.0 hours)</li>
                        <li><strong>High:</strong> 45 minutes (0.75 hours)</li>
                        <li><strong>Medium:</strong> 16.5 minutes (0.275 hours) - baseline for non-success objects</li>
                        <li><strong>Low:</strong> 3.5 minutes (0.058 hours)</li>
                        <li><strong>Success/None:</strong> 0 minutes (0 hours)</li>
                    </ul>
                </li>
            </ol>
            <p style="margin-top: 15px;"><em>Note: Objects with "Success" conversion status are always assigned 0 hours regardless of estimation method.</em></p>
        </div>

    </div>
'''
    
    # Add second script block with functions
    # First, generate the JSON data for missing dependencies
    missing_objects_json = json.dumps(list(missing_obj_refs.get('missing_objects', [])))
    dependents_json = json.dumps(missing_obj_refs.get('dependents', {}))
    missing_deps_warning_json = json.dumps(missing_obj_refs.get('warning'))
    
    html += '''
    <script>
        let currentWaveNum = null;
        let visibleWaveNums = [];
        let blockedObjectsFilterActive = false;
        let blockedObjectsSet = new Set();
        
        // Initialize blocked objects set on page load
        function initializeBlockedObjectsSet() {
            blockedObjectsSet.clear();
            document.querySelectorAll('.blocked-dependent-item').forEach(item => {
                const objName = item.dataset.object;
                if (objName) {
                    blockedObjectsSet.add(objName);
                }
            });
        }
        
        // Toggle blocked object dependents list
        function toggleBlockedDependents(header) {
            const list = header.nextElementSibling;
            list.classList.toggle('active');
            const arrow = header.querySelector('span:last-child');
            if (list.classList.contains('active')) {
                arrow.textContent = arrow.textContent.replace('▼', '▲');
            } else {
                arrow.textContent = arrow.textContent.replace('▲', '▼');
            }
        }
        
        // Toggle filter for blocked objects in waves
        function toggleBlockedObjectsFilter() {
            const checkbox = document.getElementById('filterBlockedObjects');
            blockedObjectsFilterActive = checkbox.checked;
            
            // Build set of blocked objects (dependents of missing dependencies)
            blockedObjectsSet.clear();
            if (blockedObjectsFilterActive) {
                document.querySelectorAll('.blocked-dependent-item').forEach(item => {
                    const objName = item.dataset.object;
                    if (objName) {
                        blockedObjectsSet.add(objName);
                    }
                });
            }
            
            // Reapply wave filters to include blocked objects filter
            applyWaveFilters();
        }
        
        function toggleExpandRow(rowId) {
            const expandRow = document.getElementById(rowId);
            if (expandRow) {
                expandRow.classList.toggle('show');
            }
        }
        
        function copyToClipboard(text, iconElement) {
            // Use modern clipboard API
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(() => {
                    showCopySuccess(iconElement);
                }).catch(err => {
                    // Fallback for older browsers
                    fallbackCopyToClipboard(text, iconElement);
                });
            } else {
                fallbackCopyToClipboard(text, iconElement);
            }
        }
        
        function fallbackCopyToClipboard(text, iconElement) {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                showCopySuccess(iconElement);
            } catch (err) {
                // Silent fail - clipboard fallback failed
            }
            document.body.removeChild(textArea);
        }
        
        function showCopySuccess(iconElement) {
            // Create success message
            const successMsg = document.createElement('span');
            successMsg.className = 'copy-success';
            successMsg.textContent = '✓ Copied';
            
            // Insert after the icon
            iconElement.parentNode.insertBefore(successMsg, iconElement.nextSibling);
            
            // Remove after animation
            setTimeout(() => {
                if (successMsg.parentNode) {
                    successMsg.parentNode.removeChild(successMsg);
                }
            }, 2000);
        }
        
        function generateMissingDepsContent(missingDeps, dependencyCount, dependentCount, objectName, technology, subtype, category) {
            let content = '';
            
            // Check if this object is a dependent of a missing object (blocked object)
            const isBlockedObject = blockedObjectsSet.has(objectName);
            
            // Get dependencies and dependents lists for counting
            const allDependencies = objectReferences.filter(ref => ref.caller === objectName).map(ref => ref.referenced);
            const allDependents = objectReferences.filter(ref => ref.referenced === objectName).map(ref => ref.caller);
            
            // Filter by pipeline if active
            let dependencies = allDependencies;
            let dependents = allDependents;
            let isPipelineActive = window.pipelineFilter && window.pipelineFilter.size > 0;
            
            if (isPipelineActive) {
                dependencies = allDependencies.filter(dep => window.pipelineFilter.has(dep));
                dependents = allDependents.filter(dep => window.pipelineFilter.has(dep));
            }
            
            // Add dependency counts section
            content += '<div style="background: #EEF6F7; padding: 12px; border-radius: 4px; margin-bottom: 12px;">';
            content += '<h4 style="margin-top: 0; margin-bottom: 8px; color: #005C8F;">Dependency Statistics</h4>';
            
            // Add Technology if available
            if (technology && technology !== '') {
                content += `<div style="margin-bottom: 8px;"><strong>Technology:</strong> ${technology}</div>`;
            }
            
            // Add Subtype if available and category is ETL
            if (category === 'ETL' && subtype && subtype !== '') {
                content += `<div style="margin-bottom: 8px;"><strong>Subtype:</strong> ${subtype}</div>`;
            }
            
            content += `<div style="margin-bottom: 8px;"><strong>Total Dependencies In Workload:</strong> ${dependencyCount}</div>`;
            content += `<div style="margin-bottom: 8px;"><strong>Total Dependents In Workload:</strong> ${dependentCount}</div>`;
            content += `<div style="font-size: 0.85em; color: #666; font-style: italic; margin-top: 4px; padding: 6px; background: #E8F4F8; border-radius: 3px;">
                ℹ️ Only CREATE objects are tracked. Temp tables, external objects, and system objects are excluded from deployment waves.
            </div>`;
            
            // Add Total Missing Dependencies count
            const missingCount = missingDeps ? missingDeps.length : 0;
            content += `<div style="margin-top: 8px; margin-bottom: 8px;"><strong>Total Missing Dependencies:</strong> ${missingCount}</div>`;
            
            content += '</div>';
            
            // Add missing dependencies section
            if (!missingDeps || missingDeps.length === 0) {
                content += '<div style="background: #D4EDDA; padding: 12px; border-radius: 4px; color: #155724;">';
                content += '<h4 style="margin-top: 0; margin-bottom: 8px; color: #155724;">Missing Dependencies</h4>';
                content += '<div>✓ No missing dependencies - all referenced objects are defined</div>';
                content += '</div>';
            } else {
                content += '<div style="background: #FFF3CD; padding: 12px; border-radius: 4px; margin-bottom: 12px;">';
                content += '<h4 style="margin-top: 0; margin-bottom: 8px; color: #856404;">Missing Dependencies</h4>';
                content += '<div style="margin-bottom: 8px; font-size: 0.9em; color: #666;">The following objects are referenced but not found in TopLevelCodeUnits (may be external, temp, or system objects):</div>';
                missingDeps.forEach(dep => {
                    const referenced = dep.referenced || 'N/A';
                    const relationType = dep.relation_type || 'N/A';
                    const line = dep.line || 'N/A';
                    const file = dep.file || 'N/A';
                    
                    content += `
                        <div class="missing-dep-item" style="margin-bottom: 8px; padding: 8px; background: white; border-radius: 3px;">
                            <strong>Referenced Object:</strong> ${referenced}<br>
                            <strong>Relation Type:</strong> ${relationType}<br>
                            <strong>Line:</strong> ${line}<br>
                            <strong>Source File:</strong> ${file}
                        </div>
                    `;
                });
                content += '</div>';
            }
            return content;
        }
        
        function updateVisibleWaves() {
            const allDropdowns = document.querySelectorAll('.wave-dropdown');
            visibleWaveNums = [];
            allDropdowns.forEach(dropdown => {
                if (dropdown.style.display !== 'none') {
                    visibleWaveNums.push(parseInt(dropdown.dataset.wave));
                }
            });
            visibleWaveNums.sort((a, b) => a - b);
        }
        
        function updateNavigationButtons() {
            const prevBtn = document.getElementById('prevWaveBtn');
            const nextBtn = document.getElementById('nextWaveBtn');
            
            if (!prevBtn || !nextBtn || currentWaveNum === null) return;
            
            const currentIndex = visibleWaveNums.indexOf(currentWaveNum);
            
            prevBtn.disabled = currentIndex <= 0;
            nextBtn.disabled = currentIndex >= visibleWaveNums.length - 1;
        }
        
        function openWaveModal(waveNum) {
            currentWaveNum = waveNum;
            updateVisibleWaves();
            
            const modal = document.getElementById('waveModal');
            const modalLabel = document.getElementById('modalWaveLabel');
            const modalBadge = document.getElementById('modalWaveBadge');
            const modalBody = document.getElementById('modalWaveBody');
            
            const waveObjects = wavesData[waveNum];
            
            // Get current filter values
            const searchObject = document.getElementById('searchObject').value.toLowerCase();
            const exactMatch = document.getElementById('exactMatchToggle').checked;
            const category = document.getElementById('filterCategory').value;
            const missing = document.getElementById('filterMissing').value;
            const status = document.getElementById('filterStatus').value;
            
            // Filter objects based on current filters
            const filteredObjects = waveObjects.filter(obj => {
                const matchesSearch = searchObject === '' || (exactMatch ? obj.name.toLowerCase() === searchObject : obj.name.toLowerCase().includes(searchObject));
                const matchesCategory = !category || obj.category === category;
                const matchesMissing = !missing || (missing === 'yes' && obj.has_missing) || (missing === 'no' && !obj.has_missing);
                const matchesStatus = !status || obj.conversion_status === status;
                const matchesPipeline = !window.pipelineFilter || window.pipelineFilter.has(obj.name);
                
                return matchesSearch && matchesCategory && matchesMissing && matchesStatus && matchesPipeline;
            });
            
            modalLabel.textContent = waveNames[waveNum] || `Wave ${waveNum}`;
            
            // Show filtered count vs total
            if (filteredObjects.length === waveObjects.length) {
                modalBadge.textContent = `${waveObjects.length} objects`;
            } else {
                modalBadge.textContent = `${filteredObjects.length} of ${waveObjects.length} objects`;
            }
            
            // Build table HTML
            let tableHTML = `
                <table class="object-table">
                    <thead>
                        <tr>
                            <th>Deployment Order</th>
                            <th>Object Type</th>
                            <th>Object Name</th>
                            <th>File Name</th>
                            <th>EWIs</th>
                            <th>Missing Dependencies</th>
                            <th>Conversion Status</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            if (filteredObjects.length === 0) {
                tableHTML += `
                    <tr>
                        <td colspan="7" style="text-align: center; padding: 30px; color: #666;">No objects match the current filters</td>
                    </tr>
                `;
            } else {
                filteredObjects.forEach((obj, index) => {
                    const rowId = `obj-row-${currentWaveNum}-${index}`;
                    const expandRowId = `expand-row-${currentWaveNum}-${index}`;
                    
                    // Generate pipeline label if pipeline search is active
                    let pipelineLabel = '';
                    if (window.pipelineRelations && window.pipelineRelations.has(obj.name)) {
                        const relationType = window.pipelineRelations.get(obj.name);
                        let labelText = '';
                        let labelColor = '';
                        
                        if (relationType === 'searched') {
                            labelText = 'SEARCHED';
                            labelColor = '#005C8F';
                        } else if (relationType === 'direct_dependency') {
                            labelText = 'DIRECT DEPENDENCY';
                            labelColor = '#FF6B35';
                        } else if (relationType === 'transitive_dependency') {
                            labelText = 'TRANSITIVE DEPENDENCY';
                            labelColor = '#FFA07A';
                        } else if (relationType === 'direct_dependent') {
                            labelText = 'DIRECT DEPENDENT';
                            labelColor = '#4ECDC4';
                        } else if (relationType === 'transitive_dependent') {
                            labelText = 'TRANSITIVE DEPENDENT';
                            labelColor = '#87CEEB';
                        } else if (relationType === 'both') {
                            labelText = 'BOTH';
                            labelColor = '#9C27B0';
                        }
                        
                        pipelineLabel = `<div style="display: inline-block; margin-left: 8px; padding: 2px 8px; background: ${labelColor}; color: white; border-radius: 4px; font-size: 11px; font-weight: bold;">${labelText}</div>`;
                    }
                    
                    // Add picked SCC badge
                    let pickedSccBadge = '';
                    if (obj.is_picked_scc) {
                        pickedSccBadge = '<div style="display: inline-block; margin-left: 8px; padding: 2px 8px; background: #FFD700; color: #000; border-radius: 4px; font-size: 11px; font-weight: bold;">⭐ PRIORITY</div>';
                    }
                    
                    // Add row highlight class for picked SCC
                    const rowClass = obj.is_picked_scc ? 'object-row picked-scc-row' : 'object-row';
                    
                    // Format EWI badge
                    const ewiCount = obj.ewi_count || 0;
                    
                    let ewiBadge = '';
                    if (ewiCount > 0) {
                        const severity = obj.highest_ewi_severity || '';
                        let severityColor = '#FFC107';  // Default: warning (yellow)
                        if (severity === 'Critical') severityColor = '#DC3545';  // Red
                        else if (severity === 'High') severityColor = '#FF6B35';  // Orange
                        else if (severity === 'Medium') severityColor = '#FFC107';  // Yellow
                        else if (severity === 'Low') severityColor = '#17A2B8';  // Cyan
                        
                        ewiBadge = `<span class="badge" style="background-color: ${severityColor}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">${ewiCount}</span>`;
                    } else {
                        ewiBadge = '<span class="badge badge-success">0</span>';
                    }
                    
                    // Extract badge HTML from object properties
                    const missingBadge = obj.missing_badge || '';
                    const statusBadge = obj.status_badge || '';
                    
                    tableHTML += `
                        <tr class="${rowClass}" data-category="${obj.category}" data-missing="${obj.has_missing}" data-status="${obj.conversion_status}" onclick="toggleExpandRow('${expandRowId}')">
                            <td style="text-align: center; font-weight: 600; color: #005C8F;">${obj.deployment_position}</td>
                            <td><span class="badge badge-info">${obj.category}</span></td>
                            <td>
                                <strong>${obj.name}</strong>
                                <span class="copy-icon" onclick="event.stopPropagation(); copyToClipboard('${obj.name.replace(/'/g, "\\'")}', this);" title="Copy object name">❐</span>
                                ${pipelineLabel}${pickedSccBadge}
                            </td>
                            <td>
                                ${obj.file_name}
                                <span class="copy-icon" onclick="event.stopPropagation(); copyToClipboard('${obj.file_name.replace(/'/g, "\\'")}', this);" title="Copy file name">❐</span>
                            </td>
                            <td>${ewiBadge}</td>
                            <td>${missingBadge}</td>
                            <td>${statusBadge}</td>
                        </tr>
                        <tr class="expandable-row" id="${expandRowId}">
                            <td colspan="7">
                                <div class="expandable-content">
                                    ${generateMissingDepsContent(obj.missing_dependencies, obj.dependency_count, obj.dependent_count, obj.name, obj.technology, obj.subtype, obj.category)}
                                </div>
                            </td>
                        </tr>
                    `;
                });
            }
            
            tableHTML += `
                    </tbody>
                </table>
            `;
            
            modalBody.innerHTML = tableHTML;
            updateNavigationButtons();
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
        
        function navigateWave(direction) {
            const currentIndex = visibleWaveNums.indexOf(currentWaveNum);
            const newIndex = currentIndex + direction;
            
            if (newIndex >= 0 && newIndex < visibleWaveNums.length) {
                const targetWaveNum = visibleWaveNums[newIndex];
                // Check if navigating to wave 0 (Missing Dependencies)
                if (targetWaveNum === 0) {
                    openMissingDepsModal();
                } else {
                    openWaveModal(targetWaveNum);
                }
            }
        }
        
        function closeWaveModal(event) {
            if (event) event.stopPropagation();
            const modal = document.getElementById('waveModal');
            modal.classList.remove('show');
            document.body.style.overflow = 'auto';
        }
        
        function openMissingDepsModal() {
            currentWaveNum = 0;  // Set current wave to 0 for Missing Dependencies
            updateVisibleWaves();  // Update the visible waves list
            
            const modal = document.getElementById('waveModal');
            const modalWaveLabel = document.getElementById('modalWaveLabel');
            const modalWaveBadge = document.getElementById('modalWaveBadge');
            const modalBody = document.getElementById('modalWaveBody');
            
            // Update modal title
            modalWaveLabel.textContent = 'Missing Dependencies Overview';
            modalWaveBadge.textContent = '';
            
            // Show navigation buttons
            document.getElementById('prevWaveBtn').style.display = 'block';
            document.getElementById('nextWaveBtn').style.display = 'block';
            
            // Build missing dependencies content
            let content = `
                <div style="background: #FFF3CD; border-left: 4px solid #FFC107; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                    <p style="margin: 0 0 10px 0; color: #856404; font-size: 0.95em;">
                        This section identifies objects that reference missing dependencies. Each missing object shows all dependent objects 
                        and their assigned waves.
                    </p>
                    <p style="margin: 0; color: #856404; font-size: 0.9em;">
                        <strong>Note:</strong> Some object names may contain SQLCMD variables (e.g., <code>[$(SOME_NAME)]</code>) which are placeholders 
                        replaced at deployment time with actual values, commonly used to make scripts environment-agnostic. 
                        Additionally, objects prefixed with <code>#</code> (e.g., <code>#TempTable</code>) are local temporary tables that exist only 
                        for the duration of a session and are automatically dropped when the session ends.
                    </p>
                </div>
            `;
            
            const missingObjects = ''' + missing_objects_json + ''';
            const dependents = ''' + dependents_json + ''';
            const missingDepsWarning = ''' + missing_deps_warning_json + ''';
            
            if (missingDepsWarning) {
                // Show warning when data source is unavailable
                content += `
                    <div style="background: #FFF3CD; border-left: 4px solid #FFC107; padding: 20px; text-align: center; border-radius: 4px;">
                        <div style="font-size: 2em; margin-bottom: 10px;">⚠️</div>
                        <div style="color: #856404; font-size: 1.1em; font-weight: 600; margin-bottom: 10px;">Missing Dependencies Data Unavailable</div>
                        <div style="color: #856404; font-size: 0.95em; text-align: left; padding: 10px; background: rgba(255,193,7,0.1); border-radius: 4px;">
                            <p style="margin: 0 0 10px 0;"><strong>What happened:</strong> ${missingDepsWarning}</p>
                            <p style="margin: 0 0 10px 0;"><strong>What this means:</strong> The report could not find either ObjectReferences.csv (with Referenced_Element_Type='MISSING' filtering) or the legacy MissingObjectReferences.csv file in the reports directory.</p>
                            <p style="margin: 0;"><strong>Next steps:</strong> Please verify your SnowConvert reports directory contains the necessary CSV files. This does NOT mean there are no missing dependencies - the data source is simply unavailable for analysis.</p>
                        </div>
                    </div>
                `;
            } else if (missingObjects.length === 0) {
                content += `
                    <div style="background: #D4EDDA; border-left: 4px solid #28A745; padding: 20px; text-align: center; border-radius: 4px;">
                        <div style="font-size: 2em; margin-bottom: 10px;">✅</div>
                        <div style="color: #155724; font-size: 1.1em; font-weight: 600;">Great news! There are no blocked objects with missing dependencies.</div>
                    </div>
                `;
            } else {
                content += '<div style="display: flex; flex-direction: column; gap: 15px;">';
                
                missingObjects.sort();
                for (const missingObj of missingObjects) {
                    const deps = dependents[missingObj] || [];
                    if (deps.length === 0) continue;
                    
                    content += `
                        <div style="background: white; border: 1px solid #ddd; border-radius: 6px; overflow: hidden;">
                            <div style="background: #F8F9FA; padding: 12px 16px; border-bottom: 1px solid #ddd; cursor: pointer;" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none';">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-weight: 600; color: #B8860B;">Missing: ${missingObj}</span>
                                    <span style="font-size: 0.9em; color: #666;">▼ ${deps.length} dependent(s)</span>
                                </div>
                            </div>
                            <div style="display: none; padding: 12px 16px; max-height: 300px; overflow-y: auto;">
                    `;
                    
                    for (const dep of deps) {
                        const caller = dep.caller;
                        let waveDisplay = 'No Wave';
                        
                        // Find which wave this dependent is in
                        for (const [waveNum, waveObjects] of Object.entries(wavesData)) {
                            if (waveObjects.some(obj => obj.name === caller)) {
                                waveDisplay = 'Wave ' + waveNum;
                                break;
                            }
                        }
                        
                        content += `
                            <div style="padding: 8px 0; border-bottom: 1px solid #F0F0F0; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div style="font-weight: 500; color: #333;">${caller}</div>
                                    <div style="font-size: 0.85em; color: #666; margin-top: 2px;">
                                        ${dep.relation_type} (Line ${dep.line})
                                    </div>
                                </div>
                                <span style="background: #E8F4F8; color: #005C8F; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">
                                    ${waveDisplay}
                                </span>
                            </div>
                        `;
                    }
                    
                    content += `
                            </div>
                        </div>
                    `;
                }
                
                content += '</div>';
            }
            
            modalBody.innerHTML = content;
            updateNavigationButtons();
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
        
        // Close modal on ESC key
        document.addEventListener('keydown', function(event) {
            const modal = document.getElementById('waveModal');
            if (modal && modal.classList.contains('show')) {
                if (event.key === 'Escape') {
                    closeWaveModal();
                } else if (event.key === 'ArrowLeft') {
                    navigateWave(-1);
                } else if (event.key === 'ArrowRight') {
                    navigateWave(1);
                }
            }
        });
        
        
        function applyWaveFilters() {
            const searchWave = document.getElementById('searchWaveDetails').value.toLowerCase();
            const searchObject = document.getElementById('searchObject').value.toLowerCase();
            const exactMatch = document.getElementById('exactMatchToggle').checked;
            const category = document.getElementById('filterCategory').value;
            const missing = document.getElementById('filterMissing').value;
            const status = document.getElementById('filterStatus').value;
            
            const allDropdowns = document.querySelectorAll('.wave-dropdown');
            
            allDropdowns.forEach(dropdown => {
                const waveNum = dropdown.dataset.wave;
                const matchesWave = waveNum.includes(searchWave);
                
                // Check if any objects in this wave match filters
                const waveObjects = wavesData[waveNum];
                let matchingCount = 0;
                let totalCount = waveObjects ? waveObjects.length : 0;
                
                if (waveObjects) {
                    matchingCount = waveObjects.filter(obj => {
                        const matchesSearch = searchObject === '' || (exactMatch ? obj.name.toLowerCase() === searchObject : obj.name.toLowerCase().includes(searchObject));
                        const matchesCategory = !category || obj.category === category;
                        const matchesMissing = !missing || (missing === 'yes' && obj.has_missing) || (missing === 'no' && !obj.has_missing);
                        const matchesStatus = !status || obj.conversion_status === status;
                        const matchesPipeline = !window.pipelineFilter || window.pipelineFilter.has(obj.name);
                        const matchesBlocked = !blockedObjectsFilterActive || !blockedObjectsSet.has(obj.name);
                        
                        return matchesSearch && matchesCategory && matchesMissing && matchesStatus && matchesPipeline && matchesBlocked;
                    }).length;
                }
                
                // Update badge
                const badge = document.getElementById(`wave-badge-${waveNum}`);
                if (badge) {
                    if (matchingCount < totalCount) {
                        badge.textContent = `${matchingCount} of ${totalCount} objects`;
                    } else {
                        badge.textContent = `${totalCount} objects`;
                    }
                }
                
                // Show wave only if it matches wave filter AND has matching objects
                dropdown.style.display = (matchesWave && matchingCount > 0) ? '' : 'none';
            });
        }
        
        function clearWaveFilters() {
            document.getElementById('searchWaveDetails').value = '';
            document.getElementById('searchObject').value = '';
            document.getElementById('exactMatchToggle').checked = false;
            document.getElementById('filterCategory').value = '';
            document.getElementById('filterMissing').value = '';
            document.getElementById('filterStatus').value = '';
            
            // Clear blocked objects filter
            blockedObjectsFilterActive = false;
            blockedObjectsSet.clear();
            
            // Reset wave badges to show total counts
            for (const [waveNum, objects] of Object.entries(wavesData)) {
                const badge = document.getElementById(`wave-badge-${waveNum}`);
                if (badge) {
                    // Check if pipeline filter is active
                    if (window.pipelineFilter) {
                        const matchingCount = objects.filter(obj => window.pipelineFilter.has(obj.name)).length;
                        if (matchingCount < objects.length) {
                            badge.textContent = `${matchingCount} of ${objects.length} objects`;
                        } else {
                            badge.textContent = `${objects.length} objects`;
                        }
                    } else {
                        badge.textContent = `${objects.length} objects`;
                    }
                }
            }
            
            // Show all waves (unless pipeline filter is active)
            if (!window.pipelineFilter) {
                document.querySelectorAll('.wave-dropdown').forEach(d => d.style.display = '');
            } else {
                // If pipeline is active, only show waves with pipeline objects
                document.querySelectorAll('.wave-dropdown').forEach(dropdown => {
                    const waveNum = dropdown.dataset.wave;
                    const waveObjects = wavesData[waveNum];
                    const hasPipelineObjects = waveObjects.some(obj => window.pipelineFilter.has(obj.name));
                    dropdown.style.display = hasPipelineObjects ? '' : 'none';
                });
            }
        }
        
        function searchPipeline() {
            const searchTerm = document.getElementById('searchPipeline').value.trim().toLowerCase();
            const viewMode = document.getElementById('pipelineView').value;
            
            if (!searchTerm) {
                return;
            }
            
            // Show loading indicator
            document.getElementById('pipelineSearchLoading').style.display = 'block';
            document.getElementById('pipelineSearchResults').style.display = 'none';
            
            // Use setTimeout to allow UI to update before heavy computation
            setTimeout(() => {
                try {
                    // Find objects matching the search term (exact match)
                    const matchedObjects = new Set();
                    for (const [waveNum, objects] of Object.entries(wavesData)) {
                        for (const obj of objects) {
                            if (obj.name.toLowerCase() === searchTerm) {
                                matchedObjects.add(obj.name);
                            }
                        }
                    }
                    
                    if (matchedObjects.size === 0) {
                        document.getElementById('pipelineSearchLoading').style.display = 'none';
                        alert(`No object found with name: "${document.getElementById('searchPipeline').value}"\n\nPlease ensure:\n- Object name is spelled correctly\n- Object exists in the wave data\n- Name matches exactly (case-insensitive)`);
                        return;
                    }
                    
                    // Initialize or add to pipeline search objects
                    if (!window.pipelineSearchObjects) {
                        window.pipelineSearchObjects = new Set();
                    }
                    
                    matchedObjects.forEach(obj => window.pipelineSearchObjects.add(obj));
            
            // Trace all dependencies and dependents
            const relatedObjects = new Set();
            const dependencies = new Map(); // Map of object -> type (direct_dependency, transitive_dependency, direct_dependent, transitive_dependent, both, searched)
            const directDeps = new Set(); // Track direct relationships from searched objects
            const directDependents = new Set();
            const queue = [];
            
            // Mark searched objects
            window.pipelineSearchObjects.forEach(obj => {
                relatedObjects.add(obj);
                dependencies.set(obj, 'searched');
                queue.push({obj: obj, type: 'searched', depth: 0});
            });
            
            // First pass: identify direct dependencies and dependents of searched objects
            window.pipelineSearchObjects.forEach(searchedObj => {
                for (const ref of objectReferences) {
                    if (ref.caller === searchedObj) {
                        directDeps.add(ref.referenced);
                    }
                    if (ref.referenced === searchedObj) {
                        directDependents.add(ref.caller);
                    }
                }
            });
            
            // BFS to find all related objects
            const visited = new Set();
            while (queue.length > 0) {
                const {obj: current, type: relationType, depth} = queue.shift();
                const key = current + '|' + relationType;
                if (visited.has(key)) continue;
                visited.add(key);
                
                // Find DEPENDENCIES: objects that current depends on (current is CALLER, referenced is DEPENDENCY)
                // If A calls B, then B is a dependency of A (B must exist first, B is in earlier wave)
                if (viewMode === 'all' || viewMode === 'dependencies') {
                    for (const ref of objectReferences) {
                        if (ref.caller === current) {
                            // current CALLS ref.referenced, so ref.referenced is a DEPENDENCY
                            if (!relatedObjects.has(ref.referenced)) {
                                relatedObjects.add(ref.referenced);
                                // Determine if direct or transitive
                                const isDirect = directDeps.has(ref.referenced);
                                const newType = isDirect ? 'direct_dependency' : 'transitive_dependency';
                                dependencies.set(ref.referenced, newType);
                                queue.push({obj: ref.referenced, type: 'dependency', depth: depth + 1});
                            } else {
                                const currentType = dependencies.get(ref.referenced);
                                // Handle "both" case
                                if (currentType === 'direct_dependent' || currentType === 'transitive_dependent') {
                                    dependencies.set(ref.referenced, 'both');
                                } else if (currentType === 'transitive_dependency' && directDeps.has(ref.referenced)) {
                                    dependencies.set(ref.referenced, 'direct_dependency');
                                }
                            }
                        }
                    }
                }
                
                // Find DEPENDENTS: objects that depend on current (current is REFERENCED, caller is DEPENDENT)
                // If C calls A, then C is a dependent of A (C needs A, C is in later wave)
                if (viewMode === 'all' || viewMode === 'dependents') {
                    for (const ref of objectReferences) {
                        if (ref.referenced === current) {
                            // ref.caller CALLS current, so ref.caller is a DEPENDENT
                            if (!relatedObjects.has(ref.caller)) {
                                relatedObjects.add(ref.caller);
                                // Determine if direct or transitive
                                const isDirect = directDependents.has(ref.caller);
                                const newType = isDirect ? 'direct_dependent' : 'transitive_dependent';
                                dependencies.set(ref.caller, newType);
                                queue.push({obj: ref.caller, type: 'dependent', depth: depth + 1});
                            } else {
                                const currentType = dependencies.get(ref.caller);
                                // Handle "both" case
                                if (currentType === 'direct_dependency' || currentType === 'transitive_dependency') {
                                    dependencies.set(ref.caller, 'both');
                                } else if (currentType === 'transitive_dependent' && directDependents.has(ref.caller)) {
                                    dependencies.set(ref.caller, 'direct_dependent');
                                }
                            }
                        }
                    }
                }
            }
            
            // Store for filtering
            window.pipelineFilter = relatedObjects;
            window.pipelineRelations = dependencies;
            window.pipelineViewMode = viewMode;
            
            // Calculate total hours and objects in pipeline
            let totalPipelineObjects = 0;
            let totalPipelineHours = 0;
            let waveCount = 0;
            
            // Filter waves and update counts
            document.querySelectorAll('.wave-dropdown').forEach(dropdown => {
                const waveNum = dropdown.dataset.wave;
                
                // Skip wave 0 (missing dependencies wave) - it's not in wavesData
                if (waveNum === '0') {
                    return;
                }
                
                const waveObjects = wavesData[waveNum];
                if (!waveObjects) {
                    return; // Skip if no data for this wave
                }
                
                const pipelineMatchingObjects = waveObjects.filter(obj => relatedObjects.has(obj.name));
                const pipelineMatchingCount = pipelineMatchingObjects.length;
                const totalCount = waveObjects.length;
                
                dropdown.style.display = pipelineMatchingCount > 0 ? '' : 'none';
                
                if (pipelineMatchingCount > 0) {
                    waveCount++;
                    totalPipelineObjects += pipelineMatchingCount;
                    
                    // Calculate hours for this wave's pipeline objects
                    const waveHours = pipelineMatchingObjects.reduce((sum, obj) => sum + obj.estimated_hours, 0);
                    totalPipelineHours += waveHours;
                    
                    // Update badge with count and hours
                    const badge = document.getElementById(`wave-badge-${waveNum}`);
                    if (badge) {
                        if (pipelineMatchingCount < totalCount) {
                            badge.textContent = `${pipelineMatchingCount} of ${totalCount} objects (${waveHours.toFixed(1)}h)`;
                        } else {
                            badge.textContent = `${totalCount} objects (${waveHours.toFixed(1)}h)`;
                        }
                    }
                }
            });
            
            // Update UI buttons and stats based on pipeline state
            document.getElementById('pipelineSearchLoading').style.display = 'none';
            document.getElementById('pipelineSearchResults').style.display = 'block';
            
            // Create clickable object list with delete buttons
            const objectsList = document.getElementById('pipelineObjectsList');
            objectsList.innerHTML = '';
            Array.from(window.pipelineSearchObjects).forEach((obj) => {
                const objChip = document.createElement('div');
                objChip.style.cssText = 'display: inline-flex; align-items: center; background: #005C8F; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 500;';
                
                const objText = document.createElement('span');
                objText.textContent = obj;
                objChip.appendChild(objText);
                
                const deleteBtn = document.createElement('button');
                deleteBtn.textContent = '×';
                deleteBtn.style.cssText = 'margin-left: 6px; background: rgba(255,255,255,0.3); color: white; border: none; border-radius: 50%; width: 20px; height: 20px; cursor: pointer; font-size: 16px; line-height: 1; padding: 0; display: inline-flex; align-items: center; justify-content: center; transition: background 0.2s;';
                deleteBtn.onmouseover = () => deleteBtn.style.background = 'rgba(255,255,255,0.5)';
                deleteBtn.onmouseout = () => deleteBtn.style.background = 'rgba(255,255,255,0.3)';
                deleteBtn.onclick = () => removeFromPipeline(obj);
                deleteBtn.title = `Remove ${obj} from search`;
                
                objChip.appendChild(deleteBtn);
                objectsList.appendChild(objChip);
            });
            
            // Update pipeline statistics
            const statsDiv = document.getElementById('pipelineStats');
            statsDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div><strong>Total Objects:</strong> ${totalPipelineObjects} across ${waveCount} waves</div>
                    <div><strong>Estimated Effort:</strong> ${totalPipelineHours.toFixed(1)} hours</div>
                </div>
            `;
            
            // Hide 'Search Pipeline' button, show 'Add to Pipeline' and 'Clear Pipeline'
            const searchBtn = document.querySelector('button[onclick="searchPipeline()"]');
            if (searchBtn) searchBtn.style.display = 'none';
            document.getElementById('addToPipelineBtn').style.display = 'inline-block';
            document.getElementById('clearPipelineBtn').style.display = 'inline-block';
            
            // Clear the input field
            document.getElementById('searchPipeline').value = '';
                } catch (error) {
                    document.getElementById('pipelineSearchLoading').style.display = 'none';
                    alert('An error occurred while searching. Please try again.');
                }
            }, 100);
        }
        
        function addToPipeline() {
            searchPipeline();
        }
        
        function applyPipelineView() {
            // Reapply the pipeline search with current view mode
            if (window.pipelineSearchObjects && window.pipelineSearchObjects.size > 0) {
                // Re-run the search with existing objects but new view mode
                const viewMode = document.getElementById('pipelineView').value;
                const relatedObjects = new Set();
                const dependencies = new Map();
                const directDeps = new Set();
                const directDependents = new Set();
                const queue = [];
                
                // Mark searched objects
                window.pipelineSearchObjects.forEach(obj => {
                    relatedObjects.add(obj);
                    dependencies.set(obj, 'searched');
                    queue.push({obj: obj, type: 'searched', depth: 0});
                });
                
                // First pass: identify direct dependencies and dependents of searched objects
                window.pipelineSearchObjects.forEach(searchedObj => {
                    for (const ref of objectReferences) {
                        if (ref.caller === searchedObj) {
                            directDeps.add(ref.referenced);
                        }
                        if (ref.referenced === searchedObj) {
                            directDependents.add(ref.caller);
                        }
                    }
                });
                
                // BFS to find all related objects
                const visited = new Set();
                while (queue.length > 0) {
                    const {obj: current, type: relationType, depth} = queue.shift();
                    const key = current + '|' + relationType;
                    if (visited.has(key)) continue;
                    visited.add(key);
                    
                    // Find DEPENDENCIES
                    if (viewMode === 'all' || viewMode === 'dependencies') {
                        for (const ref of objectReferences) {
                            if (ref.caller === current) {
                                if (!relatedObjects.has(ref.referenced)) {
                                    relatedObjects.add(ref.referenced);
                                    const isDirect = directDeps.has(ref.referenced);
                                    const newType = isDirect ? 'direct_dependency' : 'transitive_dependency';
                                    dependencies.set(ref.referenced, newType);
                                    queue.push({obj: ref.referenced, type: 'dependency', depth: depth + 1});
                                } else {
                                    const currentType = dependencies.get(ref.referenced);
                                    if (currentType === 'direct_dependent' || currentType === 'transitive_dependent') {
                                        dependencies.set(ref.referenced, 'both');
                                    } else if (currentType === 'transitive_dependency' && directDeps.has(ref.referenced)) {
                                        dependencies.set(ref.referenced, 'direct_dependency');
                                    }
                                }
                            }
                        }
                    }
                    
                    // Find DEPENDENTS
                    if (viewMode === 'all' || viewMode === 'dependents') {
                        for (const ref of objectReferences) {
                            if (ref.referenced === current) {
                                if (!relatedObjects.has(ref.caller)) {
                                    relatedObjects.add(ref.caller);
                                    const isDirect = directDependents.has(ref.caller);
                                    const newType = isDirect ? 'direct_dependent' : 'transitive_dependent';
                                    dependencies.set(ref.caller, newType);
                                    queue.push({obj: ref.caller, type: 'dependent', depth: depth + 1});
                                } else {
                                    const currentType = dependencies.get(ref.caller);
                                    if (currentType === 'direct_dependency' || currentType === 'transitive_dependency') {
                                        dependencies.set(ref.caller, 'both');
                                    } else if (currentType === 'transitive_dependent' && directDependents.has(ref.caller)) {
                                        dependencies.set(ref.caller, 'direct_dependent');
                                    }
                                }
                            }
                        }
                    }
                }
                
                // Update stored data
                window.pipelineFilter = relatedObjects;
                window.pipelineRelations = dependencies;
                window.pipelineViewMode = viewMode;
                
                // Calculate total hours and objects in pipeline
                let totalPipelineObjects = 0;
                let totalPipelineHours = 0;
                let waveCount = 0;
                
                // Filter waves and update counts
                document.querySelectorAll('.wave-dropdown').forEach(dropdown => {
                    const waveNum = dropdown.dataset.wave;
                    
                    // Skip wave 0 (missing dependencies wave) - it's not in wavesData
                    if (waveNum === '0') {
                        return;
                    }
                    
                    const waveObjects = wavesData[waveNum];
                    if (!waveObjects) {
                        return; // Skip if no data for this wave
                    }
                    
                    const pipelineMatchingObjects = waveObjects.filter(obj => relatedObjects.has(obj.name));
                    const pipelineMatchingCount = pipelineMatchingObjects.length;
                    const totalCount = waveObjects.length;
                    
                    dropdown.style.display = pipelineMatchingCount > 0 ? '' : 'none';
                    
                    if (pipelineMatchingCount > 0) {
                        waveCount++;
                        totalPipelineObjects += pipelineMatchingCount;
                        
                        // Calculate hours for this wave's pipeline objects
                        const waveHours = pipelineMatchingObjects.reduce((sum, obj) => sum + obj.estimated_hours, 0);
                        totalPipelineHours += waveHours;
                        
                        // Update badge with count and hours
                        const badge = document.getElementById(`wave-badge-${waveNum}`);
                        if (badge) {
                            if (pipelineMatchingCount < totalCount) {
                                badge.textContent = `${pipelineMatchingCount} of ${totalCount} objects (${waveHours.toFixed(1)}h)`;
                            } else {
                                badge.textContent = `${totalCount} objects (${waveHours.toFixed(1)}h)`;
                            }
                        }
                    }
                });
                
                // Update pipeline statistics
                const statsDiv = document.getElementById('pipelineStats');
                statsDiv.innerHTML = `
                    📊 <strong>Pipeline Summary:</strong> 
                    ${totalPipelineObjects} objects across ${waveCount} waves | 
                    Estimated effort: <strong>${totalPipelineHours.toFixed(1)} hours</strong>
                `;
            }
        }
        
        function clearPipelineSearch() {
            window.pipelineFilter = null;
            window.pipelineRelations = null;
            window.pipelineSearchObjects = null;
            window.pipelineViewMode = null;
            
            document.getElementById('searchPipeline').value = '';
            document.getElementById('pipelineView').value = 'all';
            document.getElementById('pipelineSearchResults').style.display = 'none';
            document.getElementById('pipelineSearchLoading').style.display = 'none';
            
            // Show 'Search Pipeline' button, hide others
            const searchBtn = document.querySelector('button[onclick="searchPipeline()"]');
            if (searchBtn) searchBtn.style.display = 'inline-block';
            document.getElementById('addToPipelineBtn').style.display = 'none';
            document.getElementById('clearPipelineBtn').style.display = 'none';
            
            // Reset all wave badges to total counts and show all waves
            for (const [waveNum, objects] of Object.entries(wavesData)) {
                const badge = document.getElementById(`wave-badge-${waveNum}`);
                if (badge) {
                    badge.textContent = `${objects.length} objects`;
                }
            }
            
            // Show all waves
            document.querySelectorAll('.wave-dropdown').forEach(d => d.style.display = '');
            
            // Reapply regular filters if any are active
            applyWaveFilters();
        }
        
        function removeFromPipeline(objectName) {
            if (!window.pipelineSearchObjects) return;
            
            // Remove object from the set
            window.pipelineSearchObjects.delete(objectName);
            
            // If no objects left, clear the entire search
            if (window.pipelineSearchObjects.size === 0) {
                clearPipelineSearch();
                return;
            }
            
            // Otherwise, re-run the search with remaining objects
            searchPipeline();
        }
        
        // Add event listener for view dropdown
        document.getElementById('pipelineView').addEventListener('change', applyPipelineView);
        
        // Initialize blocked objects set on page load
        initializeBlockedObjectsSet();
    </script>
</body>
</html>
'''
    
    return html


def main():
    parser = argparse.ArgumentParser(description='Generate HTML wave migration report')
    parser.add_argument('--analysis-dir', '-a', required=True, 
                       help='Path to dependency analysis directory')
    parser.add_argument('--issues-json', '-i', required=True,
                       help='Path to issues-estimation.json')
    parser.add_argument('--output', '-o', required=False,
                       help='Output HTML file path (optional)')
    parser.add_argument('--reports-dir', '-r', required=False,
                       help='Path to Reports directory containing TopLevelCodeUnits CSV (optional)')
    
    args = parser.parse_args()
    
    generate_html_report(args.analysis_dir, args.issues_json, args.output, args.reports_dir)


if __name__ == '__main__':
    main()
