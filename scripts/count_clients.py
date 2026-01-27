
import sys
import os
from pathlib import Path

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cch_parser_pkg import CCHParser

def count_clients(filepath):
    parser = CCHParser()
    try:
        count = 0
        names = set()
        print(f"Counting in {filepath.name}...")
        for doc in parser.parse_multi_file(str(filepath)):
            count += 1
            # Parse full return to get name? Or just count docs?
            # To be useful, let's get name.
            tr = parser.to_tax_return(doc)
            names.add(tr.taxpayer.full_name)
        
        print(f"  Total Entries: {count}")
        print(f"  Unique Clients: {len(names)}")
        return count
    except Exception as e:
        print(f"  Error reading {filepath.name}: {e}")
        return 0

if __name__ == "__main__":
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir = Path("../data")
    
    if not data_dir.exists():
        print("Data dir not found")
        sys.exit(1)

    for f in data_dir.glob("*.txt"):
        count_clients(f)
