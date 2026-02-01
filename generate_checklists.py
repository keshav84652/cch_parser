"""
CCH Tax Document Checklist Generator - Enhanced Version

Generates detailed client document checklists with employer/payer names
and recipient information (taxpayer/spouse/joint).
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from cch_parser_pkg import CCHParser, CCHDocument
from cch_parser_pkg.models import TaxReturn, TaxpayerType, FilingStatus


@dataclass
class DetailedChecklistItem:
    """Single item with payer/employer details"""
    category: str
    form_type: str
    payer_name: str
    recipient: str  # Taxpayer, Spouse, Joint
    prior_year_amount: str = ""
    notes: str = ""


@dataclass
class DetailedChecklist:
    """Enhanced checklist with specific names and amounts"""
    client_name: str
    tax_year: int
    prior_year: int
    generated_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    taxpayer_name: str = ""
    spouse_name: str = ""
    filing_status: FilingStatus = FilingStatus.SINGLE
    items: List[DetailedChecklistItem] = field(default_factory=list)
    _seen_items: set = field(default_factory=set, repr=False)  # Track unique items
    
    def add_item(self, category: str, form_type: str, payer_name: str, 
                 recipient: str, prior_year_amount: str = "", notes: str = ""):
        # Forms that should NEVER be deduplicated (may have multiple legitimate entries)
        # - Income forms: 1099-INT/DIV/B could have multiple accounts at same bank
        # - Property forms: 1098, Sch E could have multiple properties
        # NOTE: W-2 and K-1 CAN be deduplicated since recipient (Taxpayer/Spouse) is in the key
        no_dedup_form_types = {
            "1099-INT", "1099-DIV", "1099-B/DIV/INT", "1099-R", 
            "1099-NEC", "1099-MISC", "1099-K", "1099-SA", "1098"
        }
        
        # Only deduplicate if:
        # 1. Form type is not in the no-dedup list, OR
        # 2. Payer name contains "Unknown" (clearly a data issue)
        # Filter out invalid/placeholder payers
        payer_lower = payer_name.lower().strip()
        if payer_lower in ["estimate", "various", "unknown"] and "unknown" not in payer_lower: 
             # Keep "Unknown" if it's explicit like "Unknown Employer", but skip generic "Estimate"
             if payer_lower == "estimate":
                 return
        
        # Single filer duplicate spouse skip:
        # If filing status is Single and this is a Spouse entry, check if matching Taxpayer exists
        # Note: We need to track Taxpayer entries even for no-dedup forms for this check to work
        single_filer_check_key = (category, form_type, payer_lower, prior_year_amount)
        if self.filing_status == FilingStatus.SINGLE:
            if recipient == "Spouse":
                # Check if we've already added a Taxpayer entry with same payer/amount
                if ("Taxpayer", single_filer_check_key) in self._seen_items:
                    return  # Skip duplicate spouse entry on single return
            elif recipient == "Taxpayer":
                # Track this Taxpayer entry for duplicate spouse detection
                self._seen_items.add(("Taxpayer", single_filer_check_key))
        
        should_dedup = (form_type not in no_dedup_form_types) or ("unknown" in payer_lower)
        
        if should_dedup:
            item_key = (category, form_type, payer_lower, recipient, prior_year_amount)
            if item_key in self._seen_items:
                return  # Skip duplicate
            self._seen_items.add(item_key)
        
        self.items.append(DetailedChecklistItem(
            category=category,
            form_type=form_type,
            payer_name=payer_name,
            recipient=recipient,
            prior_year_amount=prior_year_amount,
            notes=notes
        ))
    
    def to_markdown(self) -> str:
        """Generate markdown checklist with details"""
        lines = [
            f"# Document Checklist: {self.client_name}",
            f"**Tax Year:** {self.tax_year}",
            f"**Based on:** {self.prior_year} Tax Return",
            f"**Generated:** {self.generated_date}",
            ""
        ]
        
        if self.taxpayer_name:
            lines.append(f"**Taxpayer:** {self.taxpayer_name}")
        # Only show spouse for married filing statuses
        if self.spouse_name and self.filing_status in [FilingStatus.MARRIED_FILING_JOINTLY, FilingStatus.MARRIED_FILING_SEPARATELY]:
            lines.append(f"**Spouse:** {self.spouse_name}")
        lines.append(f"**Filing Status:** {self._format_filing_status()}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Group by category
        categories: Dict[str, List[DetailedChecklistItem]] = {}
        for item in self.items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)
            
        # Sort items within categories
        for cat in categories:
            categories[cat].sort(key=lambda x: (x.payer_name.lower(), x.recipient))
        
        # Determine if we should show recipient column (only for MFJ)
        show_recipient = self.filing_status == FilingStatus.MARRIED_FILING_JOINTLY
        
        for category, items in categories.items():
            lines.append(f"## {category}")
            lines.append("")
            if show_recipient:
                lines.append("| ☐ | Form | Payer/Employer | Recipient | Prior Year Amount |")
                lines.append("|---|------|----------------|-----------|-------------------|")
            else:
                lines.append("| ☐ | Form | Payer/Employer | Prior Year Amount |")
                lines.append("|---|------|----------------|-------------------|")
            
            for item in items:
                # Skip $0 amounts - show '-' instead
                amount = item.prior_year_amount
                if not amount or amount in ["$0", "$0.00", "$0.0", "0", "0.00"]:
                    amount = "-"
                notes = f" *{item.notes}*" if item.notes else ""
                if show_recipient:
                    recipient_badge = self._get_recipient_badge(item.recipient)
                    lines.append(f"| ☐ | {item.form_type} | {item.payer_name}{notes} | {recipient_badge} | {amount} |")
                else:
                    lines.append(f"| ☐ | {item.form_type} | {item.payer_name}{notes} | {amount} |")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_filing_status(self) -> str:
        """Format filing status for display"""
        status_names = {
            FilingStatus.SINGLE: "Single",
            FilingStatus.MARRIED_FILING_JOINTLY: "Married Filing Jointly",
            FilingStatus.MARRIED_FILING_SEPARATELY: "Married Filing Separately",
            FilingStatus.HEAD_OF_HOUSEHOLD: "Head of Household",
            FilingStatus.QUALIFYING_WIDOW: "Qualifying Widow(er)"
        }
        return status_names.get(self.filing_status, str(self.filing_status))
    
    def _get_recipient_badge(self, recipient: str) -> str:
        """Get display badge for recipient"""
        badges = {
            "T": "👤 Taxpayer",
            "S": "👥 Spouse", 
            "J": "👫 Joint",
            "Taxpayer": "👤 Taxpayer",
            "Spouse": "👥 Spouse",
            "Joint": "👫 Joint"
        }
        return badges.get(recipient, recipient)

    def to_text(self) -> str:
        """Generate plain text checklist suitable for email"""
        lines = [
            f"Document Checklist: {self.client_name}",
            f"Tax Year: {self.tax_year}",
            f"Based on: {self.prior_year} Tax Return",
            ""
        ]
        
        if self.taxpayer_name:
            lines.append(f"Taxpayer: {self.taxpayer_name}")
        if self.spouse_name and self.filing_status in [FilingStatus.MARRIED_FILING_JOINTLY, FilingStatus.MARRIED_FILING_SEPARATELY]:
            lines.append(f"Spouse: {self.spouse_name}")
            
        lines.append(f"Filing Status: {self._format_filing_status()}")
        lines.append("-" * 40)
        lines.append("Please upload or provide the following documents:")
        lines.append("")
        
        # Group by category
        categories = {}
        for item in self.items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)
        
        show_recipient = self.filing_status == FilingStatus.MARRIED_FILING_JOINTLY
        
        for category, items in categories.items():
            # Sort items by payer/recipient
            items.sort(key=lambda x: (x.payer_name.lower(), x.recipient))
            
            lines.append(category.upper())
            for item in items:
                # Skip $0 amounts - don't show prior amount at all
                amount = item.prior_year_amount
                show_amount = amount and amount not in ["$0", "$0.00", "$0.0", "0", "0.00"]
                amount_str = f" (Prior: {amount})" if show_amount else ""
                recipient_str = f" [{item.recipient}]" if (show_recipient and item.recipient) else ""
                notes_str = f" -- {item.notes}" if item.notes else ""
                
                # Format: - FormType: Payer (Prior: $X) [Recipient] -- Notes
                line = f"- {item.form_type}: {item.payer_name}{amount_str}{recipient_str}{notes_str}"
                lines.append(line)
            lines.append("")
            
        return "\n".join(lines)

def _populate_checklist_from_return(checklist: DetailedChecklist, tax_return: TaxReturn, 
                                     consolidated_brokers: set = None) -> None:
    """Populate checklist items from structured TaxReturn data"""
    consolidated_brokers = consolidated_brokers or set()
    
    # W-2s
    for w2 in tax_return.income.w2s:
        recipient = "Taxpayer" if w2.owner == TaxpayerType.TAXPAYER else "Spouse"
        checklist.add_item(
            category="Employment Income (W-2)",
            form_type="W-2",
            payer_name=w2.employer_name or "Unknown Employer",
            recipient=recipient,
            prior_year_amount=f"${w2.wages:,.2f}" if w2.wages else ""
        )
    
    # 1099-INT - Skip entries that are already in consolidated 1099
    # Issue #4 Fix: Also skip negative amounts and adjustment entries
    # Skeleton Filter: Skip entries with no amounts (prior year placeholders)
    for f in tax_return.income.form_1099_int:
        payer_lower = (f.payer_name or "").lower().strip()
        # Skip if this broker appears in consolidated 1099 (interest is already captured there)
        if any(payer_lower in broker or broker in payer_lower for broker in consolidated_brokers):
            continue
        
        # Issue #4: Skip negative amounts (adjustments, not real documents)
        if f.interest_income and f.interest_income < 0:
            continue
        
        # Issue #4: Skip adjustment entries by name pattern
        adjustment_keywords = ['(less)', 'non-eci', 'nominee', 'adjustment', 'reclass']
        if any(kw in payer_lower for kw in adjustment_keywords):
            continue
        
        # Skeleton Filter: Skip entries with no amounts at all (rollovers/placeholders)
        current_amount = f.interest_income or 0
        prior_amount = getattr(f, 'prior_year_interest', 0) or 0
        if not current_amount and not prior_amount:
            continue
            
        recipient = "Taxpayer" if f.owner == TaxpayerType.TAXPAYER else ("Spouse" if f.owner == TaxpayerType.SPOUSE else "Joint")
        # Add account number if available and not already in name
        payer_display = f.payer_name or "Unknown Bank"
        if f.account_number and not any(c.isdigit() for c in payer_display):
            # Use last 4 chars of account number
            acct_suffix = f.account_number[-4:] if len(f.account_number) >= 4 else f.account_number
            payer_display = f"{payer_display} #{acct_suffix}"
        
        # Use current year amount, fallback to prior year
        display_amount = current_amount if current_amount else prior_amount
        checklist.add_item(
            category="Interest Income (1099-INT)",
            form_type="1099-INT",
            payer_name=payer_display,
            recipient=recipient,
            prior_year_amount=f"${display_amount:,.2f}" if display_amount else ""
        )
    
    # 1099-DIV
    # Issue #4 Fix: Also skip negative amounts and adjustment entries
    # Skeleton Filter: Skip entries with no amounts (prior year placeholders)
    for f in tax_return.income.form_1099_div:
        payer_lower = (f.payer_name or "").lower().strip()
        
        # Issue #4: Skip negative dividend amounts
        if f.ordinary_dividends and f.ordinary_dividends < 0:
            continue
        
        # Issue #4: Skip adjustment entries by name pattern
        adjustment_keywords = ['(less)', 'non-eci', 'nominee', 'adjustment', 'reclass']
        if any(kw in payer_lower for kw in adjustment_keywords):
            continue
        
        # Skeleton Filter: Skip entries with no amounts at all (rollovers/placeholders)
        current_amount = f.ordinary_dividends or 0
        prior_amount = getattr(f, 'prior_year_dividends', 0) or 0
        if not current_amount and not prior_amount:
            continue
        
        recipient = "Taxpayer" if f.owner == TaxpayerType.TAXPAYER else ("Spouse" if f.owner == TaxpayerType.SPOUSE else "Joint")
        # Add account number if available and not already in name
        payer_display = f.payer_name or "Unknown Payer"
        if f.account_number and not any(c.isdigit() for c in payer_display):
            # Use last 4 chars of account number
            acct_suffix = f.account_number[-4:] if len(f.account_number) >= 4 else f.account_number
            payer_display = f"{payer_display} #{acct_suffix}"
        
        # Use current year amount, fallback to prior year
        display_amount = current_amount if current_amount else prior_amount
        checklist.add_item(
            category="Dividend Income (1099-DIV)",
            form_type="1099-DIV",
            payer_name=payer_display,
            recipient=recipient,
            prior_year_amount=f"${display_amount:,.2f}" if display_amount else ""
        )
    
    # 1099-R
    for f in tax_return.income.form_1099_r:
        recipient = "Taxpayer" if f.owner == TaxpayerType.TAXPAYER else "Spouse"
        # Build payer name with account number if available
        payer_display = f.payer_name or "Unknown Payer"
        # Add account number suffix if available and not already in payer name
        if f.account_number and '#' not in payer_display:
            # Use last 4 digits of account number for display
            acct_clean = ''.join(c for c in f.account_number if c.isdigit())
            if len(acct_clean) >= 4:
                payer_display = f"{payer_display} #{acct_clean[-4:]}"
        checklist.add_item(
            category="Retirement Distributions (1099-R)",
            form_type="1099-R",
            payer_name=payer_display,
            recipient=recipient,
            prior_year_amount=f"${f.gross_distribution:,.2f}" if f.gross_distribution else ""
        )
    
    # 1099-NEC
    for f in tax_return.income.form_1099_nec:
        recipient = "Taxpayer" if f.owner == TaxpayerType.TAXPAYER else "Spouse"
        checklist.add_item(
            category="Self-Employment Income (1099-NEC)",
            form_type="1099-NEC",
            payer_name=f.payer_name or "Unknown Payer",
            recipient=recipient,
            prior_year_amount=f"${f.nonemployee_compensation:,.2f}" if f.nonemployee_compensation else ""
        )
        
    # 1099-MISC (New structured)
    for f in tax_return.income.form_1099_misc:
        recipient = "Taxpayer" if f.owner == TaxpayerType.TAXPAYER else "Spouse"
        amt = f.other_income or f.rents or f.royalties
        checklist.add_item(
            category="Miscellaneous Income (1099-MISC)",
            form_type="1099-MISC",
            payer_name=f.payer_name or "Unknown Payer",
            recipient=recipient,
            prior_year_amount=f"${amt:,.2f}" if amt else ""
        )
    
    # K-1s
    for k1 in tax_return.income.k1_1065:
        recipient = "Taxpayer" if k1.owner == TaxpayerType.TAXPAYER else "Spouse"
        checklist.add_item(
            category="Partnership Income (K-1 1065)",
            form_type="K-1 (1065)",
            payer_name=k1.partnership_name or "Unknown Partnership",
            recipient=recipient,
            prior_year_amount=f"${k1.ordinary_income:,.2f}" if k1.ordinary_income else ""
        )
    
    # K-1s (S-Corporation - Form 1120S)
    for k1 in tax_return.income.k1_1120s:
        recipient = "Taxpayer" if k1.owner == TaxpayerType.TAXPAYER else "Spouse"
        checklist.add_item(
            category="S-Corporation Income (K-1 1120S)",
            form_type="K-1 (1120S)",
            payer_name=k1.corporation_name or "Unknown S-Corp",
            recipient=recipient,
            prior_year_amount=f"${k1.ordinary_income:,.2f}" if k1.ordinary_income else ""
        )
    
    # 1099-G (Government Payments)
    for g in tax_return.income.form_1099_g:
        recipient = "Taxpayer" if g.owner == TaxpayerType.TAXPAYER else "Spouse"
        amount = g.unemployment_compensation or g.state_local_refund
        checklist.add_item(
            category="Government Payments (1099-G)",
            form_type="1099-G",
            payer_name=g.payer_name or "State Government",
            recipient=recipient,
            prior_year_amount=f"${amount:,.2f}" if amount else ""
        )
    
    # FBAR (Foreign Bank Accounts)
    for fbar in tax_return.income.fbar:
        recipient = "Taxpayer" if fbar.owner == TaxpayerType.TAXPAYER else "Spouse"
        checklist.add_item(
            category="Foreign Bank Accounts (FBAR)",
            form_type="FBAR/FinCEN 114",
            payer_name=fbar.bank_name or "Unknown Foreign Bank",
            recipient=recipient,
            prior_year_amount=f"${fbar.max_value:,.2f}" if fbar.max_value else ""
        )
    for ssa in tax_return.income.ssa_1099:
        # Skeleton filter: Skip entries with no current benefits (prior-year rollovers)
        if not ssa.net_benefits or ssa.net_benefits == 0:
            continue
        recipient = "Taxpayer" if ssa.owner == TaxpayerType.TAXPAYER else "Spouse"
        checklist.add_item(
            category="Social Security (SSA-1099)",
            form_type="SSA-1099",
            payer_name=ssa.beneficiary_name or "Social Security Administration",
            recipient=recipient,
            prior_year_amount=f"${ssa.net_benefits:,.2f}" if ssa.net_benefits else ""
        )

    
    # 1098 Mortgage Interest
    for m in tax_return.deductions.mortgage_interest:
        recipient = "Taxpayer" if m.owner == TaxpayerType.TAXPAYER else "Spouse"
        checklist.add_item(
            category="Mortgage Interest (1098)",
            form_type="1098",
            payer_name=m.lender_name or "Unknown Lender",
            recipient=recipient,
            prior_year_amount=f"${m.mortgage_interest:,.2f}" if m.mortgage_interest else ""
        )
        
    # 1095-C Health Coverage
    for c in tax_return.deductions.form_1095_c:
        recipient = "Taxpayer" if c.owner == TaxpayerType.TAXPAYER else "Spouse"
        checklist.add_item(
            category="Employer Health Coverage (1095-C)",
            form_type="1095-C",
            payer_name=c.employer_name or "Unknown Employer",
            recipient=recipient
        )

    # NOTE: Balance Sheet items (Form 291) removed from client checklist.
    # These are preparer tracking items, not documents clients can provide.
    # Consider adding to a future "Preparer Notes" output instead.


def generate_detailed_checklist(filepath: str, new_tax_year: int) -> DetailedChecklist:
    """
    Generate detailed checklist from CCH export file.
    """
    parser = CCHParser()
    doc = parser.parse_file(filepath)
    tax_return = parser.to_tax_return(doc)
    
    checklist = DetailedChecklist(
        client_name=tax_return.taxpayer.full_name,
        tax_year=new_tax_year,
        prior_year=tax_return.tax_year,
        taxpayer_name=tax_return.taxpayer.full_name,
        spouse_name=tax_return.spouse.full_name if tax_return.spouse else "",
        filing_status=tax_return.filing_status
    )
    
    # Collect consolidated broker names to detect duplicates
    # Form 882 field .30 has broker name, field .57 has interest income
    consolidated_brokers = set()
    for entry in doc.get_form_entries("881"):
        broker = entry.get("34", "").lower().strip()
        if broker:
            consolidated_brokers.add(broker)
    
    _populate_checklist_from_return(checklist, tax_return, consolidated_brokers)

    
    # Get additional forms from raw data
    _add_raw_form_items(doc, checklist)
    
    return checklist


def _add_raw_form_items(doc: CCHDocument, checklist: DetailedChecklist):
    """Add items from raw form data for forms not in structured models"""
    

    
    # 1099-K (Form 761)
    for entry in doc.get_form_entries("761"):
        recipient = "Taxpayer" if entry.get("30") == "T" else "Spouse"
        payer = entry.get("40", "Unknown Payment Processor")
        if payer:
            checklist.add_item(
                category="Payment Card Income (1099-K)",
                form_type="1099-K",
                payer_name=payer,
                recipient=recipient
            )
    
    # 1098-E Student Loan (Form 622)
    for entry in doc.get_form_entries("622"):
        recipient = "Taxpayer" if entry.get("30") == "T" else "Spouse"
        lender = entry.get("40", "Unknown Lender")
        amount = entry.get_decimal("60")
        checklist.add_item(
            category="Student Loan Interest (1098-E)",
            form_type="1098-E",
            payer_name=lender,
            recipient=recipient,
            prior_year_amount=f"${amount:,.2f}" if amount else ""
        )
    
    # 1098-T Tuition (Form 208)
    for entry in doc.get_form_entries("208"):
        recipient = "Taxpayer" if entry.get("30") == "T" else "Spouse"
        institution = entry.get("40", "Educational Institution")  # Field .40 is institution name
        amount = entry.get_decimal("60")
        checklist.add_item(
            category="Tuition Statement (1098-T)",
            form_type="1098-T",
            payer_name=institution or "Educational Institution",
            recipient=recipient,
            prior_year_amount=f"${amount:,.2f}" if amount else ""
        )
    
    # 1095-A Health Insurance (Form 624)
    for entry in doc.get_form_entries("624"):
        plan = entry.get("42", "Health Insurance Marketplace")
        name = entry.get("62", "")
        checklist.add_item(
            category="Health Insurance (1095-A)",
            form_type="1095-A",
            payer_name=plan,
            recipient=name if name else "Taxpayer"
        )
    

    
    # 1099-Q Education (Form 205)
    for entry in doc.get_form_entries("205"):
        recipient = "Taxpayer" if entry.get("30") == "T" else "Spouse"
        payer = entry.get("40", "529 Plan")
        amount = entry.get_decimal("55")
        checklist.add_item(
            category="Education Distributions (1099-Q)",
            form_type="1099-Q",
            payer_name=payer,
            recipient=recipient,
            prior_year_amount=f"${amount:,.2f}" if amount else ""
        )
    
    # 1099-SA HSA (Form 623)
    for entry in doc.get_form_entries("623"):
        recipient = "Taxpayer" if entry.get("30") == "T" else "Spouse"
        trustee = entry.get("40", "HSA Trustee")
        amount = entry.get_decimal("60")
        checklist.add_item(
            category="HSA Distributions (1099-SA)",
            form_type="1099-SA",
            payer_name=trustee,
            recipient=recipient,
            prior_year_amount=f"${amount:,.2f}" if amount else ""
        )
    
    # Schedule E Rental Properties (Form 211)
    for entry in doc.get_form_entries("211"):
        recipient = "Taxpayer" if entry.get("30") == "T" else ("Spouse" if entry.get("30") == "S" else "Joint")
        # Try .42 (address) first, then .41 (description), then build from city/state
        property_name = entry.get("42") or entry.get("41")
        if not property_name:
            city = entry.get("43", "")
            state = entry.get("44", "")
            if city or state:
                property_name = f"{city}, {state}".strip(", ")
            else:
                property_name = "Unknown Property"
        rents = entry.get_decimal("66")  # .66 = rents received
        if property_name:
            checklist.add_item(
                category="Rental Income (Schedule E)",
                form_type="Sch E",
                payer_name=property_name,
                recipient=recipient,
                prior_year_amount=f"${rents:,.2f}" if rents else ""
            )
    
    # Consolidated 1099 - Combine Form 882/883/886 (details with account numbers)
    # Form 882 = CN-2 Summary, Form 883 = CN-3 Details, Form 886 = CN-4 Transactions
    # Field .30 has broker names WITH account numbers embedded (e.g., "Merrill #1692", "Fidelity #0208")
    import re
    
    # Issue #2 Fix: Helper function to normalize broker names for deduplication
    def _normalize_broker_name(name: str) -> str:
        """Aggressively normalize broker name for deduplication.
        Removes common suffixes like LLC, Inc, Securities, etc."""
        result = name.lower().strip()

        # Fix common typos
        typo_fixes = {
            'schawb': 'schwab',  # Common typo
            'fideltiy': 'fidelity',
            'vangaurd': 'vanguard',
        }
        for typo, fix in typo_fixes.items():
            result = result.replace(typo, fix)

        # Remove common corporate suffixes and variations
        # Note: Order matters - check longer patterns first
        suffixes_to_remove = [
            r'\s*&\s*co\.?\s*inc\.?\b',  # "& Co Inc" as a unit
            r'\s+securities\s+llc\b',  # "Securities LLC" as a unit
            r'\s+llc\b', r'\s+inc\.?\b', r'\s+corp\.?\b', r'\s+ltd\.?\b', r'\s+plc\b',
            r'\s+securities\b', r'\s+sec\.?\b', r'\s+brokerage\b', r'\s+services\b',
            r'\s+markets\b', r'\s+crypto\b', r'\s+financial\b', r'\s+investments?\b',
            r'\s+n\.?a\.?\b',  # Bank N.A.
            r'\s+us\s+market\s+discount\b',  # Transaction type suffix
            r'\s*x\d+\b',  # "x5956" style account refs
        ]
        for suffix in suffixes_to_remove:
            result = re.sub(suffix, '', result, flags=re.IGNORECASE)
        # Also remove trailing periods and extra whitespace
        result = re.sub(r'\.$', '', result).strip()
        return result.strip()
    
    # Issue #1 Fix: Helper function to detect stock/security names vs broker names
    def _is_likely_security_name(name: str) -> bool:
        """Returns True if the name looks like a stock/security rather than a broker."""
        name_lower = name.lower().strip()
        
        # Skip if it has an account number pattern - those are likely valid
        if re.search(r'#\d{3,}', name):
            return False
        
        # Corporate suffixes that indicate a company stock, not a broker
        # (when NOT accompanied by financial institution keywords)
        stock_indicators = [
            r'\binc\b', r'\bcorp\b', r'\bltd\b', r'\bplc\b', r'\bhldg\b', r'\bholdings\b',
            r'\bgroup\b', r'\bcomputer\b', r'\btechnolog', r'\bpharmaceut',
            r'\benergy\b', r'\boil\b', r'\bgas\b', r'\bmining\b', r'\bresources\b',
            r'\binfras\b', r'\binfrastructure\b', r'\bppty\b', r'\bproperties\b',
            r'\breit\b', r'\bretail\b', r'\bautomotive\b', r'\baerospace\b',
            r'\bsemiconductor\b', r'\bnetworks?\b', r'\bsystems?\b',
            r'\broseburg\b',  # Company locations that indicate stock names
        ]
        
        # Financial institution keywords that indicate a valid broker
        broker_keywords = [
            'fidelity', 'schwab', 'merrill', 'vanguard', 'etrade', 'e*trade', 'e-trade',
            'robinhood', 'td ameritrade', 'interactive brokers', 'jpmorgan', 'morgan stanley',
            'edward jones', 'wells fargo', 'bank', 'trust', 'brokerage', 'securities',
            'financial', 'capital one', 'citibank', 'chase', 'goldman', 'ubs',
            'credit suisse', 'barclays', 'hsbc', 'ally', 'coinbase', 'webull'
        ]
        
        # If it contains a known broker keyword, it's valid
        if any(kw in name_lower for kw in broker_keywords):
            return False
        
        # Check for stock indicators without broker keywords
        if any(re.search(pattern, name_lower) for pattern in stock_indicators):
            return True
        
        # Known security types to filter
        security_types = [
            r'\betf\b', r'\bishares\b', r'\btreasury\b', r'\bbond\b', r'\bfund\b',
            r'\bspdr\b', r'\bvix\b', r'\bindex\b'
        ]
        if any(re.search(pattern, name_lower) for pattern in security_types):
            return True
        
        return False
    
    # Issue #5 Fix: Helper to standardize account number format
    def _standardize_account_format(name: str) -> str:
        """Standardize account number separator to # format."""
        # Replace patterns like "BrokerName-1234" with "BrokerName #1234"
        result = re.sub(r'([A-Za-z])[-]+(\d{4})$', r'\1 #\2', name)
        # Also handle "BrokerName- 1234" or "BrokerName -1234"
        result = re.sub(r'\s*-\s*(\d{4})$', r' #\1', result)
        return result
    
    # Helper to extract clean account suffix (digits only, last 4, zero-padded)
    def _extract_account_suffix(acct_str: str) -> str:
        """Extract last 4 digits from account string, ignoring letters.
        Short suffixes are zero-padded for consistent deduplication."""
        if not acct_str:
            return ""
        # Keep only digits
        digits_only = re.sub(r'[^0-9]', '', acct_str)
        if len(digits_only) >= 4:
            return digits_only[-4:]
        elif digits_only:
            # Pad short suffixes with leading zeros (e.g., "801" -> "0801")
            return digits_only.zfill(4)
        return ""
    
    seen_account_nums = set()  # Deduplicate by (normalized_broker, account) tuple
    seen_brokers_from_881 = set()  # Track brokers that have accounts from Form 881
    best_display_names = {}  # Track longest/best display name for each dedup key
    
    # Use Form 881 as PRIMARY source - it has all broker accounts with owner info
    # Field .34 = Broker name
    # Field .46 = Full account number (e.g., "4509-9702", "8387-1489")
    # Field .30 = Owner code: T=Taxpayer, S=Spouse, J=Joint
    for entry in doc.get_form_entries("881"):
        broker = entry.get("34", "").strip()
        if not broker:
            continue
        
        # Get full account number from field .46
        full_acct = entry.get("46", "").strip()
        
        # Extract last 4 digits only for deduplication
        acct_suffix = _extract_account_suffix(full_acct)
        
        # Issue #2: Use normalized broker name for deduplication
        normalized_broker = _normalize_broker_name(broker)
        dedup_key = (normalized_broker, acct_suffix)
        
        # Track broker name for filtering Form 882/883/886
        seen_brokers_from_881.add(broker.lower())
        seen_brokers_from_881.add(normalized_broker)
        
        # Build display name with account suffix (Issue #5: use # format)
        if acct_suffix:
            display_name = f"{broker} #{acct_suffix}"
        else:
            display_name = broker
        # Apply account format standardization to clean up any oddities
        display_name = _standardize_account_format(display_name)
        
        # Issue #2: Keep the longest/most complete display name
        if dedup_key in seen_account_nums:
            existing = best_display_names.get(dedup_key, "")
            if len(display_name) > len(existing):
                best_display_names[dedup_key] = display_name
            continue
        seen_account_nums.add(dedup_key)
        best_display_names[dedup_key] = display_name
        
        # Get owner: T=Taxpayer, S=Spouse, J=Joint (treat as Taxpayer for display)
        owner_code = entry.get("30", "T")
        if owner_code == "S":
            recipient = "Spouse"
        elif owner_code == "J":
            recipient = "Joint"
        else:
            recipient = "Taxpayer"
        
        checklist.add_item(
            category="Brokerage Statements (Consolidated 1099)",
            form_type="1099-B/DIV/INT",
            payer_name=display_name,
            recipient=recipient
        )
    
    # Also check Form 882/883/886 for any accounts not in Form 881
    # These have broker+account embedded in field .30 (e.g., "Fidelity #0208")
    for form_code in ["882", "883", "886"]:
        for entry in doc.get_form_entries(form_code):
            broker_with_acct = entry.get("30", "").strip()
            if not broker_with_acct:
                continue
            
            # Issue #1: Skip if this looks like a stock/security name
            if _is_likely_security_name(broker_with_acct):
                continue
            
            # Clean up display name - remove suffixes like "_ Covered_ LT", "STCG"
            display_name = broker_with_acct
            cleanup_patterns = [
                r'[-_]?\s*Covered[-_]?\s*(LT|ST)?',
                r'[-_]?\s*(LT|ST)CG',
                r'[-_]?\s*(LT|ST)\b',
                r'\s+Covered\b',
                r'_\s*Not\b',
                r'_\s*NON\b',
                r'\s*-\s*Market\s*Discount\b',  # Issue #1: Remove market discount suffix
            ]
            for pattern in cleanup_patterns:
                display_name = re.sub(pattern, '', display_name, flags=re.IGNORECASE)
            display_name = display_name.strip(" -_#")
            
            # Issue #5: Standardize account number format
            display_name = _standardize_account_format(display_name)
            
            # Extract account number for deduplication using same helper as Form 881
            raw_acct = ""
            acct_match = re.search(r'[#-]?(\d{3,}[A-Za-z]?)', broker_with_acct)
            if acct_match:
                raw_acct = acct_match.group(1)
            acct_suffix = _extract_account_suffix(raw_acct)
            
            # Extract base broker name - strip account numbers AND _Covered_* suffixes
            # Match #, x, or digits followed by more digits (e.g., "#5956", "x5956", "5956")
            base_broker = re.sub(r'[#x]?\d+.*$', '', broker_with_acct, flags=re.IGNORECASE).strip()
            base_broker = re.sub(r'[-_]\s*(Covered|ST|LT|STCG|LTCG|Not|NON).*$', '', base_broker, flags=re.IGNORECASE).strip()
            
            # Issue #2: Use normalized broker name for deduplication
            normalized_broker = _normalize_broker_name(base_broker)
            
            # Skip if no account number AND broker already covered by Form 881
            # (These are likely transaction-level entries, not new accounts)
            if not acct_suffix and (base_broker.lower() in seen_brokers_from_881 or normalized_broker in seen_brokers_from_881):
                continue
            
            # Deduplicate using normalized name
            dedup_key = (normalized_broker, acct_suffix)
            if dedup_key in seen_account_nums:
                # Issue #2: Update display name if this one is longer/better
                existing = best_display_names.get(dedup_key, "")
                if len(display_name) > len(existing):
                    best_display_names[dedup_key] = display_name
                continue
            seen_account_nums.add(dedup_key)
            best_display_names[dedup_key] = display_name
            
            # Note: Form 882/883/886 don't have owner field, use Taxpayer as default
            checklist.add_item(
                category="Brokerage Statements (Consolidated 1099)",
                form_type="1099-B/DIV/INT",
                payer_name=display_name,
                recipient="Taxpayer"
            )


def generate_all_checklists(filepath: str, new_tax_year: int, output_dir: str = "."):
    """Generate checklists for all clients in a multi-client file"""
    parser = CCHParser()
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    checklists = []
    for doc in parser.parse_multi_file(filepath):
        tax_return = parser.to_tax_return(doc)
        
        checklist = DetailedChecklist(
            client_name=tax_return.taxpayer.full_name,
            tax_year=new_tax_year,
            prior_year=tax_return.tax_year,
            taxpayer_name=tax_return.taxpayer.full_name,
            spouse_name=tax_return.spouse.full_name if tax_return.spouse else "",
            filing_status=tax_return.filing_status
        )
        
        # Collect consolidated broker names to detect duplicates
        consolidated_brokers = set()
        for entry in doc.get_form_entries("881"):
            broker = entry.get("34", "").lower().strip()
            if broker:
                consolidated_brokers.add(broker)
        
        _populate_checklist_from_return(checklist, tax_return, consolidated_brokers)
        
        # Add raw form items
        _add_raw_form_items(doc, checklist)

        
        checklists.append(checklist)
        
        # Save individual checklist
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in tax_return.taxpayer.full_name)
        output_file = output_path / f"checklist_{safe_name}_{new_tax_year}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(checklist.to_markdown())
            
        # Save text checklist
        output_txt = output_path / f"checklist_{safe_name}_{new_tax_year}.txt"
        with open(output_txt, 'w', encoding='utf-8') as f:
            f.write(checklist.to_text())
        
        print(f"Generated: {output_file} & {output_txt}")
    
    # Concatenate all text checklists
    all_checklists_path = output_path / "all_checklists.txt"
    with open(all_checklists_path, 'w', encoding='utf-8') as outfile:
        for cl in checklists:
             outfile.write(cl.to_text())
             outfile.write("\n\n" + "="*80 + "\n\n")
    print(f"Concatenated all checklists to: {all_checklists_path}")

    return checklists


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python generate_checklists.py <cch_file> [tax_year]")
        print("       python generate_checklists.py <cch_file> --multi [tax_year]")
        sys.exit(1)
    
    filename = sys.argv[1]
    multi_mode = "--multi" in sys.argv
    
    # Resolve input path (check data/ folder first)
    input_path = Path(filename)
    if not input_path.exists():
        if (Path("data") / filename).exists():
            input_path = Path("data") / filename
    
    # Output path
    output_path = Path("output")
    output_path.mkdir(exist_ok=True)
    
    # Mapping file
    mapping_file = Path("mappings") / "cch_mapping.json"
    
    # Default to next year
    tax_year = 2025
    for arg in sys.argv[2:]:
        if arg.isdigit():
            tax_year = int(arg)
    
    print(f"Reading from: {input_path}")
    print(f"Output to: {output_path}")

    try:
        # Pass mapping file if it exists, otherwise Default
        parser = CCHParser(str(mapping_file)) if mapping_file.exists() else CCHParser()
        
        if multi_mode:
            # Correct signature: (filepath, new_tax_year, output_dir)
            checklists = generate_all_checklists(str(input_path), tax_year, str(output_path))
            print(f"\nGenerated {len(checklists)} checklists in {output_path}")
        else:
            checklist = generate_detailed_checklist(str(input_path), tax_year)
            if checklist:
                safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in checklist.client_name)
                output_file = output_path / f"checklist_{safe_name}_{tax_year}.md"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(checklist.to_markdown())
                print(f"Generated: {output_file}")
                
                output_txt = output_path / f"checklist_{safe_name}_{tax_year}.txt"
                with open(output_txt, 'w', encoding='utf-8') as f:
                    f.write(checklist.to_text())
                print(f"Generated: {output_txt}")
            else:
                print("Failed to generate checklist")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

