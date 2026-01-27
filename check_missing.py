"""Check Form 184 fields for account numbers - clean output"""
import sys
sys.path.insert(0, ".")

from cch_parser_pkg import CCHParser

parser = CCHParser()
for doc in parser.parse_multi_file("data/2024 tax returns.txt"):
    entries = list(doc.get_form_entries("184"))
    if entries and len(entries) >= 2:
        tax_return = parser.to_tax_return(doc)
        print(f"Client: {tax_return.taxpayer.full_name}")
        for i, e in enumerate(entries[:2]):
            print(f"\nEntry {i+1}:")
            for field_num in sorted(e.fields.keys(), key=lambda x: int(x) if x.isdigit() else 999):
                val = e.get(field_num)
                if val and len(str(val)) < 50:  # Skip long values
                    print(f"  .{field_num} = {val}")
        break
