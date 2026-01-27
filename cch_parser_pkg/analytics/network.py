"""
K-1 Partnership Network Analysis

Analyzes partnership relationships across clients to identify:
- Common partnerships
- Delay propagation (if X K-1 is late, these clients are blocked)
- Investment patterns
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from collections import defaultdict

from ..models.return_data import TaxReturn


@dataclass
class PartnershipNode:
    """Represents a partnership in the network"""
    name: str
    ein: str = ""
    client_count: int = 0
    clients: List[str] = field(default_factory=list)
    total_income: float = 0.0


@dataclass 
class K1NetworkAnalysis:
    """Complete K-1 network analysis results"""
    # Partnership -> list of client names
    partnership_clients: Dict[str, List[str]] = field(default_factory=dict)
    
    # Client -> list of partnerships
    client_partnerships: Dict[str, List[str]] = field(default_factory=dict)
    
    # Partnerships with multiple clients (shared investments)
    shared_partnerships: List[PartnershipNode] = field(default_factory=list)
    
    # Total K-1 stats
    total_k1s: int = 0
    unique_partnerships: int = 0
    clients_with_k1s: int = 0
    
    # Top partnerships by client count
    top_partnerships: List[PartnershipNode] = field(default_factory=list)


class K1NetworkEngine:
    """Analyze K-1 network relationships"""
    
    def analyze(self, returns: List[TaxReturn]) -> K1NetworkAnalysis:
        """Build complete K-1 network analysis"""
        result = K1NetworkAnalysis()
        
        partnership_data = defaultdict(lambda: {
            'clients': [],
            'total_income': 0.0
        })
        
        client_k1s = defaultdict(list)
        
        # Process all returns
        for tr in returns:
            client_name = tr.taxpayer.full_name
            
            # Partnership K-1s (Form 1065)
            for k1 in tr.income.k1_1065:
                partnership_name = k1.partnership_name or "Unknown Partnership"
                partnership_name = partnership_name.strip().upper()
                
                partnership_data[partnership_name]['clients'].append(client_name)
                partnership_data[partnership_name]['total_income'] += float(k1.ordinary_income or 0)
                client_k1s[client_name].append(partnership_name)
                result.total_k1s += 1
            
            # S-Corp K-1s (Form 1120S)
            for k1 in tr.income.k1_1120s:
                corp_name = k1.corporation_name or "Unknown S-Corp"
                corp_name = corp_name.strip().upper()
                
                partnership_data[corp_name]['clients'].append(client_name)
                partnership_data[corp_name]['total_income'] += float(k1.ordinary_income or 0)
                client_k1s[client_name].append(corp_name)
                result.total_k1s += 1
        
        # Build results
        result.unique_partnerships = len(partnership_data)
        result.clients_with_k1s = len(client_k1s)
        result.client_partnerships = dict(client_k1s)
        result.partnership_clients = {
            name: data['clients'] 
            for name, data in partnership_data.items()
        }
        
        # Find shared partnerships (>1 client)
        for name, data in partnership_data.items():
            if len(data['clients']) > 1:
                result.shared_partnerships.append(PartnershipNode(
                    name=name,
                    client_count=len(data['clients']),
                    clients=data['clients'],
                    total_income=data['total_income']
                ))
        
        # Sort by client count
        result.shared_partnerships.sort(key=lambda x: x.client_count, reverse=True)
        
        # Top partnerships overall
        all_partnerships = [
            PartnershipNode(
                name=name,
                client_count=len(data['clients']),
                clients=data['clients'],
                total_income=data['total_income']
            )
            for name, data in partnership_data.items()
        ]
        all_partnerships.sort(key=lambda x: x.client_count, reverse=True)
        result.top_partnerships = all_partnerships[:20]
        
        return result
    
    def get_delay_impact(self, analysis: K1NetworkAnalysis, 
                         partnership_name: str) -> List[str]:
        """Get list of clients blocked if a partnership K-1 is delayed"""
        name_upper = partnership_name.strip().upper()
        return analysis.partnership_clients.get(name_upper, [])
    
    def get_similar_clients(self, analysis: K1NetworkAnalysis,
                            client_name: str) -> Set[str]:
        """Find clients with overlapping K-1s (potential referral network)"""
        similar = set()
        
        # Get this client's partnerships
        partnerships = analysis.client_partnerships.get(client_name, [])
        
        # Find other clients in same partnerships
        for partnership in partnerships:
            other_clients = analysis.partnership_clients.get(partnership, [])
            for other in other_clients:
                if other != client_name:
                    similar.add(other)
        
        return similar


def analyze_k1_network(returns: List[TaxReturn]) -> K1NetworkAnalysis:
    """Convenience function for network analysis"""
    engine = K1NetworkEngine()
    return engine.analyze(returns)
