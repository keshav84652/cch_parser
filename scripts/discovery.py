import sys
import os
import json
from collections import Counter
from pathlib import Path

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cch_parser_pkg import CCHParser

KNOWN_CODES = {
    # Converter.py
    "101", "921", # Client/Bank Info
    "180", # W-2
    "181", # 1099-INT
    "182", # 1099-DIV
    "184", # 1099-R
    "267", # 1099-NEC
    "209", # 1099-G
    "185", # K-1 1065
    "120", # K-1 1120S
    "190", # SSA-1099
    "925", # FBAR
    "206", # 1098
    "624", # 1095-A
    
    # Generate Checklists (Raw Items)
    "183", # 1099-MISC
    "761", # 1099-K
    "622", # 1098-E
    "208", # 1098-T
    "641", # 1095-C
    "205", # 1099-Q
    "623", # 1099-SA
    "881", # Consolidated 1099
}

def analyze():
    # Load mapping for descriptions
    mapping = {}
    mapping_file = Path("mappings/cch_mapping.json")
    if not mapping_file.exists():
        # Try checking from root
        mapping_file = Path("cch_mapping.json")
        
    if mapping_file.exists():
        try:
            with open(mapping_file, 'r') as f:
                data = json.load(f)
                mapping = data.get("forms", {})
        except Exception as e:
            print(f"Error loading mapping: {e}")

    parser = CCHParser(str(mapping_file) if mapping_file.exists() else None)
    
    # Analyze
    input_file = Path("data/2024 tax returns.txt")
    if not input_file.exists():
        # Try absolute or relative
        input_file = Path("../data/2024 tax returns.txt")
        
    if not input_file.exists():
        print(f"Input file not found: {input_file}")
        # Try finding any large txt file
        data_dir = Path("data")
        if data_dir.exists():
             files = list(data_dir.glob("*.txt"))
             if files:
                 input_file = files[0] # Pick the first one
                 print(f"Defaulting to {input_file}")

    print(f"Scanning {input_file}...")
    form_counts = Counter()
    total_docs = 0

    try:
        for doc in parser.parse_multi_file(str(input_file)):
            total_docs += 1
            for code in doc.forms.keys():
                form_counts[code] += 1
    except Exception as e:
        print(f"Scan failed: {e}")
        return
    
    # Load categories
    categories_map = {}
    if mapping_file.exists():
        try:
            with open(mapping_file, 'r') as f:
                data = json.load(f)
                form_cats = data.get("form_categories", {})
                for cat, codes in form_cats.items():
                    for c in codes:
                        categories_map[c] = cat
        except:
            pass
            
    # Report
    print(f"\nScanned {total_docs} documents.\n")
    print(f"{'Code':<6} | {'Count':<6} | {'Status':<10} | {'Category':<15} | {'Description'}")
    print("-" * 100)
    
    unknown_total = 0
    unique_unknowns = 0
    
    for code, count in form_counts.most_common():
        status = "KNOWN" if code in KNOWN_CODES else "UNKNOWN"
        cat = categories_map.get(code, "Uncategorized")
        
        # If categorized but not in KNOWN_CODES, it's a "Known Unknown" (we know what it is, but don't parse it)
        
        desc = mapping.get(code, {}).get("description", "N/A")
        print(f"{code:<6} | {count:<6} | {status:<10} | {cat:<15} | {desc}")
        
        if status == "UNKNOWN":
            unique_unknowns += 1
            unknown_total += count

    print(f"\nUnique Unknown Form Types: {unique_unknowns}")
    print(f"Total Unknown Form Instances: {unknown_total}")


if __name__ == "__main__":
    analyze()
