
import glob
import os
import re

def analyze_checklists():
    # Define paths
    paths = {
        "2025_Checklists (2024 Returns)": "c:/Users/kesha/OneDrive/cch_parser/output/*.txt",
        "2024_Checklists (2023 Returns)": "c:/Users/kesha/OneDrive/cch_parser/output/2023_checklists/*.txt"
    }

    results = {}

    for year_label, pattern in paths.items():
        files = glob.glob(pattern)
        stats = {
            "total_files": len(files),
            "files_with_unknown": 0,
            "total_unknown_entries": 0,
            "empty_or_header_only": 0,
            "doc_types": {}
        }
        
        print(f"\nAnalyzing {year_label} - {len(files)} files found...")

        for file_path in files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
                # Check for "Unknown"
                unknown_count = content.count("Unknown")
                if unknown_count > 0:
                    stats["files_with_unknown"] += 1
                    stats["total_unknown_entries"] += unknown_count
                
                # Check for content length (Header is usually ~7-8 lines)
                # If less than 10 lines and no doc bullets, likely empty
                if len(lines) < 10 and not any(line.strip().startswith("-") for line in lines):
                    stats["empty_or_header_only"] += 1
                
                # Count doc types
                doc_matches = re.findall(r'^[A-Z\s]+ \([A-Z0-9-]+\)$', content, re.MULTILINE)
                for doc in doc_matches:
                    doc = doc.strip()
                    stats["doc_types"][doc] = stats["doc_types"].get(doc, 0) + 1

        results[year_label] = stats

    # Print Summary
    print("\n" + "="*50)
    print("CHECKLIST ANALYSIS SUMMARY")
    print("="*50)
    
    for year, data in results.items():
        print(f"\ndataset: {year}")
        print(f"Total Files: {data['total_files']}")
        print(f"Files containing 'Unknown': {data['files_with_unknown']} ({data['files_with_unknown']/data['total_files']*100:.1f}%)")
        print(f"Total 'Unknown' occurrences: {data['total_unknown_entries']}")
        print(f"Empty/Header-only files: {data['empty_or_header_only']}")
        print("Document Distribution Top 5:")
        sorted_docs = sorted(data['doc_types'].items(), key=lambda x: x[1], reverse=True)[:5]
        for doc, count in sorted_docs:
            print(f"  - {doc}: {count}")

if __name__ == "__main__":
    analyze_checklists()
