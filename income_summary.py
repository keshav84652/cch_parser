#!/usr/bin/env python3
"""
Generate income summary report for all clients.
Shows total income by category for quick review.
"""

from pathlib import Path
from decimal import Decimal
from cch_parser_pkg import CCHParser

def format_currency(amount: Decimal) -> str:
    """Format decimal as currency string."""
    if amount == 0:
        return "-"
    return f"${amount:,.0f}"

def generate_summary(filepath: str):
    """Generate income summary for all clients in file."""
    parser = CCHParser()

    print("=" * 100)
    print(f"{'CLIENT NAME':<35} {'TYPE':<4} {'W-2':>12} {'1099-INT':>10} {'1099-DIV':>10} {'K-1 1065':>12} {'K-1 1120S':>12} {'TOTAL':>14}")
    print("=" * 100)

    total_clients = 0
    individuals = 0

    for doc in parser.parse_multi_file(filepath):
        tr = parser.to_tax_return(doc)
        total_clients += 1

        # Calculate totals
        w2_total = sum(w.wages or 0 for w in tr.income.w2s)
        int_total = sum(f.interest_income or 0 for f in tr.income.form_1099_int)
        div_total = sum(f.ordinary_dividends or 0 for f in tr.income.form_1099_div)
        k1_1065_total = sum(k.ordinary_income or 0 for k in tr.income.k1_1065)
        k1_1120s_total = sum(k.ordinary_income or 0 for k in tr.income.k1_1120s)

        grand_total = w2_total + int_total + div_total + k1_1065_total + k1_1120s_total

        # Determine return type
        return_type = doc.return_type or "?"
        if return_type == "I":
            individuals += 1

        # Client name
        name = tr.taxpayer.full_name if tr.taxpayer else doc.client_id
        if len(name) > 33:
            name = name[:30] + "..."

        print(f"{name:<35} {return_type:<4} {format_currency(w2_total):>12} {format_currency(int_total):>10} {format_currency(div_total):>10} {format_currency(k1_1065_total):>12} {format_currency(k1_1120s_total):>12} {format_currency(grand_total):>14}")

    print("=" * 100)
    print(f"Total clients: {total_clients} | Individuals: {individuals} | Business: {total_clients - individuals}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 income_summary.py <cch_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not Path(filepath).exists():
        # Try data/ folder
        if Path(f"data/{filepath}").exists():
            filepath = f"data/{filepath}"

    generate_summary(filepath)
