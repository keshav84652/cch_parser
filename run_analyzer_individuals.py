"""
Run CCH Field Analyzer on INDIVIDUAL-ONLY source data files.

Usage: python run_analyzer_individuals.py
"""

import sys
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from cch_parser_pkg import CCHParser
from cch_parser_pkg.tools.analyzer import FieldAnalyzer


def main():
    # Use individual-only data directory
    data_dir = Path("data/individuals_only")
    yaml_path = Path("mappings/cch_mapping.yaml")
    output_dir = Path("output/field_analysis_individuals")
    
    print("="*60)
    print("CCH FIELD ANALYZER - INDIVIDUAL RETURNS ONLY")
    print("="*60)
    
    if not data_dir.exists():
        print(f"ERROR: {data_dir} does not exist!")
        print("Run extract_individuals.py first to create individual-only source files.")
        return
    
    analyzer = FieldAnalyzer(yaml_path=str(yaml_path))
    parser = CCHParser()
    
    # Analyze all .txt files in individuals_only directory
    for file_path in data_dir.glob("*.txt"):
        print(f"\nAnalyzing {file_path.name}...")
        try:
            doc_count = 0
            for doc in parser.parse_multi_file(str(file_path)):
                analyzer.analyze_document(doc)
                doc_count += 1
            print(f"  Processed {doc_count} documents")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Generate reports
    print(f"\nGenerating reports to {output_dir}/...")
    output_dir.mkdir(exist_ok=True)
    analyzer.generate_report(str(output_dir))
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Forms analyzed: {len(analyzer.forms)}")
    for form_code, form_analysis in sorted(analyzer.forms.items())[:20]:  # First 20
        print(f"  Form {form_code}: {form_analysis.entry_count} entries, {len(form_analysis.fields)} fields")
    
    if len(analyzer.forms) > 20:
        print(f"  ... and {len(analyzer.forms) - 20} more forms")
    
    # Show key issues
    yaml_issues = analyzer.validate_against_yaml()
    mixed_issues = analyzer.detect_mixed_semantic_fields()
    
    print(f"\nValidation Issues:")
    print(f"  Unmapped fields: {len([i for i in yaml_issues if i['type'] == 'unmapped_field'])}")
    print(f"  Mixed semantic fields: {len(mixed_issues)}")


if __name__ == "__main__":
    main()
