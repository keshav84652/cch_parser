# Checklist Generation - Known Issues & Fix Plan

## Overview
This document tracks remaining logic and code issues in the checklist generation system that affect usability. These are distinct from data entry issues in the CCH source.

---

## Issue #1: Detail-Level Data Leakage (Stocks Instead of Brokerages)

### Problem
The code extracts individual holdings/transactions instead of parent Brokerage Account names for Consolidated 1099s.

### Impact
- **Severity:** Critical
- **Affected Clients:** Wai Kit Tsin, Ramesh D Mirchandani, others
- **Example Output:**
  ```
  - 1099-B/DIV/INT: Alibaba Group [Taxpayer]
  - 1099-B/DIV/INT: Super Micro Computer [Taxpayer]
  ```
  (These are stocks *inside* Edward Jones, not separate tax forms)

### Root Cause
Form 886 (CN-4) contains transaction-level data with stock names in field `.30`. The current filter only removes `_Covered_*` suffixes but doesn't detect stock ticker patterns.

### Fix Plan
1. Add stock/security detection patterns to exclude:
   - Names matching ticker format (2-5 uppercase letters)
   - Names containing "Inc", "Corp", "PLC", "LLC" without an account number
   - Names matching known security types: "Treasury", "iShares", "ETF", "Bond"
2. Only include entries from Form 882/883/886 that have:
   - A valid account number pattern (`#XXXX` or similar)
   - OR match a known financial institution name list

---

## Issue #2: Fuzzy Name Deduplication (Same Account, Different Names)

### Problem
Same account number with slightly different institution names creates duplicate entries.

### Impact
- **Severity:** Medium
- **Affected Clients:** Matthew A Fermin
- **Example Output:**
  ```
  - 1099-B/DIV/INT: Robinhood Sec. #0801
  - 1099-B/DIV/INT: Robinhood Securities LLC #0801
  ```

### Root Cause
Deduplication key is `(base_broker, acct_suffix)`. If "Robinhood Sec." ≠ "Robinhood Securities LLC", they're treated as different.

### Fix Plan
1. Change deduplication priority: **Account Number first, then Name**
2. Build dedup key as `(acct_suffix, normalized_broker)` where `normalized_broker` is extracted via aggressive normalization:
   - Remove: "LLC", "Inc", "Corp", "Securities", "Sec.", "Brokerage", "Services"
   - Lowercase and strip whitespace
3. When merging duplicates, keep the **longest/most complete** name for display

---

## Issue #3: Unknown Property (Schedule E)

### Problem
Schedule E entries show "Unknown Property" when the address field is empty, even if other descriptive fields exist.

### Impact
- **Severity:** Medium
- **Affected Clients:** Reuven Schwartz, Margarito Martinez, Michael Betesh
- **Example Output:**
  ```
  - Sch E: Unknown Property
  ```

### Root Cause
Only checking field `.41` (Property Address). Other fields like description are ignored.

### Fix Plan
Implement fallback chain for Schedule E property name:
1. Field `.41` - Property Address
2. Field `.42` - Property Description (e.g., "Mixed Use", "Storefront")
3. Field `.43` or `.40` - Alternative name fields
4. Only show "Unknown Property" if ALL are empty

---

## Issue #4: Negative/Adjustment Rows as Payers

### Problem
Mathematical adjustments (negative amounts, nominee distributions) are printed as if they're banks requiring documents.

### Impact
- **Severity:** Medium
- **Affected Clients:** Michael Zweig, Eliahu Yakuel, Amir Izaki
- **Example Output:**
  ```
  - 1099-INT: (Less) Portfolio Interest (Prior: $-388.00)
  - 1099-INT: Non-ECI Portfolio Interest Income (Prior: $-3.00)
  ```

### Root Cause
No filter for adjustment entries in 1099-INT/DIV processing.

### Fix Plan
Add exclusion filter for entries where:
1. Amount is negative (for Interest/Dividends)
2. Name contains keywords: "(Less)", "Non-ECI", "Nominee", "Adjustment", "Reclass"

---

## Issue #5: Inconsistent Account Number Formatting

### Problem
Some entries use `#` separator, others use `-`.

### Impact
- **Severity:** Low
- **Affected Clients:** Matthew A Fermin
- **Example Output:**
  ```
  - E*Trade Securities LLC #7209
  - E*Trade Securities LLC-5720
  ```

### Root Cause
Inconsistent source data formatting being passed through without normalization.

### Fix Plan
Standardize in display logic:
1. Always use ` #` as the separator
2. Extract account number, then rebuild display string as `{broker} #{acct}`

---

## Issue #6: "Various" Entries Not Actionable

### Problem
Entries like "1099-INT: Various" don't tell clients what documents to provide.

### Impact
- **Severity:** Low
- **Affected Clients:** Benjamin Ahdut
- **Example Output:**
  ```
  - 1099-INT: Various (Prior: $50.00)
  ```

### Root Cause
Placeholder values in source data being passed through.

### Fix Plan
Options (choose one):
1. **Suppress** "Various" entries entirely if amount < threshold (e.g., $100)
2. **Rename** to: "Miscellaneous Interest Items (consolidated)" with a note
3. **Flag** with asterisk: "* Various sources - see prior year return for details"

---

## Implementation Priority

| Issue | Severity | Effort | Priority |
|-------|----------|--------|----------|
| #1 Detail-Level Leakage | Critical | High | 1 |
| #2 Fuzzy Deduplication | Medium | Medium | 2 |
| #4 Negative Adjustments | Medium | Low | 3 |
| #3 Unknown Property | Medium | Low | 4 |
| #5 Formatting Consistency | Low | Low | 5 |
| #6 "Various" Entries | Low | Low | 6 |

---

## Files to Modify

- `generate_checklists.py` - Main checklist generation logic
  - `_add_raw_form_items()` - Issues #1, #2, #5
  - `_populate_checklist_from_return()` - Issues #4, #6
- `cch_parser_pkg/core/converter.py` - Issue #3 (Schedule E parsing)
