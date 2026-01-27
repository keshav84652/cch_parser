import re

fp = r'c:\Users\kesha\OneDrive\cch_parser\data\2024 tax returns.txt'
with open(fp, 'r', encoding='utf-16') as f:
    content = f.read()

# Find all S-Corp K-1 blocks
blocks = re.findall(r'@120 \\ IRS-K1 1120S.*?(?=@\d|$)', content, re.DOTALL)
print(f'Total S-Corp K-1 blocks: {len(blocks)}')
print()

for i, block in enumerate(blocks[:15]):
    f34 = re.search(r'\.34 ([^\r\n]+)', block)
    f45 = re.search(r'\.45 ([^\r\n]+)', block)
    f46 = re.search(r'\.46 ([^\r\n]+)', block)
    f945 = re.search(r'\.945 ([^\r\n]+)', block)
    
    val34 = f34.group(1)[:60] if f34 else "[EMPTY]"
    val45 = f45.group(1)[:60] if f45 else "[EMPTY]"
    val46 = f46.group(1)[:60] if f46 else "[EMPTY]"
    val945 = f945.group(1)[:60] if f945 else "[EMPTY]"
    
    print(f'Block {i+1}:')
    print(f'  .34 (name):     {val34}')
    print(f'  .45 (???):      {val45}')
    print(f'  .46 (address):  {val46}')
    print(f'  .945 (???):     {val945}')
    print()
