"""
Analytics Chart Generator

Generates visualizations for tax practice analytics.
"""
import yaml
from pathlib import Path
from typing import List, Optional
from collections import Counter

from ..models.return_data import TaxReturn
from .scoring import ComplexityScorer



def generate_all_charts(returns: List[TaxReturn], output_dir: str,
                        config_path: Optional[str] = None,
                        opportunities: Optional[List] = None,
                        network: Optional[object] = None) -> List[str]:
    """
    Generate all analytics charts.
    Returns list of generated file paths.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        print("matplotlib not installed. Run: pip install matplotlib")
        return []
    
    # Load config for chart settings
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    chart_config = config.get('charts', {})
    figsize = tuple(chart_config.get('figsize', [10, 6]))
    dpi = chart_config.get('dpi', 150)
    
    try:
        plt.style.use(chart_config.get('style', 'seaborn-v0_8-whitegrid'))
    except:
        pass  # Use default style if specified one not available
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    scorer = ComplexityScorer(config_path)
    generated = []
    
    # 1. Filing Status Distribution
    fig, ax = plt.subplots(figsize=figsize)
    status_counts = Counter(tr.filing_status.name for tr in returns)
    labels = [s.replace('_', ' ').title() for s in status_counts.keys()]
    sizes = list(status_counts.values())
    colors = plt.cm.Blues([0.3, 0.5, 0.7, 0.85, 0.95][:len(labels)])
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
    ax.set_title('Clients by Filing Status', fontsize=14, fontweight='bold')
    filepath = output_path / "filing_status_distribution.png"
    plt.savefig(filepath, dpi=dpi, bbox_inches='tight')
    plt.close()
    generated.append(str(filepath))
    
    # 2. Complexity Score Distribution
    fig, ax = plt.subplots(figsize=figsize)
    scores = [scorer.score(tr).total_score for tr in returns]
    ax.hist(scores, bins=20, color='#2ecc71', edgecolor='white', alpha=0.8)
    ax.set_xlabel('Complexity Score', fontsize=12)
    ax.set_ylabel('Number of Clients', fontsize=12)
    ax.set_title('Client Complexity Distribution', fontsize=14, fontweight='bold')
    ax.axvline(x=sum(scores)/len(scores), color='red', linestyle='--', 
               label=f'Average: {sum(scores)/len(scores):.0f}')
    ax.legend()
    filepath = output_path / "complexity_histogram.png"
    plt.savefig(filepath, dpi=dpi, bbox_inches='tight')
    plt.close()
    generated.append(str(filepath))
    
    # 3. Fee Tier Breakdown
    fig, ax = plt.subplots(figsize=figsize)
    tier_counts = Counter(scorer.score(tr).fee_tier for tr in returns)
    tiers = list(tier_counts.keys())
    counts = list(tier_counts.values())
    colors = ['#27ae60', '#3498db', '#f39c12', '#e74c3c', '#9b59b6'][:len(tiers)]
    bars = ax.bar(tiers, counts, color=colors, edgecolor='white')
    ax.set_xlabel('Fee Tier', fontsize=12)
    ax.set_ylabel('Number of Clients', fontsize=12)
    ax.set_title('Clients by Fee Tier', fontsize=14, fontweight='bold')
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                str(count), ha='center', va='bottom', fontweight='bold')
    filepath = output_path / "fee_tier_breakdown.png"
    plt.savefig(filepath, dpi=dpi, bbox_inches='tight')
    plt.close()
    generated.append(str(filepath))
    
    # 4. Income by Source
    fig, ax = plt.subplots(figsize=figsize)
    income_sources = {
        'Wages': sum(float(tr.income.total_wages) for tr in returns),
        'Interest': sum(float(tr.income.total_interest) for tr in returns),
        'Dividends': sum(float(tr.income.total_dividends) for tr in returns),
        'K-1 Income': sum(float(tr.income.total_k1_income) for tr in returns),
        'Self-Emp': sum(float(tr.income.total_self_employment) for tr in returns),
        'Retirement': sum(float(tr.income.total_retirement_distributions) for tr in returns),
    }
    # Filter out zero values
    income_sources = {k: v for k, v in income_sources.items() if v > 0}
    if income_sources:
        sources = list(income_sources.keys())
        amounts = [v / 1000000 for v in income_sources.values()]  # In millions
        colors = plt.cm.Spectral([0.1, 0.25, 0.4, 0.55, 0.7, 0.85][:len(sources)])
        bars = ax.barh(sources, amounts, color=colors, edgecolor='white')
        ax.set_xlabel('Total Amount ($ Millions)', fontsize=12)
        ax.set_title('Aggregate Income by Source', fontsize=14, fontweight='bold')
        for bar, amt in zip(bars, amounts):
            ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                    f'${amt:.2f}M', va='center', fontsize=10)
    filepath = output_path / "income_by_source.png"
    plt.savefig(filepath, dpi=dpi, bbox_inches='tight')
    plt.close()
    generated.append(str(filepath))
    
    # 5. Document Count Distribution
    fig, ax = plt.subplots(figsize=figsize)
    doc_counts = [scorer.score(tr).document_count for tr in returns]
    ax.hist(doc_counts, bins=15, color='#9b59b6', edgecolor='white', alpha=0.8)
    ax.set_xlabel('Documents per Client', fontsize=12)
    ax.set_ylabel('Number of Clients', fontsize=12)
    ax.set_title('Document Volume Distribution', fontsize=14, fontweight='bold')
    ax.axvline(x=sum(doc_counts)/len(doc_counts), color='red', linestyle='--',
               label=f'Average: {sum(doc_counts)/len(doc_counts):.1f}')
    ax.legend()
    filepath = output_path / "document_distribution.png"
    plt.savefig(filepath, dpi=dpi, bbox_inches='tight')
    plt.close()
    generated.append(str(filepath))
    
    # 6. Complexity vs Income Scatter Plot
    fig, ax = plt.subplots(figsize=figsize)
    incomes = [float(tr.income.total_income)/1000 for tr in returns]  # In '000s
    scores_vals = [scorer.score(tr).total_score for tr in returns]
    fees = [scorer.score(tr).suggested_fee for tr in returns]
    
    scatter = ax.scatter(incomes, scores_vals, c=fees, cmap='viridis', 
                         alpha=0.6, s=100, edgecolors='w')
    ax.set_xlabel('Total Income ($ Thousands)', fontsize=12)
    ax.set_ylabel('Complexity Score', fontsize=12)
    ax.set_title('Client Complexity vs. Income', fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Add colorbar
    cbar = plt.colorbar(scatter)
    cbar.set_label('Suggested Fee ($)', fontsize=10)
    
    # Annotate top outliers
    indices = range(len(returns))
    sorted_idx = sorted(indices, key=lambda i: scores_vals[i], reverse=True)[:5]
    for i in sorted_idx:
        ax.annotate(returns[i].taxpayer.last_name, 
                   (incomes[i], scores_vals[i]),
                   xytext=(5, 5), textcoords='offset points')
                   
    filepath = output_path / "complexity_vs_income.png"
    plt.savefig(filepath, dpi=dpi, bbox_inches='tight')
    plt.close()
    generated.append(str(filepath))
    
    # 7. State Filing Distribution
    states = []
    state_forms = ['4940', '6640', '6840', '5240', '7040']
    state_map = {'4940': 'IL', '6640': 'NJ', '6840': 'NY', '5240': 'CA', '7040': 'PA'}
    
    for tr in returns:
        for form_code in tr.raw_forms.keys():
            if form_code in state_map:
                states.append(state_map[form_code])
    
    if states:
        fig, ax = plt.subplots(figsize=figsize)
        state_counts = Counter(states)
        labels = list(state_counts.keys())
        counts = list(state_counts.values())
        
        bars = ax.bar(labels, counts, color='#E67E22')
        ax.set_title('State Returns Filed', fontsize=14, fontweight='bold')
        ax.set_ylabel('Number of Returns')
        
        for bar, count in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    str(count), ha='center', va='bottom')
                    
        filepath = output_path / "state_distribution.png"
        plt.savefig(filepath, dpi=dpi, bbox_inches='tight')
        plt.close()
        generated.append(str(filepath))
        
    # 8. Revenue Opportunity Potential (if data available)
    if opportunities:
        fig, ax = plt.subplots(figsize=figsize)
        opp_values = Counter()
        for client_opp in opportunities:
            for opp in client_opp.opportunities:
                opp_values[opp.name] += opp.estimated_revenue
        
        # Sort by value
        sorted_opps = opp_values.most_common(8)
        labels = [x[0] for x in sorted_opps]
        values = [x[1]/1000 for x in sorted_opps] # In thousands
        
        bars = ax.barh(labels, values, color='#3498DB')
        ax.set_xlabel('Potential Revenue ($ Thousands)', fontsize=12)
        ax.set_title('Top Revenue Opportunities', fontsize=14, fontweight='bold')
        
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                    f'${val:.1f}k', va='center')
                    
        filepath = output_path / "revenue_opportunities.png"
        plt.savefig(filepath, dpi=dpi, bbox_inches='tight')
        plt.close()
        generated.append(str(filepath))
        
    # 9. Top Partnerships (if network data available)
    if network and network.top_partnerships:
        fig, ax = plt.subplots(figsize=figsize)
        top_pships = network.top_partnerships[:10]
        # Truncate names
        names = [p.name[:25] + '...' if len(p.name)>25 else p.name for p in top_pships]
        counts = [p.client_count for p in top_pships]
        
        bars = ax.barh(names, counts, color='#8E44AD')
        ax.set_xlabel('Number of Clients', fontsize=12)
        ax.set_title('Most Common Partnerships (K-1s)', fontsize=14, fontweight='bold')
        ax.invert_yaxis() # Top items at top
        
        for bar, count in zip(bars, counts):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                    str(count), va='center')
                    
        filepath = output_path / "top_partnerships.png"
        plt.savefig(filepath, dpi=dpi, bbox_inches='tight')
        plt.close()
        generated.append(str(filepath))

    return generated
