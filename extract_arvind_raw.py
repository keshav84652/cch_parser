import sys
sys.path.insert(0, ".")
from cch_parser_pkg import CCHParser

# Re-initialize parser to handle UTF-16 if necessary, 
# but mostly we just need to ensure we read the file correctly.
parser = CCHParser()
target_client = "Arvind L Suthar"
found = False

# We'll use the parser's built-in multi-file parsing which should handle encoding 
# if it's already working for the rest of the app, but let's be safe.
# The CCHParser likely uses standard open(), so we might need to check its implementation.

with open("data/arvind_suthar_2024_raw.txt", "w", encoding="utf-8") as out:
    # Note: parse_multi_file might need to be told it's UTF-16 if it doesn't auto-detect
    for doc in parser.parse_multi_file("data/2024 tax returns.txt"):
        is_arvind = False
        for entry in doc.get_form_entries("103"):
            first_name = entry.get("3", "")
            last_name = entry.get("4", "")
            if "Arvind" in first_name and "Suthar" in last_name:
                is_arvind = True
                print(f"Found client: {first_name} {last_name}")
                break
        
        if is_arvind:
            found = True
            for line in doc.lines:
                out.write(line + "\n")
            break

if found:
    print("Successfully extracted Arvind Suthar's raw data to data/arvind_suthar_2024_raw.txt")
else:
    print("Could not find Arvind L Suthar. Checking if names are capitalized differently...")
    # Try a broader search in the next step if this fails
