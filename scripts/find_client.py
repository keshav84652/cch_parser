
import sys
import os
from pathlib import Path

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cch_parser_pkg import CCHParser

def find_client(name_part, filepath=None):
    data_path = Path(filepath) if filepath else Path("data/2024 tax returns.txt")
    print(f"Searching for '{name_part}' in {data_path}...")
    
    parser = CCHParser()
    found = False
    
    for doc in parser.parse_multi_file(str(data_path)):
        try:
            tr = parser.converter.to_tax_return(doc)
            if name_part.lower() in tr.taxpayer.full_name.lower():
                print(f"\n--- MATCH FOUND ---")
                print(f"Client ID: {tr.client_id}")
                print(f"Name: {tr.taxpayer.full_name}")
                
                keys = sorted(list(doc.forms.keys()))
                print(f"Forms ({len(keys)}): {keys}")
                
                # Check critical income forms
                check = ["181", "187", "189", "183", "206", "641", "291", "881", "228"]
                for c in check:
                    print(f"Code {c}: {'PRESENT' if c in keys else 'MISSING'}")
                    
                found = True
        except Exception as e:
            pass
            
    if not found:
        print("No match found.")

if __name__ == "__main__":
    name = "john"
    filepath = None
    if len(sys.argv) > 1:
        name = sys.argv[1]
    if len(sys.argv) > 2:
        filepath = sys.argv[2]
    find_client(name, filepath)
