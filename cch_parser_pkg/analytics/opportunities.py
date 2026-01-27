"""
Service Opportunities Engine

Identifies advisory and upsell opportunities based on client profile.
"""
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from decimal import Decimal

from ..models.return_data import TaxReturn


@dataclass
class Opportunity:
    """Represents a service opportunity"""
    name: str
    description: str
    estimated_revenue: int
    priority: str  # High, Medium, Low
    trigger_reason: str


@dataclass
class ClientOpportunities:
    """All opportunities for a client"""
    client_name: str
    client_id: str
    agi: Decimal
    opportunities: List[Opportunity] = field(default_factory=list)
    
    @property
    def total_potential_revenue(self) -> int:
        return sum(o.estimated_revenue for o in self.opportunities)


class OpportunitiesEngine:
    """Detect service opportunities based on client data"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Default thresholds and pricing
        self.thresholds = self.config.get('opportunities', {})
        self.pricing = {
            'S-Corp Conversion Analysis': 3000,
            'Tax Planning Session': 2000,
            'QBI Optimization Review': 1200,
            'Multi-State Nexus Review': 1500,
            'Estate Planning Consultation': 5000,
            'Quarterly Estimates Setup': 800,
            'Retirement Planning Analysis': 2500,
            'Cost Segregation Study': 5000,
            'Entity Structure Review': 2200,
            'Crypto Tax Advisory': 1500,
            'Rental Property Advisory': 1200,
            'FBAR Compliance Review': 1000,
        }
    
    def analyze(self, tr: TaxReturn) -> ClientOpportunities:
        """Analyze a tax return for opportunities"""
        result = ClientOpportunities(
            client_name=tr.taxpayer.full_name,
            client_id=tr.client_id,
            agi=tr.income.total_income
        )
        
        agi = float(tr.income.total_income)
        
        # S-Corp Conversion
        self_emp = float(tr.income.total_self_employment)
        if self_emp > 50000:
            result.opportunities.append(Opportunity(
                name='S-Corp Conversion Analysis',
                description=f'Self-employment income ${self_emp:,.0f} may benefit from S-Corp structure',
                estimated_revenue=self.pricing['S-Corp Conversion Analysis'],
                priority='High' if self_emp > 100000 else 'Medium',
                trigger_reason=f'Schedule C/SE income > $50K'
            ))
        
        # Tax Planning Session
        if agi > 200000:
            result.opportunities.append(Opportunity(
                name='Tax Planning Session',
                description='High income client would benefit from proactive planning',
                estimated_revenue=self.pricing['Tax Planning Session'],
                priority='High',
                trigger_reason=f'AGI ${agi:,.0f} > $200K'
            ))
        
        # QBI Optimization
        k1_count = len(tr.income.k1_1065) + len(tr.income.k1_1120s)
        if k1_count > 0 or self_emp > 0:
            result.opportunities.append(Opportunity(
                name='QBI Optimization Review',
                description='Maximize Section 199A deduction',
                estimated_revenue=self.pricing['QBI Optimization Review'],
                priority='High' if k1_count > 3 else 'Medium',
                trigger_reason=f'{k1_count} K-1s and/or self-employment'
            ))
        
        # Multi-State Planning
        # Check raw forms for state filings
        state_forms = ['4940', '6640', '6840', '5240', '7040']  # IL, NJ, NY, CA, etc.
        states_filed = sum(1 for code in state_forms if code in tr.raw_forms)
        if states_filed > 1:
            result.opportunities.append(Opportunity(
                name='Multi-State Nexus Review',
                description='Multiple state filings require nexus analysis',
                estimated_revenue=self.pricing['Multi-State Nexus Review'],
                priority='High',
                trigger_reason=f'{states_filed} state returns filed'
            ))
        
        # Estate Planning
        if agi > 300000:
            result.opportunities.append(Opportunity(
                name='Estate Planning Consultation',
                description='High net worth requires estate planning review',
                estimated_revenue=self.pricing['Estate Planning Consultation'],
                priority='Medium',
                trigger_reason=f'AGI > $300K'
            ))
        
        # Quarterly Estimates
        if k1_count > 2 or self_emp > 25000:
            result.opportunities.append(Opportunity(
                name='Quarterly Estimates Setup',
                description='Complex income requires estimated payment planning',
                estimated_revenue=self.pricing['Quarterly Estimates Setup'],
                priority='Medium',
                trigger_reason='K-1 or self-employment income'
            ))
        
        # Entity Structure Review
        if k1_count > 3:
            result.opportunities.append(Opportunity(
                name='Entity Structure Review',
                description='Multiple K-1s may indicate consolidation opportunity',
                estimated_revenue=self.pricing['Entity Structure Review'],
                priority='Medium',
                trigger_reason=f'{k1_count} K-1 partnerships'
            ))
        
        # Rental Property Advisory
        rental_count = len(tr.raw_forms.get('211', []))
        if rental_count > 0:
            result.opportunities.append(Opportunity(
                name='Rental Property Advisory',
                description='Real estate holdings require specialized planning',
                estimated_revenue=self.pricing['Rental Property Advisory'],
                priority='High' if rental_count > 2 else 'Medium',
                trigger_reason=f'{rental_count} rental properties'
            ))
        
        # Cost Segregation Study
        if rental_count > 1 and agi > 150000:
            result.opportunities.append(Opportunity(
                name='Cost Segregation Study',
                description='Accelerate depreciation on rental properties',
                estimated_revenue=self.pricing['Cost Segregation Study'],
                priority='High',
                trigger_reason='Multiple rentals + high income'
            ))
        
        # FBAR Compliance
        if len(tr.income.fbar) > 0:
            result.opportunities.append(Opportunity(
                name='FBAR Compliance Review',
                description='Foreign account reporting requires annual review',
                estimated_revenue=self.pricing['FBAR Compliance Review'],
                priority='High',
                trigger_reason=f'{len(tr.income.fbar)} foreign accounts'
            ))
        
        return result


def analyze_all_opportunities(returns: List[TaxReturn], 
                               config_path: Optional[str] = None) -> List[ClientOpportunities]:
    """Analyze all returns for opportunities"""
    engine = OpportunitiesEngine(config_path)
    return [engine.analyze(tr) for tr in returns]
