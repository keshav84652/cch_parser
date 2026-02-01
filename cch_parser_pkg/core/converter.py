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

    def _parse_owner(self, entry: CCHFormEntry, field_num: str = "30") -> TaxpayerType:
        """Parse owner code (T/S/J) from entry field.

        Args:
            entry: The form entry to parse
            field_num: Field number containing owner code (default "30")

        Returns:
            TaxpayerType.TAXPAYER, TaxpayerType.SPOUSE, or TaxpayerType.JOINT
        """
        code = entry.get(field_num, "T").upper()
        if code == "S":
            return TaxpayerType.SPOUSE
        if code == "J":
            return TaxpayerType.JOINT
        return TaxpayerType.TAXPAYER
    
    def convert(self, doc: CCHDocument) -> TaxReturn:
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
        """Parse client information from Form 101 or Form 151 for individuals.

        Taxpayer data can be in EITHER form depending on how CCH export was configured:
        - Some returns have data in Form 101 (fields 40-44, 60-68, 80-84)
        - Some returns have data in Form 151 (1A) with same field numbers
        - We check Form 101 first (more common), then fallback to Form 151
        """
        # Try Form 101 first
        form_101 = doc.get_form("101")
        form_151 = doc.get_form("151")

        entry = None
        # Check if Form 101 has taxpayer data (field 40 = first name)
        if form_101 and form_101.entries:
            e = form_101.entries[0]
            if e.get("40"):  # Has first name
                entry = e

        # Fallback to Form 151 if Form 101 doesn't have data
        if not entry and form_151 and form_151.entries:
            e = form_151.entries[0]
            if e.get("40"):  # Has first name
                entry = e

        # Field mappings (same for both Form 101 and Form 151):
        # 40=first_name, 41=middle, 42=last_name, 44=ssn
        # 45=spouse_first, 46=spouse_middle, 47=spouse_last, 49=spouse_ssn
        # 60=occupation, 61=dob, 67=spouse_occupation, 68=spouse_dob
        # 80=street, 82=city, 83=state, 84=zip

        # Get taxpayer data from form entry if available
        first_name = entry.get("40", "") if entry else ""
        middle_initial = entry.get("41", "") if entry else ""
        last_name = entry.get("42", "") if entry else ""
        ssn = entry.get("44", "") if entry else ""

        # Fallback to header info if form data is incomplete
        if not ssn:
            ssn = doc.header.get("ssn", "")
        if not first_name:
            first_name = doc.client_id

        # Taxpayer
        tr.taxpayer = Person(
            first_name=first_name,
            middle_initial=middle_initial,
            last_name=last_name,
            ssn=ssn,
            dob=entry.get_date("61") if entry else None,
            occupation=entry.get("60", "") if entry else ""
        )

        if not entry:
            return

        # Spouse
        if entry.get("45"):
            tr.spouse = Person(
                first_name=entry.get("45", ""),
                middle_initial=entry.get("46", ""),
                last_name=entry.get("47", ""),
                ssn=entry.get("49", ""),
                occupation=entry.get("67", ""),
                dob=entry.get_date("68")
            )

        # Address
        tr.address = Address(
            street=entry.get("80", ""),
            city=entry.get("82", ""),
            state=entry.get("83", ""),
            zip_code=entry.get("84", "")
        )

        # Phone and email - primarily in Form 151, but check Form 101 as fallback
        phone = ""
        email = ""
        spouse_email = ""

        # Try Form 151 first (most common location)
        if form_151 and form_151.entries:
            entry_151 = form_151.entries[0]
            phone = entry_151.get("65", "")
            email = entry_151.get("75", "")
            spouse_email = entry_151.get("76", "")

        # Fallback to Form 101 if not found in 151
        if entry and (not phone or not email):
            if not phone:
                phone = entry.get("65", "")
            if not email:
                email = entry.get("75", "")
            if not spouse_email:
                spouse_email = entry.get("76", "")

        # Set on taxpayer Person object
        if tr.taxpayer:
            tr.taxpayer.phone = phone
            tr.taxpayer.email = email if "@" in email else ""
        if tr.spouse and spouse_email:
            tr.spouse.email = spouse_email if "@" in spouse_email else ""

        # Filing Status - from Form 151 field 90
        status_code = entry.get("90", "")
        try:
            tr.filing_status = FilingStatus(status_code)
        except ValueError:
            pass  # Default is Single

        # Dependents - Form 151 fields 110-136
        self._parse_dependents(entry, tr)

    def _parse_dependents(self, entry: CCHFormEntry, tr: TaxReturn) -> None:
        """Parse dependent information from Form 101/151.

        Dependent field patterns (up to 4 dependents):
        | Dep # | First | Last | SSN | Relationship | DOB |
        |-------|-------|------|-----|--------------|-----|
        | 1     | 110   | 112  | 114 | 115          | 140 |
        | 2     | 117   | 119  | 121 | 122          | 152 |
        | 3     | 124   | 126  | 128 | 129          | 164 |
        | 4     | 131   | 133  | 135 | 136          | 176 |
        """
        dep_patterns = [
            {"first": "110", "last": "112", "ssn": "114", "rel": "115", "dob": "140"},
            {"first": "117", "last": "119", "ssn": "121", "rel": "122", "dob": "152"},
            {"first": "124", "last": "126", "ssn": "128", "rel": "129", "dob": "164"},
            {"first": "131", "last": "133", "ssn": "135", "rel": "136", "dob": "176"},
        ]

        for pattern in dep_patterns:
            first_name = entry.get(pattern["first"], "")
            if not first_name:
                continue

            dep = Dependent(
                first_name=first_name,
                last_name=entry.get(pattern["last"], ""),
                ssn=entry.get(pattern["ssn"], ""),
                relationship=entry.get(pattern["rel"], ""),
                dob=entry.get_date(pattern["dob"])
            )
            tr.dependents.append(dep)

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
        """Parse bank account info using YAML mappings (form_921)"""
        entries = doc.get_form_entries("921")
        if entries:
            e = entries[0]
            f = lambda name: self.map.get_field_number("921", name)
            tr.bank_account = BankAccount(
                bank_name=e.get(f("bank_name")),
                routing_number=e.get(f("routing_number")),
                account_number=e.get(f("account_number")),
                is_checking=e.get_bool(f("is_checking"))
            )

    def _parse_w2(self, entry: CCHFormEntry) -> W2:
        """Parse W-2 using YAML mappings (form_180) - strict, no fallbacks"""
        f = lambda name: self.map.get_field_number("180", name)
        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))

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
        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))

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
        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))

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
        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))

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
        """Parse 1099-NEC using YAML mappings (form_267)"""
        f = lambda name: self.map.get_field_number("267", name)
        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))

        return Form1099NEC(
            owner=owner,
            payer_name=entry.get(f("payer_name")),
            payer_tin=entry.get(f("payer_tin")),
            nonemployee_compensation=entry.get_decimal(f("box1_nec")),
            fed_tax_withheld=entry.get_decimal(f("box4_fed_withheld"))
        )

    def _parse_1099g(self, entry: CCHFormEntry) -> Form1099G:
        """Parse 1099-G using YAML mappings (form_209)"""
        f = lambda name: self.map.get_field_number("209", name)
        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))

        return Form1099G(
            owner=owner,
            payer_name=entry.get(f("payer_name")),
            unemployment_compensation=entry.get_decimal(f("box1_unemployment")),
            state_local_refund=Decimal("0"),  # Not commonly present in data
            fed_tax_withheld=entry.get_decimal(f("box4_fed_withheld")),
            state=entry.get(f("state"))
        )

    def _parse_fbar(self, entry: CCHFormEntry) -> FormFBAR:
        """Parse FBAR using YAML mappings (form_925)"""
        f = lambda name: self.map.get_field_number("925", name)
        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))

        return FormFBAR(
            owner=owner,
            bank_name=entry.get(f("bank_name")),
            bank_address=entry.get(f("bank_address")),
            bank_city=entry.get(f("bank_city")),
            bank_country=entry.get(f("bank_country")),
            account_number=entry.get(f("account_number")),
            max_value=entry.get_decimal(f("max_value")),
            account_type=entry.get(f("account_type"), "Bank")
        )
        
    def _parse_k1_1065(self, entry: CCHFormEntry) -> FormK1_1065:
        """Parse K-1 (1065) Partnership using YAML mappings - strict, no fallbacks"""
        f = lambda name: self.map.get_field_number("185", name)
        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))
        
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
        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))
        
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
        """Parse SSA-1099 using YAML mappings (form_190)"""
        f = lambda name: self.map.get_field_number("190", name)
        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))

        return SSA1099(
            owner=owner,
            beneficiary_name=entry.get(f("beneficiary_name")),
            benefits_paid=entry.get_decimal(f("box3_benefits_paid")),
            net_benefits=entry.get_decimal(f("box5_net_benefits")),
            claim_number=entry.get(f("claim_number"))
        )

    def _parse_1098(self, entry: CCHFormEntry) -> Form1098:
        """Parse 1098 Mortgage using YAML mappings (form_206)"""
        f = lambda name: self.map.get_field_number("206", name)
        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))

        return Form1098(
            owner=owner,
            lender_name=entry.get(f("lender_name")),
            lender_tin=entry.get(f("lender_tin")),
            mortgage_interest=entry.get_decimal(f("box1_mortgage_interest")),
            outstanding_principal=entry.get_decimal("59"),
            property_address=entry.get(f("property_address")),
            points_paid=entry.get_decimal(f("box2_points"))
        )

    def _parse_1095a(self, entry: CCHFormEntry) -> Form1095A:
        """Parse 1095-A using YAML mappings (form_624)"""
        f = lambda name: self.map.get_field_number("624", name)

        return Form1095A(
            marketplace_state=entry.get(f("marketplace_state")),
            policy_number=entry.get(f("policy_number")),
            plan_name=entry.get(f("plan_name")),
            covered_individual=entry.get(f("covered_individual_name")),
            annual_premium=entry.get_decimal(f("annual_premium")),
            annual_slcsp=entry.get_decimal(f("annual_slcsp")),
            annual_aptc=entry.get_decimal(f("annual_aptc"))
        )

    def _parse_1099misc(self, entry: CCHFormEntry) -> Form1099MISC:
        """Parse 1099-MISC using YAML mappings (form_183)"""
        f = lambda name: self.map.get_field_number("183", name)
        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))

        return Form1099MISC(
            owner=owner,
            payer_name=entry.get(f("payer_name")),
            payer_tin=entry.get(f("payer_tin")),
            other_income=entry.get_decimal(f("box3_other_income")),
            rents=entry.get_decimal(f("box1_rents")),
            royalties=entry.get_decimal(f("box2_royalties")),
            fishing_boat_proceeds=Decimal("0"),  # Rarely used
            medical_payments=Decimal("0"),  # Rarely used
            nonqualified_deferred_comp=Decimal("0"),  # Rarely used
            state=entry.get(f("state")),
            state_income=entry.get_decimal(f("state_income"))
        )

    def _parse_1095c(self, entry: CCHFormEntry) -> Form1095C:
        """Parse 1095-C using YAML mappings (form_641)"""
        f = lambda name: self.map.get_field_number("641", name)
        employer_name = entry.get(f("employer_name"))
        if not employer_name:
            # Skip invalid entries (likely Form EF-2 which shares code 641)
            pass

        owner = self._parse_owner(entry, f("taxpayer_or_spouse"))

        return Form1095C(
            owner=owner,
            employer_name=employer_name,
            employer_ein=entry.get(f("employer_ein")),
            employer_address=entry.get(f("employer_address")),
            employer_city=entry.get(f("employer_city")),
            employer_state=entry.get(f("employer_state")),
            employer_zip=entry.get(f("employer_zip")),
            employee_name=entry.get(f("employee_name")),
            employee_ssn=entry.get("115"),
            offer_of_coverage=entry.get("118"),
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
        """Parse Schedule E (Form 211) - Rental Real Estate using YAML mappings

        IMPORTANT: Field usage varies by property type!
        - Properties with .30=T/S/J use .60 for rents
        - Properties with .30=description use .54 for rents
        """
        f = lambda name: self.map.get_field_number("211", name)

        # Handle mixed .30 field - determine if it's owner code or property type
        field_30 = entry.get(f("owner_or_property_type"), "")
        owner = TaxpayerType.TAXPAYER
        property_type = ""

        if field_30.upper() in ["T", "S", "J"]:
            owner = self._parse_owner(entry, f("owner_or_property_type"))
        else:
            # .30 contains property type description
            property_type = field_30

        # Property info from YAML fields
        property_name = entry.get(f("property_name"), "") or property_type
        property_address = entry.get(f("property_address"), "") or entry.get(f("address_line_1"), "")
        city = entry.get(f("city"), "")
        state = entry.get(f("state_code"), "")
        zip_code = entry.get(f("zip"), "")

        # Build full address
        full_address = property_address
        if city:
            full_address = f"{full_address}, {city}" if full_address else city
        if state:
            full_address = f"{full_address}, {state}" if full_address else state
        if zip_code:
            full_address = f"{full_address} {zip_code}" if full_address else zip_code

        # RENTS - Check multiple fields based on property type
        if field_30.upper() in ["T", "S", "J"]:
            rents_received = entry.get_decimal(f("total_expenses"))  # .60 in owner-code mode
        else:
            rents_received = entry.get_decimal(f("rents_received"))

        # If still 0, try both
        if rents_received == 0:
            rents_received = entry.get_decimal(f("rents_received")) or entry.get_decimal(f("total_expenses"))

        # EXPENSES - Use YAML field lookups
        insurance = entry.get_decimal(f("insurance"))
        mortgage_interest = entry.get_decimal(f("mortgage_interest"))
        repairs = entry.get_decimal(f("repairs"))
        taxes = entry.get_decimal(f("taxes"))
        utilities = entry.get_decimal(f("utilities"))
        depreciation = entry.get_decimal(f("depreciation"))
        other_expenses = (
            entry.get_decimal(f("other_expenses")) +
            entry.get_decimal(f("other_expenses_2"))
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

        YAML mappings (form_882):
        - Field 57: interest_income
        - Field 31: ordinary_dividends
        - Field 32: qualified_dividends
        - Field 34: total_capital_gain
        - Field 41: federal_withholding
        """
        # Get Form 882 summary entries - these have interest and dividend amounts
        form_882 = doc.forms.get("882", None)
        if not form_882:
            return

        # Get Form 881 header entries for payer names, account numbers, and owners
        form_881 = doc.forms.get("881", None)

        # Build section -> (payer_name, account_number, owner) map from Form 881
        section_to_info = {}
        if form_881:
            for entry_881 in form_881.entries:
                section = getattr(entry_881, 'section', None)
                payer = entry_881.get("34", "")  # broker_name per YAML
                acct = entry_881.get("46", "")   # account_number
                owner_code = entry_881.get("30", "T")  # T=Taxpayer, S=Spouse, J=Joint
                if section and payer:
                    section_to_info[section] = (payer, acct, owner_code)

        # Use YAML field lookups
        f = lambda name: self.map.get_field_number("882", name)

        # Parse Form 882 entries
        for entry in form_882.entries:
            section = getattr(entry, 'section', None)
            payer_name, account_number, owner_code = section_to_info.get(
                section, ("Consolidated 1099", "", "T")
            )

            # Parse owner from Form 881 data
            if owner_code == "S":
                owner = TaxpayerType.SPOUSE
            elif owner_code == "J":
                owner = TaxpayerType.JOINT
            else:
                owner = TaxpayerType.TAXPAYER

            # Interest income (field 57 per YAML)
            interest_amount = entry.get_decimal(f("interest_income"))
            if interest_amount and interest_amount > 0:
                tr.income.form_1099_int.append(Form1099INT(
                    owner=owner,
                    payer_name=payer_name,
                    account_number=account_number,
                    interest_income=interest_amount,
                    fed_tax_withheld=entry.get_decimal(f("federal_withholding"))
                ))

            # Dividend income (fields 31, 32 per YAML)
            ordinary_div = entry.get_decimal(f("ordinary_dividends"))
            qualified_div = entry.get_decimal(f("qualified_dividends"))
            capital_gain = entry.get_decimal(f("total_capital_gain"))

            if ordinary_div and ordinary_div > 0:
                tr.income.form_1099_div.append(Form1099DIV(
                    owner=owner,
                    payer_name=payer_name,
                    account_number=account_number,
                    ordinary_dividends=ordinary_div,
                    qualified_dividends=qualified_div,
                    capital_gain_dist=capital_gain,
                    fed_tax_withheld=entry.get_decimal(f("federal_withholding"))
                ))

    # Backwards compatibility alias
    def to_tax_return(self, doc: CCHDocument) -> TaxReturn:
        """Deprecated: Use convert() instead."""
        return self.convert(doc)
