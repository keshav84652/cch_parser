"""Analyze all SSA-1099 entries across all clients for skeleton filter"""
from cch_parser_pkg import CCHParser

parser = CCHParser()
docs = parser.parse_multi_file('data/2024 tax returns.txt')

kept = []
removed = []

for doc in docs:
    # Get client name
    form_101 = doc.forms.get('101')
    client_name = "Unknown"
    if form_101 and form_101.entries:
        e = form_101.entries[0]
        first = e.get('40', '')
        last = e.get('42', '')
        client_name = f"{first} {last}".strip()
    
    # Check Form 190 (SSA-1099) entries
    for entry in doc.get_form_entries("190"):
        owner = entry.get('30', 'T')
        beneficiary = entry.get('48', '')
        current_amount = entry.get_decimal('42')  # Current gross benefits
        prior_amount = entry.get_decimal('42M')  # Prior year gross benefits
        net_benefits = entry.get_decimal('56')  # Net benefits
        
        entry_info = {
            'client': client_name,
            'owner': owner,
            'beneficiary': beneficiary or 'N/A',
            'current': f"${current_amount:,.2f}" if current_amount else "-",
            'prior': f"${prior_amount:,.2f}" if prior_amount else "-",
            'net_benefits': f"${net_benefits:,.2f}" if net_benefits else "-"
        }
        
        # Skeleton = no current amount
        if not current_amount or current_amount == 0:
            removed.append(entry_info)
        else:
            kept.append(entry_info)

# Write results
with open('output/ssa_skeleton_analysis.txt', 'w') as f:
    f.write("=" * 80 + "\n")
    f.write("SSA-1099 SKELETON FILTER ANALYSIS\n")
    f.write("=" * 80 + "\n\n")
    
    f.write(f"Total SSA entries found: {len(kept) + len(removed)}\n")
    f.write(f"KEPT (have current amount): {len(kept)}\n")
    f.write(f"REMOVED (no current amount): {len(removed)}\n\n")
    
    f.write("-" * 80 + "\n")
    f.write("ENTRIES TO BE KEPT\n")
    f.write("-" * 80 + "\n")
    for e in kept:
        f.write(f"\n{e['client']} [{e['owner']}]\n")
        f.write(f"  Current: {e['current']}, Prior: {e['prior']}, Net: {e['net_benefits']}\n")
    
    f.write("\n" + "-" * 80 + "\n")
    f.write("ENTRIES TO BE REMOVED (SKELETONS)\n")
    f.write("-" * 80 + "\n")
    for e in removed:
        f.write(f"\n{e['client']} [{e['owner']}]\n")
        f.write(f"  Current: {e['current']}, Prior: {e['prior']}, Net: {e['net_benefits']}\n")

print(f"Analysis written to output/ssa_skeleton_analysis.txt")
print(f"KEPT: {len(kept)}, REMOVED: {len(removed)}")
