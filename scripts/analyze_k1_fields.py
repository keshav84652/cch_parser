"""Analyze K-1 1065 fields to identify amount fields"""
from parser import CCHParser
from collections import defaultdict
import statistics

parser = CCHParser()
docs = list(parser.parse_multi_file('selected_2024_individual_returns.txt'))
arvind = docs[3]
k1_entries = arvind.get_form_entries("185")
valid_k1s = [e for e in k1_entries if e.get("46")]

print(f"Analyzing {len(valid_k1s)} K-1 entries for Arvind Suthar")

field_stats = defaultdict(list)

for e in valid_k1s:
    for k, v in e.fields.items():
        val = v.value
        # Check if it looks like money
        is_money = False
        try:
            if '.' in val or ',' in val or '-' in val:
                clean = val.replace(',', '').replace('.', '')
                if clean.replace('-', '').isdigit():
                    float(val.replace(',', ''))
                    is_money = True
        except:
            pass
            
        if is_money:
            field_stats[k].append(val)

print("\nPotential Money Fields (sorted by frequency):")
sorted_fields = sorted(field_stats.items(), key=lambda x: len(x[1]), reverse=True)

for field_code, values in sorted_fields:
    if len(values) < 2: continue # skip rare fields
    
    # Calculate numeric stats
    try:
        nums = [float(v.replace(',', '')) for v in values]
        avg = statistics.mean(nums)
        max_val = max(nums)
        min_val = min(nums)
    except:
        avg = 0
    
    print(f"Field .{field_code}: {len(values)} entries")
    print(f"  Range: {min_val:,.2f} to {max_val:,.2f} (Avg: {avg:,.2f})")
    print(f"  Samples: {values[:5]}")
