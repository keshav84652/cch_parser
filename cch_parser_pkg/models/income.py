from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import date
from .base import TaxpayerType

@dataclass
class W2:
    """Form W-2 Wage and Tax Statement"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    employer_name: str = ""
    employer_ein: str = ""
    employer_address: str = ""
    employer_city: str = ""
    employer_state: str = ""
    employer_zip: str = ""
    control_number: str = ""
    
    # Box 1-6: Income and withholding
    wages: Decimal = Decimal("0")
    fed_tax_withheld: Decimal = Decimal("0")
    ss_wages: Decimal = Decimal("0")
    ss_tax_withheld: Decimal = Decimal("0")
    medicare_wages: Decimal = Decimal("0")
    medicare_tax_withheld: Decimal = Decimal("0")
    
    # Box 7-11
    ss_tips: Decimal = Decimal("0")
    allocated_tips: Decimal = Decimal("0")
    dependent_care: Decimal = Decimal("0")
    nonqualified_plans: Decimal = Decimal("0")
    
    # Box 12 codes
    box12: Dict[str, Decimal] = field(default_factory=dict)
    
    # Box 13 checkboxes
    statutory_employee: bool = False
    retirement_plan: bool = False
    third_party_sick_pay: bool = False
    
    # Box 14 other
    box14: Dict[str, Decimal] = field(default_factory=dict)
    
    # State/local (boxes 15-20)
    state: str = ""
    state_ein: str = ""
    state_wages: Decimal = Decimal("0")
    state_tax: Decimal = Decimal("0")
    local_wages: Decimal = Decimal("0")
    local_tax: Decimal = Decimal("0")
    locality_name: str = ""


@dataclass
class Form1099INT:
    """Form 1099-INT Interest Income"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    payer_name: str = ""
    payer_tin: str = ""
    payer_address: str = ""
    payer_city: str = ""
    payer_state: str = ""
    payer_zip: str = ""
    account_number: str = ""
    
    interest_income: Decimal = Decimal("0")  # Box 1
    prior_year_interest: Decimal = Decimal("0")  # Box 1 Prior Year (from .71M)
    early_withdrawal_penalty: Decimal = Decimal("0")  # Box 2
    us_savings_bond_interest: Decimal = Decimal("0")  # Box 3
    fed_tax_withheld: Decimal = Decimal("0")  # Box 4
    investment_expenses: Decimal = Decimal("0")  # Box 5
    foreign_tax_paid: Decimal = Decimal("0")  # Box 6
    foreign_country: str = ""  # Box 7
    tax_exempt_interest: Decimal = Decimal("0")  # Box 8
    private_activity_bond: Decimal = Decimal("0")  # Box 9


@dataclass
class Form1099DIV:
    """Form 1099-DIV Dividend Income"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    payer_name: str = ""
    payer_tin: str = ""
    account_number: str = ""
    
    ordinary_dividends: Decimal = Decimal("0")  # Box 1a
    prior_year_dividends: Decimal = Decimal("0")  # Box 1a Prior Year (from .70M)
    qualified_dividends: Decimal = Decimal("0")  # Box 1b
    capital_gain_dist: Decimal = Decimal("0")  # Box 2a
    unrecap_sec_1250: Decimal = Decimal("0")  # Box 2b
    section_1202_gain: Decimal = Decimal("0")  # Box 2c
    collectibles_gain: Decimal = Decimal("0")  # Box 2d
    nondividend_dist: Decimal = Decimal("0")  # Box 3
    fed_tax_withheld: Decimal = Decimal("0")  # Box 4
    section_199a_div: Decimal = Decimal("0")  # Box 5
    investment_expenses: Decimal = Decimal("0")  # Box 6
    foreign_tax_paid: Decimal = Decimal("0")  # Box 7
    foreign_country: str = ""  # Box 8


@dataclass
class Form1099R:
    """Form 1099-R Retirement Distributions"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    payer_name: str = ""
    payer_tin: str = ""
    payer_address: str = ""
    payer_city: str = ""
    payer_state: str = ""
    payer_zip: str = ""
    account_number: str = ""  # Recipient's account number
    
    gross_distribution: Decimal = Decimal("0")  # Box 1
    taxable_amount: Decimal = Decimal("0")  # Box 2a
    taxable_not_determined: bool = False  # Box 2b
    total_distribution: bool = False  # Box 2b
    capital_gain: Decimal = Decimal("0")  # Box 3
    fed_tax_withheld: Decimal = Decimal("0")  # Box 4
    employee_contributions: Decimal = Decimal("0")  # Box 5
    net_unrealized_appreciation: Decimal = Decimal("0")  # Box 6
    distribution_code: str = ""  # Box 7
    ira_sep_simple: bool = False  # Box 7
    state_tax_withheld: Decimal = Decimal("0")  # Box 12
    state: str = ""  # Box 13
    local_tax_withheld: Decimal = Decimal("0")  # Box 15


@dataclass
class Form1099NEC:
    """Form 1099-NEC Non-Employee Compensation"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    payer_name: str = ""
    payer_tin: str = ""
    payer_address: str = ""
    payer_city: str = ""
    payer_state: str = ""
    payer_zip: str = ""
    
    nonemployee_compensation: Decimal = Decimal("0")  # Box 1
    payer_direct_sales: bool = False  # Box 2
    fed_tax_withheld: Decimal = Decimal("0")  # Box 4
    state_tax_withheld: Decimal = Decimal("0")  # Box 5
    state: str = ""  # Box 6

@dataclass
class Form1099G:
    """Form 1099-G Government Payments"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    payer_name: str = ""
    payer_tin: str = ""
    payer_address: str = ""
    payer_city: str = ""
    payer_state: str = ""
    payer_zip: str = ""
    
    unemployment_compensation: Decimal = Decimal("0")  # Box 1
    state_local_refund: Decimal = Decimal("0")  # Box 2
    box_2_year: int = 0  # Year for Box 2
    fed_tax_withheld: Decimal = Decimal("0")  # Box 4
    rtaa_payments: Decimal = Decimal("0")  # Box 5
    taxable_grants: Decimal = Decimal("0")  # Box 6
    agriculture_payments: Decimal = Decimal("0")  # Box 7
    market_gain: Decimal = Decimal("0")  # Box 9
    state: str = ""
    state_id: str = ""
    state_tax_withheld: Decimal = Decimal("0")  # Box 11

@dataclass
class FormFBAR:
    """FBAR - Report of Foreign Bank and Financial Accounts"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    bank_name: str = ""
    account_number: str = ""
    bank_address: str = ""
    bank_city: str = ""
    bank_country: str = ""
    
    max_value: Decimal = Decimal("0")
    account_type: str = ""  # Bank, Securities, Other
    is_joint: bool = False

@dataclass
class SSA1099:
    """Form SSA-1099 Social Security Benefit Statement"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    beneficiary_name: str = ""
    claim_number: str = ""
    
    benefits_paid: Decimal = Decimal("0")  # Box 3
    benefits_repaid: Decimal = Decimal("0")  # Box 4
    net_benefits: Decimal = Decimal("0")  # Box 5
    voluntary_withholding: Decimal = Decimal("0")  # Box 6

@dataclass
class FormK1_1065:
    """Schedule K-1 (Form 1065) Partner's Share of Income"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    partnership_name: str = ""
    partnership_ein: str = ""
    partnership_address: str = ""
    partnership_city: str = ""
    partnership_state: str = ""
    partnership_zip: str = ""
    
    is_final: bool = False
    is_amended: bool = False
    partner_type: str = ""  # General/Limited
    domestic_foreign: str = ""  # D/F
    
    # Part III - Partner's Share of Current Year Income
    ordinary_income: Decimal = Decimal("0")  # Box 1
    net_rental_re_income: Decimal = Decimal("0")  # Box 2
    other_rental_income: Decimal = Decimal("0")  # Box 3
    guaranteed_payments: Decimal = Decimal("0")  # Box 4c
    interest_income: Decimal = Decimal("0")  # Box 5
    ordinary_dividends: Decimal = Decimal("0")  # Box 6a
    qualified_dividends: Decimal = Decimal("0")  # Box 6b
    royalties: Decimal = Decimal("0")  # Box 7
    net_stcg: Decimal = Decimal("0")  # Box 8
    net_ltcg: Decimal = Decimal("0")  # Box 9a
    section_1231_gain: Decimal = Decimal("0")  # Box 10
    
    # Additional boxes stored as dict
    other_income: Dict[str, Decimal] = field(default_factory=dict)
    deductions: Dict[str, Decimal] = field(default_factory=dict)
    credits: Dict[str, Decimal] = field(default_factory=dict)

@dataclass
class FormK1_1120S:
    """Schedule K-1 (Form 1120-S) Shareholder's Share of Income - S Corporation"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    corporation_name: str = ""
    corporation_ein: str = ""
    corporation_address: str = ""
    corporation_city: str = ""
    corporation_state: str = ""
    corporation_zip: str = ""
    
    is_final: bool = False
    is_amended: bool = False
    
    # Shareholder info
    share_percent: Decimal = Decimal("0")
    
    # Part III - Shareholder's Share of Current Year Income
    ordinary_income: Decimal = Decimal("0")  # Box 1
    net_rental_re_income: Decimal = Decimal("0")  # Box 2
    other_rental_income: Decimal = Decimal("0")  # Box 3
    interest_income: Decimal = Decimal("0")  # Box 4
    ordinary_dividends: Decimal = Decimal("0")  # Box 5a
    qualified_dividends: Decimal = Decimal("0")  # Box 5b
    royalties: Decimal = Decimal("0")  # Box 6
    net_stcg: Decimal = Decimal("0")  # Box 7
    net_ltcg: Decimal = Decimal("0")  # Box 8a
    section_1231_gain: Decimal = Decimal("0")  # Box 9
    
    # Additional boxes stored as dict
    other_income: Dict[str, Decimal] = field(default_factory=dict)
    deductions: Dict[str, Decimal] = field(default_factory=dict)
    credits: Dict[str, Decimal] = field(default_factory=dict)

@dataclass
class Form1099MISC:
    """Form 1099-MISC Miscellaneous Information"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    payer_name: str = ""
    payer_tin: str = ""
    payer_address: str = ""
    payer_city: str = ""
    payer_state: str = ""
    payer_zip: str = ""
    
    rents: Decimal = Decimal("0")  # Box 1
    royalties: Decimal = Decimal("0")  # Box 2
    other_income: Decimal = Decimal("0")  # Box 3
    fed_tax_withheld: Decimal = Decimal("0")  # Box 4
    fishing_boat_proceeds: Decimal = Decimal("0") # Box 5
    medical_payments: Decimal = Decimal("0") # Box 6
    substitute_payments: Decimal = Decimal("0") # Box 8
    crop_insurance: Decimal = Decimal("0") # Box 9
    gross_proceeds_attorney: Decimal = Decimal("0") # Box 10
    section_409a_deferrals: Decimal = Decimal("0") # Box 12
    excess_golden_parachute: Decimal = Decimal("0") # Box 14
    nonqualified_deferred_comp: Decimal = Decimal("0") # Box 15
    state_tax_withheld: Decimal = Decimal("0") # Box 16
    state: str = "" # Box 17
    state_income: Decimal = Decimal("0") # Box 18


@dataclass
class ScheduleE:
    """Schedule E - Supplemental Income and Loss (Rental Real Estate, etc.)"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    property_description: str = ""
    property_address: str = ""
    property_type: str = ""  # Multi-family, Single-family, etc.
    
    # Days rented / personal use
    fair_rental_days: int = 0
    personal_use_days: int = 0
    
    # Income
    rents_received: Decimal = Decimal("0")
    royalties_received: Decimal = Decimal("0")
    
    # Expenses
    advertising: Decimal = Decimal("0")
    auto_travel: Decimal = Decimal("0")
    cleaning_maintenance: Decimal = Decimal("0")
    commissions: Decimal = Decimal("0")
    insurance: Decimal = Decimal("0")
    legal_professional: Decimal = Decimal("0")
    management_fees: Decimal = Decimal("0")
    mortgage_interest: Decimal = Decimal("0")
    other_interest: Decimal = Decimal("0")
    repairs: Decimal = Decimal("0")
    supplies: Decimal = Decimal("0")
    taxes: Decimal = Decimal("0")
    utilities: Decimal = Decimal("0")
    depreciation: Decimal = Decimal("0")
    other_expenses: Decimal = Decimal("0")
    
    # Totals
    total_expenses: Decimal = Decimal("0")
    net_income_loss: Decimal = Decimal("0")
