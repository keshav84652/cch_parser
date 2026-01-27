"""Test: Verify skeleton entries are filtered for Michael Betesh"""
import sys
sys.path.insert(0, '.')

from generate_checklists import generate_detailed_checklist

# Generate checklist for Michael Betesh
checklists = generate_detailed_checklist('data/2024 tax returns.txt', 2025)

# Find Michael Betesh's checklist
betesh_checklist = None
for c in checklists:
    if 'betesh' in c.client_name.lower():
        betesh_checklist = c
        break

if not betesh_checklist:
    print("ERROR: Could not find Michael Betesh checklist")
    exit(1)

print("="*60)
print("MICHAEL BETESH CHECKLIST - 1099-INT/DIV ITEMS")
print("="*60)

int_items = [i for i in betesh_checklist.items if '1099-INT' in i.form_type]
div_items = [i for i in betesh_checklist.items if '1099-DIV' in i.form_type]

print(f"\n1099-INT items: {len(int_items)}")
for i in int_items:
    print(f"  - {i.payer_name} | {i.prior_year_amount}")

print(f"\n1099-DIV items: {len(div_items)}")
for i in div_items:
    print(f"  - {i.payer_name} | {i.prior_year_amount}")

print("\n" + "="*60)
print("EXPECTED: AXA Advisors entries should be FILTERED OUT")
print("          (they were skeleton entries with no amounts)")
print("="*60)

# Check if any AXA entries exist
axa_items = [i for i in betesh_checklist.items if 'AXA' in (i.payer_name or '')]
if axa_items:
    print(f"\n❌ FAIL: Found {len(axa_items)} AXA entries (should be 0)")
    for i in axa_items:
        print(f"  - {i.form_type}: {i.payer_name}")
else:
    print("\n✓ SUCCESS: No AXA entries found (skeleton filter working)")
