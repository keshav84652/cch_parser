"""
Extract only Individual (I type) returns from CCH source data files.
Creates new files with only individual returns for cleaner analysis.

BEGIN line format: **BEGIN,YEAR:TYPE:NAME:SEQ,EIN,...
- Type I = Individual
- Type P = Partnership  
- Type S = S-Corporation
- Type C = C-Corporation
"""

import re
from pathlib import Path

def extract_individual_returns(input_file: str, output_file: str) -> tuple[int, int]:
    """
    Extract only Individual returns from a CCH source file.
    
    Returns: (individual_count, other_count)
    """
    # Try multiple encodings (some files are UTF-16, some are UTF-8)
    for encoding in ['utf-16', 'utf-8', 'latin-1']:
        try:
            with open(input_file, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except (UnicodeError, UnicodeDecodeError):
            continue
    else:
        print(f"  Could not decode {input_file}")
        return 0, 0
    
    # Split into sections by **BEGIN, (keeping the delimiter in next section)
    parts = content.split('**BEGIN,')
    
    individual_sections = []
    individual_count = 0
    other_count = 0
    
    for i, part in enumerate(parts):
        if i == 0:
            # First part is header before any BEGIN - skip it
            continue
            
        if not part.strip():
            continue
        
        # Check return type - format is YEAR:TYPE:NAME:...
        # Example: 2024:I:Toibin:1,... or 2024:S:20621:1,...
        type_match = re.match(r'\d{4}:([A-Z]):', part)
        
        if type_match:
            return_type = type_match.group(1)
        else:
            # No type letter found - skip
            return_type = "?"
        
        # Keep only Individual (I) returns
        if return_type == 'I':
            individual_sections.append('**BEGIN,' + part)
            individual_count += 1
        else:
            other_count += 1
    
    # Write filtered content
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(individual_sections))
    
    return individual_count, other_count


def main():
    data_dir = Path("data")
    output_dir = Path("data/individuals_only")
    output_dir.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("EXTRACTING INDIVIDUAL RETURNS ONLY")
    print("=" * 60)
    
    for input_file in data_dir.glob("*.txt"):
        if input_file.parent.name == "individuals_only":
            continue  # Skip already filtered files
            
        output_file = output_dir / input_file.name
        
        print(f"\nProcessing: {input_file.name}")
        individual_count, other_count = extract_individual_returns(
            str(input_file), 
            str(output_file)
        )
        
        print(f"  Individual returns: {individual_count}")
        print(f"  Other returns skipped: {other_count}")
        print(f"  Saved to: {output_file}")
    
    print("\n" + "=" * 60)
    print("DONE! Individual-only files saved to data/individuals_only/")
    print("=" * 60)


if __name__ == "__main__":
    main()
