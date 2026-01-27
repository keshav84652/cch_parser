"""Analyze all forms in the full 2024 tax returns file."""
from parser import CCHParser
from collections import Counter

parser = CCHParser()
all_forms = Counter()
client_count = 0
return_types = Counter()

for doc in parser.parse_multi_file('2024 tax returns.txt'):
    client_count += 1
    for code, form in doc.forms.items():
        all_forms[code] += len(form.entries)
    
print(f"Total clients: {client_count}")
print(f"\nUnique form codes: {len(all_forms)}")
print(f"\nAll forms sorted by frequency:")
for code, count in all_forms.most_common():
    form = None
    # Get form name from last parsed doc
    print(f"  {code}: {count} entries")
