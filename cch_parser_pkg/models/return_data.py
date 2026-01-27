from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Any
from .base import Person, Address, TaxpayerType, FilingStatus, BankAccount, Dependent
from .income import (
    W2, Form1099INT, Form1099DIV, Form1099R, Form1099NEC, Form1099G,
    FormK1_1065, FormK1_1120S, SSA1099, FormFBAR, Form1099MISC, ScheduleE
)
from .deductions import Form1098, Form1095A, Form1095C
from .statements import BalanceSheet

@dataclass
class IncomeData:
    """Aggregated income information"""
    w2s: List[W2] = field(default_factory=list)
    form_1099_int: List[Form1099INT] = field(default_factory=list)
    form_1099_div: List[Form1099DIV] = field(default_factory=list)
    form_1099_r: List[Form1099R] = field(default_factory=list)
    form_1099_nec: List[Form1099NEC] = field(default_factory=list)
    form_1099_g: List[Form1099G] = field(default_factory=list)
    k1_1065: List[FormK1_1065] = field(default_factory=list)
    k1_1120s: List[FormK1_1120S] = field(default_factory=list)
    ssa_1099: List[SSA1099] = field(default_factory=list)
    fbar: List[FormFBAR] = field(default_factory=list)
    form_1099_misc: List[Form1099MISC] = field(default_factory=list)
    schedule_e: List[ScheduleE] = field(default_factory=list)  # Rental income
    
    @property
    def total_wages(self) -> Decimal:
        return sum(w.wages for w in self.w2s)
    
    @property
    def total_interest(self) -> Decimal:
        return sum(f.interest_income for f in self.form_1099_int)
    
    @property
    def total_dividends(self) -> Decimal:
        return sum(f.ordinary_dividends for f in self.form_1099_div)
    
    @property
    def total_qualified_dividends(self) -> Decimal:
        return sum(f.qualified_dividends for f in self.form_1099_div)
    
    @property
    def total_retirement_distributions(self) -> Decimal:
        return sum(f.taxable_amount for f in self.form_1099_r)
    
    @property
    def total_self_employment(self) -> Decimal:
        return sum(f.nonemployee_compensation for f in self.form_1099_nec)
    
    @property
    def total_partnership_income(self) -> Decimal:
        return sum(k.ordinary_income for k in self.k1_1065)
    
    @property
    def total_scorp_income(self) -> Decimal:
        return sum(k.ordinary_income for k in self.k1_1120s)
    
    @property
    def total_k1_income(self) -> Decimal:
        return self.total_partnership_income + self.total_scorp_income
    
    @property
    def total_social_security(self) -> Decimal:
        return sum(s.net_benefits for s in self.ssa_1099)

    @property
    def total_other_income(self) -> Decimal:
        return sum(f.other_income for f in self.form_1099_misc)

    @property
    def total_income(self) -> Decimal:
        """Total of all income sources"""
        return (
            self.total_wages +
            self.total_interest +
            self.total_dividends +
            self.total_retirement_distributions +
            self.total_self_employment +
            self.total_k1_income +
            self.total_social_security +
            self.total_other_income
        )

@dataclass
class DeductionData:
    """Aggregated deduction information"""
    mortgage_interest: List[Form1098] = field(default_factory=list)
    health_insurance: List[Form1095A] = field(default_factory=list)
    form_1095_c: List[Form1095C] = field(default_factory=list)
    
    # From worksheets
    state_local_taxes: Decimal = Decimal("0")
    real_estate_taxes: Decimal = Decimal("0")
    medical_expenses: Decimal = Decimal("0")
    charitable_cash: Decimal = Decimal("0")
    charitable_noncash: Decimal = Decimal("0")
    student_loan_interest: Decimal = Decimal("0")
    
    @property
    def total_mortgage_interest(self) -> Decimal:
        return sum(m.mortgage_interest for m in self.mortgage_interest)
    
    @property
    def total_charitable(self) -> Decimal:
        return self.charitable_cash + self.charitable_noncash

@dataclass
class TaxReturn:
    """Complete parsed tax return"""
    tax_year: int = 0
    client_id: str = ""
    
    # Taxpayer info
    taxpayer: Person = field(default_factory=Person)
    spouse: Optional[Person] = None
    filing_status: FilingStatus = FilingStatus.SINGLE
    address: Address = field(default_factory=Address)
    dependents: List[Dependent] = field(default_factory=list)
    
    # Bank info
    bank_account: Optional[BankAccount] = None
    
    # Financial data
    income: IncomeData = field(default_factory=IncomeData)
    deductions: DeductionData = field(default_factory=DeductionData)
    balance_sheet: Optional[BalanceSheet] = None
    
    # Raw forms for reference
    raw_forms: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export"""
        return {
            "tax_year": self.tax_year,
            "client_id": self.client_id,
            "taxpayer": {
                "name": self.taxpayer.full_name,
                "ssn": self.taxpayer.ssn,
                "dob": str(self.taxpayer.dob) if self.taxpayer.dob else None,
                "occupation": self.taxpayer.occupation,
                "email": self.taxpayer.email,
                "phone": self.taxpayer.phone
            },
            "spouse": {
                "name": self.spouse.full_name,
                "ssn": self.spouse.ssn
            } if self.spouse else None,
            "address": str(self.address),
            "filing_status": self.filing_status.name,
            "dependents": [
                {"name": d.full_name, "relationship": d.relationship}
                for d in self.dependents
            ],
            "income_summary": {
                "wages": float(self.income.total_wages),
                "interest": float(self.income.total_interest),
                "dividends": float(self.income.total_dividends),
                "retirement": float(self.income.total_retirement_distributions),
                "self_employment": float(self.income.total_self_employment),
                "partnership": float(self.income.total_partnership_income),
                "social_security": float(self.income.total_social_security),
                "other_income": float(self.income.total_other_income)
            },
            "deduction_summary": {
                "mortgage_interest": float(self.deductions.total_mortgage_interest),
                "state_local_taxes": float(self.deductions.state_local_taxes),
                "charitable": float(self.deductions.total_charitable),
                "medical": float(self.deductions.medical_expenses)
            },
            "balance_sheet": [
                {"description": item.description, "amount": float(item.amount)}
                for item in self.balance_sheet.items
            ] if self.balance_sheet else None
        }
