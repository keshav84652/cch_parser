"""Check Arvind L Suthar data details"""
import sys
sys.path.insert(0, ".")
from cch_parser_pkg import CCHParser

print("=== Checking Arvind L Suthar data ===")

parser = CCHParser()
for doc in parser.parse_multi_file("data/2024 tax returns.txt"):
    tr = parser.to_tax_return(doc)
    if "Arvind" in tr.taxpayer.full_name and "Suthar" in tr.taxpayer.full_name:
        print(f"\nClient: {tr.taxpayer.full_name}")
        
        # Check 1099-R (Form 184)
        print("\n--- 1099-R (Form 184) ---")
        for i, e in enumerate(doc.get_form_entries("184")):
            print(f"Entry {i+1}:")
            print(f"  .40 (Name): {e.get('40')}")
            print(f"  .84 (Acct): {e.get('84')}")
            print(f"  .30 (Owner): {e.get('30')}")

        # Check K-1 1065 (Form 185) for missing items
        print("\n--- K-1 1065 (Form 185) - Match 'Trinity' or 'TPEG' ---")
        for i, e in enumerate(doc.get_form_entries("185")):
            # Check fields used for naming
            name_46 = e.get("46")
            name_956 = e.get("956")
            
            if "Trinity" in str(name_46) or "Trinity" in str(name_956) or \
               "TPEG" in str(name_46) or "TPEG" in str(name_956):
                 print(f"Entry {i+1}:")
                 print(f"  .46: {name_46}")
                 print(f"  .956: {name_956}")
                 print(f"  .967M: {e.get('967M')}") # Worksheet field seen earlier

        break
