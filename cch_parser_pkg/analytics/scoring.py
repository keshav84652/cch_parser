"""
Complexity Scoring Engine

Calculates complexity scores for tax returns based on configurable weights.
"""
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional
from decimal import Decimal

from ..models.return_data import TaxReturn


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of complexity score"""
    total_score: int
    components: Dict[str, int]
    document_count: int
    suggested_fee: int
    fee_tier: str


class ComplexityScorer:
    """Config-driven complexity scoring engine"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.weights = self.config.get('scoring', {})
        self.fee_tiers = self.config.get('fee_tiers', [])
    
    def score(self, tr: TaxReturn) -> ScoreBreakdown:
        """Calculate complexity score for a tax return"""
        components = {}
        
        # Count forms and apply weights
        counts = {
            'w2': len(tr.income.w2s),
            'form_1099_int': len(tr.income.form_1099_int),
            'form_1099_div': len(tr.income.form_1099_div),
            'form_1099_r': len(tr.income.form_1099_r),
            'form_1099_nec': len(tr.income.form_1099_nec),
            'form_1099_misc': len(tr.income.form_1099_misc),
            'form_1099_g': len(tr.income.form_1099_g),
            'k1_1065': len(tr.income.k1_1065),
            'k1_1120s': len(tr.income.k1_1120s),
            'fbar': len(tr.income.fbar),
            'form_1098': len(tr.deductions.mortgage_interest),
            'form_1095_a': len(tr.deductions.health_insurance),
            'form_1095_c': len(tr.deductions.form_1095_c),
            'ssa_1099': len(tr.income.ssa_1099),
            'balance_sheet': 1 if tr.balance_sheet else 0,
        }
        
        # Calculate brokerage count from raw forms if available
        brokerage_count = len(tr.raw_forms.get('881', []))
        counts['brokerage'] = brokerage_count
        
        total_score = 0
        doc_count = 0
        
        for form_type, count in counts.items():
            if count > 0:
                weight = self.weights.get(form_type, 5)
                score = count * weight
                components[form_type] = score
                total_score += score
                doc_count += count
        
        # Determine fee tier
        suggested_fee = 250
        tier_name = "Simple"
        for tier in self.fee_tiers:
            if total_score <= tier['max_score']:
                suggested_fee = tier['fee']
                tier_name = tier['tier_name']
                break
        
        return ScoreBreakdown(
            total_score=total_score,
            components=components,
            document_count=doc_count,
            suggested_fee=suggested_fee,
            fee_tier=tier_name
        )


def calculate_client_score(tr: TaxReturn, config_path: Optional[str] = None) -> ScoreBreakdown:
    """Convenience function to calculate score for a single return"""
    scorer = ComplexityScorer(config_path)
    return scorer.score(tr)
