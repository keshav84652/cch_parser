
import sys
import os
from pathlib import Path

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cch_parser_pkg import CCHParser

def verify():
    parser = CCHParser()
    data_path = Path("data/2024 tax returns.txt")
    
    if not data_path.exists():
        print("Data file not found!")
        return

    print(f"Scanning {data_path}...")
    
    targets = ["AHDU098", "20288", "Barak Naveh"]
    found_count = 0
    
    for doc in parser.parse_multi_file(str(data_path)):
        if doc.client_id in targets or any(t in doc.client_id for t in targets):
            tr = parser.converter.to_tax_return(doc)
            print(f"\n--- Client: {tr.client_id} ---")
            found_count += 1
            
            # Check 1095-C
            if hasattr(tr.deductions, 'form_1095_c') and tr.deductions.form_1095_c:
                print(f"[PASS] Form 1095-C Found: {len(tr.deductions.form_1095_c)} items")
                for f in tr.deductions.form_1095_c:
                    print(f"  Employer: {f.employer_name}")
            else:
                print("[INFO] No 1095-C found")

            # Check 1099-MISC
            if hasattr(tr.income, 'form_1099_misc') and tr.income.form_1099_misc:
                print(f"[PASS] Form 1099-MISC Found: {len(tr.income.form_1099_misc)} items")
                for f in tr.income.form_1099_misc:
                    print(f"  Payer: {f.payer_name}, Other Inc: {f.other_income}")
            else:
                print("[INFO] No 1099-MISC found")

            # Check Balance Sheet
            if hasattr(tr, 'balance_sheet') and tr.balance_sheet:
                 print(f"[PASS] Balance Sheet Found: {len(tr.balance_sheet.items)} items")
                 for item in tr.balance_sheet.items[:5]:
                     print(f"  Item: {item.description} = {item.amount}")
            else:
                print("[INFO] No Balance Sheet found")

if __name__ == "__main__":
    verify()
