# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CCH Parser extracts and structures data from CCH Tax Software export files. It parses proprietary UTF-16LE encoded files containing tax return data (Forms, Sections, Entries, Fields) and converts them into structured Python objects.

## Commands

```bash
# Generate document checklists for INDIVIDUALS
python3 generate_checklists.py <cch_file> [tax_year]
python3 generate_checklists.py data/samples/I/KASATS.txt 2025
python3 generate_checklists.py "data/2024 tax returns.txt" --multi 2025

# Generate document checklists for BUSINESSES (P, S, C, F)
python3 generate_business_checklists.py <cch_file> [tax_year]
python3 generate_business_checklists.py data/samples/P/APPHOSP.txt 2025
python3 generate_business_checklists.py "data/2024 tax returns.txt" --multi 2025

# Income summary report (quick overview of all clients)
python3 income_summary.py "data/2024 tax returns.txt"

# Verify field mappings (raw CCH vs extracted values)
python3 compare_mappings.py

# Extract sample returns from master file
python3 extract_samples.py
```

## Architecture

### Data Flow
```
CCH File (UTF-16LE) → CCHReader → CCHDocument → CCHConverter → TaxReturn
```

### Core Components

**cch_parser_pkg/** - Main library
- `CCHParser` (in `__init__.py`) - Main entry point combining reader + converter
- `core/reader.py` - Parses CCH export format into `CCHDocument` with forms/entries/fields
- `core/converter.py` - Converts `CCHDocument` into structured `TaxReturn` objects
- `core/mapping_loader.py` - Loads field mappings from YAML
- `models/` - Dataclasses for tax entities (Person, W2, K1, etc.)

**mappings/cch_mapping.yaml** - Field mappings (form code → field number → semantic name)

### CCH File Format

Header: `**BEGIN,{year}:{type}:{client_id}:{seq},{ssn_or_ein},...`
- Types: I=Individual, P=Partnership, S=S-Corp, C=C-Corp, F=Fiduciary

Structure:
- `\@{form_code} \ {form_name}` - Form start
- `\:{section}` - Section marker
- `\&{entry}` - Entry marker (e.g., multiple W-2s)
- `.{field} {value}` - Field data
- `\*` - End marker

**"M" Suffix Fields** - Fields ending with "M" contain **prior year** data (memo fields):
```
.70 14728        # Current year ordinary dividends: $14,728
.70M 12500       # Prior year ordinary dividends: $12,500
```

### Key Form Codes

**Individual Forms:**
- 101: Client Information (name, SSN, address)
- 151: Contact Info (phone, email)
- 180: W-2
- 182: 1099-DIV
- 183: 1099-INT
- 184: 1099-R
- 185: K-1 (Partnership 1065)
- 120: K-1 (S-Corp 1120S)
- 209: 1099-G

**Consolidated 1099 (Brokerage):**
- 881: CN-1 Header - broker name, account number, owner (T/S/J)
- 882: CN-2 Summary - interest, dividends, capital gains totals
- 883: CN-3 Details - individual security details
- 886: CN-4 Transactions - buy/sell transactions with dates, proceeds, basis

### Sample Data

`data/samples/{I,P,S,C,F}/` contains individual return files extracted from master exports, organized by return type.

## Converter Logic (How Extraction Works)

### Step-by-Step Process

1. **Taxpayer Info (Form 101 + 151)**
   - Form 101: name, SSN, address, dependents
   - Form 151: phone, email (with Form 101 as fallback)

2. **W-2s (Form 180)**
   - Each entry = one W-2
   - Field .30 = owner (T/S), .41 = employer name, .54 = wages

3. **1099-INT/DIV (Form 183, 182)**
   - Field .59 = account number
   - Field .60/.70 = current year amount
   - Field .60M/.70M = prior year amount (M suffix)

4. **Consolidated 1099 (Forms 881 + 882)** - The tricky part:
   ```
   Form 881 (headers):     Form 882 (amounts):
   Section 1: Fidelity     Section 1: Div=$2000
   Section 2: Schwab       Section 2: Div=$5000

   → Joined by section number to get:
     Fidelity: $2000, Schwab: $5000
   ```

5. **K-1s (Form 185 for 1065, Form 120 for 1120S)**
   - Field .46 = partnership/corp name
   - Field .93 = Box 1 ordinary income

### Output Structure

```
TaxReturn
├── taxpayer/spouse: Person (name, SSN, phone, email)
├── dependents: [Dependent, ...]
├── income:
│   ├── w2s, form_1099_int, form_1099_div, form_1099_r
│   ├── k1_1065, k1_1120s
│   └── ssa_1099, fbar
└── deductions:
    └── mortgage_interest, form_1095
```

## Adding New Field Mappings

1. Find the form code and field number in raw CCH data
2. Add to `mappings/cch_mapping.yaml`:
   ```yaml
   form_XXX:
     fields:
       "YY": {name: "field_name", type: "currency"}
   ```
3. Update converter.py to use the new field
4. Run `compare_mappings.py` to verify
