"""
Data Explorer Utility for CCH Tax Data

Provides helper functions to explore specific returns and forms in the 
large CCH export files. Useful for debugging issues in checklist generation.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Generator


def read_cch_file(filepath: str) -> str:
    """Read a CCH file with proper encoding detection."""
    path = Path(filepath)
    # Try UTF-16LE first (common for CCH exports)
    try:
        with open(path, 'r', encoding='utf-16-le') as f:
            content = f.read()
            if '\x00' not in content:  # Sanity check
                return content
    except:
        pass
    
    # Try UTF-8 
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        pass
    
    # Try cp1252 (Windows)
    with open(path, 'r', encoding='cp1252') as f:
        return f.read()


def extract_returns(filepath: str) -> Generator[Dict, None, None]:
    """
    Extract individual tax returns from a multi-client CCH file.
    Each return starts with **BEGIN and ends at the next **BEGIN or end of file.
    
    Yields: dict with 'header', 'client_name', 'content', 'line_start', 'line_end'
    """
    content = read_cch_file(filepath)
    lines = content.split('\n')
    
    returns = []
    current_return_start = None
    current_header = None
    
    for i, line in enumerate(lines):
        if line.startswith('**BEGIN'):
            # Save previous return if exists
            if current_return_start is not None:
                yield {
                    'header': current_header,
                    'line_start': current_return_start,
                    'line_end': i - 1,
                    'lines': lines[current_return_start:i]
                }
            current_return_start = i
            current_header = line.strip()
    
    # Don't forget the last return
    if current_return_start is not None:
        yield {
            'header': current_header,
            'line_start': current_return_start,
            'line_end': len(lines) - 1,
            'lines': lines[current_return_start:]
        }


def get_client_name_from_return(return_lines: List[str]) -> str:
    """Extract client name from return data (Form 101 fields .40, .42)."""
    first_name = ""
    last_name = ""
    
    in_form_101 = False
    for line in return_lines[:200]:  # Name is usually in first 200 lines
        line = line.strip()
        if line.startswith('\\@101 '):
            in_form_101 = True
        elif line.startswith('\\@') and in_form_101:
            in_form_101 = False
        
        if in_form_101:
            if line.startswith('.40 '):
                first_name = line[4:].strip()
            elif line.startswith('.42 '):
                last_name = line[4:].strip()
    
    return f"{first_name} {last_name}".strip()


def find_client_return(filepath: str, client_name: str) -> Optional[Dict]:
    """
    Find a specific client's return by name (case-insensitive partial match).
    
    Returns: dict with header, lines, line_start, line_end if found, else None
    """
    client_lower = client_name.lower()
    
    for tax_return in extract_returns(filepath):
        name = get_client_name_from_return(tax_return['lines'])
        if client_lower in name.lower():
            tax_return['client_name'] = name
            return tax_return
    
    return None


def extract_form_entries(return_lines: List[str], form_code: str) -> List[Dict]:
    """
    Extract all entries for a specific form from a return.
    
    Returns: list of dicts, each containing form fields as key-value pairs
    """
    entries = []
    current_entry = None
    in_form = False
    
    for line in return_lines:
        line = line.strip()
        
        # Check for form start
        if line.startswith(f'\\@{form_code} '):
            in_form = True
            current_entry = {'_form_code': form_code, '_raw_header': line}
            continue
        
        # Check for different form (end current form)
        if line.startswith('\\@') and in_form:
            if current_entry:
                entries.append(current_entry)
            in_form = False
            current_entry = None
            
            # Check if it's another instance of our form
            if line.startswith(f'\\@{form_code} '):
                in_form = True
                current_entry = {'_form_code': form_code, '_raw_header': line}
            continue
        
        # Parse field within form
        if in_form and line.startswith('.'):
            match = re.match(r'\.(\d+[A-Z]?)\s*(.*)', line)
            if match:
                field_num = match.group(1)
                field_val = match.group(2).strip()
                current_entry[field_num] = field_val
    
    # Don't forget last entry
    if current_entry:
        entries.append(current_entry)
    
    return entries


def print_client_forms(filepath: str, client_name: str, form_codes: List[str]) -> None:
    """
    Print all entries for specified forms for a specific client.
    Useful for debugging specific issues.
    """
    result = find_client_return(filepath, client_name)
    if not result:
        print(f"Client '{client_name}' not found")
        return
    
    print(f"=== Client: {result['client_name']} ===")
    print(f"Lines: {result['line_start']} - {result['line_end']}")
    print(f"Header: {result['header']}")
    print()
    
    for form_code in form_codes:
        entries = extract_form_entries(result['lines'], form_code)
        print(f"--- Form {form_code}: {len(entries)} entries ---")
        for i, entry in enumerate(entries, 1):
            print(f"\n  Entry {i}:")
            for k, v in sorted(entry.items()):
                if not k.startswith('_'):
                    print(f"    .{k} = {v}")
        print()


def analyze_brokerage_entries(filepath: str, client_name: str) -> None:
    """
    Analyze all brokerage-related entries for a client.
    Shows Form 881 (broker headers), 882 (summaries), and 886 (transactions).
    """
    print(f"\n{'='*60}")
    print(f"BROKERAGE ANALYSIS: {client_name}")
    print(f"{'='*60}\n")
    
    result = find_client_return(filepath, client_name)
    if not result:
        print(f"Client '{client_name}' not found")
        return
    
    print(f"Client: {result['client_name']}")
    print(f"Lines: {result['line_start']} - {result['line_end']}")
    
    # Form 881 - Broker Headers
    entries_881 = extract_form_entries(result['lines'], '881')
    print(f"\n--- Form 881 (Broker Headers): {len(entries_881)} entries ---")
    for e in entries_881:
        broker = e.get('34', 'N/A')
        acct = e.get('46', 'N/A')
        owner = e.get('30', 'N/A')
        print(f"  Broker: {broker} | Account: {acct} | Owner: {owner}")
    
    # Form 882 - Summaries
    entries_882 = extract_form_entries(result['lines'], '882')
    print(f"\n--- Form 882 (Summaries): {len(entries_882)} entries ---")
    for e in entries_882:
        field_30 = e.get('30', 'N/A')
        print(f"  .30 = {field_30}")
    
    # Form 886 - Transactions (can be many, show first 20)  
    entries_886 = extract_form_entries(result['lines'], '886')
    print(f"\n--- Form 886 (Transactions): {len(entries_886)} entries (showing first 20) ---")
    for e in entries_886[:20]:
        field_30 = e.get('30', 'N/A')
        field_38 = e.get('38', '')
        print(f"  .30 = {field_30}  |  .38 = {field_38}")
    if len(entries_886) > 20:
        print(f"  ... and {len(entries_886) - 20} more")


def analyze_1099_int_entries(filepath: str, client_name: str) -> None:
    """Analyze 1099-INT entries for a client (Issue #4 - negative adjustments)."""
    print(f"\n{'='*60}")
    print(f"1099-INT ANALYSIS: {client_name}")
    print(f"{'='*60}\n")
    
    result = find_client_return(filepath, client_name)
    if not result:
        print(f"Client '{client_name}' not found")
        return
    
    entries = extract_form_entries(result['lines'], '181')
    print(f"Found {len(entries)} Form 181 (1099-INT) entries:\n")
    
    for i, e in enumerate(entries, 1):
        payer = e.get('40', 'N/A')
        interest = e.get('71', 'N/A')
        owner = e.get('30', 'N/A')
        print(f"  {i}. Payer: {payer}")
        print(f"     Interest: {interest}")
        print(f"     Owner: {owner}\n")


if __name__ == "__main__":
    import sys
    
    # Default data file
    data_file = "data/2024 tax returns.txt"
    
    if len(sys.argv) < 2:
        print("Usage: python data_explorer.py <client_name> [form_codes...]")
        print("       python data_explorer.py <client_name> --brokerage")
        print("       python data_explorer.py <client_name> --1099int")
        print("\nExamples:")
        print("  python data_explorer.py 'Wai Kit' --brokerage")
        print("  python data_explorer.py 'Matthew Fermin' 881 882 886")
        print("  python data_explorer.py 'Michael Zweig' --1099int")
        sys.exit(0)
    
    client = sys.argv[1]
    
    if len(sys.argv) > 2:
        if sys.argv[2] == '--brokerage':
            analyze_brokerage_entries(data_file, client)
        elif sys.argv[2] == '--1099int':
            analyze_1099_int_entries(data_file, client)
        else:
            forms = sys.argv[2:]
            print_client_forms(data_file, client, forms)
    else:
        # Default: show brokerage info
        analyze_brokerage_entries(data_file, client)
