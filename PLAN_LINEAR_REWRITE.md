# Implementation Spec: The Linear Pipe (Ground-Up Rewrite)

**Concept:** A complete reconstruction of the parsing pipeline focusing on speed, strictness, and a unidirectional data flow. This approach moves away from persistent object trees (DOM) toward a streaming "Scanner -> Logic -> Schema" model.

## Core Philosophy
1.  **Single-Pass Parsing:** Read raw text once, emit structured blocks immediately.
2.  **Fail-Fast Validation:** If a form changes or a required field is missing, fail immediately with a precise error.
3.  **Decoupled Logic:** Tax logic (calculating net amounts) is separate from Parsing logic (reading text).

---

## 1. Directory Structure
The new architecture will live in a clean `src/` directory to separate it from legacy code.

```text
src/
├── __init__.py
├── scanner.py       # Stage 1: Raw Text -> Blocks
├── logic/           # Stage 2: Blocks -> Objects
│   ├── __init__.py
│   ├── registry.py  # Maps Form Codes to Generators
│   ├── common.py    # Shared helpers (Owner, Amounts, Names)
│   └── forms/       # Individual Form Logic
│       ├── w2.py
│       ├── k1.py
│       └── ...
├── schema.py        # Stage 3: Pydantic/Dataclass Models
└── interface.py     # CLI Entry point
```

## 2. The 3-Stage Engine Details

### Stage 1: The Scanner (`src/scanner.py`)
**Goal:** Convert raw text into a stream of "Form Blocks" (Dictionaries). No domain knowledge here, just structural parsing.

**Technical Spec:**
*   **Encoding:** Use `open(..., encoding="utf-8-sig")` to automatically handle BOM. Fallback to `latin-1` only if explicit UTF-8 fails.
*   **Memo Key Storage:**
    *   *Input:* `^.54M 1250.00`
    *   *Storage:* `{"54M": "1250.00"}` (Preserve the suffix key)
    *   *Correction:* Do NOT merge into `.54`.
*   **Output Format:** Yields generic blocks.
    ```python
    {
        "client_id": "Reuven Schwartz",
        "form_code": "180",
        "line_number": 450,
        "fields": {
            "30": "T",
            "54": "10000.00",
            "54M": "9000.00"
        }
    }
    ```

### Stage 2: The Logic Engine (`src/logic/`)
**Goal:** A centralized registry that maps Form Codes (e.g., "180") to Processing Functions.

**The Registry (`registry.py`):**
```python
FORM_HANDLERS = {
    "180": forms.w2.process,
    "181": forms.income.process_1099int,
    "211": forms.rental.process_sch_e,
    # ...
}
```

**Shared Helpers (`common.py`) - The "Anti-Whack-a-Mole" Layer:**
*   `get_owner(field_30)`: Returns `Owner.JOINT` if "J", `Owner.SPOUSE` if "S", else `Owner.TAXPAYER`. **One source of truth.**
*   `get_amount(fields, keys=["54", "60"])`: Handles decimals, commas, and tries keys in order.
*   `resolve_name(fields)`: Checks priority fields (46 -> 34 -> 956) based on form type configuration.

**Handling Consolidated Forms (The "Complex State" Problem):**
*   *Challenge:* Consolidated 1099s (Form 881) link to 1099-INT (Form 181). Linear parsing makes this hard because Form 181 might come before or after 881.
*   *Solution:* **Buffered Generators**.
    1.  Scanner yields blocks.
    2.  `Logic` phase groups blocks by Client ID.
    3.  Load *all* blocks for **one client** into memory.
    4.  Run a "Linker" pass: Match 181s to 881s based on sequence numbers.
    5.  Process form handlers.
    *   *Benefit:* Keeps memory usage low (1 client at a time) but allows complex linking.

### Stage 3: The Unified Schema (`src/schema.py`)
**Goal:** A single file defining the shape of the output data.

**Key Changes:**
*   **Strict Types:** `amount: Decimal`, `date: date`, `owner: Enum`.
*   **Built-in Reporting:** The models themselves know how to format for a checklist or report.
    ```python
    @dataclass
    class W2:
        employer: str
        wages: Decimal
        owner: Owner
        
        def to_checklist_item(self):
            return f"- W-2: {self.employer} (${self.wages}) [{self.owner.name}]"
    ```

---

## 3. Migration Strategy (Zero Downtime)

We cannot simply delete the old code. We must run parallel.

1.  **Dual Run Mode:** Update `generate_checklists.py` to accept a `--engine=v2` flag.
2.  **Snapshot Testing:**
    *   Run V1 (Current) on "Reuven", "Betesh", "Arvind". Save outputs.
    *   Run V2 (New) on same files.
    *   Compare outputs. They should be *identical* except for bug fixes.
3.  **Cutover:** Once V2 matches V1 for 100% of clients, flip the default switch.

## 4. Addressing Specific User Pain Points

*   **"Unknown Property"**: Schema will enforce a `description` field. If source is missing (like Reuven), the `Logic` layer tries to construct it (from address/city/state) *before* creating the object.
*   **"Spencer Duplicates"**: `Logic` layer for 1099-INT will have a dedicated `deduplicate()` step that runs *before* creating the Schema objects, catching "T" vs "S" anomalies.
*   **"SSA Skeletons"**: `Logic` layer for SSA will explicitly check `net_benefits > 0`. If false, it simply *does not yield* a Schema object.

## Effort Estimate
*   **Code Volume:** ~450-600 lines total.
*   **Timeline:** 3-5 days.
    *   Day 1: Scanner + Schema.
    *   Day 2: Logic Helpers + W2/1099 Handlers.
    *   Day 3: Complex Forms (K1, Sch E) + Consolidated Linking.
    *   Day 4: Integration & Testing.
