"""
Risk Flags Detection Engine

Identifies audit risks, compliance issues, and items requiring review.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from decimal import Decimal

from ..models.return_data import TaxReturn


@dataclass
class RiskFlag:
    """Represents a risk or compliance flag"""
    category: str  # Audit, Compliance, Review
    severity: str  # High, Medium, Low
    description: str
    recommendation: str


@dataclass
class ClientRisks:
    """All risk flags for a client"""
    client_name: str
    client_id: str
    flags: List[RiskFlag] = field(default_factory=list)
    
    @property
    def high_risk_count(self) -> int:
        return sum(1 for f in self.flags if f.severity == 'High')
    
    @property
    def needs_partner_review(self) -> bool:
        return self.high_risk_count > 0


class RiskEngine:
    """Detect risk flags based on client data"""
    
    def analyze(self, tr: TaxReturn) -> ClientRisks:
        """Analyze a tax return for risks"""
        result = ClientRisks(
            client_name=tr.taxpayer.full_name,
            client_id=tr.client_id
        )
        
        agi = float(tr.income.total_income)
        
        # Schedule C with losses
        self_emp = float(tr.income.total_self_employment)
        if self_emp < 0:
            result.flags.append(RiskFlag(
                category='Audit',
                severity='High',
                description=f'Schedule C loss of ${abs(self_emp):,.0f}',
                recommendation='Verify hobby loss rules, document profit motive'
            ))
        
        # High charitable relative to income
        # Would need deduction data; placeholder for now
        
        # Multiple K-1 losses
        k1_income = float(tr.income.total_k1_income)
        k1_count = len(tr.income.k1_1065) + len(tr.income.k1_1120s)
        if k1_income < 0 and k1_count > 2:
            result.flags.append(RiskFlag(
                category='Review',
                severity='Medium',
                description=f'Multiple K-1s with net loss ${abs(k1_income):,.0f}',
                recommendation='Verify basis, at-risk, and passive loss limitations'
            ))
        
        # FBAR without apparent foreign income
        if len(tr.income.fbar) > 0:
            result.flags.append(RiskFlag(
                category='Compliance',
                severity='High',
                description=f'{len(tr.income.fbar)} foreign accounts require FBAR',
                recommendation='Confirm FBAR filed, review Form 8938 requirements'
            ))
        
        # High income with no estimated payments
        # Would need estimated payment data from form 109
        if agi > 200000:
            # Check if we have data on estimated payments
            has_withholding = any(
                w.fed_tax_withheld > 0 
                for w in tr.income.w2s
            )
            if not has_withholding and len(tr.income.w2s) == 0:
                result.flags.append(RiskFlag(
                    category='Compliance',
                    severity='Medium',
                    description='High income with no W-2 withholding',
                    recommendation='Verify estimated payments made to avoid penalty'
                ))
        
        # Complex K-1 structure
        if k1_count > 5:
            result.flags.append(RiskFlag(
                category='Review',
                severity='Medium',
                description=f'{k1_count} K-1 partnerships',
                recommendation='Basis tracking critical, verify carryovers'
            ))
        
        # Balance sheet present (complex business)
        if tr.balance_sheet and tr.balance_sheet.items:
            if len(tr.balance_sheet.items) > 5:
                result.flags.append(RiskFlag(
                    category='Review',
                    severity='Low',
                    description='Complex balance sheet with multiple items',
                    recommendation='Verify asset/liability accuracy'
                ))
        
        # Multiple states (nexus risk)
        state_forms = ['4940', '6640', '6840', '5240', '7040']
        states_filed = sum(1 for code in state_forms if code in tr.raw_forms)
        if states_filed > 2:
            result.flags.append(RiskFlag(
                category='Compliance',
                severity='High',
                description=f'{states_filed} state returns filed',
                recommendation='Multi-state nexus review recommended'
            ))
        
        # 1099-MISC/NEC without Schedule C
        misc_count = len(tr.income.form_1099_misc) + len(tr.income.form_1099_nec)
        has_sch_c = '171' in tr.raw_forms
        if misc_count > 0 and not has_sch_c and self_emp == 0:
            result.flags.append(RiskFlag(
                category='Review',
                severity='Medium',
                description='1099 income without Schedule C',
                recommendation='Verify income classification (employee vs contractor)'
            ))
        
        return result


def analyze_all_risks(returns: List[TaxReturn]) -> List[ClientRisks]:
    """Analyze all returns for risks"""
    engine = RiskEngine()
    return [engine.analyze(tr) for tr in returns]
