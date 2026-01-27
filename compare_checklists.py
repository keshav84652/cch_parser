"""
Compare 2024 Client Checklists with 2025 Generated Checklists
"""
import pandas as pd
import os
import re

# Paths
checklist_2024_folder = r'c:\Users\kesha\Downloads\taxdocchecklistincomerecofortheyear2024'
output_folder = r'c:\Users\kesha\OneDrive\cch_parser\output'

# Map 2024 files to client names
client_map_2024 = {
    'Tax Doc Checklist-Rabiel Amirian.xlsx': 'Rabiel Amirian',
    'Arvind Suthar Check list of Tax Documents.xlsx': 'Arvind L Suthar',
    '02 Check list of Tax Documents_2024.xlsx': None,  # Generic template
    'List of tax documents.xlsx': None,  # Generic template
}

def read_2024_checklist(filepath):
    """Read 2024 checklist from Excel and extract document items."""
    xl = pd.ExcelFile(filepath)
    items = []
    
    for sheet in xl.sheet_names:
        try:
            df = pd.read_excel(xl, sheet_name=sheet, header=None)
            # Look for document entries (non-empty first column)
            for idx, row in df.iterrows():
                first_cell = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
                if first_cell and first_cell not in ['nan', 'NaN', '']:
                    # Skip header rows
                    if 'Personal Tax Documents' in first_cell or 'Tax Year' in first_cell:
                        continue
                    items.append({
                        'sheet': sheet,
                        'item': first_cell,
                        'status': str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ''
                    })
        except Exception as e:
            print(f"Error reading sheet {sheet}: {e}")
    
    return items


def read_2025_checklist(filepath):
    """Read 2025 markdown checklist and extract document items."""
    items = []
    current_section = ''
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Track section headers
            if line.startswith('## '):
                current_section = line[3:].strip()
            # Extract table rows (items)
            elif line.startswith('| ☐ |'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 5:
                    items.append({
                        'section': current_section,
                        'form': parts[2],
                        'payer': parts[3],
                        'recipient': parts[4],
                        'amount': parts[5] if len(parts) > 5 else ''
                    })
    
    return items


def compare_and_report():
    """Compare checklists and generate report."""
    report = []
    report.append("# 2024 vs 2025 Tax Checklist Comparison Report\n")
    report.append(f"Generated: 2026-01-13\n\n")
    
    # Process each 2024 file
    for filename in os.listdir(checklist_2024_folder):
        if not filename.endswith('.xlsx'):
            continue
        
        filepath_2024 = os.path.join(checklist_2024_folder, filename)
        
        report.append(f"---\n\n## 2024 File: {filename}\n\n")
        
        # Read Excel file and print structure
        try:
            xl = pd.ExcelFile(filepath_2024)
            report.append(f"**Sheets:** {', '.join(xl.sheet_names)}\n\n")
            
            for sheet in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=sheet, header=None)
                report.append(f"### Sheet: {sheet}\n\n")
                report.append("```\n")
                
                # Get first 40 rows to understand structure
                for idx, row in df.head(50).iterrows():
                    row_data = [str(c).strip() if pd.notna(c) else '' for c in row]
                    row_str = ' | '.join([r[:50] for r in row_data if r])
                    if row_str:
                        report.append(f"{row_str}\n")
                
                report.append("```\n\n")
        except Exception as e:
            report.append(f"Error reading file: {e}\n\n")
    
    # Find matching 2025 checklists
    report.append("---\n\n## Matching 2025 Generated Checklists\n\n")
    
    # Rabiel Amirian comparison
    checklist_2025 = os.path.join(output_folder, 'checklist_Rabiel Amirian_2025.md')
    if os.path.exists(checklist_2025):
        items_2025 = read_2025_checklist(checklist_2025)
        report.append("### Rabiel Amirian (2025)\n\n")
        report.append(f"Total items: {len(items_2025)}\n\n")
        
        # Summarize by section
        sections = {}
        for item in items_2025:
            sec = item['section']
            if sec not in sections:
                sections[sec] = []
            sections[sec].append(item)
        
        for sec, items in sections.items():
            report.append(f"- **{sec}**: {len(items)} items\n")
        report.append("\n")
    
    # Arvind Suthar comparison
    checklist_2025 = os.path.join(output_folder, 'checklist_Arvind L Suthar_2025.md')
    if os.path.exists(checklist_2025):
        items_2025 = read_2025_checklist(checklist_2025)
        report.append("### Arvind L Suthar (2025)\n\n")
        report.append(f"Total items: {len(items_2025)}\n\n")
        
        sections = {}
        for item in items_2025:
            sec = item['section']
            if sec not in sections:
                sections[sec] = []
            sections[sec].append(item)
        
        for sec, items in sections.items():
            report.append(f"- **{sec}**: {len(items)} items\n")
        report.append("\n")
    
    # Jayant Suthar comparison
    checklist_2025 = os.path.join(output_folder, 'checklist_Jayant L Suthar_2025.md')
    if os.path.exists(checklist_2025):
        items_2025 = read_2025_checklist(checklist_2025)
        report.append("### Jayant L Suthar (2025)\n\n")
        report.append(f"Total items: {len(items_2025)}\n\n")
        
        sections = {}
        for item in items_2025:
            sec = item['section']
            if sec not in sections:
                sections[sec] = []
            sections[sec].append(item)
        
        for sec, items in sections.items():
            report.append(f"- **{sec}**: {len(items)} items\n")
        report.append("\n")
    
    return ''.join(report)


if __name__ == '__main__':
    report = compare_and_report()
    
    # Save report
    report_path = os.path.join(output_folder, 'checklist_comparison_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Report saved to: {report_path}")
    print("\n" + "="*60 + "\n")
    print(report)
