#!/usr/bin/env python3
"""Extract sample returns from master file into individual files."""

import re
from pathlib import Path

# Sample returns to extract by type
SAMPLES = {
    'I': ['ASUTHAR', 'KASATS', 'AHDU098', 'ITIELKAP', 'AHolder', '3070', 'BLAUS988', '20288'],
    'P': ['APPHOSP', 'EASYDOUG', '20E66LLC'],
    'S': ['STARLING', 'PLNINC'],
    'C': ['KASATCPA', 'Publishing'],
    'F': ['RASD'],
}

# Pattern to match header: **BEGIN,{year}:{type}:{client_id}:
HEADER_PATTERN = re.compile(r'\*\*BEGIN,(\d{4}):([IPSCF]):([^:]+):')


def read_master_file(filepath: Path) -> str:
    """Read UTF-16LE encoded master file."""
    with open(filepath, 'r', encoding='utf-16-le') as f:
        content = f.read()
        if content.startswith('\ufeff'):
            content = content[1:]
        return content


def extract_returns(master_content: str):
    """Parse master file and yield (type, client_id, content) tuples."""
    lines = master_content.split('\n')
    current_lines = []
    current_type = None
    current_client_id = None
    current_year = None

    for line in lines:
        match = HEADER_PATTERN.match(line)
        if match:
            # Save previous return
            if current_lines and current_type and current_client_id:
                yield (current_year, current_type, current_client_id, '\n'.join(current_lines))

            # Start new return
            current_year = int(match.group(1))
            current_type = match.group(2)
            current_client_id = match.group(3)
            current_lines = [line]
        elif current_lines:
            current_lines.append(line)

    # Yield last return
    if current_lines and current_type and current_client_id:
        yield (current_year, current_type, current_client_id, '\n'.join(current_lines))


def main():
    project_root = Path(__file__).parent
    master_file = project_root / 'data' / '2024 tax returns.txt'
    samples_dir = project_root / 'data' / 'samples'

    print(f"Reading master file: {master_file}")
    content = read_master_file(master_file)
    print(f"Master file size: {len(content):,} characters")

    # Build lookup of all client_ids we need
    needed = {}
    for return_type, client_ids in SAMPLES.items():
        for cid in client_ids:
            needed[cid] = return_type

    print(f"\nLooking for {len(needed)} sample returns...")

    found = set()
    for year, return_type, client_id, return_content in extract_returns(content):
        if year != 2024:
            continue

        if client_id in needed:
            # Verify the return type matches
            expected_type = needed[client_id]
            if return_type != expected_type:
                print(f"  WARNING: {client_id} is type {return_type}, expected {expected_type}")
                continue

            # Check for Form 101 (individual taxpayer data marker)
            has_form_101 = '\\@101 \\' in return_content

            output_file = samples_dir / return_type / f"{client_id}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(return_content)

            found.add(client_id)
            status = "with Form 101" if has_form_101 else "NO Form 101"
            print(f"  {return_type}/{client_id}.txt ({len(return_content):,} chars, {status})")

    # Report missing
    missing = set(needed.keys()) - found
    if missing:
        print(f"\nMISSING: {missing}")
    else:
        print(f"\nAll {len(found)} samples extracted successfully!")


if __name__ == '__main__':
    main()
