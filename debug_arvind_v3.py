import sys
import json
sys.path.insert(0, ".")
from cch_parser_pkg import CCHParser

parser = CCHParser()
target_client = "Arvind L Suthar"
results = {
    "1099R": [],
    "K1_Trinity": []
}

for doc in parser.parse_multi_file("data/2024 tax returns.txt"):
    tr = parser.to_tax_return(doc)
    if tr.taxpayer.full_name == target_client:
        for i, e in enumerate(doc.get_form_entries("184")):
            results["1099R"].append({
                "index": i,
                "name": e.get("40"),
                "acct": e.get("84"),
                "fields": {k: v.value for k, v in e.fields.items()}
            })
            
        for i, e in enumerate(doc.get_form_entries("185")):
            found = False
            for val in e.fields.values():
                if any(term in str(val.value).upper() for term in ["TRINITY", "TPEG", "CRESTVIEW"]):
                    found = True
                    break
            if found:
                results["K1_Trinity"].append({
                    "index": i,
                    "fields": {k: v.value for k, v in e.fields.items()}
                })
        break

with open("arvind_debug_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("Saved to arvind_debug_results.json")
