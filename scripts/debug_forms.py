from parser import CCHParser
import json

def print_entry(name, entries):
    print(f"\n=== {name} ({len(entries)} entries) ===")
    for i, e in enumerate(entries):
        print(f"Entry {i+1}:")
        # Print all fields for inspection
        fields = {k: v.value for k, v in e.fields.items()}
        print(json.dumps(fields, indent=2))

parser = CCHParser()
docs = list(parser.parse_multi_file('selected_2024_individual_returns.txt'))
d = docs[3]  # Arvind Suthar
tr = parser.to_tax_return(d)

print(f"Data Analysis for: {tr.taxpayer.full_name}")

# Check 1099-INT for ICICI
int_entries = d.get_form_entries("181")
icici_int = [e for e in int_entries if "ICICI" in str(e.get("40")) or "ICICI" in str(e.get("41"))]
print_entry("1099-INT (Form 181) - ICICI Only", icici_int)

# Check K-1 1065 for small amounts
k1_entries = d.get_form_entries("185")
valid_k1 = [e for e in k1_entries if e.get("46") and e.get("45")]
print_entry("K-1 1065 (Form 185) - First 2 Valid Entries", valid_k1[:2])

# Check 1099-G
g_entries = d.get_form_entries("209")
print_entry("1099-G (Form 209)", g_entries)
