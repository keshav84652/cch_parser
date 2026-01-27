from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

@dataclass
class StatementItem:
    """A generic line item for financial statements"""
    description: str
    amount: Decimal
    
    # Optional metadata if we later want to track which column/year
    year_label: str = "" 

@dataclass
class BalanceSheet:
    """Represents a Balance Sheet (Assets/Liabilities)"""
    # Simply a list of items for now, as the structure is dynamic
    items: List[StatementItem] = field(default_factory=list)
