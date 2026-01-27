import sys
sys.path.insert(0, ".")
from cch_parser_pkg import CCHParser

parser = CCHParser()
target_client = "Arvind L Suthar"

for doc in parser.parse_multi_file("data/2024 tax returns.txt"):
    tr = parser.to_tax_return(doc)
    if tr.taxpayer.full_name == target_client:
        print(f"=== {tr.taxpayer.full_name} ===")
        
        print("\n--- ALL 1099-R (Form 184) ---")
        for i, e in enumerate(doc.get_form_entries("184")):
            print(f"[{i}] Name: {e.get('40')} | Acct: {e.get('84')}")
            
        print("\n--- K-1 SEARCH (Trinity/TPEG/Crestview) ---")
        # Check all fields in all 185 entries
        for i, e in enumerate(doc.get_form_entries("185")):
            found = False
            for val in e.fields.values():
                if any(term in str(val.value).upper() for term in ["TRINITY", "TPEG", "CRESTVIEW"]):
                    found = True
                    break
            if found:
                print(f"[{i}] Fields: { {k: v.value for k, v in e.fields.items() if any(term in str(v.value).upper() for term in ['TRINITY', 'TPEG', 'CRESTVIEW'])} }")
                print(f"    Full Fields for context: { {k: v.value for k, v in e.fields.items() if len(str(v.value)) < 100} }")
        break
