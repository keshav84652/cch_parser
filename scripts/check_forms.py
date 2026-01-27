from parser import CCHParser

parser = CCHParser()
docs = list(parser.parse_multi_file('selected_2024_individual_returns.txt'))

for i, d in enumerate(docs):
    tr = parser.to_tax_return(d)
    form_120 = d.get_form_entries("120")
    form_925 = d.get_form_entries("925")
    print(f"Client {i}: {tr.taxpayer.full_name}")
    print(f"  Form 120 (K-1 1120S): {len(form_120)} entries")
    print(f"  Form 925 (FBAR): {len(form_925)} entries")
    
    if form_120:
        e = form_120[0]
        print(f"    120 Sample: .30={e.get('30')}, .45={e.get('45')}")
    if form_925:
        e = form_925[0]
        print(f"    925 Sample: .36={e.get('36')}, .45={e.get('45')}")
