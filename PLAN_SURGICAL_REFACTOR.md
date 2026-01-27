# Implementation Spec: The Surgical Refactor (Incremental Improvements)

**Concept:** Maintain the existing Object-Oriented (OOP) architecture but surgically repair the specific "rot" (technical debt) that causes recurring bugs. This minimizes risk while stabilizing the codebase.

## Core Philosophy
1.  **Targeted Repairs:** Fix specific modules (`reader.py`, `converter.py`) without changing the data flow or downstream consumers.
2.  **Centralized Configuration:** Move all "magic numbers" (field IDs) into `cch_mapping.yaml`.
3.  **Code Hygiene:** Archive legacy scripts to reduce cognitive load.

---

## 1. Step-by-Step Implementation

### Step 1: The Smart Scanner Upgrade (`reader.py`)
**Problem:** Encoding issues (null bytes) and Data Loss (Memo fields overwriting parent fields).

**The Fix:**
*   **Function:** `read_file(filepath)`
    *   **Action:** Add BOM detection. `if content.startswith(b'\xff\xfe'): encoding = 'utf-16'`.
*   **Function:** `parse_line(line)`
    *   **Current:** Logic strips 'M' suffix and checks if parent key exists.
    *   **New Spec:**
        ```python
        # Store full key exactly as seen
        key = match.group(1)  # e.g., "54M"
        value = match.group(2)
        current_entry.fields[key] = value
        ```
    *   **Impact:** `converter.py` must be updated to look for `"54M"` explicitly instead of relying on the implicit overwrite behavior.

### Step 2: Logic Centralization (`cch_parser_pkg/utils.py`)
**Problem:** "Whack-a-Mole" bugs. Logic for "T/S/J" owners copies-pasted 13 times. Name resolution logic scattered.

**The Fix:**
*   **Create `utils.py`:**
    ```python
    def get_owner(entry, field="30"):
        code = entry.get(field, "T").upper()
        if code == "S": return TaxpayerType.SPOUSE
        if code == "J": return TaxpayerType.JOINT
        return TaxpayerType.TAXPAYER
    
    def resolve_name(entry, priority_fields=["46", "34", "956"]):
        for field in priority_fields:
            val = entry.get(field)
            if val and "various" not in val.lower():
                return val
        return "Unknown"
    ```
*   **Refactor `converter.py`:**
    *   Replace all `if entry.get("30") == "S"...` blocks (13 occurrences) with `owner = utils.get_owner(entry)`.
    *   Replace hard-coded name lookups with `utils.resolve_name(entry)`.

### Step 3: Workspace Sanitization
**Problem:** Root directory has 40+ junk files, making it hard to find the "real" code.

**The Fix:**
1.  **Create `archive/` folder.**
2.  **Manifest of files to move:**
    *   `test_*.py` (except units)
    *   `debug_*.py`
    *   `investigate_*.py`
    *   `check_*.py`
    *   `*.txt` (logs)
3.  **Config Cleanup:**
    *   Delete `cch_mapping.json`.
    *   Verify `cch_mapping.yaml` is the ONLY config loaded in `settings.py` or parser init.

---

## 2. Managing "Complex State" (Consolidated Forms)
The surgical approach preserves the existing `CCHDocument` DOM. This is actually an *advantage* for complex Consolidated 1099s.

**Verification:**
*   Ensure the `Consolidated1099` parser in `converter.py` still works correctly with the new "Smart Scanner" keys.
*   *Risk:* If the Consolidated parser expected `.54` to contain the "Prior" amount (because of the old overwrite bug), it will now find `.54` is empty and `.54M` has the value.
*   *Mitigation:* We must grep for all field accesses in `converter.py` and ensure they check both keys if needed: `val = entry.get("54") or entry.get("54M")`.

---

## 3. Comparison to User Pain Points

*   **"Unknown Property"**: Fixed by centralizing name resolution in `utils.py`. We can add logic: *if name is empty, try address fields*.
*   **"Spencer Duplicates"**: Fixed by adding a specific deduplication pass in `converter.py` for 1099-INT, utilizing the cleaner data.
*   **"SSA Skeletons"**: Fixed by adding a filter in the `converter.py` loop (as we already planned).

## Effort Estimate
*   **Code Volume:** ~100 lines changed.
*   **Timeline:** 1 day.
    *   Hour 1: Workspace cleanup.
    *   Hour 2: Reader BOM/Memo fix.
    *   Hour 3-5: `utils.py` creation and Converter refactor.
    *   Hour 6: Testing.
