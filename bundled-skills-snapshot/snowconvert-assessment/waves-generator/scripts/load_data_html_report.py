#!/usr/bin/env python3
"""
Data Loading Module for HTML Wave Migration Report Generator

Contains all data loading and parsing functions for dependency analysis outputs.
"""
import csv
import json
from pathlib import Path


def load_issues_estimation(json_path):
    """Load issues estimation data from JSON file."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    issue_map = {}
    for issue in data.get('Issues', []):
        code = issue.get('Code', '')
        manual_effort = issue.get('ManualEffort', 0)
        if manual_effort == -1:
            manual_effort = 0
        issue_map[code] = {
            'code': code,
            'severity': issue.get('Severity', 'Unknown'),
            'manual_effort': manual_effort,
            'friendly_name': issue.get('FriendlyName', '')
        }
    
    severity_map = {}
    for severity in data.get('Severities', []):
        severity_map[severity.get('Severity', '')] = severity.get('ManualEffort', 0)
    
    return issue_map, severity_map


def load_toplevel_code_units(csv_path):
    """Load TopLevelCodeUnits CSV with object metadata.
    Uses CodeUnitId (fully qualified name) as the primary key for matching with partition_membership.
    """
    objects_data = {}
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Use CodeUnitId as the primary key - it has the fully qualified name
            code_unit_id = row.get('CodeUnitId', '').strip()
            obj_name = row.get('CodeUnitName', '').strip()
            
            if code_unit_id:
                deployment_order = row.get('Deployment Order', '').strip()
                has_missing = '*' in deployment_order
                clean_order = deployment_order.replace('*', '')
                
                # ConversionStatus column can have values like "Success", "Action required", etc.
                conversion_status = row.get('ConversionStatus', row.get('Conversion', '')).strip()
                
                # Get EWI, FDM, PRF counts from TopLevelCodeUnits
                ewi_count_str = row.get('EWI Count', '0').strip()
                fdm_count_str = row.get('FDM Count', '0').strip()
                prf_count_str = row.get('PRF Count', '0').strip()
                highest_ewi_severity = row.get('HighestEWISeverity', '').strip()
                
                try:
                    ewi_count = int(ewi_count_str) if ewi_count_str else 0
                except ValueError:
                    ewi_count = 0
                
                try:
                    fdm_count = int(fdm_count_str) if fdm_count_str else 0
                except ValueError:
                    fdm_count = 0
                
                try:
                    prf_count = int(prf_count_str) if prf_count_str else 0
                except ValueError:
                    prf_count = 0
                
                obj_data = {
                    'category': row.get('Category', ''),
                    'file_name': row.get('FileName', ''),
                    'has_missing_dependencies': has_missing,
                    'deployment_order': clean_order,
                    'conversion_status': conversion_status,
                    'lines_of_code': row.get('Lines of Code', '0'),
                    'ewi_count': ewi_count,
                    'fdm_count': fdm_count,
                    'prf_count': prf_count,
                    'highest_ewi_severity': highest_ewi_severity
                }
                
                # Store by fully qualified name (CodeUnitId)
                objects_data[code_unit_id] = obj_data
                
                # Also store by short name (CodeUnitName) as fallback
                if obj_name:
                    objects_data[obj_name] = obj_data
    
    return objects_data


def load_partition_membership(csv_path):
    """Load partition membership CSV with object metadata."""
    membership = {}
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            obj_name = row.get('object', '').strip()
            # Try both 'partition' and 'partition_number' column names
            partition = row.get('partition_number', row.get('partition', '')).strip()
            is_root = row.get('is_root', '').lower() == 'true'
            is_leaf = row.get('is_leaf', '').lower() == 'true'
            is_picked_scc = row.get('is_picked_scc', '').lower() == 'true'
            category = row.get('category', '').strip()
            file_name = row.get('file_name', '').strip()
            technology = row.get('technology', '').strip()
            conversion_status = row.get('conversion_status', '').strip()
            subtype = row.get('subtype', '').strip()
            
            partition_type = row.get('partition_type', 'regular').strip()
            
            membership[obj_name] = {
                'partition': int(partition) if partition.isdigit() else 0,
                'is_root': is_root,
                'is_leaf': is_leaf,
                'is_picked_scc': is_picked_scc,
                'category': category,
                'file_name': file_name,
                'technology': technology,
                'conversion_status': conversion_status,
                'subtype': subtype,
                'partition_type': partition_type
            }
    
    return membership


def parse_graph_summary(txt_path):
    """Parse graph_summary.txt for comprehensive statistics."""
    summary = {
        'total_nodes': 0,
        'total_edges': 0,
        'avg_dependencies': 0.0,
        'weakly_connected_components': 0,
        'strongly_connected_components': 0,
        'cyclic_dependencies': 0,
        'root_nodes': 0,
        'leaf_nodes': 0,
        'max_dependencies': 0,
        'max_dependents': 0,
        'generated_timestamp': ''
    }
    
    with open(txt_path, 'r') as f:
        content = f.read()
        
        for line in content.split('\n'):
            line = line.strip()
            if 'Generated:' in line:
                summary['generated_timestamp'] = line.split('Generated:')[-1].strip()
            elif 'Total Nodes (Objects):' in line:
                summary['total_nodes'] = line.split(':')[-1].strip().replace(',', '')
            elif 'Total Edges (Dependencies):' in line:
                summary['total_edges'] = line.split(':')[-1].strip().replace(',', '')
            elif 'Average Dependencies per Node:' in line:
                summary['avg_dependencies'] = line.split(':')[-1].strip()
            elif 'Weakly Connected Components' in line:
                summary['weakly_connected_components'] = line.split(':')[-1].strip().replace(',', '')
            elif 'Strongly Connected Components:' in line:
                summary['strongly_connected_components'] = line.split(':')[-1].strip().replace(',', '')
            elif 'Cyclic Dependencies' in line:
                summary['cyclic_dependencies'] = line.split(':')[-1].strip().replace(',', '')
            elif 'Root Nodes' in line:
                summary['root_nodes'] = line.split(':')[-1].strip().replace(',', '')
            elif 'Leaf Nodes' in line:
                summary['leaf_nodes'] = line.split(':')[-1].strip().replace(',', '')
            elif 'Max Dependencies:' in line:
                summary['max_dependencies'] = line.split(':')[-1].strip().replace(',', '')
            elif 'Max Dependents:' in line:
                summary['max_dependents'] = line.split(':')[-1].strip().replace(',', '')
    
    return summary


def parse_cycles(txt_path):
    """Parse cycles.txt for cyclic dependency information."""
    cycles = []
    
    with open(txt_path, 'r') as f:
        content = f.read()
        lines = content.strip().split('\n')
        
        if len(lines) < 2:
            return cycles
        
        # First line contains total count
        total_line = lines[0] if 'Total Cycles' in lines[0] else ''
        
        current_cycle = None
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('Cycle ') and '(' in line:
                if current_cycle:
                    cycles.append(current_cycle)
                # Extract cycle number and node count
                parts = line.split('(')
                cycle_num = parts[0].replace('Cycle', '').replace(':', '').strip()
                node_count = parts[1].split(' ')[0] if len(parts) > 1 else '0'
                current_cycle = {
                    'cycle_num': cycle_num,
                    'node_count': node_count,
                    'nodes': []
                }
            elif line.startswith('- ') and current_cycle:
                node_name = line[2:].strip()
                current_cycle['nodes'].append(node_name)
        
        if current_cycle:
            cycles.append(current_cycle)
    
    return cycles


def parse_excluded_edges(txt_path):
    """Parse excluded_edges_analysis.txt for comprehensive information."""
    excluded = {
        'total_excluded': 0,
        'undefined_caller': 0,
        'undefined_referenced': 0,
        'both_undefined': 0,
        'exclusion_reasons': [],
        'relation_types': [],
        'top_undefined_referenced': []
    }
    
    with open(txt_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if 'Total Excluded Edges:' in line:
                excluded['total_excluded'] = line.split(':')[-1].strip().replace(',', '')
            elif 'Edges with undefined caller:' in line:
                excluded['undefined_caller'] = line.split(':')[-1].strip().replace(',', '')
            elif 'Edges with undefined referenced object:' in line:
                excluded['undefined_referenced'] = line.split(':')[-1].strip().replace(',', '')
            elif 'Edges with both undefined:' in line:
                excluded['both_undefined'] = line.split(':')[-1].strip().replace(',', '')
            elif 'EXCLUSION REASONS' in line:
                # Parse exclusion reasons section
                j = i + 2
                while j < len(lines) and lines[j].strip() and not lines[j].startswith('=') and not lines[j].startswith('RELATION'):
                    reason_line = lines[j].strip()
                    if ':' in reason_line:
                        reason, count = reason_line.rsplit(':', 1)
                        excluded['exclusion_reasons'].append({
                            'reason': reason.strip(),
                            'count': count.strip().replace(',', '')
                        })
                    j += 1
            elif 'RELATION TYPES' in line:
                # Parse relation types section
                j = i + 2
                while j < len(lines) and lines[j].strip() and not lines[j].startswith('=') and not lines[j].startswith('TOP'):
                    rel_line = lines[j].strip()
                    if ':' in rel_line:
                        rel_type, count = rel_line.rsplit(':', 1)
                        excluded['relation_types'].append({
                            'type': rel_type.strip(),
                            'count': count.strip().replace(',', '')
                        })
                    j += 1
            elif 'TOP 20 UNDEFINED REFERENCED OBJECTS' in line:
                # Parse top undefined referenced objects
                j = i + 2
                count = 0
                while j < len(lines) and count < 10 and lines[j].strip() and not lines[j].startswith('=') and not lines[j].startswith('SAMPLE'):
                    obj_line = lines[j].strip()
                    if 'x -' in obj_line:
                        parts = obj_line.split('x -', 1)
                        if len(parts) == 2:
                            excluded['top_undefined_referenced'].append({
                                'count': parts[0].strip(),
                                'object': parts[1].strip()
                            })
                            count += 1
                    j += 1
    
    return excluded


def load_toplevel_objects_estimation(csv_path):
    """Load TopLevelObjectsEstimation report with per-object effort data and EWI counts."""
    objects_estimation = {}
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            obj_id = row.get('Object Id', '').strip()
            if obj_id:
                manual_effort = row.get('Manual Effort', '0').strip()
                try:
                    effort_minutes = float(manual_effort) if manual_effort else 0.0
                except ValueError:
                    effort_minutes = 0.0
                
                ewis_number = row.get('EWIsNumber', '0').strip()
                try:
                    ewis_count = int(ewis_number) if ewis_number else 0
                except ValueError:
                    ewis_count = 0
                
                objects_estimation[obj_id] = {
                    'manual_effort_minutes': effort_minutes,
                    'conversion_status': row.get('ConversionStatus', '').strip(),
                    'ewis_number': ewis_count,
                    'highest_ewi_severity': row.get('HighestEWISeverity', '').strip()
                }
    
    return objects_estimation


def find_estimation_reports(reports_dir):
    """Find estimation report files with NA or timestamp patterns."""
    reports_path = Path(reports_dir)
    estimation_files = {}
    
    # Patterns to search for
    patterns = {
        'toplevel_estimation': ['TopLevelObjectsEstimation.*.csv', 'TopLevelObjectsEstimation.NA.csv'],
        'issues_estimation': ['IssuesEstimation.*.csv', 'IssuesEstimation.NA.csv'],
        'issues_aggregate': ['IssuesEstimationAggregate.*.csv', 'IssuesEstimationAggregate.NA.csv'],
        'effort_formula': ['EffortEstimationFormula.*.csv', 'EffortEstimationFormula.NA.csv']
    }
    
    for key, pattern_list in patterns.items():
        for pattern in pattern_list:
            matches = list(reports_path.glob(pattern))
            if matches:
                estimation_files[key] = matches[0]
                break
    
    return estimation_files


def load_estimation_grand_totals(estimation_files):
    """Load grand totals from estimation reports for display in HTML."""
    grand_totals = {}
    
    # Load TopLevelObjectsEstimation totals
    if 'toplevel_estimation' in estimation_files:
        try:
            with open(estimation_files['toplevel_estimation'], 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                total_objects = 0
                total_manual_minutes = 0.0
                success_count = 0
                
                for row in reader:
                    total_objects += 1
                    manual_effort = row.get('Manual Effort', '0').strip()
                    try:
                        total_manual_minutes += float(manual_effort) if manual_effort else 0.0
                    except ValueError:
                        pass
                    
                    if row.get('ConversionStatus', '').strip() == 'Success':
                        success_count += 1
                
                grand_totals['toplevel'] = {
                    'total_objects': total_objects,
                    'total_manual_hours': total_manual_minutes / 60.0,
                    'success_count': success_count,
                    'success_rate': (success_count / total_objects * 100) if total_objects > 0 else 0
                }
        except Exception as e:
            print(f"Error loading toplevel estimation totals: {e}")
    
    # Load IssuesEstimationAggregate totals
    if 'issues_aggregate' in estimation_files:
        try:
            with open(estimation_files['issues_aggregate'], 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                severity_breakdown = {}
                total_issues = 0
                total_issue_minutes = 0.0
                
                for row in reader:
                    severity = row.get('Highest EWI Severity', '').strip()
                    count = int(row.get('Object Count', '0'))
                    manual_effort = row.get('Manual Effort', '0').strip()
                    
                    try:
                        effort_minutes = float(manual_effort) if manual_effort else 0.0
                    except ValueError:
                        effort_minutes = 0.0
                    
                    total_issues += count
                    total_issue_minutes += effort_minutes
                    
                    if severity:
                        severity_breakdown[severity] = {
                            'count': count,
                            'manual_hours': effort_minutes / 60.0
                        }
                
                grand_totals['issues_aggregate'] = {
                    'total_issues': total_issues,
                    'total_manual_hours': total_issue_minutes / 60.0,
                    'severity_breakdown': severity_breakdown
                }
        except Exception as e:
            print(f"Error loading issues aggregate totals: {e}")
    
    # Load EffortEstimationFormula totals
    if 'effort_formula' in estimation_files:
        try:
            with open(estimation_files['effort_formula'], 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                code_unit_breakdown = {}
                
                for row in reader:
                    code_unit = row.get('Code Unit Type', '').strip()
                    count = int(row.get('Code Unit Count', '0'))
                    manual_effort = row.get('Manual Effort', '0').strip()
                    
                    try:
                        effort_minutes = float(manual_effort) if manual_effort else 0.0
                    except ValueError:
                        effort_minutes = 0.0
                    
                    if code_unit:
                        code_unit_breakdown[code_unit] = {
                            'count': count,
                            'manual_hours': effort_minutes / 60.0
                        }
                
                grand_totals['effort_formula'] = {
                    'code_unit_breakdown': code_unit_breakdown
                }
        except Exception as e:
            print(f"Error loading effort formula totals: {e}")
    
    return grand_totals


def estimate_hours_for_object(obj_name, objects_data, issue_map, severity_map, estimation_data=None, conversion_status_override=None):
    """Estimate hours based on conversion status and issues.
    Uses estimation reports if provided, otherwise baseline from issues-estimation.json.
    """
    obj_info = objects_data.get(obj_name, {})
    conversion_status = conversion_status_override if conversion_status_override is not None else obj_info.get('conversion_status', 'Unknown')
    
    # If estimation reports are provided, use those
    if estimation_data and obj_name in estimation_data:
        effort_minutes = estimation_data[obj_name].get('manual_effort_minutes', 0.0)
        return effort_minutes / 60.0  # Convert minutes to hours
    
    # Otherwise use baseline
    if conversion_status == 'Success':
        return 0.0
    
    # Use medium severity baseline for non-success objects (in minutes)
    base_minutes = severity_map.get('Medium', 16.5)
    
    return base_minutes / 60.0  # Convert to hours


def load_missing_object_references(reports_dir):
    """Load missing object references to identify blocked objects.
    
    Tries to load from (in order of priority):
    1. ObjectReferences.*.csv filtered by Referenced_Element_Type='MISSING' (new format)
    2. MissingObjectReferences.*.csv (legacy format)
    
    Returns:
        dict: {
            'missing_objects': set of missing object names,
            'dependents': {missing_obj: [list of dependent objects]},
            'details': [list of dicts with full edge details],
            'data_source': str ('ObjectReferences', 'MissingObjectReferences', or 'none'),
            'warning': str or None (warning message if data couldn't be loaded)
        }
    """
    reports_path = Path(reports_dir)
    
    # Try ObjectReferences.*.csv first (new format)
    obj_ref_matches = list(reports_path.glob('ObjectReferences.*.csv'))
    if obj_ref_matches:
        result = _load_missing_refs_from_object_references(obj_ref_matches[0])
        if result['missing_objects'] or result['details']:
            result['data_source'] = 'ObjectReferences'
            result['warning'] = None
            return result
    
    # Fallback to MissingObjectReferences.*.csv (legacy format)
    missing_ref_matches = list(reports_path.glob('MissingObjectReferences.*.csv'))
    if missing_ref_matches:
        result = _load_missing_refs_from_legacy_csv(missing_ref_matches[0])
        if result['missing_objects'] or result['details']:
            result['data_source'] = 'MissingObjectReferences'
            result['warning'] = None
            return result
    
    # Neither source found or both empty - return with warning
    warning_msg = None
    if not obj_ref_matches and not missing_ref_matches:
        warning_msg = "Warning: Could not load missing dependencies data. Neither ObjectReferences.csv nor MissingObjectReferences.csv was found in the reports directory. This does not mean there are no missing dependencies - the data source is unavailable."
    elif obj_ref_matches and not missing_ref_matches:
        # ObjectReferences.csv exists but had no MISSING rows, and no legacy fallback available
        # This likely means older report format where MISSING data was in separate file
        warning_msg = "Warning: ObjectReferences.csv was found but contains no 'MISSING' entries, and MissingObjectReferences.csv (legacy format) was not found. Cannot determine if there are missing dependencies."
    # else: Both files checked OR only legacy file checked - truly no missing deps (no warning)
    
    return {
        'missing_objects': set(),
        'dependents': {},
        'details': [],
        'data_source': 'none',
        'warning': warning_msg
    }


def _load_missing_refs_from_object_references(csv_path):
    """Load from ObjectReferences.*.csv, filtering for Referenced_Element_Type='MISSING'.
    
    ETL PROCESS callers are rolled up to package level (FileName minus .dtsx extension)
    to match the package-level nodes used in the dependency graph.
    """
    missing_objects = set()
    dependents = {}
    details = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ref_type = row.get('Referenced_Element_Type', '').strip()
            if ref_type != 'MISSING':
                continue
            
            caller = row.get('Caller_CodeUnit_FullName', '').strip()
            caller_type = row.get('Caller_CodeUnit', '').strip()
            referenced = row.get('Referenced_Element_FullName', '').strip()
            relation_type = row.get('Relation_Type', '').strip()
            line = row.get('Line', '').strip()
            file_name = row.get('FileName', '').strip()
            
            # Roll up ETL components to package level
            if caller_type == 'ETL PROCESS' and file_name.endswith('.dtsx'):
                caller = str(Path(file_name).with_suffix(''))
            
            if not referenced or not caller or caller == 'N/A' or referenced == 'N/A':
                continue
            
            missing_objects.add(referenced)
            
            if referenced not in dependents:
                dependents[referenced] = []
            
            dependents[referenced].append({
                'caller': caller,
                'relation_type': relation_type,
                'line': line,
                'file_name': file_name
            })
            
            details.append({
                'missing_object': referenced,
                'dependent': caller,
                'relation_type': relation_type,
                'line': line,
                'file_name': file_name
            })
    
    return {
        'missing_objects': missing_objects,
        'dependents': dependents,
        'details': details
    }


def _load_missing_refs_from_legacy_csv(csv_path):
    """Load from legacy MissingObjectReferences.*.csv file."""
    missing_objects = set()
    dependents = {}
    details = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            caller = row.get('Caller_CodeUnit_FullName', '').strip()
            referenced = row.get('Referenced_Element_FullName', '').strip()
            relation_type = row.get('Relation_Type', '').strip()
            line = row.get('Line', '').strip()
            file_name = row.get('FileName', '').strip()
            
            # Skip rows with missing or N/A caller/referenced values
            if not referenced or not caller or caller == 'N/A' or referenced == 'N/A':
                continue
            
            missing_objects.add(referenced)
            
            if referenced not in dependents:
                dependents[referenced] = []
            
            dependents[referenced].append({
                'caller': caller,
                'relation_type': relation_type,
                'line': line,
                'file_name': file_name
            })
            
            details.append({
                'missing_object': referenced,
                'dependent': caller,
                'relation_type': relation_type,
                'line': line,
                'file_name': file_name
            })
    
    return {
        'missing_objects': missing_objects,
        'dependents': dependents,
        'details': details
    }
