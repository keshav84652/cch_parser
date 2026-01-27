"""
CCH Field Analyzer - Validates mapping definitions against actual data patterns.

This tool:
1. Parses all CCH files and collects field values per form
2. Runs pattern validators (regex) to check value types
3. Detects inconsistencies between YAML mapping and actual data
4. Generates validation reports
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass, field, asdict
import yaml


# ============================================================================
# PATTERN VALIDATORS - Regex patterns for known field types
# ============================================================================

PATTERNS = {
    "owner_code": re.compile(r"^[TtSsJj]$"),
    "state": re.compile(r"^[A-Z]{2}$"),
    "ein": re.compile(r"^\d{2}-?\d{7}$"),
    "ssn": re.compile(r"^\d{3}-?\d{2}-?\d{4}$"),
    "zip": re.compile(r"^\d{5}(-\d{4})?$"),
    "currency": re.compile(r"^-?\d+\.?\d*$"),
    "integer": re.compile(r"^-?\d+$"),
    "date": re.compile(r"^\d{2}/\d{2}/\d{2,4}$"),
    "percentage": re.compile(r"^\.\d+$|^\d+\.?\d*%?$"),
    "phone": re.compile(r"^\d{3}[- ]?\d{3}[- ]?\d{4}$"),
    "email": re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$"),
    "code_letter": re.compile(r"^[A-Z]$"),
    "boolean_x": re.compile(r"^[Xx]$"),
}


@dataclass
class FieldStats:
    """Statistics for a single field across all entries"""
    field_num: str
    total_count: int = 0
    unmatched_count: int = 0  # Values that don't match any pattern
    unique_values: Set[str] = field(default_factory=set)
    sample_values: List[str] = field(default_factory=list)
    detected_types: Set[str] = field(default_factory=set)
    is_numeric_only: bool = True
    has_mixed_types: bool = False
    max_length: int = 0
    
    def add_value(self, value: str):
        """Add a value and update statistics"""
        if not value or value.strip() == "":
            return
        
        value = value.strip()
        self.total_count += 1
        self.unique_values.add(value)
        self.max_length = max(self.max_length, len(value))
        
        # Keep up to 10 sample values
        if len(self.sample_values) < 10 and value not in self.sample_values:
            self.sample_values.append(value)
        
        # Detect type from patterns
        matched = False
        for pattern_name, pattern in PATTERNS.items():
            if pattern.match(value):
                self.detected_types.add(pattern_name)
                matched = True
        
        # Track unmatched values
        if not matched:
            self.unmatched_count += 1
        
        # Check if numeric
        if not PATTERNS["currency"].match(value):
            self.is_numeric_only = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        # Detect true mixed types: some match patterns, some don't
        has_pattern_and_unmatched = len(self.detected_types) > 0 and self.unmatched_count > 0
        has_multiple_patterns = len(self.detected_types) > 1
        
        return {
            "field_num": self.field_num,
            "total_count": self.total_count,
            "unique_count": len(self.unique_values),
            "unmatched_count": self.unmatched_count,
            "sample_values": self.sample_values[:10],
            "detected_types": list(self.detected_types),
            "is_numeric_only": self.is_numeric_only,
            "has_mixed_types": has_pattern_and_unmatched or has_multiple_patterns,
            "max_length": self.max_length,
        }


@dataclass
class FormAnalysis:
    """Analysis results for a single form type"""
    form_code: str
    form_name: str = ""
    entry_count: int = 0
    fields: Dict[str, FieldStats] = field(default_factory=dict)
    
    def add_entry(self, entry_fields: Dict[str, str]):
        """Add an entry's fields to the analysis"""
        self.entry_count += 1
        for field_num, value in entry_fields.items():
            if field_num not in self.fields:
                self.fields[field_num] = FieldStats(field_num=field_num)
            self.fields[field_num].add_value(value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "form_code": self.form_code,
            "form_name": self.form_name,
            "entry_count": self.entry_count,
            "field_count": len(self.fields),
            "fields": {k: v.to_dict() for k, v in sorted(self.fields.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 9999)}
        }


class FieldAnalyzer:
    """Analyzes CCH field usage patterns across all parsed files"""
    
    def __init__(self, yaml_path: str = None):
        self.forms: Dict[str, FormAnalysis] = {}
        self.yaml_mapping: Dict[str, Any] = {}
        
        if yaml_path and Path(yaml_path).exists():
            with open(yaml_path, 'r', encoding='utf-8') as f:
                self.yaml_mapping = yaml.safe_load(f) or {}
    
    def analyze_document(self, doc) -> None:
        """Analyze all forms in a CCH document"""
        for form_code, form in doc.forms.items():
            if form_code not in self.forms:
                yaml_key = f"form_{form_code}"
                form_name = self.yaml_mapping.get(yaml_key, {}).get("name", f"Form {form_code}")
                self.forms[form_code] = FormAnalysis(form_code=form_code, form_name=form_name)
            
            for entry in form.entries:
                # Convert entry fields to dict
                entry_fields = {}
                for field_num, field_obj in entry.fields.items():
                    value = field_obj.value if hasattr(field_obj, 'value') else str(field_obj)
                    if value:
                        entry_fields[field_num] = value
                
                self.forms[form_code].add_entry(entry_fields)
    
    def validate_against_yaml(self) -> List[Dict[str, Any]]:
        """Compare actual field usage against YAML mapping definitions"""
        issues = []
        
        for form_code, form_analysis in self.forms.items():
            yaml_key = f"form_{form_code}"
            yaml_form = self.yaml_mapping.get(yaml_key, {})
            yaml_fields = yaml_form.get("fields", {})
            
            # Check for fields in data but not in YAML
            for field_num in form_analysis.fields:
                if field_num not in yaml_fields:
                    stats = form_analysis.fields[field_num]
                    issues.append({
                        "type": "unmapped_field",
                        "form": form_code,
                        "field": field_num,
                        "count": stats.total_count,
                        "samples": stats.sample_values[:5],
                        "detected_types": list(stats.detected_types),
                    })
            
            # Check for YAML fields not used in data
            for field_num in yaml_fields:
                if field_num not in form_analysis.fields:
                    issues.append({
                        "type": "unused_yaml_field",
                        "form": form_code,
                        "field": field_num,
                        "yaml_name": yaml_fields[field_num].get("name", ""),
                    })
            
            # Check for type mismatches
            for field_num, stats in form_analysis.fields.items():
                if field_num in yaml_fields:
                    yaml_type = yaml_fields[field_num].get("type", "")
                    actual_types = stats.detected_types
                    
                    # Simple type compatibility check
                    if yaml_type == "currency" and not stats.is_numeric_only:
                        issues.append({
                            "type": "type_mismatch",
                            "form": form_code,
                            "field": field_num,
                            "yaml_type": yaml_type,
                            "actual_samples": stats.sample_values[:5],
                        })
        
        return issues
    
    def detect_mixed_semantic_fields(self) -> List[Dict[str, Any]]:
        """Find fields that contain truly mixed semantic content.
        
        Only flags fields where there's a semantic conflict, NOT:
        - All dates (even though they contain slashes)
        - All phone numbers (even though they have mixed chars)
        - All emails (contain @ and dots)
        - All addresses or apartment numbers (like "2A", "Apt 5B")
        - All names (text strings)
        - All ZIP codes (even with extensions)
        """
        mixed_fields = []
        
        # Additional patterns for homogeneous field detection
        date_pattern = re.compile(r'^\d{1,2}/\d{1,2}/\d{2,4}$')
        phone_pattern = re.compile(r'^[\d\(\)\-\.\s]{10,}$')
        email_pattern = re.compile(r'^[\w\.\-]+@[\w\.\-]+\.\w+$')
        zip_pattern = re.compile(r'^\d{5}(-\d{4})?$')
        apt_pattern = re.compile(r'^(#?\d+[A-Za-z]?|Apt\.?\s*\d*[A-Za-z]*|STE\s*\d*[A-Za-z]*|Unit\s*\d*[A-Za-z]*)$', re.IGNORECASE)
        
        for form_code, form_analysis in self.forms.items():
            for field_num, stats in form_analysis.fields.items():
                unique_vals = list(stats.unique_values)
                
                if len(unique_vals) < 2:
                    continue  # Not enough variety to detect issues
                
                # Check if field is homogeneous (all same type)
                def all_match(pattern, vals):
                    return all(pattern.match(v) for v in vals if v)
                
                # Skip if all values are dates
                if all_match(date_pattern, unique_vals):
                    continue
                
                # Skip if all values are phone numbers
                if all_match(phone_pattern, unique_vals):
                    continue
                
                # Skip if all values are emails
                if all_match(email_pattern, unique_vals):
                    continue
                
                # Skip if all values are ZIP codes
                if all_match(zip_pattern, unique_vals):
                    continue
                
                # Skip if all values are apartment/unit numbers
                if all_match(apt_pattern, unique_vals):
                    continue
                
                # Skip if all values are pure text (names, addresses - no digits at all or all have digits)
                all_text = all(not any(c.isdigit() for c in v) for v in unique_vals if v)
                all_alphanumeric = all(any(c.isdigit() for c in v) and any(c.isalpha() for c in v) for v in unique_vals if v)
                if all_text:
                    continue  # All names/text - consistent
                if all_alphanumeric:
                    continue  # All mixed like addresses - consistent
                
                # Skip if all values are pure numbers (amounts, codes)
                all_numeric = all(PATTERNS["currency"].match(v) for v in unique_vals if v)
                if all_numeric:
                    continue
                
                # NOW check for truly mixed semantics
                
                # Case 1: Mix of owner codes (T/S) AND descriptive text (>5 chars)
                has_owner_codes = any(PATTERNS["owner_code"].match(v) for v in unique_vals)
                has_long_text = any(len(v) > 5 and not v.isdigit() for v in unique_vals)
                
                if has_owner_codes and has_long_text:
                    mixed_fields.append({
                        "form": form_code,
                        "field": field_num,
                        "issue": "Contains both owner codes (T/S/J) and descriptive text",
                        "samples": stats.sample_values[:10],
                        "severity": "HIGH"
                    })
                    continue
                
                # Case 2: Mix of numeric codes (1, 2, 3) AND text descriptions
                has_single_digit = any(v.isdigit() and len(v) == 1 for v in unique_vals)
                has_word_text = any(len(v) > 3 and v.isalpha() for v in unique_vals)
                
                if has_single_digit and has_word_text:
                    mixed_fields.append({
                        "form": form_code,
                        "field": field_num,
                        "issue": "Contains both numeric codes and text descriptions",
                        "samples": stats.sample_values[:10],
                        "severity": "MEDIUM"
                    })
                    continue
                
                # Case 3: Mix of large currency amounts AND emails
                has_large_numbers = any(v.isdigit() and len(v) >= 4 for v in unique_vals)
                has_emails = any('@' in v for v in unique_vals)
                
                if has_large_numbers and has_emails:
                    mixed_fields.append({
                        "form": form_code,
                        "field": field_num,
                        "issue": "Contains both numeric amounts and email addresses",
                        "samples": stats.sample_values[:10],
                        "severity": "HIGH"
                    })
                    continue
        
        return mixed_fields
    
    def generate_report(self, output_dir: str) -> None:
        """Generate analysis reports"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 1. Save per-form analysis as JSON
        for form_code, form_analysis in self.forms.items():
            json_path = output_path / f"form_{form_code}_analysis.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(form_analysis.to_dict(), f, indent=2)
        
        # 2. Generate validation issues
        yaml_issues = self.validate_against_yaml()
        mixed_issues = self.detect_mixed_semantic_fields()
        
        # 3. Save issues as JSON
        issues_path = output_path / "validation_issues.json"
        with open(issues_path, 'w', encoding='utf-8') as f:
            json.dump({
                "yaml_issues": yaml_issues,
                "mixed_semantic_fields": mixed_issues,
            }, f, indent=2)
        
        # 4. Generate markdown report
        report_path = output_path / "validation_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# CCH Mapping Validation Report\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Forms analyzed:** {len(self.forms)}\n")
            f.write(f"- **Unmapped fields found:** {len([i for i in yaml_issues if i['type'] == 'unmapped_field'])}\n")
            f.write(f"- **Unused YAML fields:** {len([i for i in yaml_issues if i['type'] == 'unused_yaml_field'])}\n")
            f.write(f"- **Mixed semantic fields:** {len(mixed_issues)}\n\n")
            
            f.write("---\n\n")
            
            f.write("## Mixed Semantic Fields (HIGH PRIORITY)\n\n")
            f.write("These fields contain inconsistent data types:\n\n")
            for issue in mixed_issues[:20]:
                f.write(f"### Form {issue['form']} - Field .{issue['field']}\n")
                f.write(f"- **Issue:** {issue['issue']}\n")
                f.write(f"- **Samples:** `{issue['samples']}`\n\n")
            
            f.write("---\n\n")
            
            f.write("## Unmapped Fields\n\n")
            f.write("Fields in data but NOT in YAML:\n\n")
            f.write("| Form | Field | Count | Samples | Detected Types |\n")
            f.write("|------|-------|-------|---------|----------------|\n")
            for issue in yaml_issues[:50]:
                if issue['type'] == 'unmapped_field':
                    samples = str(issue.get('samples', []))[:40]
                    types = str(issue.get('detected_types', []))
                    f.write(f"| {issue['form']} | .{issue['field']} | {issue['count']} | {samples} | {types} |\n")
        
        print(f"Reports saved to {output_path}")


def run_analysis(data_dir: str, yaml_path: str, output_dir: str):
    """Run full analysis on CCH data files"""
    from ..core.reader import CCHParser
    
    analyzer = FieldAnalyzer(yaml_path=yaml_path)
    parser = CCHParser()
    
    data_path = Path(data_dir)
    for file_path in data_path.glob("*.txt"):
        print(f"Analyzing {file_path.name}...")
        try:
            for doc in parser.parse_multi_file(str(file_path)):
                analyzer.analyze_document(doc)
        except Exception as e:
            print(f"  Error: {e}")
    
    analyzer.generate_report(output_dir)
    print("Analysis complete!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python -m cch_parser_pkg.tools.analyzer <data_dir> <yaml_path> <output_dir>")
        sys.exit(1)
    
    run_analysis(sys.argv[1], sys.argv[2], sys.argv[3])
