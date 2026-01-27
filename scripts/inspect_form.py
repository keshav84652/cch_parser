
import sys
import os
import json
from pathlib import Path

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cch_parser_pkg import CCHParser

def inspect_form(target_code, limit=3):
    parser = CCHParser()
    input_file = Path("data/2024 tax returns.txt")
    
    if not input_file.exists():
         # Try relative
         input_file = Path("../data/2024 tax returns.txt")
    
    print(f"Inspecting Code {target_code} in {input_file} (First {limit} samples)...")
    
    count = 0
    for doc in parser.parse_multi_file(str(input_file)):
        if target_code in doc.forms:
            form = doc.forms[target_code]
            print(f"\n--- Sample {count + 1} (Client: {doc.client_id}) ---")
            # Print first entry
            if form.entries:
                entry = form.entries[0]
                # Print all fields
                for k, v in entry.fields.items():
                    print(f"  Field {k}: {v.value}")
            
            count += 1
            if count >= limit:
                break

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_form.py <form_code>")
        sys.exit(1)
        
    code = sys.argv[1]
    inspect_form(code)
