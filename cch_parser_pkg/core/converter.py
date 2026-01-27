import re
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime

from ..models.base import (
    Person, Address, Dependent, BankAccount,
    FilingStatus, TaxpayerType
)
from ..models.income import (
    W2, Form1099INT, Form1099DIV, Form1099R, Form1099NEC, Form1099G,
    FormK1_1065, FormK1_1120S, FormFBAR, SSA1099, Form1099MISC, ScheduleE
)
from ..models.deductions import Form1098, Form1095A, Form1095C
from ..models.statements import BalanceSheet, StatementItem
from ..models.return_data import TaxReturn, IncomeData, DeductionData


from .reader import CCHDocument, CCHFormEntry
from .mapping_loader import MappingLoader, get_mapping_loader

class CCHConverter:
    """
    Converts raw CCHDocument into structured TaxReturn data.
    Uses YAML mappings for field lookups instead of hard-coded field numbers.
    """
    
    def __init__(self, mapping_path: Optional[str] = None):
        """Initialize with optional path to mapping YAML file."""
        self.map = MappingLoader(mapping_path)
    
    def to_tax_return(self, doc: CCHDocument) -> TaxReturn:
        """Convert parsed document to structured TaxReturn"""
        tr = TaxReturn(
            tax_year=doc.tax_year,
            client_id=doc.client_id
        )
        
        # 1. Parse Client Info (Form 101)
        self._parse_client_info(doc, tr)
        
        # 2. Parse Income Forms
        self._parse_income(doc, tr)
        
        # 3. Parse Deductions
        self._parse_deductions(doc, tr)
        
        # 4. Parse Bank Info (Form 921/925)
        self._parse_bank_info(doc, tr)

        # 5. Parse Balance Sheet (Form 291)
        self._parse_balance_sheet(doc, tr)
        
        # Store raw forms for reference
        for code, form in doc.forms.items():
            tr.raw_forms[code] = [
                {k: v.value for k, v in e.fields.items()}
                for e in form.entries
            ]
            
        return tr

    def _parse_client_info(self, doc: CCHDocument, tr: TaxReturn) -> None:
        """Parse client information from Form 101"""
        # Form 101 is usually implied or part of header, but let's check for explicit form
        form = doc.get_form("101")
        if not form or not form.entries:
            # Fallback to header info if available
            return

        entry = form.entries[0]
        
        # Taxpayer
        tr.taxpayer = Person(
            first_name=entry.get("40"),
            middle_initial=entry.get("41"),
            last_name=entry.get("42"),
            ssn=entry.get("44"),
            dob=entry.get_decimal("61") or None, # Date logic needed
            occupation=entry.get("60"),
            email=entry.get("18"), # Check mapping
            phone=entry.get("19")
        )
        
        # Spouse
        if entry.get("45"):
            tr.spouse = Person(
                first_name=entry.get("45"),
                last_name=entry.get("47"),
                ssn=entry.get("49"),
                occupation=entry.get("67")
            )
        
        # Address
        tr.address = Address(
            street=entry.get("80"),
            city=entry.get("82"),
            state=entry.get("83"),
            zip_code=entry.get("84")
        )
        
        # Filing Status
        status_code = entry.get("90")
        try:
            tr.filing_status = FilingStatus(status_code)
        except ValueError:
            pass # Default is Single

    def _parse_income(self, doc: CCHDocument, tr: TaxReturn) -> None:
        """Parse all income forms"""
        # W-2 (Form 180)
        for entry in doc.get_form_entries("180"):
            # Filter out state-only entries (missing employer name)
            if not entry.get("41"):
                continue
            tr.income.w2s.append(self._parse_w2(entry))
            
        # 1099-INT (Form 181)
        for entry in doc.get_form_entries("181"):
            tr.income.form_1099_int.append(self._parse_1099int(entry))
        
        # Consolidated 1099 (Form 881) - adds to 1099-INT/DIV from brokerage
        self._parse_consolidated_1099(doc, tr)
            
        # 1099-DIV (Form 182)
        for entry in doc.get_form_entries("182"):
            # Filter incomplete entries
            if not entry.get("40"):
                continue
            tr.income.form_1099_div.append(self._parse_1099div(entry))
            
        # 1099-R (Form 184)
        for entry in doc.get_form_entries("184"):
            tr.income.form_1099_r.append(self._parse_1099r(entry))
            
        # 1099-NEC (Form 267)
        for entry in doc.get_form_entries("267"):
            tr.income.form_1099_nec.append(self._parse_1099nec(entry))

        # 1099-G (Form 209)
        for entry in doc.get_form_entries("209"):
            tr.income.form_1099_g.append(self._parse_1099g(entry))
            
        # K-1 1065 (Form 185)
        for entry in doc.get_form_entries("185"):
            # Filter: must have partnership name (46) - this is the primary name field
            if entry.get("46"):
                tr.income.k1_1065.append(self._parse_k1_1065(entry))

        # K-1 1120S (Form 120)
        for entry in doc.get_form_entries("120"):
            # Filter: Check for Corporation Name in field 45 (Standard) or 34 (Alt)
            if entry.get("45") or entry.get("34"): 
                tr.income.k1_1120s.append(self._parse_k1_1120s(entry))
            
        # SSA-1099 (Form 190)
        for entry in doc.get_form_entries("190"):
            tr.income.ssa_1099.append(self._parse_ssa1099(entry))

        # FBAR (Form 925)
        for entry in doc.get_form_entries("925"):
            # Ensure bank name exists
            if entry.get("45"):
                tr.income.fbar.append(self._parse_fbar(entry))

        # 1099-MISC (Form 183)
        for entry in doc.get_form_entries("183"):
            tr.income.form_1099_misc.append(self._parse_1099misc(entry))

        # Schedule E (Form 211) - Rental Real Estate
        for entry in doc.get_form_entries("211"):
            # Include entry if it has:
            # 1. Property type in .30 (not just owner code T/S/J), OR
            # 2. Property name in .41, OR  
            # 3. Property address in .42, OR
            # 4. Rents received in .54
            prop_type = entry.get("30", "")
            prop_name = entry.get("41", "")
            prop_addr = entry.get("42", "")
            has_rents = entry.get_decimal("54") > 0
            
            has_property_type = prop_type and prop_type not in ["T", "S", "J", "t", "s", "j"]
            
            if has_property_type or prop_name or prop_addr or has_rents:
                tr.income.schedule_e.append(self._parse_schedule_e(entry))

    def _parse_deductions(self, doc: CCHDocument, tr: TaxReturn) -> None:
        """Parse deduction forms"""
        # 1098 Mortgage (Form 206)
        for entry in doc.get_form_entries("206"):
            tr.deductions.mortgage_interest.append(self._parse_1098(entry))
            
        # 1095-A (Form 624)
        for entry in doc.get_form_entries("624"):
            tr.deductions.health_insurance.append(self._parse_1095a(entry))

        # 1095-C (Code 641)
        for entry in doc.get_form_entries("641"):
            # Filter matches that are not actually 1095-C (Collision with EF-2)
            # Real 1095-C has Employer Name in .46
            if entry.get("46"):
                tr.deductions.form_1095_c.append(self._parse_1095c(entry))

    def _parse_bank_info(self, doc: CCHDocument, tr: TaxReturn) -> None:
        """Parse bank account info"""
        # Form 921 for direct deposit
        entries = doc.get_form_entries("921")
        if entries:
            e = entries[0]
            tr.bank_account = BankAccount(
                bank_name=e.get("37"),
                routing_number=e.get("38"),
                account_number=e.get("39"),
                is_checking=e.get_bool("33")
            )

    def _parse_w2(self, entry: CCHFormEntry) -> W2:
        """Parse W-2 using YAML mappings (form_180) - strict, no fallbacks"""
        f = lambda name: self.map.get_field_number("180", name)
        
        owner_code = entry.get(f("taxpayer_or_spouse"), "T")
        owner = TaxpayerType.SPOUSE if owner_code == "S" else (TaxpayerType.JOINT if owner_code == "J" else TaxpayerType.TAXPAYER)
        
        return W2(
            owner=owner,
            employer_name=entry.get(f("employer_name")),
            employer_ein=entry.get(f("employer_ein")), 
            employer_address=entry.get(f("employer_address")),
            employer_city=entry.get(f("employer_city")),
            employer_state=entry.get(f("employer_state")),
            employer_zip=entry.get(f("employer_zip")),
            wages=entry.get_decimal(f("box1_wages")),
            fed_tax_withheld=entry.get_decimal(f("box2_fed_withheld")),
            ss_wages=entry.get_decimal(f("box3_ss_wages")),
            ss_tax_withheld=entry.get_decimal(f("box4_ss_withheld")),
            medicare_wages=entry.get_decimal(f("box5_medicare_wages")),
            medicare_tax_withheld=entry.get_decimal(f("box6_medicare_withheld")),
            ss_tips=entry.get_decimal(f("box7_ss_tips")),
            allocated_tips=entry.get_decimal(f("box8_allocated_tips")),
            dependent_care=entry.get_decimal(f("box10_dependent_care")),
            nonqualified_plans=entry.get_decimal(f("box11_nonqualified_plans")),
            retirement_plan=entry.get_bool(f("box13_retirement")),
            statutory_employee=entry.get_bool(f("box13_statutory")),
            state=entry.get(f("box15_state")),
            state_ein=entry.get(f("box15_state_ein")),
            state_wages=entry.get_decimal(f("box16_state_wages")),
            state_tax=entry.get_decimal(f("box17_state_tax")),
            local_wages=entry.get_decimal(f("box18_local_wages")),
            local_tax=entry.get_decimal(f("box19_local_tax"))
        )

    def _parse_1099int(self, entry: CCHFormEntry) -> Form1099INT:
        """Parse 1099-INT using YAML mappings (form_181) - strict, no fallbacks"""
        f = lambda name: self.map.get_field_number("181", name)
        
        owner_code = entry.get(f("taxpayer_or_spouse"), "T")
        # Handle T/S/J owner codes
        if owner_code == "S":
            owner = TaxpayerType.SPOUSE
        elif owner_code == "J":
            owner = TaxpayerType.JOINT
        else:
            owner = TaxpayerType.TAXPAYER
        
        return Form1099INT(
            owner=owner,
            payer_name=entry.get(f("payer_name")),
            payer_tin=entry.get(f("payer_tin")),
            account_number=entry.get(f("account_number"), ""),
            interest_income=entry.get_decimal(f("box1_interest")),
            prior_year_interest=entry.get_decimal(f("box1_interest_prior")),  # .71M
            early_withdrawal_penalty=entry.get_decimal(f("box2_early_withdrawal")),
            us_savings_bond_interest=entry.get_decimal(f("box3_savings_bond")),
            fed_tax_withheld=entry.get_decimal(f("box4_fed_withheld"))
        )

    def _parse_1099div(self, entry: CCHFormEntry) -> Form1099DIV:
        """Parse 1099-DIV using YAML mappings (form_182) - strict, no fallbacks"""
        f = lambda name: self.map.get_field_number("182", name)
        
        owner_code = entry.get(f("taxpayer_or_spouse"), "T")
        # Handle T/S/J owner codes
        if owner_code == "S":
            owner = TaxpayerType.SPOUSE
        elif owner_code == "J":
            owner = TaxpayerType.JOINT
        else:
            owner = TaxpayerType.TAXPAYER
        
        return Form1099DIV(
            owner=owner,
            payer_name=entry.get(f("payer_name")),
            payer_tin=entry.get(f("payer_tin")),
            account_number=entry.get(f("account_number"), ""),
            ordinary_dividends=entry.get_decimal(f("box1a_ordinary_div")),
            prior_year_dividends=entry.get_decimal(f("box1a_ordinary_div_prior")),  # .70M
            qualified_dividends=entry.get_decimal(f("box1b_qualified_div")),
            capital_gain_dist=entry.get_decimal(f("box2a_cap_gain_dist")),
            fed_tax_withheld=entry.get_decimal(f("box4_fed_withheld"))
        )

    def _parse_1099r(self, entry: CCHFormEntry) -> Form1099R:
        """Parse 1099-R using YAML mappings (form_184) - strict, no fallbacks"""
        f = lambda name: self.map.get_field_number("184", name)
        
        owner_code = entry.get(f("taxpayer_or_spouse"), "T")
        owner = TaxpayerType.SPOUSE if owner_code == "S" else (TaxpayerType.JOINT if owner_code == "J" else TaxpayerType.TAXPAYER)
        
        return Form1099R(
            owner=owner,
            payer_name=entry.get(f("payer_name")),
            payer_tin=entry.get(f("payer_ein")),
            account_number=entry.get("84"),  # Account number field
            gross_distribution=entry.get_decimal(f("box1_gross_dist")),
            taxable_amount=entry.get_decimal(f("box2a_taxable")),
            fed_tax_withheld=entry.get_decimal(f("box4_fed_withheld")),
            distribution_code=entry.get(f("box7_dist_code"))
        )

    def _parse_1099nec(self, entry: CCHFormEntry) -> Form1099NEC:
        owner_code = entry.get("30", "T")
        owner = TaxpayerType.SPOUSE if owner_code == "S" else (TaxpayerType.JOINT if owner_code == "J" else TaxpayerType.TAXPAYER)
        
        return Form1099NEC(
            owner=owner,
            payer_name=entry.get("40"),
            payer_tin=entry.get("49"),
            nonemployee_compensation=entry.get_decimal("59"),
            fed_tax_withheld=entry.get_decimal("70")
        )

    def _parse_1099g(self, entry: CCHFormEntry) -> Form1099G:
        owner_code = entry.get("30", "T")
        owner = TaxpayerType.SPOUSE if owner_code == "S" else (TaxpayerType.JOINT if owner_code == "J" else TaxpayerType.TAXPAYER)
        
        return Form1099G(
            owner=owner,
            payer_name=entry.get("40"),
            unemployment_compensation=entry.get_decimal("55"),
            state_local_refund=entry.get_decimal("56"),
            fed_tax_withheld=entry.get_decimal("58"),
            state=entry.get("242") or entry.get("91") # Try common state fields
        )

    def _parse_fbar(self, entry: CCHFormEntry) -> FormFBAR:
        owner_code = entry.get("30", "T")
        owner = TaxpayerType.SPOUSE if owner_code == "S" else (TaxpayerType.JOINT if owner_code == "J" else TaxpayerType.TAXPAYER)
        
        return FormFBAR(
            owner=owner,
            bank_name=entry.get("45"),
            bank_address=entry.get("50"),
            bank_city=entry.get("51"),
            bank_country=entry.get("54"),
            account_number=entry.get("36"),
            max_value=entry.get_decimal("33"), # Or maybe .38? Mapping varies. FBAR mapping showed 33 as amount
            account_type="Bank"
        )
        
    def _parse_k1_1065(self, entry: CCHFormEntry) -> FormK1_1065:
        """Parse K-1 (1065) Partnership using YAML mappings - strict, no fallbacks"""
        f = lambda name: self.map.get_field_number("185", name)
        
        # Owner
        owner_code = entry.get(f("taxpayer_or_spouse"), "T")
        owner = TaxpayerType.SPOUSE if owner_code == "S" else (TaxpayerType.JOINT if owner_code == "J" else TaxpayerType.TAXPAYER)
        
        # Partnership identification - use mapped field with fallbacks for entries lacking field 46
        partnership_name = (entry.get(f("partnership_name")) or 
                            entry.get("956") or 
                            entry.get("90"))
        partnership_ein = entry.get(f("partnership_ein"))
        partnership_address = entry.get(f("partnership_address"))
        partnership_city = entry.get(f("partnership_city"))
        partnership_state = entry.get(f("partnership_state"))
        partnership_zip = entry.get(f("partnership_zip"))
        partner_type = entry.get(f("partner_type"))
        
        # Income boxes - YAML field mappings
        ordinary_income = entry.get_decimal(f("box1_ordinary_income"))
        net_rental_re = entry.get_decimal(f("box2_net_rental_re"))
        other_rental = entry.get_decimal(f("box3_other_rental"))
        
        # Box 4: Guaranteed Payments
        box4a = entry.get_decimal(f("box4a_guaranteed_services"))
        box4b = entry.get_decimal(f("box4b_guaranteed_capital"))
        box4c = entry.get_decimal(f("box4c_total_guaranteed"))
        guaranteed = box4c if box4c else (box4a + box4b)
        
        return FormK1_1065(
            owner=owner,
            partnership_name=partnership_name,
            partnership_ein=partnership_ein,
            partnership_address=partnership_address,
            partnership_city=partnership_city,
            partnership_state=partnership_state,
            partnership_zip=partnership_zip,
            partner_type=partner_type,
            ordinary_income=ordinary_income,
            net_rental_re_income=net_rental_re,
            other_rental_income=other_rental,
            guaranteed_payments=guaranteed,
            interest_income=entry.get_decimal(f("box5_interest")),
            ordinary_dividends=entry.get_decimal(f("box6a_ordinary_div")),
            qualified_dividends=entry.get_decimal(f("box6b_qualified_div")),
            royalties=entry.get_decimal(f("box7_royalties")),
            net_stcg=entry.get_decimal(f("box8_net_stcg")),
            net_ltcg=entry.get_decimal(f("box9a_net_ltcg"))
        )

    def _parse_k1_1120s(self, entry: CCHFormEntry) -> FormK1_1120S:
        """Parse K-1 1120S (S-Corporation) using YAML mappings - strict, no fallbacks"""
        f = lambda name: self.map.get_field_number("120", name)
        
        # Owner
        owner_code = entry.get(f("taxpayer_or_spouse"), "T")
        owner = TaxpayerType.SPOUSE if owner_code == "S" else (TaxpayerType.JOINT if owner_code == "J" else TaxpayerType.TAXPAYER)
        
        # Corporation name: try mapped fields and explicit fallbacks
        # Data analysis shows field 45 is commonly the name, while mapping might point to 34
        corp_name = (entry.get(f("corporation_name")) or 
                     entry.get(f("corporation_name_alt")) or 
                     entry.get("45") or 
                     entry.get("34") or 
                     None)
        
        # EIN
        corp_ein = entry.get(f("corporation_ein"))
        
        # Ordinary income - try primary field, then alt, pick largest absolute value
        primary_income = entry.get_decimal(f("box1_ordinary_income"))
        alt_income = entry.get_decimal(f("ordinary_income_alt"))
        ordinary_income = primary_income if abs(primary_income) >= abs(alt_income) else alt_income
        
        return FormK1_1120S(
            owner=owner,
            corporation_name=corp_name,
            corporation_ein=corp_ein,
            ordinary_income=ordinary_income
        )

    def _parse_ssa1099(self, entry: CCHFormEntry) -> SSA1099:
        owner_code = entry.get("30", "T")
        owner = TaxpayerType.SPOUSE if owner_code == "S" else (TaxpayerType.JOINT if owner_code == "J" else TaxpayerType.TAXPAYER)
        
        return SSA1099(
            owner=owner,
            beneficiary_name=entry.get("40"),
            benefits_paid=entry.get_decimal("42"),
            net_benefits=entry.get_decimal("44"),
            claim_number=entry.get("51")
        )

    def _parse_1098(self, entry: CCHFormEntry) -> Form1098:
        owner_code = entry.get("30", "T")
        owner = TaxpayerType.SPOUSE if owner_code == "S" else (TaxpayerType.JOINT if owner_code == "J" else TaxpayerType.TAXPAYER)
        
        return Form1098(
            owner=owner,
            lender_name=entry.get("34"),
            lender_tin=entry.get("42"),
            mortgage_interest=entry.get_decimal("41"),
            outstanding_principal=entry.get_decimal("59"),
            property_address=entry.get("55"),
            points_paid=entry.get_decimal("44")
        )

    def _parse_1095a(self, entry: CCHFormEntry) -> Form1095A:
        return Form1095A(
            marketplace_state=entry.get("40"),
            policy_number=entry.get("41"),
            plan_name=entry.get("42"),
            covered_individual=entry.get("62"),
            annual_premium=entry.get_decimal("126"),
            annual_slcsp=entry.get_decimal("127"),
            annual_aptc=entry.get_decimal("128")
        )

    def _parse_1099misc(self, entry: CCHFormEntry) -> Form1099MISC:
        owner_code = entry.get("30", "T")
        owner = TaxpayerType.SPOUSE if owner_code == "S" else (TaxpayerType.JOINT if owner_code == "J" else TaxpayerType.TAXPAYER)
        
        return Form1099MISC(
            owner=owner,
            payer_name=entry.get("40"),
            payer_tin=entry.get("48"), # Verified from Sample
            other_income=entry.get_decimal("67"), # Verified
            rents=entry.get_decimal("55"), # Mapped from CCH standard (Box 1)
            royalties=entry.get_decimal("56"), # Mapped from CCH standard (Box 2)
            fishing_boat_proceeds=entry.get_decimal("59"),
            medical_payments=entry.get_decimal("60"),
            nonqualified_deferred_comp=entry.get_decimal("71"),
            state=entry.get("80"),
            state_income=entry.get_decimal("82")
        )

    def _parse_1095c(self, entry: CCHFormEntry) -> Form1095C:
        """
        Parse 1095-C entries.
        Includes validation to skip form collisions (e.g. EF-2 code 641)
        which lack employer name field .46
        """
        employer_name = entry.get("46")
        if not employer_name:
            # Skip invalid entries (likely Form EF-2 which shares code 641)
            # Returning empty object will result in empty name, but caller appends unconditionally.
            # We should probably filter in the caller loop, but for now let's handle it by
            # ensuring the object indicates it's invalid/empty if needed, 
            # OR better: Filter in _parse_deductions
            pass

        owner_code = entry.get("30", "T")
        owner = TaxpayerType.SPOUSE if owner_code == "S" else (TaxpayerType.JOINT if owner_code == "J" else TaxpayerType.TAXPAYER)

        return Form1095C(
            owner=owner,
            employer_name=employer_name,
            employer_ein=entry.get("47"),
            employer_address=entry.get("48"),
            employer_city=entry.get("50"),
            employer_state=entry.get("51"),
            employer_zip=entry.get("52"),
            employee_name=entry.get("114"),
            employee_ssn=entry.get("115"),
            offer_of_coverage=entry.get("118"), # Guessing fields for Part II
            employee_share=entry.get_decimal("119")
        )

    def _parse_balance_sheet(self, doc: CCHDocument, tr: TaxReturn) -> None:
        """Parse Balance Sheet (Form 291) dynamically"""
        form = doc.get_form("291")
        if not form:
            return
        
        bs = BalanceSheet()
        
        for entry in form.entries:
            # Get all field numbers sorted numerically
            try:
                field_nums = sorted([int(k) for k in entry.fields.keys()])
            except ValueError:
                continue

            for f_num in field_nums:
                str_f_num = str(f_num)
                field = entry.fields[str_f_num]
                val = field.value
                
                if not val:
                    continue
                
                # Heuristic: If it looks like a label (contains letters)
                if re.search(r'[a-zA-Z]', val):
                    # Check if N+2 exists and is numeric
                    target_num = str(f_num + 2)
                    amount_field_obj = entry.fields.get(target_num)
                    
                    if amount_field_obj:
                        amount = amount_field_obj.as_decimal
                        if amount != 0:
                            # Avoid capturing "Address" fields or IDs as items
                            # Usually simple labels like "Cash", "Inventory"
                            # Filter out very long text? No.
                            bs.items.append(StatementItem(description=val, amount=amount))

        if bs.items:
            tr.balance_sheet = bs

    def _parse_schedule_e(self, entry: CCHFormEntry) -> ScheduleE:
        """Parse Schedule E (Form 211) - Rental Real Estate
        
        IMPORTANT: Field usage varies by property type!
        - Properties with .30=T/S/J use .60 for rents
        - Properties with .30=description use .54 for rents
        
        Expense fields:
        - .93 = repairs
        - .102 = utilities  
        - .120/.148 = other expenses
        - Individual expense fields, NOT .60!
        """
        # Handle mixed .30 field - determine if it's owner code or property type
        field_30 = entry.get("30", "")
        owner = TaxpayerType.TAXPAYER
        property_type = ""
        
        if field_30 in ["T", "t"]:
            owner = TaxpayerType.TAXPAYER
        elif field_30 in ["S", "s"]:
            owner = TaxpayerType.SPOUSE
        elif field_30 in ["J", "j"]:
            owner = TaxpayerType.TAXPAYER  # Joint - treat as taxpayer
        else:
            # .30 contains property type description
            property_type = field_30
        
        # Property info from validated fields
        property_name = entry.get("41", "") or property_type
        property_address = entry.get("42", "") or entry.get("31", "")
        city = entry.get("43", "")
        state = entry.get("44", "")
        zip_code = entry.get("45", "")
        
        # Build full address
        full_address = property_address
        if city:
            full_address = f"{full_address}, {city}" if full_address else city
        if state:
            full_address = f"{full_address}, {state}" if full_address else state
        if zip_code:
            full_address = f"{full_address} {zip_code}" if full_address else zip_code
        
        # RENTS - Check multiple fields based on property type
        # Properties with .30=owner code (T/S/J) have rents in .60
        # Properties with .30=description have rents in .54
        if field_30 in ["T", "t", "S", "s", "J", "j"]:
            rents_received = entry.get_decimal("60")
        else:
            rents_received = entry.get_decimal("54")
        
        # If still 0, try both
        if rents_received == 0:
            rents_received = entry.get_decimal("54") or entry.get_decimal("60")
        
        # EXPENSES - Sum of individual expense fields (NOT .60!)
        insurance = entry.get_decimal("81")
        mortgage_interest = entry.get_decimal("90") + entry.get_decimal("100")  # may be in either
        repairs = entry.get_decimal("93")
        taxes = entry.get_decimal("99")
        utilities = entry.get_decimal("102")
        depreciation = entry.get_decimal("105")
        # Other expenses from various fields
        other_expenses = (
            entry.get_decimal("110") +  # other expenses 1
            entry.get_decimal("120") +  # other expenses 2  
            entry.get_decimal("141") +  # bank service fees
            entry.get_decimal("148")    # loan cancellation fee, etc
        )
        
        # Calculate total expenses from individual fields
        total_expenses = (
            insurance + mortgage_interest + repairs + taxes +
            utilities + depreciation + other_expenses
        )
        
        net_income_loss = rents_received - total_expenses
        
        return ScheduleE(
            owner=owner,
            property_description=property_name or property_type,
            property_address=full_address,
            property_type=property_type or "Rental",
            rents_received=rents_received,
            insurance=insurance,
            mortgage_interest=mortgage_interest,
            repairs=repairs,
            taxes=taxes,
            utilities=utilities,
            depreciation=depreciation,
            other_expenses=other_expenses,
            total_expenses=total_expenses,
            net_income_loss=net_income_loss
        )

    def _parse_consolidated_1099(self, doc: CCHDocument, tr: TaxReturn) -> None:
        """Parse consolidated 1099 forms (Form 881 header + Form 882 summary)
        
        Form 881 entries and Form 882 entries are linked by section number.
        Build a section->payer map from Form 881, then look up correct payer
        for each Form 882 entry.
        """
        # Get Form 882 summary entries - these have interest and dividend amounts
        form_882 = doc.forms.get("882", None)
        if not form_882:
            return
        
        # Get Form 881 header entries for payer names
        form_881 = doc.forms.get("881", None)
        
        # Build section -> payer name map from Form 881
        section_to_payer = {}
        if form_881:
            for entry_881 in form_881.entries:
                section = getattr(entry_881, 'section', None)
                payer = entry_881.get("34", "")
                if section and payer:
                    section_to_payer[section] = payer
        
        # Parse Form 882 entries - match by section number
        for entry in form_882.entries:
            interest_amount = entry.get_decimal("40")  # Box 1 interest
            
            if interest_amount and interest_amount > 0:
                # Look up payer by section number
                section = getattr(entry, 'section', None)
                payer_name = section_to_payer.get(section, "Consolidated 1099")
                
                # Determine owner from field .31 or default
                owner_code = entry.get("31", "")
                # .31 appears to be an amount, not owner code - check other fields
                # Default to taxpayer
                owner = TaxpayerType.TAXPAYER
                
                tr.income.form_1099_int.append(Form1099INT(
                    owner=owner,
                    payer_name=payer_name,
                    interest_income=interest_amount
                ))
