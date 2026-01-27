from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import date
from .base import TaxpayerType


@dataclass
class Form1098:
    """Form 1098 Mortgage Interest Statement"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    lender_name: str = ""
    lender_tin: str = ""
    lender_address: str = ""
    lender_city: str = ""
    lender_state: str = ""
    lender_zip: str = ""
    
    mortgage_interest: Decimal = Decimal("0")  # Box 1
    outstanding_principal: Decimal = Decimal("0")  # Box 2
    origination_date: Optional[date] = None  # Box 3
    refund_of_interest: Decimal = Decimal("0")  # Box 4
    pmi_premiums: Decimal = Decimal("0")  # Box 5
    points_paid: Decimal = Decimal("0")  # Box 6
    property_address: str = ""  # Box 8
    property_count: int = 1  # Box 9
    loan_number: str = ""

@dataclass
class Form1095A:
    """Form 1095-A Health Insurance Marketplace Statement"""
    marketplace_state: str = ""
    policy_number: str = ""
    plan_name: str = ""
    
    covered_individual: str = ""
    covered_ssn: str = ""
    coverage_start: Optional[date] = None
    coverage_end: Optional[date] = None
    
    # Monthly amounts (indexed 1-12 for Jan-Dec)
    monthly_premium: Dict[int, Decimal] = field(default_factory=dict)
    monthly_slcsp: Dict[int, Decimal] = field(default_factory=dict)
    monthly_aptc: Dict[int, Decimal] = field(default_factory=dict)
    
    annual_premium: Decimal = Decimal("0")
    annual_slcsp: Decimal = Decimal("0")
    annual_aptc: Decimal = Decimal("0")

@dataclass
class Form1095C:
    """Form 1095-C Employer-Provided Health Insurance Offer and Coverage"""
    owner: TaxpayerType = TaxpayerType.TAXPAYER
    employer_name: str = ""
    employer_ein: str = ""
    employer_address: str = ""
    employer_city: str = ""
    employer_state: str = ""
    employer_zip: str = ""
    
    employee_name: str = ""
    employee_ssn: str = ""
    
    # Coverage data (Part II)
    offer_of_coverage: str = "" # Line 14
    employee_share: Decimal = Decimal("0") # Line 15
    safe_harbor_code: str = "" # Line 16
    
    # Covered Individuals (Part III)
    covered_individuals: List[str] = field(default_factory=list)

