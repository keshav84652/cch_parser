
from generate_checklists import generate_all_checklists
import os

def test_fix():
    print("Testing fix on FULL dataset...")
    
    client_file = "data/2024 tax returns.txt"
    if not os.path.exists(client_file):
        print(f"File not found: {client_file}")
        return

    try:
        # Generate all checklists (in memory + file)
        # Verify logic on the returned objects
        checklists = generate_all_checklists(client_file, 2025, output_dir="output/test_verification")
        
        found_rock_built = False
        found_yelp = False
        total_unknowns = 0
        
        for chk in checklists:
            # Check 1120S
            for item in chk.items:
                if "Rock Built" in item.payer_name:
                    print(f"FOUND: Rock Built LLC in checklist for {chk.client_name}")
                    found_rock_built = True
                if "Yelp" in item.payer_name:
                    print(f"FOUND: Yelp Inc in checklist for {chk.client_name}")
                    found_yelp = True
                if "Unknown" in item.payer_name:
                    total_unknowns += 1
                    # Only print if it's the type we thought we fixed
                    if "1120S" in item.form_type or "1095-C" in item.form_type:
                         print(f"RESIDUAL FAILURE in {chk.client_name}: {item.payer_name} ({item.form_type})")
                         # Debug: Find the source object in the checklist's items?
                         # The item doesn't link back to source.
                         # But we know it came from 1120S loop.
                         # We need to access the TaxReturn object, but generate_all_checklists doesn't return it.
                         # We can't see valid objects here.
                         pass

        print(f"\nTotal Checklists: {len(checklists)}")
        print(f"Total Remaining Unknowns: {total_unknowns}")
        
        if found_rock_built:
             print("SUCCESS: Rock Built LLC found.")
        else:
             print("FAILURE: Rock Built LLC NOT found.")

        if found_yelp:
             print("SUCCESS: Yelp Inc found.")
        else:
             print("FAILURE: Yelp Inc NOT found.")
             
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_fix()
