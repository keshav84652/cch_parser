import sys
sys.path.insert(0, ".")
from cch_parser_pkg import CCHParser
from generate_checklists import DetailedChecklist, _populate_checklist_from_return, _add_raw_form_items

parser = CCHParser()
target_client = "Arvind L Suthar"

for doc in parser.parse_multi_file("data/2024 tax returns.txt"):
    tr = parser.to_tax_return(doc)
    if tr.taxpayer.full_name == target_client:
        checklist = DetailedChecklist(
            client_name=tr.taxpayer.full_name,
            tax_year=2025,
            prior_year=2024,
            taxpayer_name=tr.taxpayer.full_name,
            filing_status=tr.filing_status
        )
        
        print("\n--- Items added via _populate_checklist_from_return ---")
        _populate_checklist_from_return(checklist, tr)
        for item in checklist.items:
            if "1099-R" in item.category or "1099-R" in item.form_type:
                print(f"Payer: {item.payer_name} | Amount: {item.prior_year_amount}")
        
        print("\n--- Items added via _add_raw_form_items ---")
        checklist.items = [] # Reset for clarity
        _add_raw_form_items(doc, checklist)
        for item in checklist.items:
            if "1099-R" in item.category or "1099-R" in item.form_type:
                print(f"Payer: {item.payer_name} | Amount: {item.prior_year_amount}")
        break
