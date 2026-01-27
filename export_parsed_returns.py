"""
Export full parsed return data for LLM comparison.
Creates detailed markdown files with all extracted values.
"""

from cch_parser_pkg import CCHParser
from cch_parser_pkg.models import TaxReturn
from pathlib import Path
from decimal import Decimal

def format_amount(val) -> str:
    """Format decimal amount for display"""
    if val is None:
        return "N/A"
    if isinstance(val, Decimal):
        return f"${val:,.2f}"
    return str(val)

def export_full_return(tax_return: TaxReturn, output_path: Path):
    """Export all parsed data from a tax return to markdown"""
    lines = []
    
    # Header
    lines.append(f"# Complete Parsed Return: {tax_return.taxpayer.full_name}")
    lines.append(f"**Tax Year:** {tax_return.tax_year}")
    lines.append(f"**Client ID:** {tax_return.client_id}")
    lines.append("")
    
    # Taxpayer Info
    lines.append("## Taxpayer Information")
    lines.append(f"- **Name:** {tax_return.taxpayer.full_name}")
    lines.append(f"- **SSN:** {tax_return.taxpayer.ssn or 'N/A'}")
    if tax_return.spouse:
        lines.append(f"- **Spouse:** {tax_return.spouse.full_name}")
        lines.append(f"- **Spouse SSN:** {tax_return.spouse.ssn or 'N/A'}")
    lines.append(f"- **Filing Status:** {tax_return.filing_status}")
    if tax_return.address:
        lines.append(f"- **Address:** {tax_return.address.street}, {tax_return.address.city}, {tax_return.address.state} {tax_return.address.zip_code}")
    lines.append("")
    
    # W-2s
    if tax_return.income.w2s:
        lines.append("## W-2 Forms (Employment Income)")
        lines.append("")
        for i, w2 in enumerate(tax_return.income.w2s, 1):
            lines.append(f"### W-2 #{i}: {w2.employer_name}")
            lines.append(f"- **Employer EIN:** {w2.employer_ein or 'N/A'}")
            lines.append(f"- **Employer Address:** {w2.employer_address or 'N/A'}, {w2.employer_city or ''}, {w2.employer_state or ''} {w2.employer_zip or ''}")
            lines.append(f"- **Owner:** {'Taxpayer' if str(w2.owner) == 'TaxpayerType.TAXPAYER' else 'Spouse'}")
            lines.append(f"- **Box 1 - Wages:** {format_amount(w2.wages)}")
            lines.append(f"- **Box 2 - Fed Tax Withheld:** {format_amount(w2.fed_tax_withheld)}")
            lines.append(f"- **Box 3 - SS Wages:** {format_amount(w2.ss_wages)}")
            lines.append(f"- **Box 4 - SS Tax:** {format_amount(w2.ss_tax_withheld)}")
            lines.append(f"- **Box 5 - Medicare Wages:** {format_amount(w2.medicare_wages)}")
            lines.append(f"- **Box 6 - Medicare Tax:** {format_amount(w2.medicare_tax_withheld)}")
            lines.append(f"- **State:** {w2.state or 'N/A'}")
            lines.append(f"- **State Wages:** {format_amount(w2.state_wages)}")
            lines.append(f"- **State Tax:** {format_amount(w2.state_tax)}")
            lines.append("")
    
    # 1099-INT
    if tax_return.income.form_1099_int:
        lines.append("## 1099-INT Forms (Interest Income)")
        lines.append("")
        for i, f in enumerate(tax_return.income.form_1099_int, 1):
            lines.append(f"### 1099-INT #{i}: {f.payer_name}")
            lines.append(f"- **Owner:** {'Taxpayer' if str(f.owner) == 'TaxpayerType.TAXPAYER' else 'Spouse'}")
            lines.append(f"- **Interest Income:** {format_amount(f.interest_income)}")
            lines.append(f"- **Early Withdrawal Penalty:** {format_amount(f.early_withdrawal_penalty)}")
            lines.append(f"- **Fed Tax Withheld:** {format_amount(f.fed_tax_withheld)}")
            lines.append("")
    
    # 1099-DIV
    if tax_return.income.form_1099_div:
        lines.append("## 1099-DIV Forms (Dividend Income)")
        lines.append("")
        for i, f in enumerate(tax_return.income.form_1099_div, 1):
            lines.append(f"### 1099-DIV #{i}: {f.payer_name}")
            lines.append(f"- **Owner:** {'Taxpayer' if str(f.owner) == 'TaxpayerType.TAXPAYER' else 'Spouse'}")
            lines.append(f"- **Ordinary Dividends:** {format_amount(f.ordinary_dividends)}")
            lines.append(f"- **Qualified Dividends:** {format_amount(f.qualified_dividends)}")
            lines.append(f"- **Capital Gain Dist:** {format_amount(f.capital_gain_dist)}")
            lines.append("")
    
    # 1099-R
    if tax_return.income.form_1099_r:
        lines.append("## 1099-R Forms (Retirement Distributions)")
        lines.append("")
        for i, f in enumerate(tax_return.income.form_1099_r, 1):
            lines.append(f"### 1099-R #{i}: {f.payer_name}")
            lines.append(f"- **Owner:** {'Taxpayer' if str(f.owner) == 'TaxpayerType.TAXPAYER' else 'Spouse'}")
            lines.append(f"- **Gross Distribution:** {format_amount(f.gross_distribution)}")
            lines.append(f"- **Taxable Amount:** {format_amount(f.taxable_amount)}")
            lines.append(f"- **Fed Tax Withheld:** {format_amount(f.fed_tax_withheld)}")
            lines.append(f"- **Distribution Code:** {f.distribution_code or 'N/A'}")
            lines.append("")
    
    # 1099-NEC
    if tax_return.income.form_1099_nec:
        lines.append("## 1099-NEC Forms (Non-Employee Compensation)")
        lines.append("")
        for i, f in enumerate(tax_return.income.form_1099_nec, 1):
            lines.append(f"### 1099-NEC #{i}: {f.payer_name}")
            lines.append(f"- **Owner:** {'Taxpayer' if str(f.owner) == 'TaxpayerType.TAXPAYER' else 'Spouse'}")
            lines.append(f"- **Non-Employee Compensation:** {format_amount(f.nonemployee_compensation)}")
            lines.append("")
    
    # 1099-G
    if tax_return.income.form_1099_g:
        lines.append("## 1099-G Forms (Government Payments)")
        lines.append("")
        for i, f in enumerate(tax_return.income.form_1099_g, 1):
            lines.append(f"### 1099-G #{i}: {f.payer_name}")
            lines.append(f"- **Owner:** {'Taxpayer' if str(f.owner) == 'TaxpayerType.TAXPAYER' else 'Spouse'}")
            lines.append(f"- **Unemployment:** {format_amount(f.unemployment_compensation)}")
            lines.append(f"- **State/Local Refund:** {format_amount(f.state_local_refund)}")
            lines.append("")
    
    # K-1 1065
    if tax_return.income.k1_1065:
        lines.append("## K-1 (1065) Forms (Partnership Income)")
        lines.append("")
        for i, k1 in enumerate(tax_return.income.k1_1065, 1):
            lines.append(f"### K-1 #{i}: {k1.partnership_name}")
            lines.append(f"- **EIN:** {k1.partnership_ein or 'N/A'}")
            lines.append(f"- **Owner:** {'Taxpayer' if str(k1.owner) == 'TaxpayerType.TAXPAYER' else 'Spouse'}")
            lines.append(f"- **Ordinary Income (Box 1):** {format_amount(k1.ordinary_income)}")
            lines.append(f"- **Net Rental RE Income (Box 2):** {format_amount(k1.net_rental_re_income)}")
            lines.append(f"- **Other Rental Income (Box 3):** {format_amount(k1.other_rental_income)}")
            lines.append(f"- **Guaranteed Payments (Box 4):** {format_amount(k1.guaranteed_payments)}")
            lines.append(f"- **Interest Income (Box 5):** {format_amount(k1.interest_income)}")
            lines.append(f"- **Dividends (Box 6a):** {format_amount(k1.ordinary_dividends)}")
            lines.append(f"- **Qualified Dividends (Box 6b):** {format_amount(k1.qualified_dividends)}")
            lines.append(f"- **Royalties (Box 7):** {format_amount(k1.royalties)}")
            lines.append(f"- **Net STCG (Box 8):** {format_amount(k1.net_stcg)}")
            lines.append(f"- **Net LTCG (Box 9):** {format_amount(k1.net_ltcg)}")
            lines.append("")
    
    # K-1 1120S
    if tax_return.income.k1_1120s:
        lines.append("## K-1 (1120S) Forms (S-Corp Income)")
        lines.append("")
        for i, k1 in enumerate(tax_return.income.k1_1120s, 1):
            lines.append(f"### K-1 #{i}: {k1.corporation_name}")
            lines.append(f"- **EIN:** {k1.corporation_ein or 'N/A'}")
            lines.append(f"- **Owner:** {'Taxpayer' if str(k1.owner) == 'TaxpayerType.TAXPAYER' else 'Spouse'}")
            lines.append(f"- **Ordinary Income:** {format_amount(k1.ordinary_income)}")
            lines.append("")
    
    # Schedule E (Rental Real Estate)
    if tax_return.income.schedule_e:
        lines.append("## Schedule E (Rental Real Estate)")
        lines.append("")
        for i, sch_e in enumerate(tax_return.income.schedule_e, 1):
            lines.append(f"### Property #{i}: {sch_e.property_description or 'Rental Property'}")
            lines.append(f"- **Address:** {sch_e.property_address or 'N/A'}")
            lines.append(f"- **Property Type:** {sch_e.property_type or 'N/A'}")
            lines.append(f"- **Rents Received:** {format_amount(sch_e.rents_received)}")
            lines.append(f"- **Insurance:** {format_amount(sch_e.insurance)}")
            lines.append(f"- **Mortgage Interest:** {format_amount(sch_e.mortgage_interest)}")
            lines.append(f"- **Repairs:** {format_amount(sch_e.repairs)}")
            lines.append(f"- **Taxes:** {format_amount(sch_e.taxes)}")
            lines.append(f"- **Utilities:** {format_amount(sch_e.utilities)}")
            lines.append(f"- **Depreciation:** {format_amount(sch_e.depreciation)}")
            lines.append(f"- **Other Expenses:** {format_amount(sch_e.other_expenses)}")
            lines.append(f"- **Total Expenses:** {format_amount(sch_e.total_expenses)}")
            lines.append(f"- **Net Income/Loss:** {format_amount(sch_e.net_income_loss)}")
            lines.append("")
    
    # SSA-1099
    if tax_return.income.ssa_1099:
        lines.append("## SSA-1099 Forms (Social Security)")
        lines.append("")
        for i, ssa in enumerate(tax_return.income.ssa_1099, 1):
            lines.append(f"### SSA-1099 #{i}: {ssa.beneficiary_name}")
            lines.append(f"- **Owner:** {'Taxpayer' if str(ssa.owner) == 'TaxpayerType.TAXPAYER' else 'Spouse'}")
            lines.append(f"- **Benefits Paid:** {format_amount(ssa.benefits_paid)}")
            lines.append(f"- **Net Benefits:** {format_amount(ssa.net_benefits)}")
            lines.append("")
    
    # FBAR
    if tax_return.income.fbar:
        lines.append("## FBAR (Foreign Bank Accounts)")
        lines.append("")
        for i, fbar in enumerate(tax_return.income.fbar, 1):
            lines.append(f"### FBAR #{i}: {fbar.bank_name}")
            lines.append(f"- **Owner:** {'Taxpayer' if str(fbar.owner) == 'TaxpayerType.TAXPAYER' else 'Spouse'}")
            lines.append(f"- **Account #:** {fbar.account_number or 'N/A'}")
            lines.append(f"- **Country:** {fbar.bank_country or 'N/A'}")
            lines.append(f"- **Max Value:** {format_amount(fbar.max_value)}")
            lines.append("")
    
    # 1098 Mortgage
    if tax_return.deductions.mortgage_interest:
        lines.append("## 1098 Forms (Mortgage Interest)")
        lines.append("")
        for i, m in enumerate(tax_return.deductions.mortgage_interest, 1):
            lines.append(f"### 1098 #{i}: {m.lender_name}")
            lines.append(f"- **Owner:** {'Taxpayer' if str(m.owner) == 'TaxpayerType.TAXPAYER' else 'Spouse'}")
            lines.append(f"- **Mortgage Interest:** {format_amount(m.mortgage_interest)}")
            lines.append(f"- **Outstanding Principal:** {format_amount(m.outstanding_principal)}")
            lines.append(f"- **Points Paid:** {format_amount(m.points_paid)}")
            lines.append("")
    
    # Balance Sheet
    if tax_return.balance_sheet and tax_return.balance_sheet.items:
        lines.append("## Balance Sheet Items")
        lines.append("")
        for item in tax_return.balance_sheet.items:
            lines.append(f"- **{item.description}:** {format_amount(item.amount)}")
        lines.append("")
    
    # Write file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"Exported: {output_path}")


def main():
    parser = CCHParser()
    output_dir = Path("output/parsed_returns")
    output_dir.mkdir(exist_ok=True)
    
    clients = ["Rabiel Amirian", "Jayant L Suthar", "Arvind L Suthar"]
    data_files = {
        2023: "data/2023 tax return.txt",
        2024: "data/2024 tax returns.txt"
    }
    
    for year, filepath in data_files.items():
        print(f"\nProcessing {year} returns from {filepath}...")
        
        for doc in parser.parse_multi_file(filepath):
            tax_return = parser.to_tax_return(doc)
            client_name = tax_return.taxpayer.full_name
            
            # Check if this is one of our target clients
            if any(target in client_name for target in clients):
                safe_name = client_name.replace(" ", "_")
                output_path = output_dir / f"parsed_{safe_name}_{year}.md"
                export_full_return(tax_return, output_path)

if __name__ == "__main__":
    main()
