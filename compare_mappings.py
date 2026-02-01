#!/usr/bin/env python3
"""
Verify field mappings with side-by-side comparison.
Output format: Raw CCH Field | Mapped Value | Match Status
"""

from pathlib import Path
from datetime import datetime

from cch_parser_pkg.core.reader import CCHReader
from cch_parser_pkg.core.converter import CCHConverter


def get_field(doc, form_id: str, field_num: str, entry_idx: int = 1) -> str:
    """Get a specific field value from a form.
    field_num should be without the leading dot (e.g., '40' not '.40')
    """
    # Remove leading dot if present
    if field_num.startswith("."):
        field_num = field_num[1:]

    form = doc.forms.get(form_id)
    if not form:
        return ""
    for entry in form.entries:
        if entry.entry == entry_idx:
            field = entry.fields.get(field_num)
            return field.value if field else ""
    return ""


def get_all_entries(doc, form_id: str) -> list:
    """Get all entries for a form."""
    form = doc.forms.get(form_id)
    if not form:
        return []
    return list(form.entries)


def format_comparison(sample_path: Path, reader: CCHReader, converter: CCHConverter) -> str:
    """Create side-by-side comparison for a sample."""

    docs = list(reader.parse_multi_file(str(sample_path)))
    if not docs:
        return f"ERROR: No documents in {sample_path.name}"

    doc = docs[0]
    return_type = doc.return_type

    # Use appropriate formatter based on return type
    if return_type == "I":
        return format_individual(doc, sample_path, converter)
    elif return_type == "P":
        return format_partnership(doc, sample_path)
    elif return_type == "S":
        return format_scorp(doc, sample_path)
    elif return_type == "C":
        return format_ccorp(doc, sample_path)
    elif return_type == "F":
        return format_fiduciary(doc, sample_path)
    else:
        return f"Unknown return type: {return_type}"


def format_individual(doc, sample_path: Path, converter: CCHConverter) -> str:
    """Format comparison for Individual (1040) returns."""
    tr = converter.convert(doc)

    lines = []
    lines.append("=" * 100)
    lines.append(f"SAMPLE: {sample_path.name}")
    lines.append(f"Client ID: {doc.client_id} | Tax Year: {doc.tax_year} | Type: {doc.return_type}")
    lines.append("=" * 100)

    # ========== FORM 101 - TAXPAYER INFO ==========
    lines.append("")
    lines.append("FORM 101 - TAXPAYER INFORMATION")
    lines.append("-" * 100)
    lines.append(f"{'Field':<8} {'Raw CCH Value':<35} {'Mapped To':<25} {'Extracted Value':<30}")
    lines.append("-" * 100)

    # Taxpayer
    mappings_101 = [
        (".40", "taxpayer.first_name", lambda: tr.taxpayer.first_name if tr.taxpayer else ""),
        (".41", "taxpayer.middle", lambda: tr.taxpayer.middle_initial if tr.taxpayer else ""),
        (".42", "taxpayer.last_name", lambda: tr.taxpayer.last_name if tr.taxpayer else ""),
        (".44", "taxpayer.ssn", lambda: tr.taxpayer.ssn if tr.taxpayer else ""),
        (".60", "taxpayer.occupation", lambda: tr.taxpayer.occupation if tr.taxpayer else ""),
        (".61", "taxpayer.dob", lambda: tr.taxpayer.dob.strftime("%m/%d/%Y") if tr.taxpayer and tr.taxpayer.dob else ""),
        (".45", "spouse.first_name", lambda: tr.spouse.first_name if tr.spouse else ""),
        (".46", "spouse.middle", lambda: tr.spouse.middle_initial if tr.spouse else ""),
        (".47", "spouse.last_name", lambda: tr.spouse.last_name if tr.spouse else ""),
        (".49", "spouse.ssn", lambda: tr.spouse.ssn if tr.spouse else ""),
        (".67", "spouse.occupation", lambda: tr.spouse.occupation if tr.spouse else ""),
        (".68", "spouse.dob", lambda: tr.spouse.dob.strftime("%m/%d/%Y") if tr.spouse and tr.spouse.dob else ""),
        (".80", "address.street", lambda: tr.address.street if tr.address else ""),
        (".82", "address.city", lambda: tr.address.city if tr.address else ""),
        (".83", "address.state", lambda: tr.address.state if tr.address else ""),
        (".84", "address.zip", lambda: tr.address.zip_code if tr.address else ""),
    ]

    for field_num, mapped_to, get_value in mappings_101:
        raw = get_field(doc, "101", field_num)
        extracted = get_value()
        match = "✓" if raw and extracted else ("" if not raw else "✗")
        lines.append(f"{field_num:<8} {raw:<35} {mapped_to:<25} {extracted:<30} {match}")

    # ========== DEPENDENTS ==========
    dep_mappings = [
        (1, ".110", ".112", ".114", ".115", ".140"),
        (2, ".117", ".119", ".121", ".122", ".152"),
        (3, ".124", ".126", ".128", ".129", ".164"),
        (4, ".131", ".133", ".135", ".136", ".176"),
    ]

    lines.append("")
    lines.append("DEPENDENTS")
    lines.append("-" * 100)

    for i, (dep_num, first_f, last_f, ssn_f, rel_f, dob_f) in enumerate(dep_mappings):
        raw_first = get_field(doc, "101", first_f)
        if not raw_first:
            continue

        dep = tr.dependents[i] if i < len(tr.dependents) else None

        lines.append(f"Dependent {dep_num}:")
        lines.append(f"  {first_f:<6} {raw_first:<35} {'first_name':<25} {dep.first_name if dep else '':<30}")

        raw_last = get_field(doc, "101", last_f)
        lines.append(f"  {last_f:<6} {raw_last:<35} {'last_name':<25} {dep.last_name if dep else '':<30}")

        raw_ssn = get_field(doc, "101", ssn_f)
        lines.append(f"  {ssn_f:<6} {raw_ssn:<35} {'ssn':<25} {dep.ssn if dep else '':<30}")

        raw_rel = get_field(doc, "101", rel_f)
        lines.append(f"  {rel_f:<6} {raw_rel:<35} {'relationship':<25} {dep.relationship if dep else '':<30}")

        raw_dob = get_field(doc, "101", dob_f)
        ext_dob = dep.dob.strftime("%m/%d/%Y") if dep and dep.dob else ""
        lines.append(f"  {dob_f:<6} {raw_dob:<35} {'dob':<25} {ext_dob:<30}")

    # ========== FORM 151 - CONTACT INFO ==========
    lines.append("")
    lines.append("FORM 151 - CONTACT INFO")
    lines.append("-" * 100)

    mappings_151 = [
        (".65", "taxpayer.phone", lambda: tr.taxpayer.phone if tr.taxpayer else ""),
        (".75", "taxpayer.email", lambda: tr.taxpayer.email if tr.taxpayer else ""),
        (".76", "spouse.email", lambda: tr.spouse.email if tr.spouse else ""),
    ]

    for field_num, mapped_to, get_value in mappings_151:
        raw = get_field(doc, "151", field_num)
        extracted = get_value()
        match = "✓" if raw == extracted else ("" if not raw else "✗ MISMATCH")
        lines.append(f"{field_num:<8} {raw:<35} {mapped_to:<25} {extracted:<30} {match}")

    # ========== FORM 921 - BANK INFO ==========
    lines.append("")
    lines.append("FORM 921 - BANK ACCOUNT")
    lines.append("-" * 100)

    mappings_921 = [
        (".37", "bank_name", lambda: tr.bank_account.bank_name if tr.bank_account else ""),
        (".38", "routing_number", lambda: tr.bank_account.routing_number if tr.bank_account else ""),
        (".39", "account_number", lambda: tr.bank_account.account_number if tr.bank_account else ""),
    ]

    for field_num, mapped_to, get_value in mappings_921:
        raw = get_field(doc, "921", field_num)
        extracted = get_value()
        match = "✓" if raw == extracted else ("" if not raw else "✗")
        lines.append(f"{field_num:<8} {raw:<35} {mapped_to:<25} {extracted:<30} {match}")

    # ========== FORM 180 - W-2s ==========
    w2_entries = get_all_entries(doc, "180")
    if w2_entries:
        lines.append("")
        lines.append(f"FORM 180 - W-2 ({len(w2_entries)} entries)")
        lines.append("-" * 100)

        for entry in w2_entries:
            entry_idx = entry.entry
            lines.append(f"W-2 Entry #{entry_idx}:")

            # Find matching W-2 in converted data
            raw_ein = entry.fields.get("40")
            raw_ein_val = raw_ein.value if raw_ein else ""
            matching_w2 = None
            for w2 in (tr.income.w2s if tr.income else []):
                if w2.employer_ein == raw_ein_val:
                    matching_w2 = w2
                    break

            w2_mappings = [
                ("30", "owner", lambda w: w.owner.value if w else ""),
                ("40", "employer_ein", lambda w: w.employer_ein if w else ""),
                ("41", "employer_name", lambda w: w.employer_name if w else ""),
                ("54", "wages", lambda w: str(w.wages) if w else ""),
                ("55", "fed_withheld", lambda w: str(w.fed_tax_withheld) if w else ""),
                ("56", "ss_wages", lambda w: str(w.ss_wages) if w else ""),
                ("58", "medicare_wages", lambda w: str(w.medicare_wages) if w else ""),
            ]

            for field_num, mapped_to, get_val in w2_mappings:
                raw_field = entry.fields.get(field_num)
                raw_val = raw_field.value if raw_field else ""
                extracted = get_val(matching_w2)
                lines.append(f"  .{field_num:<6} {raw_val:<35} {mapped_to:<25} {extracted:<30}")

    # ========== FORM 185 - K-1 1065 ==========
    k1_entries = get_all_entries(doc, "185")
    if k1_entries:
        lines.append("")
        lines.append(f"FORM 185 - K-1 1065 ({len(k1_entries)} entries, {len(tr.income.k1_1065) if tr.income else 0} extracted)")
        lines.append("-" * 100)
        lines.append(f"{'#':<4} {'Partnership Name':<35} {'EIN':<15} {'Raw .93':<12} {'Extracted Ord Inc':<15}")
        lines.append("-" * 100)

        for entry in k1_entries:
            entry_idx = entry.entry
            name_field = entry.fields.get("46")
            ein_field = entry.fields.get("45")
            ord_inc_field = entry.fields.get("93")

            name = name_field.value if name_field else ""
            ein = ein_field.value if ein_field else ""
            raw_ord = ord_inc_field.value if ord_inc_field else ""

            # Find matching extracted K-1
            extracted_ord = ""
            for k1 in (tr.income.k1_1065 if tr.income else []):
                if k1.partnership_ein == ein:
                    extracted_ord = f"${k1.ordinary_income:,.0f}"
                    break

            lines.append(f"{entry_idx:<4} {name[:35]:<35} {ein:<15} {raw_ord:<12} {extracted_ord:<15}")

        if len(k1_entries) > 10:
            lines.append(f"  ... showing all {len(k1_entries)} entries")

    # ========== SUMMARY ==========
    lines.append("")
    lines.append("=" * 100)
    lines.append("EXTRACTION SUMMARY")
    lines.append("-" * 100)
    lines.append(f"Taxpayer:    {tr.taxpayer.first_name} {tr.taxpayer.last_name} | SSN: {tr.taxpayer.ssn}")
    if tr.spouse:
        lines.append(f"Spouse:      {tr.spouse.first_name} {tr.spouse.last_name} | SSN: {tr.spouse.ssn}")
    lines.append(f"Dependents:  {len(tr.dependents)}")
    lines.append(f"W-2s:        {len(tr.income.w2s) if tr.income else 0}")
    lines.append(f"K-1 (1065):  {len(tr.income.k1_1065) if tr.income else 0}")
    lines.append(f"K-1 (1120S): {len(tr.income.k1_1120s) if tr.income else 0}")
    lines.append("=" * 100)

    return "\n".join(lines)


def format_entity_header(doc, sample_path: Path, entity_type: str) -> list:
    """Common header for entity returns."""
    lines = []
    lines.append("=" * 100)
    lines.append(f"SAMPLE: {sample_path.name}")
    lines.append(f"Client ID: {doc.client_id} | Tax Year: {doc.tax_year} | Type: {doc.return_type} ({entity_type})")
    lines.append("=" * 100)
    return lines


def format_partnership(doc, sample_path: Path) -> str:
    """Format comparison for Partnership (1065) returns."""
    lines = format_entity_header(doc, sample_path, "Partnership")

    # ========== FORM 101 - ENTITY INFO ==========
    lines.append("")
    lines.append("FORM 101 - ENTITY INFORMATION")
    lines.append("-" * 100)
    lines.append(f"{'Field':<8} {'Raw CCH Value':<50} {'Description':<30}")
    lines.append("-" * 100)

    # Partnership Form 101 mappings
    entity_mappings = [
        ("40", "Entity Name"),
        ("42", "EIN"),
        ("43", "Street Address"),
        ("44", "City"),
        ("45", "State"),
        ("46", "Zip"),
        ("51", "Phone"),
        ("95", "Email"),
        ("90", "Business Type"),
        ("91", "Business Description"),
        ("92", "NAICS Code"),
        ("93", "Date Formed"),
        ("30", "State Code"),
    ]

    for field_num, desc in entity_mappings:
        raw = get_field(doc, "101", field_num)
        lines.append(f".{field_num:<7} {raw:<50} {desc:<30}")

    # ========== FORM 285 - PARTNERS ==========
    partner_entries = get_all_entries(doc, "285")
    if partner_entries:
        lines.append("")
        lines.append(f"FORM 285 - PARTNERS ({len(partner_entries)} entries)")
        lines.append("-" * 100)

        for entry in partner_entries[:5]:
            entry_idx = entry.entry
            name = entry.fields.get("40")
            ein = entry.fields.get("44")
            pct = entry.fields.get("65")
            lines.append(f"Partner #{entry_idx}: {name.value if name else ''} | EIN: {ein.value if ein else ''} | Profit %: {pct.value if pct else ''}")

        if len(partner_entries) > 5:
            lines.append(f"  ... and {len(partner_entries) - 5} more partners")

    lines.append("")
    lines.append("=" * 100)
    return "\n".join(lines)


def format_scorp(doc, sample_path: Path) -> str:
    """Format comparison for S-Corp (1120S) returns."""
    lines = format_entity_header(doc, sample_path, "S-Corporation")

    lines.append("")
    lines.append("FORM 101 - ENTITY INFORMATION")
    lines.append("-" * 100)
    lines.append(f"{'Field':<8} {'Raw CCH Value':<50} {'Description':<30}")
    lines.append("-" * 100)

    entity_mappings = [
        ("40", "Entity Name"),
        ("42", "EIN"),
        ("43", "Street Address"),
        ("44", "City"),
        ("45", "State"),
        ("46", "Zip"),
        ("51", "Phone"),
        ("95", "Email"),
        ("90", "Business Type"),
        ("91", "Business Description"),
        ("92", "NAICS Code"),
    ]

    for field_num, desc in entity_mappings:
        raw = get_field(doc, "101", field_num)
        lines.append(f".{field_num:<7} {raw:<50} {desc:<30}")

    # ========== FORM 285 - SHAREHOLDERS ==========
    sh_entries = get_all_entries(doc, "285")
    if sh_entries:
        lines.append("")
        lines.append(f"FORM 285 - SHAREHOLDERS ({len(sh_entries)} entries)")
        lines.append("-" * 100)

        for entry in sh_entries[:5]:
            entry_idx = entry.entry
            name = entry.fields.get("40")
            ssn = entry.fields.get("44")
            pct = entry.fields.get("58")
            lines.append(f"Shareholder #{entry_idx}: {name.value if name else ''} | SSN/EIN: {ssn.value if ssn else ''} | Ownership %: {pct.value if pct else ''}")

    lines.append("")
    lines.append("=" * 100)
    return "\n".join(lines)


def format_ccorp(doc, sample_path: Path) -> str:
    """Format comparison for C-Corp (1120) returns."""
    lines = format_entity_header(doc, sample_path, "C-Corporation")

    lines.append("")
    lines.append("FORM 101 - ENTITY INFORMATION")
    lines.append("-" * 100)
    lines.append(f"{'Field':<8} {'Raw CCH Value':<50} {'Description':<30}")
    lines.append("-" * 100)

    entity_mappings = [
        ("40", "Entity Name"),
        ("42", "EIN"),
        ("43", "Street Address"),
        ("44", "City"),
        ("45", "State"),
        ("46", "Zip"),
        ("51", "Phone"),
        ("90", "Business Type"),
        ("91", "Business Description"),
        ("92", "NAICS Code"),
    ]

    for field_num, desc in entity_mappings:
        raw = get_field(doc, "101", field_num)
        lines.append(f".{field_num:<7} {raw:<50} {desc:<30}")

    lines.append("")
    lines.append("=" * 100)
    return "\n".join(lines)


def format_fiduciary(doc, sample_path: Path) -> str:
    """Format comparison for Fiduciary (1041) returns."""
    lines = format_entity_header(doc, sample_path, "Fiduciary/Trust")

    lines.append("")
    lines.append("FORM 101 - ENTITY INFORMATION")
    lines.append("-" * 100)
    lines.append(f"{'Field':<8} {'Raw CCH Value':<50} {'Description':<30}")
    lines.append("-" * 100)

    entity_mappings = [
        ("40", "Trust/Estate Name"),
        ("42", "EIN"),
        ("43", "Street Address"),
        ("44", "City"),
        ("45", "State"),
        ("46", "Zip"),
        ("51", "Phone"),
        ("90", "Entity Type"),
    ]

    for field_num, desc in entity_mappings:
        raw = get_field(doc, "101", field_num)
        lines.append(f".{field_num:<7} {raw:<50} {desc:<30}")

    lines.append("")
    lines.append("=" * 100)
    return "\n".join(lines)


def main():
    project_root = Path(__file__).parent
    samples_base = project_root / "data" / "samples"
    output_dir = project_root / "output" / "verification"
    output_dir.mkdir(parents=True, exist_ok=True)

    reader = CCHReader()
    converter = CCHConverter()

    print("Creating side-by-side verification reports...\n")

    all_reports = []

    # Process all return types
    return_types = [
        ("I", "Individual (1040)"),
        ("P", "Partnership (1065)"),
        ("S", "S-Corp (1120S)"),
        ("C", "C-Corp (1120)"),
        ("F", "Fiduciary (1041)"),
    ]

    for type_code, type_name in return_types:
        samples_dir = samples_base / type_code
        if not samples_dir.exists():
            continue

        sample_files = list(samples_dir.glob("*.txt"))
        if not sample_files:
            continue

        print(f"\n=== {type_name} ===")

        for sample_file in sorted(sample_files):
            print(f"Processing: {sample_file.name}")

            try:
                report = format_comparison(sample_file, reader, converter)
                all_reports.append(report)

                # Write individual report
                output_file = output_dir / f"{type_code}_{sample_file.stem}_comparison.txt"
                with open(output_file, "w") as f:
                    f.write(report)

                print(f"  -> {output_file.name}")
            except Exception as e:
                print(f"  ERROR: {e}")

    # Write combined report
    combined_file = output_dir / "ALL_COMPARISONS.txt"
    with open(combined_file, "w") as f:
        f.write("\n\n\n".join(all_reports))

    print(f"\nCombined report: {combined_file}")


if __name__ == "__main__":
    main()
