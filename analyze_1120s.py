"""Analyze K-1 1120S field structure to find correct mappings"""
import re

fp = r'c:\Users\kesha\OneDrive\cch_parser\data\2024 tax returns.txt'
with open(fp, 'r', encoding='utf-16') as f:
    lines = f.readlines()

# Find K-1 1120S blocks by line
current_block = []
in_1120s = False
blocks = []

for line in lines:
    line = line.strip()
    if '@120' in line and '1120S' in line:
        if current_block:
            blocks.append(current_block)
        current_block = [line]
        in_1120s = True
    elif in_1120s and line.startswith('@') and '@120' not in line:
        if current_block:
            blocks.append(current_block)
        current_block = []
        in_1120s = False
    elif in_1120s:
        current_block.append(line)

print(f'Found {len(blocks)} K-1 1120S blocks')

# Analyze blocks to find income fields
for i, block in enumerate(blocks[:5]):
    print(f'\n=== Block {i+1} ===')
    for line in block:
        # Match field patterns
        m = re.match(r'^\.(\d+M?)\s+(.*)$', line)
        if m:
            field_num = m.group(1)
            field_val = m.group(2)[:60]
            print(f'  .{field_num}: {field_val}')
