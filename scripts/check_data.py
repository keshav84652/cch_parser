"""Check specific form data for Arvind Suthar"""
from parser import CCHParser

parser = CCHParser()
docs = list(parser.parse_multi_file('selected_2024_individual_returns.txt'))
d = docs[3]  # Arvind Suthar
tr = parser.to_tax_return(d)

print(f"Client: {tr.taxpayer.full_name}\n")

# 1099-R
print("=== 1099-R (Form 184) ===")
for r in tr.income.form_1099_r:
    print(f"  {r.payer_name}: Gross=${r.gross_distribution}, Taxable=${r.taxable_amount}")

# 1099-G 
print("\n=== 1099-G (Form 209) - Raw Data ===")
for e in d.get_form_entries("209"):
    print(f"  .40(payer)={e.get('40')}")
    print(f"  .55(unemp)={e.get('55')}, .56(refund)={e.get('56')}, .57={e.get('57')}, .58={e.get('58')}")
    print(f"  All fields: {[(k, v.value) for k,v in e.fields.items()]}")
    print()

# 1099-INT - is ICICI really in there?
print("=== 1099-INT (Form 181) ===")
for i in tr.income.form_1099_int:
    print(f"  {i.payer_name}: Interest=${i.interest_income}")

# FBAR
print("\n=== FBAR (Form 925) - Raw Data ===")
for e in d.get_form_entries("925"):
    print(f"  All fields: {[(k, v.value) for k,v in e.fields.items()]}")
