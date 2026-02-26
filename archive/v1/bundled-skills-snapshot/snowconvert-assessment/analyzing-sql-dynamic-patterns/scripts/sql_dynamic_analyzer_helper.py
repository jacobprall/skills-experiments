#!/usr/bin/env python3
"""
SQL Dynamic Analysis Helper

Analyzes SnowConvert Issues.csv file to identify and track SQL Dynamic patterns (SSC-EWI-0030).
Generates a tracking JSON for manual classification and complexity assessment.
Supports updating individual records with status, category, complexity, and notes.
"""

import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Issue code for dynamic SQL patterns
DYNAMIC_SQL_ISSUE_CODE = "SSC-EWI-0030"


@dataclass
class Issue:
    """Represents a SnowConvert issue from Issues.csv."""
    session_id: str
    severity: str
    code: str
    name: str
    description: str
    parent_file: str
    line: int
    column: int
    code_unit_database: str
    code_unit_schema: str
    code_unit_package: str
    code_unit_name: str
    code_unit_id: str
    code_unit: str
    code_unit_size: str
    source_language: str
    migration_id: str

    @staticmethod
    def from_csv_row(row: Dict[str, str]) -> 'Issue':
        """Create Issue from CSV row."""
        return Issue(
            session_id=row.get('SessionID', '').strip(),
            severity=row.get('Severity', '').strip(),
            code=row.get('Code', '').strip(),
            name=row.get('Name', '').strip(),
            description=row.get('Description', '').strip(),
            parent_file=row.get('ParentFile', '').strip(),
            line=int(row.get('Line', '0')) if row.get('Line', '').strip() else 0,
            column=int(row.get('Column', '0')) if row.get('Column', '').strip() else 0,
            code_unit_database=row.get('Code Unit Database', '').strip(),
            code_unit_schema=row.get('Code Unit Schema', '').strip(),
            code_unit_package=row.get('Code Unit Package', '').strip(),
            code_unit_name=row.get('Code Unit Name', '').strip(),
            code_unit_id=row.get('Code Unit Id', '').strip(),
            code_unit=row.get('Code Unit', '').strip(),
            code_unit_size=row.get('Code Unit Size', '').strip(),
            source_language=row.get('SourceLanguage', '').strip(),
            migration_id=row.get('MigrationID', '').strip()
        )


@dataclass
class TopLevelCodeUnit:
    """Represents a top-level code unit from TopLevelCodeUnits.csv."""
    partition_key: str
    file_type: str
    category: str
    code_unit: str
    source_database: str
    source_schema: str
    code_unit_name: str
    code_unit_id: str
    snowflake_database: str
    snowflake_schema: str
    snowflake_name: str
    file_name: str
    line_number: int
    lines_of_code: int
    
    @staticmethod
    def from_csv_row(row: Dict[str, str]) -> 'TopLevelCodeUnit':
        """Create TopLevelCodeUnit from CSV row."""
        return TopLevelCodeUnit(
            partition_key=row.get('PartitionKey', '').strip(),
            file_type=row.get('FileType', '').strip(),
            category=row.get('Category', '').strip(),
            code_unit=row.get('CodeUnit', '').strip(),
            source_database=row.get('SourceDatabase', '').strip(),
            source_schema=row.get('SourceSchema', '').strip(),
            code_unit_name=row.get('CodeUnitName', '').strip(),
            code_unit_id=row.get('CodeUnitId', '').strip(),
            snowflake_database=row.get('SnowflakeDatabase', '').strip(),
            snowflake_schema=row.get('SnowflakeSchema', '').strip(),
            snowflake_name=row.get('SnowflakeName', '').strip(),
            file_name=row.get('FileName', '').strip(),
            line_number=int(row.get('LineNumber', '0')) if row.get('LineNumber', '').strip() else 0,
            lines_of_code=int(row.get('LinesOfCode', '0')) if row.get('LinesOfCode', '').strip() else 0
        )


@dataclass
class DynamicSQLOccurrence:
    """Represents a SQL Dynamic occurrence to be analyzed."""
    id: int
    line: int
    status: str = "PENDING"
    category: List[str] = None
    complexity: str = ""
    notes: str = ""
    generated_sql: str = ""
    sql_classification: str = ""
    
    def __post_init__(self):
        if self.category is None:
            self.category = []
    
    @staticmethod
    def from_dict(data: Dict) -> 'DynamicSQLOccurrence':
        """Create DynamicSQLOccurrence from dictionary."""
        category_data = data.get('category', [])
        # Handle both list and string formats for backward compatibility
        if isinstance(category_data, str):
            # Parse pipe-separated string into list
            category = [c.strip() for c in category_data.split('|') if c.strip()] if category_data else []
        else:
            category = category_data if category_data else []
        
        return DynamicSQLOccurrence(
            id=data.get('id', 0),
            line=data.get('line', 0),
            status=data.get('status', 'PENDING'),
            category=category,
            complexity=data.get('complexity', ''),
            notes=data.get('notes', ''),
            generated_sql=data.get('generated_sql', ''),
            sql_classification=data.get('sql_classification', '')
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON writing."""
        return {
            'id': self.id,
            'line': self.line,
            'status': self.status,
            'category': self.category,
            'complexity': self.complexity,
            'notes': self.notes,
            'generated_sql': self.generated_sql,
            'sql_classification': self.sql_classification
        }


@dataclass
class CodeUnitData:
    """Represents a code unit with its metadata and occurrences."""
    code_unit_id: str
    procedure_name: str
    filename: str
    code_unit_start_line: int
    lines_of_code: int
    occurrences: List[DynamicSQLOccurrence]
    procedure: str = ""
    
    @staticmethod
    def from_dict(code_unit_id: str, data: Dict) -> 'CodeUnitData':
        """Create CodeUnitData from dictionary."""
        metadata = data.get('metadata', {})
        occurrences_data = data.get('occurrences', [])
        
        return CodeUnitData(
            code_unit_id=code_unit_id,
            procedure_name=metadata.get('procedure_name', ''),
            filename=metadata.get('filename', ''),
            code_unit_start_line=metadata.get('code_unit_start_line', 0),
            lines_of_code=metadata.get('lines_of_code', 0),
            occurrences=[DynamicSQLOccurrence.from_dict(occ) for occ in occurrences_data],
            procedure=metadata.get('procedure', '')
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON writing."""
        return {
            'metadata': {
                'procedure_name': self.procedure_name,
                'filename': self.filename,
                'code_unit_start_line': self.code_unit_start_line,
                'lines_of_code': self.lines_of_code,
                'procedure': self.procedure
            },
            'occurrences': [occ.to_dict() for occ in self.occurrences]
        }


class SQLDynamicAnalyzer:
    """Analyzer for SQL Dynamic patterns from SnowConvert Issues.csv."""

    def __init__(self, issues_file: str, top_level_code_units_file: Optional[str] = None, source_dir: Optional[str] = None):
        self.issues_file = Path(issues_file)
        self.top_level_code_units_file = Path(top_level_code_units_file) if top_level_code_units_file else None
        self.source_dir = Path(source_dir) if source_dir else None
        self.issues: List[Issue] = []
        self.grouped_by_file: Dict[str, List[Issue]] = defaultdict(list)
        self.code_units: List[TopLevelCodeUnit] = []
        self.code_units_by_id: Dict[str, TopLevelCodeUnit] = {}

    def load_issues(self, filter_code: Optional[str] = None) -> None:
        """Load issues from CSV file, optionally filtering by code."""
        if not self.issues_file.exists():
            raise FileNotFoundError(f"Issues file not found: {self.issues_file}")

        with open(self.issues_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                issue = Issue.from_csv_row(row)
                
                # Filter by code if specified
                if filter_code and issue.code != filter_code:
                    continue
                
                self.issues.append(issue)
                self.grouped_by_file[issue.parent_file].append(issue)

        print(f"Loaded {len(self.issues)} issues from {self.issues_file}")
        if filter_code:
            print(f"Filtered by code: {filter_code}")
        print(f"Found issues in {len(self.grouped_by_file)} files")

    def load_top_level_code_units(self) -> None:
        """Load top-level code units from CSV file."""
        if not self.top_level_code_units_file:
            return
        
        if not self.top_level_code_units_file.exists():
            print(f"Warning: TopLevelCodeUnits file not found: {self.top_level_code_units_file}")
            return

        with open(self.top_level_code_units_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                code_unit = TopLevelCodeUnit.from_csv_row(row)
                self.code_units.append(code_unit)
                
                # Index by CodeUnitId for fast lookup
                if code_unit.code_unit_id:
                    self.code_units_by_id[code_unit.code_unit_id] = code_unit

        print(f"Loaded {len(self.code_units)} code units from {self.top_level_code_units_file}")
        print(f"Indexed {len(self.code_units_by_id)} code units by ID")

    def find_code_unit_by_id(self, code_unit_id: str) -> Optional[TopLevelCodeUnit]:
        """Find the code unit by its ID."""
        return self.code_units_by_id.get(code_unit_id)
    
    def detect_encoding(self, file_path: Path) -> str:
        """
        Detect file encoding by trying common encodings.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected encoding name
        """
        # Try reading BOM (Byte Order Mark) first
        with open(file_path, 'rb') as f:
            raw_data = f.read(4)
        
        # Check for BOM signatures
        if raw_data.startswith(b'\xff\xfe\x00\x00'):
            return 'utf-32-le'
        elif raw_data.startswith(b'\x00\x00\xfe\xff'):
            return 'utf-32-be'
        elif raw_data.startswith(b'\xff\xfe'):
            return 'utf-16-le'
        elif raw_data.startswith(b'\xfe\xff'):
            return 'utf-16-be'
        elif raw_data.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        
        # Try common encodings
        encodings_to_try = ['utf-8', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
        
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)
                return encoding
            except (UnicodeDecodeError, LookupError):
                continue
        
        # Default fallback
        return 'utf-8'
    
    def extract_procedure_code(self, filename: str, start_line: int, lines_of_code: int) -> str:
        """
        Extract procedure code from source file.
        Automatically detects and handles UTF-8, UTF-16, and other encodings.
        
        Args:
            filename: Relative path to the source file
            start_line: Starting line number (1-indexed)
            lines_of_code: Number of non-empty lines to extract
            
        Returns:
            Formatted procedure code with line numbers (as UTF-8 string)
        """
        if not self.source_dir:
            return ""
        
        source_file = self.source_dir / filename
        if not source_file.exists():
            print(f"Warning: Source file not found: {source_file}")
            return ""
        
        try:
            encoding = self.detect_encoding(source_file)

            with open(source_file, 'r', encoding=encoding, errors='replace') as f:
                all_lines = f.readlines()
            
            # Extract lines starting from start_line (convert to 0-indexed)
            start_idx = start_line - 1
            if start_idx < 0 or start_idx >= len(all_lines):
                return ""
            
            # Extract non-empty lines up to lines_of_code count
            extracted_lines = []
            non_empty_count = 0
            current_idx = start_idx
            
            while non_empty_count < lines_of_code and current_idx < len(all_lines):
                line = all_lines[current_idx]
                if line.strip():
                    # Format: "line_number: content"
                    # The line is already decoded to UTF-8 string
                    formatted_line = f"{current_idx + 1:3d}: {line.rstrip()}"
                    extracted_lines.append(formatted_line)
                    non_empty_count += 1
                current_idx += 1
            
            # Return as UTF-8 string (Python 3 strings are Unicode)
            return '\n'.join(extracted_lines)
            
        except Exception as e:
            print(f"Error reading source file {source_file}: {e}")
            return ""

    def generate_analysis_json(self, output_file: str = "sql_dynamic_analysis.json") -> None:
        """Generate analysis tracking JSON with all occurrences grouped by code unit."""
        code_units_data = {}
        occurrence_id = 1

        # Group by code_unit_id
        code_unit_groups = defaultdict(list)
        for filename in self.grouped_by_file.keys():
            issues_in_file = self.grouped_by_file[filename]
            
            for issue in issues_in_file:
                code_unit_id = issue.code_unit_id
                if not code_unit_id or code_unit_id.upper() == "N/A":
                    code_unit_id = f"unknown_{filename}"
                code_unit_groups[code_unit_id].append(issue)

        # Create code unit data structures
        for code_unit_id, issues in sorted(code_unit_groups.items()):
            # Sort issues by line number
            issues = sorted(issues, key=lambda x: x.line)
            
            # Get metadata from first issue or code unit lookup
            first_issue = issues[0]
            procedure_name = ""
            code_unit_start_line = 0
            lines_of_code = 0
            filename = first_issue.parent_file
            procedure_code = ""
            
            if self.top_level_code_units_file and code_unit_id:
                code_unit = self.find_code_unit_by_id(code_unit_id)
                if code_unit:
                    procedure_name = code_unit.code_unit_name
                    code_unit_start_line = code_unit.line_number
                    lines_of_code = code_unit.lines_of_code
                    filename = code_unit.file_name
                    
                    if self.source_dir and code_unit_start_line > 0 and lines_of_code > 0:
                        procedure_code = self.extract_procedure_code(
                            filename, 
                            code_unit_start_line, 
                            lines_of_code
                        )
            
            # Create occurrences for this code unit
            occurrences = []
            for issue in issues:
                occurrence = DynamicSQLOccurrence(
                    id=occurrence_id,
                    line=issue.line
                )
                occurrences.append(occurrence)
                occurrence_id += 1
            
            # Create code unit data
            code_unit_data = CodeUnitData(
                code_unit_id=code_unit_id,
                procedure_name=procedure_name,
                filename=filename,
                code_unit_start_line=code_unit_start_line,
                lines_of_code=lines_of_code,
                occurrences=occurrences,
                procedure=procedure_code
            )
            
            code_units_data[code_unit_id] = code_unit_data.to_dict()

        # Build final JSON structure
        total_occurrences = sum(len(cu['occurrences']) for cu in code_units_data.values())
        
        output_data = {
            'metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'total_occurrences': total_occurrences,
                'total_code_units': len(code_units_data),
                'files': {
                    'issues_csv': str(self.issues_file),
                    'top_level_code_units_csv': str(self.top_level_code_units_file) if self.top_level_code_units_file else None,
                    'source_dir': str(self.source_dir) if self.source_dir else None
                },
                'filter_code': DYNAMIC_SQL_ISSUE_CODE
            },
            'code_units': code_units_data
        }

        # Write to JSON file
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\nGenerated analysis JSON: {output_path}")
        print(f"Total code units: {len(code_units_data)}")
        print(f"Total occurrences to analyze: {total_occurrences}")

    def print_summary(self) -> None:
        """Print summary of findings."""
        print("\n" + "=" * 60)
        print("SQL DYNAMIC ANALYSIS SUMMARY")
        print("=" * 60)
        
        print(f"\nTotal Issues: {len(self.issues)}")
        print(f"Total Files: {len(self.grouped_by_file)}")
        
        print("\nTop 10 Files by Occurrence Count:")
        sorted_files = sorted(
            self.grouped_by_file.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        for filename, issues in sorted_files[:10]:
            print(f"  {filename}: {len(issues)} occurrences")


class AnalysisJSONManager:
    """Manager for updating analysis JSON records."""

    def __init__(self, json_file: str):
        self.json_file = Path(json_file)
        self.data: Dict = {}
        self.code_units: Dict[str, CodeUnitData] = {}

    def load(self) -> None:
        """Load existing analysis JSON."""
        if not self.json_file.exists():
            raise FileNotFoundError(f"Analysis JSON not found: {self.json_file}")

        with open(self.json_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        # Parse code units
        code_units_data = self.data.get('code_units', {})
        for code_unit_id, cu_data in code_units_data.items():
            self.code_units[code_unit_id] = CodeUnitData.from_dict(code_unit_id, cu_data)

        total_occurrences = sum(len(cu.occurrences) for cu in self.code_units.values())
        print(f"Loaded {total_occurrences} records from {self.json_file}")
        print(f"Total code units: {len(self.code_units)}")

    def save(self) -> None:
        """Save analysis JSON."""
        # Convert code units back to dict format
        code_units_data = {}
        for code_unit_id, cu in self.code_units.items():
            code_units_data[code_unit_id] = cu.to_dict()
        
        # Update counts in metadata
        total_occurrences = sum(len(cu.occurrences) for cu in self.code_units.values())
        self.data['metadata']['total_occurrences'] = total_occurrences
        self.data['metadata']['total_code_units'] = len(self.code_units)
        self.data['code_units'] = code_units_data
        
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

        print(f"Saved {total_occurrences} records to {self.json_file}")

    def update_record(
        self,
        record_id: int,
        status: Optional[str] = None,
        category: Optional[str] = None,
        complexity: Optional[str] = None,
        notes: Optional[str] = None,
        generated_sql: Optional[str] = None,
        sql_classification: Optional[str] = None
    ) -> bool:
        """Update a record by ID. Returns True if record was found and updated."""
        for cu in self.code_units.values():
            for occ in cu.occurrences:
                if occ.id == record_id:
                    if status is not None:
                        occ.status = status
                    if category is not None:
                        # Parse pipe-separated string into list
                        occ.category = [c.strip() for c in category.split('|') if c.strip()] if category else []
                    if complexity is not None:
                        occ.complexity = complexity
                    if notes is not None:
                        occ.notes = notes
                    if generated_sql is not None:
                        occ.generated_sql = generated_sql
                    if sql_classification is not None:
                        occ.sql_classification = sql_classification
                    return True
        return False

    def get_record(self, record_id: int) -> Optional[tuple[DynamicSQLOccurrence, CodeUnitData]]:
        """Get a record by ID. Returns (occurrence, code_unit) tuple."""
        for cu in self.code_units.values():
            for occ in cu.occurrences:
                if occ.id == record_id:
                    return (occ, cu)
        return None

    def print_record(self, record_id: int) -> None:
        """Print details of a specific record."""
        result = self.get_record(record_id)
        if result:
            occ, cu = result
            print(f"\nRecord ID: {occ.id}")
            print(f"  File: {cu.filename}")
            print(f"  Line: {occ.line}")
            print(f"  Procedure: {cu.procedure_name}")
            print(f"  Code Unit ID: {cu.code_unit_id}")
            print(f"  Code Unit Start Line: {cu.code_unit_start_line}")
            print(f"  Lines of Code: {cu.lines_of_code}")
            print(f"  Status: {occ.status}")
            print(f"  Category: {' | '.join(occ.category) if occ.category else ''}")
            print(f"  Complexity: {occ.complexity}")
            print(f"  SQL Classification: {occ.sql_classification}")
            print(f"  Generated SQL: {occ.generated_sql}")
            print(f"  Notes: {occ.notes}")
        else:
            print(f"Record ID {record_id} not found")

    def get_code_unit_by_id(self, code_unit_id: str) -> Optional[CodeUnitData]:
        """Get code unit by its ID."""
        return self.code_units.get(code_unit_id)
    
    def get_code_unit_by_filename(self, filename: str) -> List[CodeUnitData]:
        """Get all code units for a specific filename."""
        return [cu for cu in self.code_units.values() if cu.filename == filename]

    def print_code_unit(self, code_unit_id: str, include_code: bool = False) -> None:
        """Print all records for a specific code unit. Optionally include the stored procedure code."""
        cu = self.get_code_unit_by_id(code_unit_id)
        
        if not cu:
            print(f"\nNo code unit found with ID: {code_unit_id}")
            return
        
        print(f"\n{'='*80}")
        print(f"Code Unit: {cu.procedure_name}")
        print(f"{'='*80}")
        print(f"File: {cu.filename}")
        print(f"Code Unit Start Line: {cu.code_unit_start_line}")
        print(f"Lines of Code: {cu.lines_of_code}")
        print(f"Total occurrences in this code unit: {len(cu.occurrences)}\n")
        
        for occ in sorted(cu.occurrences, key=lambda x: x.line):
            print(f"Record ID: {occ.id}")
            print(f"  Line: {occ.line}")
            print(f"  Status: {occ.status}")
            print(f"  Category: {' | '.join(occ.category) if occ.category else ''}")
            print(f"  Complexity: {occ.complexity}")
            print(f"  Notes: {occ.notes}")
            print()

        if include_code:
            print(f"{'─'*80}")
            print("Procedure Code (from JSON metadata):")
            if cu.procedure:
                print(cu.procedure)
            else:
                print("(No procedure code stored. Re-run `generate` with a valid --source-dir.)")
            print()
    
    def print_all_code_units_in_file(self, filename: str, include_code: bool = False) -> None:
        """Print all code units in a file with their occurrences grouped. Optionally include procedure code."""
        code_units = self.get_code_unit_by_filename(filename)
        
        if not code_units:
            print(f"\nNo code units found for filename: {filename}")
            return
        
        total_occurrences = sum(len(cu.occurrences) for cu in code_units)
        
        print(f"\n{'='*80}")
        print(f"File: {filename}")
        print(f"{'='*80}")
        print(f"Total code units: {len(code_units)}")
        print(f"Total occurrences: {total_occurrences}\n")
        
        for cu in sorted(code_units, key=lambda x: x.code_unit_start_line):
            print(f"{'─'*80}")
            print(f"Code Unit: {cu.procedure_name}")
            print(f"  Code Unit ID: {cu.code_unit_id}")
            print(f"  Start Line: {cu.code_unit_start_line}")
            print(f"  Lines of Code: {cu.lines_of_code}")
            print(f"  Occurrences: {len(cu.occurrences)}")
            print()
            
            for occ in sorted(cu.occurrences, key=lambda x: x.line):
                print(f"  Record ID: {occ.id}")
                print(f"    Line: {occ.line}")
                print(f"    Status: {occ.status}")
                if occ.category:
                    print(f"    Category: {' | '.join(occ.category)}")
                if occ.complexity:
                    print(f"    Complexity: {occ.complexity}")
                print()

            if include_code:
                print(f"{'─'*80}")
                print("Procedure Code (from JSON metadata):")
                if cu.procedure:
                    print(cu.procedure)
                else:
                    print("(No procedure code stored. Re-run `generate` with a valid --source-dir.)")
                print()
        
        print(f"{'='*80}")
    
    def get_code_unit_id_from_record_id(self, record_id: int) -> Optional[str]:
        """Get code unit ID for a specific record ID."""
        result = self.get_record(record_id)
        return result[1].code_unit_id if result else None
    
    def get_filename_from_record_id(self, record_id: int) -> Optional[str]:
        """Get filename for a specific record ID."""
        result = self.get_record(record_id)
        return result[1].filename if result else None

    def get_stats(self) -> Dict:
        """Get statistics about the analysis."""
        status_counts = defaultdict(int)
        category_counts = defaultdict(int)
        total = 0
        
        for cu in self.code_units.values():
            for occ in cu.occurrences:
                total += 1
                status_counts[occ.status] += 1
                if occ.category:
                    # Count each category in the list
                    for cat in occ.category:
                        category_counts[cat] += 1

        return {
            'total': total,
            'status_counts': dict(status_counts),
            'category_counts': dict(category_counts)
        }

    def print_stats(self) -> None:
        """Print statistics about the analysis."""
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("ANALYSIS STATISTICS")
        print("=" * 60)
        print(f"\nTotal Records: {stats['total']}")
        
        print("\nStatus Distribution:")
        for status, count in sorted(stats['status_counts'].items()):
            percentage = (count / stats['total']) * 100
            print(f"  {status}: {count} ({percentage:.1f}%)")
        
        if stats['category_counts']:
            print("\nCategory Distribution:")
            for category, count in sorted(stats['category_counts'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / stats['total']) * 100
                print(f"  {category}: {count} ({percentage:.1f}%)")


def print_usage():
    """Print usage information."""
    print("SQL Dynamic Analysis Helper")
    print("\nCommands:")
    print("  generate   Generate initial analysis JSON from Issues.csv")
    print("  update     Update a record in the analysis JSON")
    print("  show       Show a specific record")
    print("  show-file  Show all code units in a file with their occurrences grouped")
    print("  show-code-unit  Show procedure/function code (from JSON metadata) for one code unit")
    print("  stats      Show statistics about the analysis")
    print("\nUsage:")
    print("  Generate:")
    print("    python sql_dynamic_analzer_helper.py generate <issues_csv> --top-level-code-units <tlcu_csv> --source-dir <dir> [--code CODE] [--output OUTPUT]")
    print("\n  Update:")
    print("    python sql_dynamic_analzer_helper.py update <analysis_json> --id ID [--status STATUS] [--category CATEGORY] [--complexity COMPLEXITY] [--notes NOTES] [--generated-sql SQL] [--sql-classification CLASS]")
    print("\n  Show:")
    print("    python sql_dynamic_analzer_helper.py show <analysis_json> --id ID")
    print("\n  Show File:")
    print("    python sql_dynamic_analzer_helper.py show-file <analysis_json> --id ID")
    print("    python sql_dynamic_analzer_helper.py show-file <analysis_json> --filename FILENAME")
    print("    python sql_dynamic_analzer_helper.py show-file <analysis_json> --id ID --include-code")
    print("    (Groups all occurrences by code unit within the file)")
    print("\n  Show Code Unit:")
    print("    python sql_dynamic_analzer_helper.py show-code-unit <analysis_json> --id ID")
    print("    python sql_dynamic_analzer_helper.py show-code-unit <analysis_json> --code-unit-id CODE_UNIT_ID")
    print("\n  Stats:")
    print("    python sql_dynamic_analzer_helper.py stats <analysis_json>")
    print("\nRequired Inputs for Generate:")
    print("  1. Issues.csv (positional) - SnowConvert output with SSC-EWI-0030 occurrences")
    print("  2. --top-level-code-units  - SnowConvert TopLevelCodeUnits.csv")
    print("  3. --source-dir            - Source code directory")
    print("\nExamples:")
    print("  # Generate analysis (ALL THREE INPUTS ARE REQUIRED)")
    print("  python sql_dynamic_analzer_helper.py generate Issues.csv --top-level-code-units TopLevelCodeUnits.csv --source-dir ../source")
    print("  python sql_dynamic_analzer_helper.py generate Issues.csv --top-level-code-units TopLevelCodeUnits.csv --source-dir ../source --output my_analysis.json")
    print("\n  # Update a record")
    print("  python sql_dynamic_analzer_helper.py update sql_dynamic_analysis.json --id 5 --status REVIEWED")
    print("  python sql_dynamic_analzer_helper.py update sql_dynamic_analysis.json --id 10 --status REVIEWED --category \"Parameter-Driven\" --complexity medium")
    print("  python sql_dynamic_analzer_helper.py update sql_dynamic_analysis.json --id 15 --notes \"Uses sp_executesql with parameters\"")
    print("  python sql_dynamic_analzer_helper.py update sql_dynamic_analysis.json --id 20 --generated-sql \"SELECT * FROM Users WHERE Id = @UserId\" --sql-classification \"DQL\"")
    print("\n  # Show a record")
    print("  python sql_dynamic_analzer_helper.py show sql_dynamic_analysis.json --id 5")
    print("\n  # Show all records for a file (by record ID) - grouped by code unit")
    print("  python sql_dynamic_analzer_helper.py show-file sql_dynamic_analysis.json --id 5")
    print("  python sql_dynamic_analzer_helper.py show-file sql_dynamic_analysis.json --id 5 --include-code")
    print("\n  # Show all records for a file (by filename) - grouped by code unit")
    print("  python sql_dynamic_analzer_helper.py show-file sql_dynamic_analysis.json --filename path/to/file.sql")
    print("\n  # Show the full procedure/function text for a code unit (by record ID)")
    print("  python sql_dynamic_analzer_helper.py show-code-unit sql_dynamic_analysis.json --id 5")
    print("\n  # Show the full procedure/function text for a code unit (by code unit id)")
    print("  python sql_dynamic_analzer_helper.py show-code-unit sql_dynamic_analysis.json --code-unit-id \"[DB].[dbo].[ProcName]\"")
    print("\n  # Show statistics")
    print("  python sql_dynamic_analzer_helper.py stats sql_dynamic_analysis.json")


def cmd_generate(args):
    """Generate command: Create initial analysis JSON from Issues.csv."""
    if len(args) < 1:
        print("Error: Missing required Issues.csv file", file=sys.stderr)
        print("Usage: python sql_dynamic_analzer_helper.py generate <issues_csv> --top-level-code-units <tlcu_csv> --source-dir <dir> [--code CODE] [--output OUTPUT]")
        sys.exit(1)

    issues_file = args[0]
    filter_code = DYNAMIC_SQL_ISSUE_CODE
    top_level_code_units_file = None
    source_dir = None
    output_file = "sql_dynamic_analysis.json"

    # Parse optional arguments
    i = 1
    while i < len(args):
        if args[i] == '--code' and i + 1 < len(args):
            filter_code = args[i + 1]
            i += 2
        elif args[i] == '--top-level-code-units' and i + 1 < len(args):
            top_level_code_units_file = args[i + 1]
            i += 2
        elif args[i] == '--source-dir' and i + 1 < len(args):
            source_dir = args[i + 1]
            i += 2
        elif args[i] == '--output' and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2
        else:
            print(f"Warning: Unknown argument '{args[i]}'", file=sys.stderr)
            i += 1

    # Validate all required parameters
    missing_params = []
    if not top_level_code_units_file:
        missing_params.append("--top-level-code-units")
    if not source_dir:
        missing_params.append("--source-dir")
    
    if missing_params:
        print(f"\nError: Missing required parameter(s): {', '.join(missing_params)}", file=sys.stderr)
        print("\nAll three inputs are required for code-unit-based analysis:")
        print("  1. Issues.csv (positional): Contains SSC-EWI-0030 dynamic SQL occurrences")
        print("  2. --top-level-code-units: Provides procedure names and code unit boundaries")
        print("  3. --source-dir: Source code directory for extracting procedure code")
        print("\nUsage: python sql_dynamic_analzer_helper.py generate <issues_csv> --top-level-code-units <tlcu_csv> --source-dir <dir> [--output OUTPUT]")
        sys.exit(1)

    analyzer = SQLDynamicAnalyzer(issues_file, top_level_code_units_file, source_dir)
    analyzer.load_issues(filter_code=filter_code)
    analyzer.load_top_level_code_units()
    analyzer.print_summary()
    analyzer.generate_analysis_json(output_file)

    print("\n✓ Analysis JSON generated successfully!")
    print(f"✓ Procedure code extracted from source directory: {source_dir}")
    print(f"\nNext steps:")
    print(f"  1. Review records: python sql_dynamic_analzer_helper.py show {output_file} --id <ID>")
    print(f"  2. Update records: python sql_dynamic_analzer_helper.py update {output_file} --id <ID> --status REVIEWED --category \"<CATEGORY>\"")
    print(f"  3. View statistics: python sql_dynamic_analzer_helper.py stats {output_file}")


def cmd_update(args):
    """Update command: Update a record in the analysis JSON."""
    if len(args) < 1:
        print("Error: Missing analysis JSON file", file=sys.stderr)
        print("Usage: python sql_dynamic_analzer_helper.py update <analysis_json> --id ID [--status STATUS] [--category CATEGORY] [--complexity COMPLEXITY] [--notes NOTES] [--generated-sql SQL] [--sql-classification CLASS]")
        sys.exit(1)

    json_file = args[0]
    record_id = None
    status = None
    category = None
    complexity = None
    notes = None
    generated_sql = None
    sql_classification = None

    # Parse arguments
    i = 1
    while i < len(args):
        if args[i] == '--id' and i + 1 < len(args):
            record_id = int(args[i + 1])
            i += 2
        elif args[i] == '--status' and i + 1 < len(args):
            status = args[i + 1]
            i += 2
        elif args[i] == '--category' and i + 1 < len(args):
            category = args[i + 1]
            i += 2
        elif args[i] == '--complexity' and i + 1 < len(args):
            complexity = args[i + 1]
            i += 2
        elif args[i] == '--notes' and i + 1 < len(args):
            notes = args[i + 1]
            i += 2
        elif args[i] == '--generated-sql' and i + 1 < len(args):
            generated_sql = args[i + 1]
            i += 2
        elif args[i] == '--sql-classification' and i + 1 < len(args):
            sql_classification = args[i + 1]
            i += 2
        else:
            print(f"Warning: Unknown argument '{args[i]}'", file=sys.stderr)
            i += 1

    if record_id is None:
        print("Error: --id is required", file=sys.stderr)
        sys.exit(1)

    if all(v is None for v in [status, category, complexity, notes, generated_sql, sql_classification]):
        print("Error: At least one of --status, --category, --complexity, --notes, --generated-sql, or --sql-classification is required", file=sys.stderr)
        sys.exit(1)

    manager = AnalysisJSONManager(json_file)
    manager.load()

    if manager.update_record(record_id, status, category, complexity, notes, generated_sql, sql_classification):
        manager.save()
        print(f"\nRecord {record_id} updated successfully!")
        manager.print_record(record_id)
    else:
        print(f"Error: Record ID {record_id} not found", file=sys.stderr)
        sys.exit(1)


def cmd_show(args):
    """Show command: Display a specific record."""
    if len(args) < 1:
        print("Error: Missing analysis JSON file", file=sys.stderr)
        print("Usage: python sql_dynamic_analzer_helper.py show <analysis_json> --id ID")
        sys.exit(1)

    json_file = args[0]
    record_id = None

    # Parse arguments
    i = 1
    while i < len(args):
        if args[i] == '--id' and i + 1 < len(args):
            record_id = int(args[i + 1])
            i += 2
        else:
            print(f"Warning: Unknown argument '{args[i]}'", file=sys.stderr)
            i += 1

    if record_id is None:
        print("Error: --id is required", file=sys.stderr)
        sys.exit(1)

    manager = AnalysisJSONManager(json_file)
    manager.load()
    manager.print_record(record_id)


def cmd_show_file(args):
    """Show-file command: Display all records grouped by code unit for a file."""
    if len(args) < 1:
        print("Error: Missing analysis JSON file", file=sys.stderr)
        print("Usage: python sql_dynamic_analzer_helper.py show-file <analysis_json> --id ID")
        print("   or: python sql_dynamic_analzer_helper.py show-file <analysis_json> --filename FILENAME")
        print("   or: python sql_dynamic_analzer_helper.py show-file <analysis_json> --id ID --include-code")
        sys.exit(1)

    json_file = args[0]
    record_id = None
    filename = None
    include_code = False

    # Parse arguments
    i = 1
    while i < len(args):
        if args[i] == '--id' and i + 1 < len(args):
            record_id = int(args[i + 1])
            i += 2
        elif args[i] == '--filename' and i + 1 < len(args):
            filename = args[i + 1]
            i += 2
        elif args[i] == '--include-code':
            include_code = True
            i += 1
        else:
            print(f"Warning: Unknown argument '{args[i]}'", file=sys.stderr)
            i += 1

    if record_id is None and filename is None:
        print("Error: Either --id or --filename is required", file=sys.stderr)
        sys.exit(1)

    manager = AnalysisJSONManager(json_file)
    manager.load()

    # If ID provided, get filename from that record
    if record_id is not None:
        filename = manager.get_filename_from_record_id(record_id)
        if filename is None:
            print(f"Error: Record ID {record_id} not found", file=sys.stderr)
            sys.exit(1)

    # Show all code units in this file with their occurrences
    manager.print_all_code_units_in_file(filename, include_code=include_code)


def cmd_show_code_unit(args):
    """Show-code-unit command: Display the procedure/function code for a single code unit."""
    if len(args) < 1:
        print("Error: Missing analysis JSON file", file=sys.stderr)
        print("Usage: python sql_dynamic_analzer_helper.py show-code-unit <analysis_json> --id ID")
        print("   or: python sql_dynamic_analzer_helper.py show-code-unit <analysis_json> --code-unit-id CODE_UNIT_ID")
        sys.exit(1)

    json_file = args[0]
    record_id = None
    code_unit_id = None

    # Parse arguments
    i = 1
    while i < len(args):
        if args[i] == '--id' and i + 1 < len(args):
            record_id = int(args[i + 1])
            i += 2
        elif args[i] == '--code-unit-id' and i + 1 < len(args):
            code_unit_id = args[i + 1]
            i += 2
        else:
            print(f"Warning: Unknown argument '{args[i]}'", file=sys.stderr)
            i += 1

    if record_id is None and code_unit_id is None:
        print("Error: Either --id or --code-unit-id is required", file=sys.stderr)
        sys.exit(1)

    manager = AnalysisJSONManager(json_file)
    manager.load()

    if record_id is not None:
        code_unit_id = manager.get_code_unit_id_from_record_id(record_id)
        if code_unit_id is None:
            print(f"Error: Record ID {record_id} not found", file=sys.stderr)
            sys.exit(1)

    manager.print_code_unit(code_unit_id, include_code=True)


def cmd_stats(args):
    """Stats command: Show statistics about the analysis."""
    if len(args) < 1:
        print("Error: Missing analysis JSON file", file=sys.stderr)
        print("Usage: python sql_dynamic_analzer_helper.py stats <analysis_json>")
        sys.exit(1)

    json_file = args[0]
    manager = AnalysisJSONManager(json_file)
    manager.load()
    manager.print_stats()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    try:
        if command == 'generate':
            cmd_generate(args)
        elif command == 'update':
            cmd_update(args)
        elif command == 'show':
            cmd_show(args)
        elif command == 'show-file':
            cmd_show_file(args)
        elif command == 'show-code-unit':
            cmd_show_code_unit(args)
        elif command == 'stats':
            cmd_stats(args)
        else:
            print(f"Error: Unknown command '{command}'", file=sys.stderr)
            print("\nAvailable commands: generate, update, show, show-file, show-code-unit, stats")
            print("Run without arguments for full usage information.")
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
