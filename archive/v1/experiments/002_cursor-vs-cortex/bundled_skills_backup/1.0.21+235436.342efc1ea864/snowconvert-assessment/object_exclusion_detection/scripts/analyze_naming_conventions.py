#!/usr/bin/env python3
"""
Naming Convention Analyzer for SnowConvert Reports

Identifies temporary/staging, deprecated/legacy, testing, and duplicate objects.
This script analyzes SnowConvert report data to detect:
1. Temporary & Transient Objects (Naming-Based)
2. Deprecated Code Indicators (Naming-Based)
3. Testing Objects (Naming-Based: Test, Fake, Mock, Demo, Sample patterns)
4. Duplicate Objects (File-Based: Same object in multiple source files)
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

# =============================================================================
# DUPLICATE DETECTION HELPER FUNCTIONS
# =============================================================================

def pick_primary_entry(entries: List[Dict[str, Any]]) -> tuple:
    """
    Pick the primary entry when multiple files have the same full_name.
    
    Priority:
    1. Entry with NO deprecated/backup patterns → Primary
    2. If multiple have no patterns → highest version number, then shortest filename
    3. If ALL have patterns → highest version number or shortest filename
    
    Args:
        entries: List of object entries with the same full_name
        
    Returns:
        tuple: (primary_entry, list_of_other_entries)
    """
    def score_entry(entry):
        """Lower score = better candidate for primary"""
        name_patterns = entry.get('name_patterns', [])
        
        # Check for deprecated patterns
        deprecated_indicators = ['_bak', '_old', '_backup', '_archive', '_deprecated', '_copy']
        has_deprecated = any(ind in str(name_patterns).lower() for ind in deprecated_indicators)
        
        # Check for version number - extract version if present (higher version = better)
        version_num = 0
        file_name = entry.get('file', '').lower()
        version_match = re.search(r'[._]v(\d+)', file_name)
        if version_match:
            version_num = int(version_match.group(1))
        
        if not name_patterns:
            # No patterns = best candidate (score 0)
            return (0, -version_num, len(entry.get('file', '')))
        elif has_deprecated:
            # Has deprecated patterns = worst candidate (score 100)
            return (100, -version_num, len(entry.get('file', '')))
        else:
            # Has some patterns but not deprecated (score 50)
            return (50, -version_num, len(entry.get('file', '')))
    
    sorted_entries = sorted(entries, key=score_entry)
    primary = sorted_entries[0]
    others = sorted_entries[1:]
    
    return primary, others


def analyze_duplicate_objects(
    all_objects: List[Dict[str, Any]], 
    dependency_data: Dict = None,
    verbose: bool = True
) -> tuple:
    """
    Analyze objects for duplicates (same full_name in multiple source files).
    
    This function:
    1. Groups objects by full_name
    2. For groups with multiple entries, picks a primary (recommended) version
    3. Marks other entries as duplicates with metadata
    4. Adds dependency warnings to duplicates
    
    Args:
        all_objects: List of objects (should already have 'name_patterns' populated)
        dependency_data: Optional dict with 'dependents' graph for dependency analysis
        verbose: Whether to print progress messages
        
    Returns:
        tuple: (primary_objects, duplicate_objects)
            - primary_objects: List of unique objects (one per full_name)
            - duplicate_objects: List of duplicate entries with metadata
    """
    # Group by full_name to find duplicates
    objects_by_fullname = defaultdict(list)
    for obj in all_objects:
        full_name = obj.get('full_name', '')
        if full_name:
            objects_by_fullname[full_name].append(obj)
    
    # Process each group
    primary_objects = []
    duplicate_objects = []
    
    for full_name, entries in objects_by_fullname.items():
        if len(entries) == 1:
            # No duplicates - single entry is primary
            entry = entries[0]
            entry['is_duplicate'] = False
            entry['is_primary'] = True
            entry['all_files_for_object'] = [entry.get('file', '')]
            primary_objects.append(entry)
        else:
            # Multiple files for same full_name - pick primary
            primary, others = pick_primary_entry(entries)
            
            # Set up primary
            primary['is_duplicate'] = False
            primary['is_primary'] = True
            primary['all_files_for_object'] = [e.get('file', '') for e in entries]
            
            # Build version_suggestion for primary
            primary['version_suggestion'] = {
                'recommended_file': primary.get('file', ''),
                'recommended_reason': 'No deprecated/backup patterns detected' if not primary.get('_has_deprecated_pattern') else 'Selected as primary (highest version or fewest patterns)',
                'current_file_status': 'primary',
                'alternatives': [
                    {
                        'file': other.get('file', ''),
                        'status': 'deprecated' if other.get('_has_deprecated_pattern') else 'duplicate',
                        'patterns': other.get('name_patterns', [])
                    }
                    for other in others
                ]
            }
            primary_objects.append(primary)
            
            # Set up duplicates
            for other in others:
                other['is_duplicate'] = True
                other['is_primary'] = False
                other['primary_file'] = primary.get('file', '')
                other['all_files_for_object'] = [e.get('file', '') for e in entries]
                
                # Build version_suggestion for duplicate
                other['version_suggestion'] = {
                    'recommended_file': primary.get('file', ''),
                    'recommended_reason': 'Primary version without deprecated patterns' if not primary.get('_has_deprecated_pattern') else 'Primary version (highest version)',
                    'current_file_status': 'deprecated' if other.get('_has_deprecated_pattern') else 'duplicate',
                    'alternatives': []
                }
                other['customer_decision'] = 'Pending Review'
                duplicate_objects.append(other)
    
    # Add dependency info to duplicates
    if dependency_data:
        dependents_graph = dependency_data.get('dependents', {})
        dependencies_graph = dependency_data.get('dependencies', {})
        invalid_values = {'', 'N/A', 'n/a', 'NA', 'na', 'None', 'null', 'NULL'}
        
        for dup_obj in duplicate_objects:
            full_name = dup_obj.get('full_name', '')
            
            # What depends on this object (depended_by)
            if full_name in dependents_graph and dependents_graph[full_name]:
                valid_dependents = [d for d in dependents_graph[full_name] 
                                   if d and str(d).strip() not in invalid_values]
                if valid_dependents:
                    dup_obj['has_dependency_warning'] = True
                    dup_obj['depended_by'] = valid_dependents
                else:
                    dup_obj['has_dependency_warning'] = False
                    dup_obj['depended_by'] = []
            else:
                dup_obj['has_dependency_warning'] = False
                dup_obj['depended_by'] = []
            
            # What this object depends on (depends_on)
            if full_name in dependencies_graph and dependencies_graph[full_name]:
                valid_dependencies = [d for d in dependencies_graph[full_name] 
                                     if d and str(d).strip() not in invalid_values]
                dup_obj['depends_on'] = valid_dependencies
            else:
                dup_obj['depends_on'] = []
    
    if verbose:
        print(f"   Found {len(primary_objects)} unique objects")
        if duplicate_objects:
            print(f"   Found {len(duplicate_objects)} duplicate objects (same full_name, different files)")
        print()
    
    return primary_objects, duplicate_objects



class NamingConventionAnalyzer:
    """Analyzes SQL objects from SnowConvert reports for naming convention patterns"""
    
    # Temporary/Staging patterns - ordered by confidence
    TEMP_STAGING_PATTERNS = [
        r'^#',           # SQL Server local temp (highest confidence)
        r'##',           # SQL Server global temp
        r'^tmp_',        # Strong temp prefix
        r'^temp_',       # Strong temp prefix
        r'_tmp$',        # Strong temp suffix
        r'_temp$',       # Strong temp suffix
        r'^staging_',    # Strong staging prefix
        r'^stg_',        # Strong staging prefix
        r'_staging$',    # Strong staging suffix
        r'_stg$',        # Strong staging suffix
        r'^work_',       # Work prefix
        r'^wrk_',        # Work prefix
        r'_work$',       # Work suffix
        r'_wrk$',        # Work suffix
        r'^t_',          # Temporary table prefix
        r'scratch',      # Scratch keyword
        r'interim',      # Interim keyword
        r'landing',      # Landing keyword
        r'\bstg\b',     # Staging abbreviation
    ]
    
    # Deprecated/Legacy patterns - ordered by confidence
    DEPRECATED_LEGACY_PATTERNS = [
        r'_deprecated$',      # Explicit deprecated (highest confidence)
        r'_obsolete$',        # Explicit obsolete
        r'_bak_\d{6,8}$',    # Dated backup
        r'_backup_\d{6,8}$', # Dated backup
        r'_old_\d{6,8}$',    # Dated old version
        r'_old_\d{4}$',      # Year-based old version
        r'_bak$',            # Backup suffix
        r'_backup$',         # Backup suffix
        r'_old$',            # Old version suffix
        r'_archive$',        # Archive suffix
        r'_archived$',       # Archived suffix
        r'_copy\d+$',        # Numbered copy
        r'_copy$',           # Copy suffix
        r'_v\d+$',           # Version number (lower versions may be deprecated)
        r'_bak_',            # Backup infix
        r'original.*bak',    # Original + backup pattern
        r'original_slow',    # Original slow version
    ]
    
    DEPRECATED_PREFIX_PATTERNS = [
        r'^deprecated_',  # Explicit deprecated (highest confidence)
        r'^obsolete_',    # Explicit obsolete
        r'^old_',         # Old prefix
        r'^bak_',         # Backup prefix
        r'^backup_',      # Backup prefix
        r'^archive_',     # Archive prefix
    ]
    
    EXCLUSION_PATTERNS = [
        r'^old_to_new',
        r'^old_to_',
        r'^new_to_old',
        r'legacy_.*_nodes',
        r'legacy_.*_mapping',
    ]
    
    UTILITY_SCHEMAS = ['UTIL', 'UTILITY', 'HELPER', 'COMMON']
    STAGING_SCHEMAS = ['STAGING', 'STG', 'TEMP', 'TMP', 'WORK', 'WRK']
    
    # Human-readable names for patterns (used in UI display)
    PATTERN_DISPLAY_NAMES = {
        # Temp/Staging
        r'^#': 'local temp',
        r'##': 'global temp',
        r'^tmp_': 'tmp prefix',
        r'^temp_': 'temp prefix',
        r'_tmp$': 'tmp suffix',
        r'_temp$': 'temp suffix',
        r'^staging_': 'staging prefix',
        r'^stg_': 'stg prefix',
        r'_staging$': 'staging suffix',
        r'_stg$': 'stg suffix',
        r'^work_': 'work prefix',
        r'^wrk_': 'wrk prefix',
        r'_work$': 'work suffix',
        r'_wrk$': 'wrk suffix',
        r'^t_': 't prefix',
        r'scratch': 'scratch',
        r'interim': 'interim',
        r'landing': 'landing',
        r'\bstg\b': 'stg',
        # Deprecated/Legacy
        r'_deprecated$': 'deprecated',
        r'_obsolete$': 'obsolete',
        r'_bak_\d{6,8}$': 'dated backup',
        r'_backup_\d{6,8}$': 'dated backup',
        r'_old_\d{6,8}$': 'dated old',
        r'_old_\d{4}$': 'year old',
        r'_bak$': 'bak suffix',
        r'_backup$': 'backup suffix',
        r'_old$': 'old suffix',
        r'_archive$': 'archive',
        r'_archived$': 'archived',
        r'_copy\d+$': 'numbered copy',
        r'_copy$': 'copy',
        r'_v\d+$': 'versioned',
        r'_bak_': 'bak infix',
        r'original.*bak': 'original backup',
        r'original_slow': 'original slow',
        r'^deprecated_': 'deprecated prefix',
        r'^obsolete_': 'obsolete prefix',
        r'^old_': 'old prefix',
        r'^bak_': 'bak prefix',
        r'^backup_': 'backup prefix',
        r'^archive_': 'archive prefix',
        # Testing
        r'_test$': 'test',
        r'_test_': 'test',
        r'_fake$': 'fake',
        r'_fake_': 'fake',
        r'^test_': 'test',
        r'^fake_': 'fake',
        r'_demo$': 'demo',
        r'_demo_': 'demo',
        r'^demo_': 'demo',
        r'_sample$': 'sample',
        r'_sample_': 'sample',
        r'^sample_': 'sample',
        r'_dummy$': 'dummy',
        r'_dummy_': 'dummy',
        r'^dummy_': 'dummy',
        r'_mock$': 'mock',
        r'_mock_': 'mock',
        r'^mock_': 'mock',
    }
    
    TESTING_PATTERNS = [
        r'_test$',
        r'_test_',
        r'_fake$',
        r'_fake_',
        r'^test_',
        r'^fake_',
        r'_demo$',
        r'_demo_',
        r'^demo_',
        r'_sample$',
        r'_sample_',
        r'^sample_',
        r'_dummy$',
        r'_dummy_',
        r'^dummy_',
        r'_mock$',
        r'_mock_',
        r'^mock_',
    ]
    
    def __init__(self, report_directory: Path, include_staging_schema: bool = True):
        self.report_directory = report_directory
        self.include_staging_schema = include_staging_schema
        self.object_references = {}  # Stores dependency relationships
        
    def analyze(self) -> Dict[str, Any]:
        """Run naming convention analysis on SnowConvert reports"""
        
        print(f"🔍 Analyzing SnowConvert reports in: {self.report_directory}")
        
        # Read dependency relationships from ObjectReferences CSV
        self._read_object_references()
        
        # Read objects from SnowConvert report
        all_objects = self._read_snowconvert_report()
        
        if not all_objects:
            print("❌ No objects found in SnowConvert reports")
            return self._empty_results()
        
        # === STEP 1: Pattern match each entry ===
        for obj in all_objects:
            obj_name = obj.get('name', '')
            schema_upper = obj.get('schema', '').upper()
            
            # Check patterns against object name
            name_temp = self._check_temp_staging_patterns(obj_name)
            name_deprecated = self._check_deprecated_legacy_patterns(obj_name, obj.get('schema', ''), obj.get('type', ''))
            name_testing = self._check_testing_patterns(obj_name)
            
            # Store pattern results
            obj['name_patterns'] = name_temp + name_deprecated + name_testing
            
            # Categorize what type of patterns were matched
            obj['_has_temp_pattern'] = bool(name_temp or (self.include_staging_schema and schema_upper in self.STAGING_SCHEMAS))
            obj['_has_deprecated_pattern'] = bool(name_deprecated)
            obj['_has_testing_pattern'] = bool(name_testing)
        
        # === STEP 2 & 3: Detect duplicates and pick primary versions ===
        dependency_data = self.object_references if self.object_references else None
        primary_objects, duplicate_objects = analyze_duplicate_objects(
            all_objects, 
            dependency_data=dependency_data,
            verbose=True
        )
        
        # === STEP 4: Classify primary objects into categories ===
        temp_staging_objects = []
        deprecated_legacy_objects = []
        testing_objects = []
        
        def get_display_names(patterns: List[str]) -> List[str]:
            """Convert regex patterns to human-readable display names"""
            display_names = []
            for p in patterns:
                if p.startswith('schema:'):
                    # Keep schema patterns as lowercase
                    display_names.append(p.replace('schema:', 'schema: ').lower())
                else:
                    display_names.append(self.PATTERN_DISPLAY_NAMES.get(p, p))
            return display_names
        
        for obj in primary_objects:
            obj_name = obj.get('name', '')
            schema_upper = obj.get('schema', '').upper()
            is_staging_schema = self.include_staging_schema and schema_upper in self.STAGING_SCHEMAS
            
            obj['customer_decision'] = 'Pending Review'
            
            if obj.get('_has_temp_pattern'):
                obj_copy = obj.copy()
                # Build matched_patterns with display names
                temp_patterns = self._check_temp_staging_patterns(obj_name)
                if is_staging_schema and not temp_patterns:
                    obj_copy['matched_patterns'] = [f"schema: {schema_upper.lower()}"]
                elif temp_patterns:
                    display_patterns = get_display_names(temp_patterns)
                    if is_staging_schema:
                        obj_copy['matched_patterns'] = display_patterns + [f"schema: {schema_upper.lower()}"]
                    else:
                        obj_copy['matched_patterns'] = display_patterns
                temp_staging_objects.append(obj_copy)
            
            if obj.get('_has_deprecated_pattern'):
                obj_copy = obj.copy()
                deprecated_patterns = self._check_deprecated_legacy_patterns(obj_name, obj.get('schema', ''), obj.get('type', ''))
                display_patterns = get_display_names(deprecated_patterns)
                if is_staging_schema and f"schema: {schema_upper.lower()}" not in display_patterns:
                    display_patterns.append(f"schema: {schema_upper.lower()}")
                obj_copy['matched_patterns'] = display_patterns
                deprecated_legacy_objects.append(obj_copy)
            
            if obj.get('_has_testing_pattern'):
                obj_copy = obj.copy()
                testing_patterns = self._check_testing_patterns(obj_name)
                display_patterns = get_display_names(testing_patterns)
                if is_staging_schema and f"schema: {schema_upper.lower()}" not in display_patterns:
                    display_patterns.append(f"schema: {schema_upper.lower()}")
                obj_copy['matched_patterns'] = display_patterns
                obj_copy['testing_reason'] = self._get_testing_reason(obj_name, testing_patterns)
                testing_objects.append(obj_copy)
        
        # === STEP 5: Calculate schema statistics ===
        objects_by_schema = defaultdict(int)
        for obj in primary_objects:
            schema = obj.get('schema', 'unknown')
            objects_by_schema[schema] += 1
        
        schema_stats = [
            {"schema": schema, "object_count": count}
            for schema, count in sorted(objects_by_schema.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # === STEP 6: Version analysis (for objects with _v1, _v2, etc. in name) ===
        version_analysis = self._identify_production_versions(primary_objects)
        
        # === STEP 7: Dependency analysis ===
        dependency_analysis = self._analyze_dependency_impact(
            deprecated_legacy_objects, 
            temp_staging_objects,
            testing_objects,
            primary_objects
        )
        
        # Add dependency info to ALL objects (what they depend on and what depends on them)
        self._add_dependency_details_to_objects(
            primary_objects,
            deprecated_legacy_objects,
            temp_staging_objects,
            testing_objects,
            dependency_analysis
        )
        
        # Add version and caller info to deprecated objects only
        # (Version analysis is only relevant for deprecated objects to suggest production versions)
        for obj in deprecated_legacy_objects:
            full_name = obj.get('full_name', '')
            if full_name in version_analysis['production_versions']:
                obj['production_version'] = version_analysis['production_versions'][full_name]['production_version']
                obj['production_name'] = version_analysis['production_versions'][full_name]['production_name']
            if full_name in dependency_analysis['potentially_normal_objects']:
                obj['dependency_validation'] = dependency_analysis['potentially_normal_objects'][full_name]
        
        # === STEP 8: Build results ===
        # Count unique objects with duplicates (not duplicate file entries)
        unique_duplicate_objects = len(set(obj.get('full_name', '') for obj in duplicate_objects))
        
        results = {
            "summary": {
                "report_directory": str(self.report_directory.absolute()),
                "total_objects_found": len(primary_objects),
                "temp_staging_objects_count": len(temp_staging_objects),
                "deprecated_legacy_objects_count": len(deprecated_legacy_objects),
                "testing_objects_count": len(testing_objects),
                "duplicate_objects_count": len(duplicate_objects),
                "unique_duplicate_objects_count": unique_duplicate_objects,
                "objects_by_schema": schema_stats,
                "objects_with_multiple_versions": len(version_analysis['version_mapping']),
                "potentially_normal_objects_count": len(dependency_analysis['potentially_normal_objects']),
                "has_dependency_data": dependency_analysis['has_dependency_data']
            },
            "temporary_staging_objects": temp_staging_objects,
            "deprecated_legacy_objects": deprecated_legacy_objects,
            "testing_objects": testing_objects,
            "duplicate_objects": duplicate_objects,
            "version_analysis": {
                "objects_with_versions": version_analysis['version_mapping'],
                "total_object_groups": len(version_analysis['version_mapping']),
                "description": "Groups of objects with multiple versions (deprecated/versioned/backup variants). The production_version is the object that should be migrated."
            },
            "dependency_analysis": {
                "potentially_normal_objects": dependency_analysis['potentially_normal_objects'],
                "has_dependency_data": dependency_analysis['has_dependency_data'],
                "description": "Analysis of objects based on their dependency relationships. Dependency details are included in each object."
            },
            "naming_pattern_definitions": {
                "temporary_staging_patterns": self.TEMP_STAGING_PATTERNS,
                "deprecated_legacy_patterns": self.DEPRECATED_LEGACY_PATTERNS,
                "testing_patterns": self.TESTING_PATTERNS,
                "exclusion_patterns": self.EXCLUSION_PATTERNS,
                "staging_schemas": self.STAGING_SCHEMAS if self.include_staging_schema else []
            }
        }
        
        return results
    
    def _read_object_references(self) -> None:
        """Read dependency relationships from ObjectReferences CSV"""
        # Try to find ObjectReferences CSV file (with or without timestamp)
        # Pattern: ObjectReferences.NA.csv or ObjectReferences.YYYYMMDD.HHMMSS.csv
        object_ref_files = list(self.report_directory.glob("ObjectReferences*.csv"))
        
        if not object_ref_files:
            print(f"  ⚠️  No ObjectReferences CSV found (optional for dependency analysis)")
            self.object_references = {}
            return
        
        # Use the most recent one if multiple exist
        ref_file = sorted(object_ref_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        print(f"  📎 Reading dependencies from: {ref_file.name}")
        
        # Build dependency graph: caller -> [list of referenced objects]
        # and reverse graph: referenced -> [list of callers]
        dependencies = defaultdict(set)  # caller -> set of referenced
        dependents = defaultdict(set)    # referenced -> set of callers
        
        encodings = ['utf-8-sig', 'utf-8', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(ref_file, 'r', encoding=encoding, newline='') as f:
                    reader = csv.DictReader(f)
                    row_count = 0
                    
                    # Invalid values to skip
                    invalid_values = {'', 'N/A', 'n/a', 'NA', 'na', 'None', 'null', 'NULL'}
                    
                    for row in reader:
                        caller = row.get('Caller_CodeUnit_FullName', '').strip()
                        referenced = row.get('Referenced_Element_FullName', '').strip()
                        
                        # Remove brackets to match TopLevelCodeUnits format
                        caller = caller.replace('[', '').replace(']', '')
                        referenced = referenced.replace('[', '').replace(']', '')
                        
                        # Skip invalid values
                        if caller in invalid_values or referenced in invalid_values:
                            continue
                        
                        if caller and referenced and caller != referenced:
                            dependencies[caller].add(referenced)
                            dependents[referenced].add(caller)
                            row_count += 1
                
                self.object_references = {
                    'dependencies': dependencies,
                    'dependents': dependents
                }
                print(f"     Loaded {row_count} dependency relationships ({encoding})")
                break
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"  ⚠️  Error reading ObjectReferences: {e}")
                return
    
    def _read_snowconvert_report(self) -> List[Dict[str, Any]]:
        """Read objects from SnowConvert TopLevelCodeUnits.*.csv report
        
        Uses direct CSV columns:
        - CodeUnit: Filter for CREATE statements only
        - Category: Object type (TABLE, VIEW, PROCEDURE, FUNCTION)
        - CodeUnitId: Full qualified name (e.g., [DB].[Schema].[Name])
        - SourceDatabase, SourceSchema, CodeUnitName: Object metadata
        """
        
        # Find TopLevelCodeUnits file with any timestamp
        matching_files = list(self.report_directory.glob("TopLevelCodeUnits.*.csv"))
        
        if not matching_files:
            print(f"❌ Error: No TopLevelCodeUnits.*.csv found in {self.report_directory}")
            return []
        
        report_file = matching_files[0]
        print(f"📄 Reading: {report_file.name}")
        
        objects = []
        encodings = ['utf-8-sig', 'utf-8', 'latin-1']
        
        def clean_brackets(value: str) -> str:
            """Remove SQL Server bracket notation and clean whitespace"""
            if not value:
                return ''
            return value.replace('[', '').replace(']', '').strip()
        
        for encoding in encodings:
            try:
                with open(report_file, 'r', encoding=encoding, newline='') as f:
                    reader = csv.DictReader(f)
                    
                    for row in reader:
                        # Only process CREATE statements (skip ALTER, DROP, etc.)
                        code_unit = row.get('CodeUnit', '').upper()
                        if not code_unit.startswith('CREATE'):
                            continue
                        
                        # Get object type from Category field
                        obj_type = row.get('Category', '').upper()
                        
                        # Only process specific object types (tables, views, procedures, functions)
                        allowed_types = {'TABLE', 'VIEW', 'PROCEDURE', 'FUNCTION'}
                        if obj_type not in allowed_types:
                            continue
                        
                        # Use CodeUnitId directly for full_name
                        code_unit_id = clean_brackets(row.get('CodeUnitId', ''))
                        if not code_unit_id or code_unit_id == 'N/A':
                            continue
                        
                        # Remove procedure/function parameter list suffix like "()"
                        if '(' in code_unit_id:
                            code_unit_id = code_unit_id.split('(')[0]
                        
                        # Get object name from CodeUnitName
                        obj_name = clean_brackets(row.get('CodeUnitName', ''))
                        if not obj_name or obj_name == 'N/A':
                            continue
                        
                        # Remove parameter list from object name
                        if '(' in obj_name:
                            obj_name = obj_name.split('(')[0]
                        
                        # Skip SnowConvert parse error entries (e.g., "Error-PROCEDURE", "Error-FUNCTION")
                        # These occur when SnowConvert fails to parse an object
                        if obj_name.startswith('Error-'):
                            continue
                        
                        # Get schema from SourceSchema
                        schema = clean_brackets(row.get('SourceSchema', ''))
                        if not schema or schema == 'N/A':
                            schema = 'dbo'
                        
                        # Get database from SourceDatabase
                        database = clean_brackets(row.get('SourceDatabase', ''))
                        if database == 'N/A':
                            database = ''
                        
                        # Get source file for reference
                        source_file = row.get('FileName', '')
                        
                        objects.append({
                            "name": obj_name,
                            "full_name": code_unit_id,
                            "schema": schema,
                            "database": database,
                            "type": obj_type,
                            "source": "SnowConvert Report",
                            "file": source_file,
                            "report_file": report_file.name
                        })
                
                print(f"  ✅ Parsed {report_file.name}: {len(objects)} objects ({encoding})")
                break
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"  ❌ Error reading {report_file.name}: {e}", file=sys.stderr)
                return []
        
        return objects
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure"""
        return {
            "summary": {
                "report_directory": str(self.report_directory.absolute()),
                "total_objects_found": 0,
                "temp_staging_objects_count": 0,
                "deprecated_legacy_objects_count": 0,
                "testing_objects_count": 0,
                "duplicate_objects_count": 0,
                "unique_duplicate_objects_count": 0,
                "objects_by_schema": [],
                "objects_with_multiple_versions": 0,
                "potentially_normal_objects_count": 0,
                "has_dependency_data": False
            },
            "temporary_staging_objects": [],
            "deprecated_legacy_objects": [],
            "testing_objects": [],
            "duplicate_objects": [],
            "version_analysis": {
                "objects_with_versions": [],
                "total_object_groups": 0,
                "description": "No objects found"
            },
            "dependency_analysis": {
                "potentially_normal_objects": {},
                "has_dependency_data": False,
                "description": "No objects found"
            },
            "naming_pattern_definitions": {
                "temporary_staging_patterns": self.TEMP_STAGING_PATTERNS,
                "deprecated_legacy_patterns": self.DEPRECATED_LEGACY_PATTERNS,
                "testing_patterns": self.TESTING_PATTERNS,
                "exclusion_patterns": self.EXCLUSION_PATTERNS,
                "staging_schemas": self.STAGING_SCHEMAS if self.include_staging_schema else []
            }
        }
    
    def _check_temp_staging_patterns(self, obj_name: str) -> List[str]:
        """Check if object name matches temp/staging patterns"""
        matched = []
        obj_lower = obj_name.lower()
        
        for pattern in self.TEMP_STAGING_PATTERNS:
            if re.search(pattern, obj_lower, re.IGNORECASE):
                matched.append(pattern)
        
        return matched
    
    def _check_deprecated_legacy_patterns(self, obj_name: str, schema: str = '', obj_type: str = '') -> List[str]:
        """Check if object name matches deprecated/legacy patterns with exclusions"""
        matched = []
        obj_lower = obj_name.lower()
        schema_upper = schema.upper() if schema else ''
        
        # Check exclusion patterns first
        for exclusion_pattern in self.EXCLUSION_PATTERNS:
            if re.search(exclusion_pattern, obj_lower, re.IGNORECASE):
                return []
        
        # Check suffix patterns
        for pattern in self.DEPRECATED_LEGACY_PATTERNS:
            if re.search(pattern, obj_lower, re.IGNORECASE):
                matched.append(pattern)
        
        # Check prefix patterns (conservative)
        is_utility_schema = schema_upper in self.UTILITY_SCHEMAS
        is_table = obj_type.upper() == 'TABLE'
        
        if not is_utility_schema or is_table:
            for pattern in self.DEPRECATED_PREFIX_PATTERNS:
                if re.search(pattern, obj_lower, re.IGNORECASE):
                    if not re.search(r'^old_to_|^new_to_old', obj_lower, re.IGNORECASE):
                        matched.append(pattern)
        
        return matched
    
    def _check_testing_patterns(self, obj_name: str) -> List[str]:
        """Check if object name matches testing patterns (test, fake, mock, demo, sample, dummy)"""
        matched = []
        obj_lower = obj_name.lower()
        
        for pattern in self.TESTING_PATTERNS:
            if re.search(pattern, obj_lower, re.IGNORECASE):
                matched.append(pattern)
        
        return matched
    
    def _get_base_object_name(self, obj_name: str) -> str:
        """Extract base object name by removing version/date/backup/test suffixes"""
        base_name = obj_name.lower()
        
        patterns_to_strip = [
            r'_bak_\d{6,8}$',
            r'_old_\d{6,8}$',
            r'_backup_\d{6,8}$',
            r'_old_\d{4}$',
            r'_v\d+$',       # _v1, _v2, _v3, etc.
            r'_v$',          # _v (version suffix without number)
            r'_copy\d+$',
            r'_bak_$',
            r'_old$',
            r'_bak$',
            r'_backup$',
            r'_archive$',
            r'_archived$',
            r'_deprecated$',
            r'_obsolete$',
            r'_copy$',
            r'_test$',
            r'_fake$',
            r'_demo$',
            r'_sample$',
            r'_dummy$',
            r'_mock$',
            r'_test_.*$',
            r'_fake_.*$',
        ]
        
        if 'original' in base_name and 'bak' in base_name:
            base_name = re.sub(r'_original.*', '', base_name)
        if 'original' in base_name and 'slow' in base_name:
            base_name = re.sub(r'_original.*', '', base_name)
        
        for pattern in patterns_to_strip:
            base_name = re.sub(pattern, '', base_name)
        
        return base_name
    
    def _identify_production_versions(self, all_objects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify production versions of objects that have deprecated/versioned variants"""
        
        object_groups = defaultdict(list)
        for obj in all_objects:
            base_name = self._get_base_object_name(obj['name'])
            schema = obj.get('schema', 'unknown')
            obj_type = obj.get('type', 'unknown')
            key = f"{schema}.{base_name}.{obj_type}"
            object_groups[key].append(obj)
        
        version_mapping = []
        production_versions = {}
        
        for key, objects in object_groups.items():
            if len(objects) > 1:
                def get_priority(obj):
                    name = obj['name'].lower()
                    
                    # Base name without any suffix (highest priority)
                    if name == self._get_base_object_name(name):
                        return 0
                    
                    # Test/demo objects (lowest priority)
                    if any(pattern in name for pattern in ['_test', '_fake', '_demo', '_sample', '_dummy', '_mock']):
                        return 1000
                    
                    # Backup/archive objects (very low priority)
                    if any(pattern in name for pattern in ['_bak', '_backup', '_archive', '_old', '_copy']):
                        return 900
                    
                    # Version with number: _v1, _v2, _v3, etc.
                    # Higher numbers = newer = higher priority (lower score)
                    version_match = re.search(r'_v(\d+)$', name)
                    if version_match:
                        version_num = int(version_match.group(1))
                        return 100 - version_num
                    
                    # Version suffix without number: _v (treated as latest version)
                    # Priority between base name and versioned names
                    if name.endswith('_v'):
                        return 50
                    
                    # Date patterns (older dates = lower priority)
                    date_match = re.search(r'_(\d{6,8})$', name)
                    if date_match:
                        date_str = date_match.group(1)
                        return 200 - int(date_str) / 100000000
                    
                    return 500
                
                sorted_objects = sorted(objects, key=get_priority)
                production_obj = sorted_objects[0]
                other_versions = sorted_objects[1:]
                
                parts = key.split('.')
                mapping_entry = {
                    "base_name": parts[1],
                    "schema": parts[0],
                    "type": parts[2],
                    "production_version": production_obj['name'],
                    "production_full_name": production_obj['full_name'],
                    "production_file": production_obj.get('file', ''),
                    "deprecated_versions": [
                        {
                            "name": obj['name'],
                            "full_name": obj['full_name'],
                            "file": obj.get('file', '')
                        }
                        for obj in other_versions
                    ],
                    "total_versions": len(objects)
                }
                version_mapping.append(mapping_entry)
                
                for obj in other_versions:
                    production_versions[obj['full_name']] = {
                        "production_version": production_obj['full_name'],
                        "production_name": production_obj['name'],
                        "production_file": production_obj.get('file', '')
                    }
        
        return {
            "version_mapping": sorted(version_mapping, key=lambda x: (x['schema'], x['base_name'])),
            "production_versions": production_versions
        }
    
    def _analyze_dependency_impact(
        self, 
        deprecated_objects: List[Dict[str, Any]],
        temp_staging_objects: List[Dict[str, Any]],
        testing_objects: List[Dict[str, Any]],
        all_objects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze dependency impact for deprecated/outdated objects.
        
        Returns:
        - potentially_normal_objects: Deprecated objects heavily referenced by normal objects
        """
        if not self.object_references or not self.object_references.get('dependents'):
            return {
                'potentially_normal_objects': {},
                'has_dependency_data': False
            }
        
        dependents_graph = self.object_references['dependents']
        dependencies_graph = self.object_references['dependencies']
        
        # Build sets of problematic object full names
        deprecated_names = {obj['full_name'] for obj in deprecated_objects}
        temp_staging_names = {obj['full_name'] for obj in temp_staging_objects}
        testing_names = {obj['full_name'] for obj in testing_objects}
        problematic_names = deprecated_names | temp_staging_names | testing_names
        
        # Build a map of all objects for quick lookup
        all_objects_map = {obj['full_name']: obj for obj in all_objects}
        
        # Find deprecated objects that are heavily referenced by normal objects
        # (might be incorrectly classified as deprecated)
        potentially_normal_objects = {}
        
        NORMAL_DEPENDENT_THRESHOLD = 3  # If 3+ normal objects depend on it, flag for review
        
        for dep_name in deprecated_names:
            if dep_name in dependents_graph:
                dependent_names = dependents_graph[dep_name]
                
                # Count how many normal (non-problematic) objects depend on this
                normal_dependents = [
                    d for d in dependent_names 
                    if d not in problematic_names
                ]
                
                if len(normal_dependents) >= NORMAL_DEPENDENT_THRESHOLD:
                    potentially_normal_objects[dep_name] = {
                        'normal_dependent_count': len(normal_dependents),
                        'normal_dependents': list(normal_dependents)[:10],  # Show first 10
                        'total_dependent_count': len(dependent_names),
                        'validation_message': f"⚠️ This object is referenced by {len(normal_dependents)} normal objects. Review to confirm it should be deprecated."
                    }
        
        print(f"\n  🔗 Dependency Analysis:")
        print(f"     Found {len(potentially_normal_objects)} deprecated objects that may actually be normal")
        
        return {
            'potentially_normal_objects': potentially_normal_objects,
            'has_dependency_data': True
        }
    
    def _add_dependency_details_to_objects(
        self,
        all_objects: List[Dict[str, Any]],
        deprecated_objects: List[Dict[str, Any]],
        temp_staging_objects: List[Dict[str, Any]],
        testing_objects: List[Dict[str, Any]],
        dependency_analysis: Dict[str, Any]
    ) -> None:
        """
        Add dependency details to each object showing what it depends on and what depends on it.
        """
        if not self.object_references:
            return
        
        dependents_graph = self.object_references.get('dependents', {})
        dependencies_graph = self.object_references.get('dependencies', {})
        
        # Build a map of all objects for quick lookup
        all_objects_map = {obj['full_name']: obj for obj in all_objects}
        
        # Build sets of categorized object names for classification
        deprecated_names = {obj['full_name'] for obj in deprecated_objects}
        temp_staging_names = {obj['full_name'] for obj in temp_staging_objects}
        testing_names = {obj['full_name'] for obj in testing_objects}
        
        def get_object_category(full_name: str) -> str:
            """Get the category of an object"""
            if full_name in deprecated_names:
                return 'deprecated'
            elif full_name in temp_staging_names:
                return 'temp_staging'
            elif full_name in testing_names:
                return 'testing'
            else:
                return 'normal'
        
        def build_dependency_detail(full_name: str) -> Dict[str, Any]:
            """Build detailed dependency info for an object reference"""
            if full_name in all_objects_map:
                obj = all_objects_map[full_name]
                return {
                    'full_name': full_name,
                    'name': obj.get('name', ''),
                    'schema': obj.get('schema', ''),
                    'type': obj.get('type', ''),
                    'category': get_object_category(full_name)
                }
            else:
                # External reference not in our analyzed objects
                parts = full_name.split('.')
                return {
                    'full_name': full_name,
                    'name': parts[-1] if parts else full_name,
                    'schema': parts[-2] if len(parts) >= 2 else 'unknown',
                    'type': 'EXTERNAL',
                    'category': 'external'
                }
        
        # Add dependency info to all categorized objects
        all_categorized = deprecated_objects + temp_staging_objects + testing_objects
        
        for obj in all_categorized:
            full_name = obj.get('full_name', '')
            
            # What this object depends on (calls/references)
            depends_on = []
            if full_name in dependencies_graph:
                for ref_name in dependencies_graph[full_name]:
                    depends_on.append(build_dependency_detail(ref_name))
            
            # What depends on this object (callers)
            depended_by = []
            if full_name in dependents_graph:
                for caller_name in dependents_graph[full_name]:
                    depended_by.append(build_dependency_detail(caller_name))
            
            # Add to object - detailed info in 'dependencies', simple lists for display
            obj['dependencies'] = {
                'depends_on': depends_on,
                'depends_on_count': len(depends_on),
                'depended_by': depended_by,
                'depended_by_count': len(depended_by)
            }
            # Simple lists of names for display (same format as duplicates)
            obj['depends_on'] = [d['full_name'] for d in depends_on]
            obj['depended_by'] = [d['full_name'] for d in depended_by]
    
    def _get_testing_reason(self, obj_name: str, patterns: List[str]) -> str:
        """Get a human-readable reason why the object is identified as testing"""
        reasons = []
        
        if any('test' in p for p in patterns):
            reasons.append("Contains 'test' pattern")
        if any('fake' in p for p in patterns):
            reasons.append("Contains 'fake' pattern")
        if any('demo' in p for p in patterns):
            reasons.append("Contains 'demo' pattern")
        if any('sample' in p for p in patterns):
            reasons.append("Contains 'sample' pattern")
        if any('dummy' in p for p in patterns):
            reasons.append("Contains 'dummy' pattern")
        if any('mock' in p for p in patterns):
            reasons.append("Contains 'mock' pattern")
        
        return "; ".join(reasons) if reasons else "Matches testing pattern"


def _get_base_object_name_standalone(name: str) -> str:
    """Get base name of object, stripping version suffixes, date suffixes, etc."""
    base_name = name.lower()
    
    patterns_to_strip = [
        r'_\d{6,8}$',   # Date suffixes like _20230101
        r'_v\d+$',      # _v1, _v2, _v3, etc.
        r'_v$',         # _v (version suffix without number)
        r'_copy\d+$',
        r'_bak_$',
        r'_old$',
        r'_bak$',
        r'_backup$',
        r'_archive$',
        r'_archived$',
        r'_deprecated$',
        r'_obsolete$',
        r'_copy$',
        r'_test$',
        r'_fake$',
        r'_demo$',
        r'_sample$',
        r'_dummy$',
        r'_mock$',
        r'_test_.*$',
        r'_fake_.*$',
    ]
    
    if 'original' in base_name and 'bak' in base_name:
        base_name = re.sub(r'_original.*', '', base_name)
    if 'original' in base_name and 'slow' in base_name:
        base_name = re.sub(r'_original.*', '', base_name)
    
    for pattern in patterns_to_strip:
        base_name = re.sub(pattern, '', base_name)
    
    return base_name


def identify_production_versions_standalone(all_objects: List[Dict]) -> Dict[str, Any]:
    """Identify production versions of objects that have deprecated/versioned variants"""
    
    object_groups = defaultdict(list)
    for obj in all_objects:
        base_name = _get_base_object_name_standalone(obj['name'])
        schema = obj.get('schema', 'unknown')
        obj_type = obj.get('type', 'unknown')
        key = f"{schema}.{base_name}.{obj_type}"
        object_groups[key].append(obj)
    
    version_mapping = []
    production_versions = {}
    
    for key, objects in object_groups.items():
        if len(objects) > 1:
            def get_priority(obj):
                name = obj['name'].lower()
                
                # Base name without any suffix (highest priority)
                if name == _get_base_object_name_standalone(name):
                    return 0
                
                # Test/demo objects (lowest priority)
                if any(pattern in name for pattern in ['_test', '_fake', '_demo', '_sample', '_dummy', '_mock']):
                    return 1000
                
                # Backup/archive objects (very low priority)
                if any(pattern in name for pattern in ['_bak', '_backup', '_archive', '_old', '_copy']):
                    return 900
                
                # Version with number: _v1, _v2, _v3, etc.
                version_match = re.search(r'_v(\d+)$', name)
                if version_match:
                    version_num = int(version_match.group(1))
                    return 100 - version_num
                
                # Version suffix without number: _v (treated as latest version)
                if name.endswith('_v'):
                    return 50
                
                # Date patterns (older dates = lower priority)
                date_match = re.search(r'_(\d{6,8})$', name)
                if date_match:
                    date_str = date_match.group(1)
                    return 200 - int(date_str) / 100000000
                
                return 500
            
            sorted_objects = sorted(objects, key=get_priority)
            production_obj = sorted_objects[0]
            other_versions = sorted_objects[1:]
            
            parts = key.split('.')
            mapping_entry = {
                "base_name": parts[1],
                "schema": parts[0],
                "type": parts[2],
                "production_version": production_obj['name'],
                "production_full_name": production_obj['full_name'],
                "production_file": production_obj.get('file', ''),
                "deprecated_versions": [
                    {
                        "name": obj['name'],
                        "full_name": obj['full_name'],
                        "file": obj.get('file', '')
                    }
                    for obj in other_versions
                ],
                "total_versions": len(objects)
            }
            version_mapping.append(mapping_entry)
            
            for obj in other_versions:
                production_versions[obj['full_name']] = {
                    "production_version": production_obj['full_name'],
                    "production_name": production_obj['name'],
                    "production_file": production_obj.get('file', '')
                }
    
    return {
        "version_mapping": sorted(version_mapping, key=lambda x: (x['schema'], x['base_name'])),
        "production_versions": production_versions
    }


def main():
    from datetime import datetime
    
    parser = argparse.ArgumentParser(
        description='Analyze SnowConvert reports for naming conventions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze SnowConvert reports
  python analyze_naming_conventions.py -r /path/to/SnowConvert/Reports -d ./analysis-output
  
  # Exclude staging schema detection
  python analyze_naming_conventions.py -r /path/to/Reports -d ./output --exclude-staging-schema
  
  # Skip HTML report generation
  python analyze_naming_conventions.py -r /path/to/Reports -d ./output --no-html
"""
    )
    
    parser.add_argument(
        '--reports', '-r',
        required=True,
        help='Path to SnowConvert Reports directory (containing TopLevelCodeUnits.*.csv)'
    )
    
    parser.add_argument(
        '--output-dir', '-d',
        required=True,
        help='Output directory for results (creates timestamped subdirectory)'
    )
    
    parser.add_argument(
        '--include-staging-schema',
        action='store_true',
        default=True,
        help='Include all objects in Staging/Temp schemas as temporary/staging objects (default: True)'
    )
    
    parser.add_argument(
        '--exclude-staging-schema',
        action='store_true',
        help='Exclude objects in Staging/Temp schemas (only match explicit naming patterns)'
    )
    
    parser.add_argument(
        '--no-html',
        action='store_true',
        help='Skip HTML report generation (only generate JSON output)'
    )
    
    args = parser.parse_args()
    
    report_dir = Path(args.reports)
    output_base_dir = Path(args.output_dir)
    
    if not report_dir.exists():
        print(f"❌ Error: Reports directory not found: {report_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Validate that required report files exist BEFORE creating output directory
    matching_files = list(report_dir.glob("TopLevelCodeUnits.*.csv"))
    if not matching_files:
        print(f"❌ Error: No TopLevelCodeUnits.*.csv found in {report_dir}", file=sys.stderr)
        print(f"   Please ensure the SnowConvert reports directory contains TopLevelCodeUnits.NA.csv or TopLevelCodeUnits.<timestamp>.csv", file=sys.stderr)
        sys.exit(1)
    
    print(f"📄 Found report file: {matching_files[0].name}")
    
    # Create timestamped output directory (like waves-generator)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = output_base_dir / f'exclusion_analysis_{timestamp}'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    include_staging = args.include_staging_schema and not args.exclude_staging_schema
    
    print("📋 Using Pattern-based Analyzer")
    analyzer = NamingConventionAnalyzer(report_dir, include_staging_schema=include_staging)
    results = analyzer.analyze()
    
    # Output files in timestamped directory
    output_file = output_dir / 'naming_conventions.json'
    html_output = output_dir / 'exclusion_analysis_report.html'
    summary_output = output_dir / 'analysis_summary.txt'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Generate summary text file
    analyzer_type = results['summary'].get('analyzer_type', 'pattern-based')
    duplicate_count = results['summary'].get('duplicate_objects_count', 0)
    summary_text = f"""Object Exclusion Analysis Summary
{'='*60}
Analyzer Type: {analyzer_type}
Report Directory: {report_dir}
Analysis Timestamp: {timestamp}

Results:
  Total Objects: {results['summary']['total_objects_found']}
  Temp/Staging Objects: {results['summary']['temp_staging_objects_count']}
  Deprecated/Legacy Objects: {results['summary']['deprecated_legacy_objects_count']}
  Testing Objects: {results['summary']['testing_objects_count']}
  Duplicate Objects: {duplicate_count}
"""
    if 'workload_type' in results['summary']:
        summary_text += f"  Detected Workload: {results['summary']['workload_type']}\n"
    
    summary_text += f"""
Output Files:
  JSON: {output_file.name}
  HTML: {html_output.name}
  Summary: {summary_output.name}
{'='*60}
"""
    
    with open(summary_output, 'w', encoding='utf-8') as f:
        f.write(summary_text)
    
    print(f"\n{'='*60}")
    print(f"📊 Object Exclusion Analysis Summary ({analyzer_type}):")
    print(f"  Report Directory: {report_dir.name}")
    print(f"  Total Objects: {results['summary']['total_objects_found']}")
    if 'workload_type' in results['summary']:
        print(f"  Detected Workload: {results['summary']['workload_type']}")
    print(f"  Temp/Staging Objects: {results['summary']['temp_staging_objects_count']}")
    print(f"  Deprecated/Legacy Objects: {results['summary']['deprecated_legacy_objects_count']}")
    print(f"  Testing Objects: {results['summary']['testing_objects_count']}")
    print(f"  Duplicate Objects: {duplicate_count}")
    print(f"{'='*60}\n")
    print(f"✅ Results written to: {output_dir.absolute()}/")
    print(f"   - {output_file.name}")
    print(f"   - {summary_output.name}")
    
    # Automatically generate HTML report unless disabled
    if not args.no_html:
        try:
            import importlib.util
            script_dir = Path(__file__).parent
            html_script_path = script_dir / 'generate_html_report.py'
            
            if html_script_path.exists():
                spec = importlib.util.spec_from_file_location("generate_html_report", html_script_path)
                html_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(html_module)
                
                html_module.generate_html_report(output_file, html_output)
                print(f"   - {html_output.name}")
            else:
                print(f"⚠️  HTML report generator not found, skipping HTML generation")
        except Exception as e:
            print(f"⚠️  Error generating HTML report: {e}")
            print(f"   You can generate it manually with:")
            print(f"   python scripts/generate_html_report.py {output_file} --output {html_output}")


if __name__ == "__main__":
    main()