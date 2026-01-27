import sys
sys.path.insert(0, ".")
from cch_parser_pkg import CCHParser

parser = CCHParser()
target_client = "Arvind L Suthar"

for doc in parser.parse_multi_file("data/2024 tax returns.txt"):
    tr = parser.to_tax_return(doc)
    if tr.taxpayer.full_name == target_client:
        print(f"=== {tr.taxpayer.full_name} ===")
        
        print("\n--- 1099-R (Form 184) ---")
        for i, e in enumerate(doc.get_form_entries("184")):
            name = e.get("40")
            acct = e.get("84")
            print(f"[{i}] Name: {name} | Acct: {acct}")
            
        print("\n--- K-1 1065 (Form 185) ---")
        for i, e in enumerate(doc.get_form_entries("185")):
            name_46 = e.get("46")
            name_956 = e.get("956")
            name_90 = e.get("90")
            if any(term in str(name_46 or "").upper() or term in str(name_956 or "").upper() or term in str(name_90 or "").upper() for term in ["TRINITY", "TPEG"]):
                print(f"[{i}] .46: {name_46} | .956: {name_956} | .90: {name_90}")
        break
