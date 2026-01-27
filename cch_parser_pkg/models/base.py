from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
from datetime import date

class FilingStatus(Enum):
    """IRS Filing Status codes"""
    SINGLE = "1"
    MARRIED_FILING_JOINTLY = "2"
    MARRIED_FILING_SEPARATELY = "3"
    HEAD_OF_HOUSEHOLD = "4"
    QUALIFYING_WIDOW = "5"

class TaxpayerType(Enum):
    """Indicates taxpayer or spouse"""
    TAXPAYER = "T"
    SPOUSE = "S"
    JOINT = "J"

@dataclass
class Address:
    """Mailing address"""
    street: str = ""
    apt: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    
    def __str__(self) -> str:
        parts = [self.street]
        if self.apt:
            parts.append(f"Apt {self.apt}")
        parts.append(f"{self.city}, {self.state} {self.zip_code}")
        return ", ".join(parts)

@dataclass
class Person:
    """Base person information"""
    first_name: str = ""
    middle_initial: str = ""
    last_name: str = ""
    ssn: str = ""
    dob: Optional[date] = None
    occupation: str = ""
    email: str = ""
    phone: str = ""
    
    @property
    def full_name(self) -> str:
        parts = [self.first_name]
        if self.middle_initial:
            parts.append(self.middle_initial)
        parts.append(self.last_name)
        return " ".join(parts)

@dataclass
class Dependent:
    """Dependent information"""
    first_name: str = ""
    last_name: str = ""
    ssn: str = ""
    relationship: str = ""
    dob: Optional[date] = None
    months_lived: int = 12
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

@dataclass
class BankAccount:
    """Bank account for direct deposit/debit"""
    bank_name: str = ""
    routing_number: str = ""
    account_number: str = ""
    is_checking: bool = True
    is_savings: bool = False
