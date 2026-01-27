import sys
sys.path.insert(0, ".")
from cch_parser_pkg import CCHParser
from cch_parser_pkg.models import TaxpayerType

parser = CCHParser()
target_client = "Arvind L Suthar"

for doc in parser.parse_multi_file("data/2024 tax returns.txt"):
    tr = parser.to_tax_return(doc)
    if tr.taxpayer.full_name == target_client:
        print(f"=== {tr.taxpayer.full_name} ===")
        print(f"Total 1099-R entries in TaxReturn object: {len(tr.income.form_1099_r)}")
        for i, r in enumerate(tr.income.form_1099_r):
            print(f"[{i}] Payer: {r.payer_name} | Acct: {r.account_number} | Amount: {r.gross_distribution}")
            
        print("\n--- Raw Form 184 Entries ---")
        for i, e in enumerate(doc.get_form_entries("184")):
            print(f"[{i}] Field 40: {e.get('40')} | Field 84: {e.get('84')}")
            # Check for worksheet comments or M-fields that might contain Schwab/NFS
            for k, f in e.fields.items():
                if "Schwab" in str(f.value) or "National Financial" in str(f.value):
                    print(f"    - Found in Field {k}: {f.value}")
        break
