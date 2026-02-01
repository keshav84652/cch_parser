#!/usr/bin/env python3
"""
Business Document Checklist Generator

Generates document request checklists for business returns (Partnership, S-Corp, C-Corp).
Includes static templates by entity type plus dynamic data from CCH prior year.
"""

from pathlib import Path
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List, Optional

from cch_parser_pkg.core.reader import CCHReader


@dataclass
class Owner:
    """Partner, shareholder, or officer"""
    name: str
    ssn_ein: str = ""
    ownership_pct: Decimal = Decimal("0")
    title: str = ""  # For officers


@dataclass
class BusinessInfo:
    """Extracted business information"""
    name: str = ""
    ein: str = ""
    entity_type: str = ""  # P, S, C, F
    entity_type_name: str = ""  # Partnership, S-Corporation, etc.
    tax_year: int = 0
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""

    # Owners/partners/shareholders
    owners: List[Owner] = field(default_factory=list)

    # Prior year financials
    total_revenue: Decimal = Decimal("0")
    total_expenses: Decimal = Decimal("0")
    net_income: Decimal = Decimal("0")

    # K-1s received (other entities this business owns)
    k1s_received: List[str] = field(default_factory=list)


def extract_business_info(doc) -> BusinessInfo:
    """Extract business information from CCH document."""
    info = BusinessInfo()

    # Get basic info from document header
    info.entity_type = doc.return_type or ""
    info.tax_year = doc.tax_year or 0
    info.ein = doc.ssn or ""  # For businesses, this is the EIN

    # Map entity type to name
    type_names = {
        "P": "Partnership (1065)",
        "S": "S-Corporation (1120S)",
        "C": "C-Corporation (1120)",
        "F": "Fiduciary (1041)"
    }
    info.entity_type_name = type_names.get(info.entity_type, info.entity_type)

    # Form 101 - Entity information
    form_101_entries = list(doc.get_form_entries("101"))
    if form_101_entries:
        entry = form_101_entries[0]
        info.name = entry.get("40", "") or entry.get("41", "")
        if not info.ein:
            info.ein = entry.get("42", "")
        info.address = entry.get("43", "")
        info.city = entry.get("44", "")
        info.state = entry.get("45", "")
        info.zip_code = entry.get("46", "")

    # Use client_id as fallback name
    if not info.name:
        info.name = doc.client_id or "Unknown Entity"

    # Extract owners based on entity type
    if info.entity_type == "P":
        # Partnership - Form 271/272 for partners
        info.owners = extract_partners(doc)
    elif info.entity_type == "S":
        # S-Corp - Form 285 for shareholders, Form 590 for officers
        info.owners = extract_shareholders(doc)
    elif info.entity_type == "C":
        # C-Corp - Form 590 for officers
        info.owners = extract_officers(doc)

    # Extract prior year financials from Form 131 (income) and expense forms
    info.total_revenue, info.total_expenses, info.net_income = extract_financials(doc)

    # Extract K-1s received (Form 185 - partnerships this entity owns)
    for entry in doc.get_form_entries("185"):
        partnership_name = entry.get("46", "")
        if partnership_name:
            info.k1s_received.append(partnership_name)

    return info


def extract_partners(doc) -> List[Owner]:
    """Extract partner information from Form 271/272."""
    owners = []
    seen = set()

    # Form 271 can have TWO partners per entry using different field prefixes
    # Partner 1: .31 (first), .33 (last), .102 (SSN), .106 (pct)
    # Partner 2: .38 (first), .40 (last), .110 (SSN), .114 (pct)
    for entry in doc.get_form_entries("271"):
        # Partner 1
        first1 = entry.get("31", "")
        last1 = entry.get("33", "")
        name1 = f"{first1} {last1}".strip()
        if name1:
            ssn1 = entry.get("102", "")
            # Percentage is stored as decimal (0.8 = 80%)
            pct1 = entry.get_decimal("106") or Decimal("0")
            if pct1 and pct1 < 1:
                pct1 = pct1 * 100  # Convert to percentage

            key = (name1.lower(), ssn1)
            if key not in seen:
                seen.add(key)
                owners.append(Owner(name=name1, ssn_ein=mask_ssn(ssn1), ownership_pct=pct1))

        # Partner 2 (alternate fields)
        first2 = entry.get("38", "")
        last2 = entry.get("40", "")
        name2 = f"{first2} {last2}".strip()
        if name2:
            ssn2 = entry.get("110", "")
            pct2 = entry.get_decimal("114") or Decimal("0")
            if pct2 and pct2 < 1:
                pct2 = pct2 * 100

            key = (name2.lower(), ssn2)
            if key not in seen:
                seen.add(key)
                owners.append(Owner(name=name2, ssn_ein=mask_ssn(ssn2), ownership_pct=pct2))

    # Also check Form 272 as fallback
    if not owners:
        for entry in doc.get_form_entries("272"):
            first = entry.get("31", "") or entry.get("38", "")
            last = entry.get("40", "") or entry.get("33", "")
            name = f"{first} {last}".strip()
            if not name:
                continue

            ssn = entry.get("102", "") or entry.get("110", "")
            pct = entry.get_decimal("106") or entry.get_decimal("114") or Decimal("0")
            if pct and pct < 1:
                pct = pct * 100

            key = (name.lower(), ssn)
            if key not in seen:
                seen.add(key)
                owners.append(Owner(name=name, ssn_ein=mask_ssn(ssn), ownership_pct=pct))

    return owners


def extract_shareholders(doc) -> List[Owner]:
    """Extract shareholder information from Form 285."""
    owners = []
    seen = set()

    for entry in doc.get_form_entries("285"):
        first = entry.get("31", "")
        last = entry.get("33", "")
        name = f"{first} {last}".strip()
        if not name:
            continue

        ssn = entry.get("110", "")
        pct = entry.get_decimal("210") or Decimal("0")

        key = (name.lower(), ssn)
        if key not in seen:
            seen.add(key)
            owners.append(Owner(name=name, ssn_ein=mask_ssn(ssn), ownership_pct=pct))

    # Also check Form 271 (K-1 recipients)
    if not owners:
        for entry in doc.get_form_entries("271"):
            first = entry.get("31", "")
            last = entry.get("33", "")
            name = f"{first} {last}".strip()
            if not name:
                continue

            ssn = entry.get("115", "")

            key = (name.lower(), ssn)
            if key not in seen:
                seen.add(key)
                owners.append(Owner(name=name, ssn_ein=mask_ssn(ssn)))

    return owners


def extract_officers(doc) -> List[Owner]:
    """Extract officer information from Form 590."""
    owners = []
    seen = set()

    for entry in doc.get_form_entries("590"):
        first = entry.get("31", "")
        last = entry.get("33", "")
        name = f"{first} {last}".strip()
        if not name:
            continue

        ssn = entry.get("78", "")
        title = entry.get("106", "")
        pct = entry.get_decimal("107") or Decimal("0")  # Ownership if available

        key = (name.lower(), ssn)
        if key not in seen:
            seen.add(key)
            owners.append(Owner(name=name, ssn_ein=mask_ssn(ssn), ownership_pct=pct, title=title))

    return owners


def extract_financials(doc) -> tuple:
    """Extract prior year revenue, expenses, net income."""
    revenue = Decimal("0")
    expenses = Decimal("0")

    # Form 131 - Gross receipts/sales
    for entry in doc.get_form_entries("131"):
        gross = entry.get_decimal("50") or entry.get_decimal("54")
        if gross:
            revenue += gross

    # Form 133/134 - Expenses
    for form_code in ["133", "134"]:
        for entry in doc.get_form_entries(form_code):
            for field_num in ["50", "54", "60", "64", "70", "74"]:
                amt = entry.get_decimal(field_num)
                if amt and amt > 0:
                    expenses += amt

    net_income = revenue - expenses
    return revenue, expenses, net_income


def mask_ssn(ssn: str) -> str:
    """Mask SSN/EIN for display (show last 4 only)."""
    if not ssn:
        return ""
    # Remove non-digits
    digits = ''.join(c for c in ssn if c.isdigit())
    if len(digits) >= 4:
        return f"xxx-xx-{digits[-4:]}"
    return ssn


def format_currency(amount: Decimal) -> str:
    """Format decimal as currency."""
    if amount == 0:
        return "-"
    return f"${amount:,.0f}"


def generate_checklist(info: BusinessInfo, new_tax_year: int) -> str:
    """Generate the business document checklist."""
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append(f"BUSINESS DOCUMENT CHECKLIST: {info.name}")
    lines.append(f"EIN: {info.ein} | Type: {info.entity_type_name} | Tax Year: {new_tax_year}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("=" * 80)
    lines.append("")

    # Prior year summary
    if info.total_revenue or info.total_expenses:
        lines.append(f"PRIOR YEAR SUMMARY ({info.tax_year})")
        lines.append("-" * 40)
        lines.append(f"Total Revenue:    {format_currency(info.total_revenue):>15}")
        lines.append(f"Total Expenses:   {format_currency(info.total_expenses):>15}")
        lines.append(f"Net Income:       {format_currency(info.net_income):>15}")
        lines.append("")

    # Owners/Partners/Shareholders
    if info.owners:
        if info.entity_type == "P":
            lines.append("PARTNERS (K-1s will be issued to)")
        elif info.entity_type == "S":
            lines.append("SHAREHOLDERS (K-1s will be issued to)")
        elif info.entity_type == "C":
            lines.append("OFFICERS")
        lines.append("-" * 40)

        for i, owner in enumerate(info.owners, 1):
            pct_str = f" ({owner.ownership_pct:.2f}%)" if owner.ownership_pct else ""
            title_str = f" - {owner.title}" if owner.title else ""
            ssn_str = f" - {owner.ssn_ein}" if owner.ssn_ein else ""
            lines.append(f"{i}. {owner.name}{pct_str}{title_str}{ssn_str}")
        lines.append("")

    # K-1s received
    if info.k1s_received:
        lines.append("K-1s TO BE RECEIVED (from other entities)")
        lines.append("-" * 40)
        for k1 in info.k1s_received:
            lines.append(f"- {k1}")
        lines.append("")

    # Static checklist section
    lines.append("=" * 80)
    lines.append("DOCUMENTS NEEDED")
    lines.append("=" * 80)
    lines.append("")

    # Common to all business types
    lines.append("BOOKKEEPING & RECORDS")
    lines.append("[ ] Bank statements (all accounts, Jan-Dec)")
    lines.append("[ ] Credit card statements (all cards, Jan-Dec)")
    lines.append("[ ] Loan statements (year-end balance, interest paid)")
    lines.append("[ ] Financial statements / Trial balance (if external bookkeeper)")
    lines.append("")

    lines.append("PAYROLL (skip if we handle payroll)")
    lines.append("[ ] W-3 (Annual wage summary)")
    lines.append("[ ] Form 941 (all 4 quarters)")
    lines.append("[ ] State unemployment/withholding reports")
    lines.append("[ ] W-2 copies issued to employees")
    lines.append("")

    lines.append("1099s ISSUED BY THE BUSINESS")
    lines.append("[ ] 1099-NEC copies (contractors paid $600+)")
    lines.append("[ ] 1099-MISC copies (rent, royalties, other)")
    lines.append("")

    lines.append("ASSET PURCHASES & DISPOSITIONS")
    lines.append("[ ] Invoices for equipment/assets over $2,500")
    lines.append("[ ] Vehicle purchase or sale documents")
    lines.append("[ ] Real estate purchase/sale closing statements")
    lines.append("")

    # Entity-specific items
    if info.entity_type == "P":
        lines.append("PARTNERSHIP-SPECIFIC")
        lines.append("[ ] Capital contribution records")
        lines.append("[ ] Distribution records")
        lines.append("[ ] Partnership agreement (if new or amended)")
        lines.append("[ ] Guaranteed payment documentation")
        lines.append("")

    elif info.entity_type == "S":
        lines.append("S-CORPORATION-SPECIFIC")
        lines.append("[ ] Shareholder health insurance premiums paid")
        lines.append("[ ] Officer compensation (reasonable salary documentation)")
        lines.append("[ ] Shareholder loan activity (advances, repayments)")
        lines.append("[ ] Distribution records")
        lines.append("")

    elif info.entity_type == "C":
        lines.append("C-CORPORATION-SPECIFIC")
        lines.append("[ ] Dividend declarations and payments")
        lines.append("[ ] Officer compensation (all officers)")
        lines.append("[ ] Related party transaction details")
        lines.append("[ ] Board meeting minutes (significant transactions)")
        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def generate_business_checklist(filepath: str, new_tax_year: int) -> Optional[str]:
    """Generate checklist for a single business return."""
    reader = CCHReader()
    doc = reader.parse_file(filepath)

    if not doc:
        print(f"Failed to parse: {filepath}")
        return None

    # Skip individual returns
    if doc.return_type == "I":
        print(f"Skipping individual return: {filepath}")
        return None

    info = extract_business_info(doc)
    return generate_checklist(info, new_tax_year)


def generate_all_business_checklists(filepath: str, new_tax_year: int, output_dir: str = "output"):
    """Generate checklists for all business returns in a multi-client file."""
    reader = CCHReader()
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    count = 0
    for doc in reader.parse_multi_file(filepath):
        # Skip individual returns
        if doc.return_type == "I":
            continue

        info = extract_business_info(doc)
        checklist = generate_checklist(info, new_tax_year)

        # Save to file
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in info.name)
        safe_name = safe_name[:50]  # Limit filename length
        output_file = output_path / f"biz_checklist_{safe_name}_{new_tax_year}.txt"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(checklist)

        print(f"Generated: {output_file}")
        count += 1

    print(f"\nGenerated {count} business checklists")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 generate_business_checklists.py <cch_file> [tax_year]")
        print("       python3 generate_business_checklists.py <cch_file> --multi [tax_year]")
        sys.exit(1)

    filepath = sys.argv[1]
    multi_mode = "--multi" in sys.argv

    # Resolve path
    if not Path(filepath).exists():
        if Path(f"data/{filepath}").exists():
            filepath = f"data/{filepath}"

    # Default tax year
    tax_year = 2025
    for arg in sys.argv[2:]:
        if arg.isdigit():
            tax_year = int(arg)

    if multi_mode:
        generate_all_business_checklists(filepath, tax_year)
    else:
        checklist = generate_business_checklist(filepath, tax_year)
        if checklist:
            print(checklist)

            # Also save to file
            output_path = Path("output")
            output_path.mkdir(exist_ok=True)

            reader = CCHReader()
            doc = reader.parse_file(filepath)
            info = extract_business_info(doc)

            safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in info.name)
            output_file = output_path / f"biz_checklist_{safe_name}_{tax_year}.txt"

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(checklist)
            print(f"\nSaved to: {output_file}")
