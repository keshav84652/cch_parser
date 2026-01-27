
from cch_parser_pkg.core.reader import CCHReader
import sys

# Force encoding
sys.stdout.reconfigure(encoding='utf-8')

def debug_jackie():
    print("Debugging Jackie Atias...")
    reader = CCHReader("mappings/cch_mapping.json")
    
    # Parse file line by line to find Jackie
    target_client = "Jackie Atias"
    file_path = "data/2024 tax returns.txt"
    
    docs = reader.parse_multi_file(file_path)
    
    count = 0
    for doc in docs:
        count += 1
        print(f"Doc #{count}: {doc.client_id}")
        is_jackie = False
        
        if "Abraham" in doc.client_id or "Kalina" in doc.client_id or "KAL091" in doc.client_id:
            print(f"FOUND ABRAHAM KALINA in Doc #{count} (ID: {doc.client_id})")
            print(f"Forms Present: {list(doc.forms.keys())}")
            
            # Print ALL 1120S entries
            if "120" in doc.forms:
                print(f"Form @120 Name: {doc.forms['120'].name}")
                print("\nForm @120 Entries:")
                for entry in doc.forms["120"].entries:
                    print(f"  Entry {entry.entry}:")
                    # ... fields ...
                    corp_name = (entry.get("corporation_name") or 
                                entry.get("corporation_name_alt") or 
                                entry.get("45") or 
                                entry.get("34") or 
                                None)
                    print(f"    Corp Name Resolved: '{corp_name}'")
                    
                    if corp_name:
                        print("    -> PASS FILTER")
                    else:
                        print("    -> FAIL FILTER")
            else:
                print("\nNO Form @120 found.")
                
            # Continue searching other docs
            # break # REMOVED BREAK

if __name__ == "__main__":
    debug_jackie()
