"""
Run CCH Field Analyzer on data files.

Usage: 
  python run_analyzer.py                   # Analyze all returns
  python run_analyzer.py --individuals-only  # Only Individual (1040) returns
"""

import sys
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from cch_parser_pkg import CCHParser
from cch_parser_pkg.tools.analyzer import FieldAnalyzer


def is_individual_return(doc) -> bool:
    """Check if document is an individual (1040) return based on Form 101 entity type"""
    if "101" not in doc.forms:
        return False
    
    form_101 = doc.forms["101"]
    for entry in form_101.entries:
        entity_type = entry.get("64", "")
        # Field .64 contains entity type: "Individual", "Partnership", "S Corp", etc.
        if entity_type.lower() in ["individual", ""]:  # Empty often means individual
            return True
    return False


def main():
    data_dir = Path("data")
    yaml_path = Path("mappings/cch_mapping.yaml")
    output_dir = Path("output/field_analysis")
    
    # Check for --individuals-only flag
    individuals_only = "--individuals-only" in sys.argv or "-i" in sys.argv
    
    print("="*60)
    print("CCH FIELD ANALYZER")
    if individuals_only:
        print("MODE: Individual Returns Only (1040)")
    else:
        print("MODE: All Returns")
    print("="*60)
    
    analyzer = FieldAnalyzer(yaml_path=str(yaml_path))
    parser = CCHParser()
    
    # Analyze all .txt files in data directory
    for file_path in data_dir.glob("*.txt"):
        print(f"\nAnalyzing {file_path.name}...")
        try:
            doc_count = 0
            skipped_count = 0
            for doc in parser.parse_multi_file(str(file_path)):
                # Filter for individual returns if requested
                if individuals_only and not is_individual_return(doc):
                    skipped_count += 1
                    continue
                    
                analyzer.analyze_document(doc)
                doc_count += 1
            print(f"  Processed {doc_count} documents", end="")
            if individuals_only:
                print(f" (skipped {skipped_count} non-individual)")
            else:
                print()
        except Exception as e:
            print(f"  Error: {e}")
    
    # Generate reports
    print(f"\nGenerating reports to {output_dir}/...")
    analyzer.generate_report(str(output_dir))
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Forms analyzed: {len(analyzer.forms)}")
    for form_code, form_analysis in sorted(analyzer.forms.items()):
        print(f"  Form {form_code}: {form_analysis.entry_count} entries, {len(form_analysis.fields)} fields")
    
    # Show key issues
    yaml_issues = analyzer.validate_against_yaml()
    mixed_issues = analyzer.detect_mixed_semantic_fields()
    
    print(f"\nValidation Issues:")
    print(f"  Unmapped fields: {len([i for i in yaml_issues if i['type'] == 'unmapped_field'])}")
    print(f"  Unused YAML fields: {len([i for i in yaml_issues if i['type'] == 'unused_yaml_field'])}")
    print(f"  Mixed semantic fields: {len(mixed_issues)}")
    
    if mixed_issues:
        print("\nMixed Semantic Fields (potential mapping errors):")
        for issue in mixed_issues[:10]:
            print(f"  Form {issue['form']} .{issue['field']}: {issue['issue']}")
            print(f"    Samples: {issue['samples'][:5]}")


if __name__ == "__main__":
    main()

