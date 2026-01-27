"""
Generate Analytics Script

Main entry point for generating client analytics, reports, and charts.
"""
import sys
import os
from pathlib import Path
from collections import Counter

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cch_parser_pkg import CCHParser
from cch_parser_pkg.analytics import (
    export_client_master, 
    generate_all_charts,
    analyze_all_opportunities,
    analyze_all_risks,
    analyze_k1_network,
    generate_executive_pdf
)
from cch_parser_pkg.analytics.scoring import ComplexityScorer
from cch_parser_pkg.analytics.reports import (
    save_opportunities_report,
    save_risks_report,
    save_k1_network_report,
    save_executive_summary
)


def main():
    # Paths
    data_path = Path("data/2024 tax returns.txt")
    output_dir = Path("output")
    charts_dir = output_dir / "charts"
    
    print("=" * 70)
    print("  CCH Parser - Tax Intelligence Platform")
    print("=" * 70)
    
    # Parse all returns
    print(f"\n[1/11] Parsing {data_path}...")
    parser = CCHParser()
    returns = []
    
    for doc in parser.parse_multi_file(str(data_path)):
        try:
            tr = parser.converter.to_tax_return(doc)
            returns.append(tr)
        except Exception as e:
            print(f"  Warning: Failed to parse {doc.client_id}: {e}")
    
    print(f"  ✓ Loaded {len(returns)} clients")
    
    # Score all clients
    print("\n[2/11] Calculating complexity scores...")
    scorer = ComplexityScorer()
    scores = [scorer.score(tr) for tr in returns]
    avg_score = sum(s.total_score for s in scores) / len(scores)
    avg_docs = sum(s.document_count for s in scores) / len(scores)
    total_fee = sum(s.suggested_fee for s in scores)
    
    print(f"  ✓ Average Complexity Score: {avg_score:.1f}")
    print(f"  ✓ Average Documents/Client: {avg_docs:.1f}")
    print(f"  ✓ Total Suggested Fees: ${total_fee:,.0f}")
    
    # Analyze opportunities
    print("\n[3/11] Identifying service opportunities...")
    opportunities = analyze_all_opportunities(returns)
    total_opp_revenue = sum(o.total_potential_revenue for o in opportunities)
    opp_count = sum(len(o.opportunities) for o in opportunities)
    print(f"  ✓ Found {opp_count} opportunities across {len([o for o in opportunities if o.opportunities])} clients")
    print(f"  ✓ Total opportunity revenue: ${total_opp_revenue:,.0f}")
    
    # Analyze risks
    print("\n[4/11] Detecting risk flags...")
    risks = analyze_all_risks(returns)
    risk_count = sum(len(r.flags) for r in risks)
    high_risk = sum(1 for r in risks if r.needs_partner_review)
    print(f"  ✓ Found {risk_count} risk flags")
    print(f"  ✓ {high_risk} clients require partner review")
    
    # K-1 Network Analysis
    print("\n[5/11] Analyzing K-1 network...")
    network = analyze_k1_network(returns)
    print(f"  ✓ Total K-1s: {network.total_k1s}")
    print(f"  ✓ Unique partnerships: {network.unique_partnerships}")
    print(f"  ✓ Shared partnerships (multi-client): {len(network.shared_partnerships)}")
    
    # Export client master
    print("\n[6/11] Exporting client master...")
    result = export_client_master(returns, str(output_dir))
    print(f"  ✓ CSV: {result['csv']}")
    print(f"  ✓ Excel: {result['excel']}")
    
    # Generate charts
    print("\n[7/11] Generating charts...")
    charts = generate_all_charts(returns, str(charts_dir), 
                                opportunities=opportunities, 
                                network=network)
    for chart in charts:
        print(f"  ✓ {Path(chart).name}")
    
    # Save detailed reports to files
    print("\n[8/11] Saving opportunities report...")
    opp_file = save_opportunities_report(opportunities, str(output_dir))
    print(f"  ✓ {Path(opp_file).name}")
    
    print("\n[9/11] Saving risk flags report...")
    risk_file = save_risks_report(risks, str(output_dir))
    print(f"  ✓ {Path(risk_file).name}")
    
    print("\n[10/11] Saving K-1 network report...")
    k1_file = save_k1_network_report(network, str(output_dir))
    print(f"  ✓ {Path(k1_file).name}")
    
    # Save PDF
    print("\n[11/11] Generating Executive Summary PDF...")
    pdf_path = output_dir / "Tax_Practice_Analytics_Report.pdf"
    generate_executive_pdf(
        returns, scores, opportunities, risks, network, 
        str(charts_dir), str(pdf_path)
    )
    print(f"  ✓ {pdf_path.name}")
    
    # Save Markdown Summary
    top_income = [(tr.taxpayer.full_name, float(tr.income.total_income)) 
                  for tr in sorted(returns, key=lambda x: float(x.income.total_income), reverse=True)]
    score_map = {returns[i].client_id: scores[i] for i in range(len(returns))}
    top_complexity = [(tr.taxpayer.full_name, score_map[tr.client_id].total_score, score_map[tr.client_id].suggested_fee)
                      for tr in sorted(returns, key=lambda x: score_map[x.client_id].total_score, reverse=True)]
    
    save_executive_summary(
        len(returns), scores, opportunities, risks, network,
        top_income, top_complexity, str(output_dir)
    )
    
    # =========================================================================
    # CONSOLE SUMMARY (also saved to executive_summary.md)
    # =========================================================================
    
    print("\n" + "=" * 70)
    print("  EXECUTIVE SUMMARY")
    print("=" * 70)
    
    # Fee Tier Summary
    print("\n📊 FEE TIER BREAKDOWN")
    print("-" * 50)
    tier_counts = Counter(s.fee_tier for s in scores)
    for tier, count in sorted(tier_counts.items()):
        tier_fee = next(s.suggested_fee for s in scores if s.fee_tier == tier)
        print(f"  {tier:15} | {count:3} clients | ${tier_fee:,}/each = ${count * tier_fee:,}")
    print(f"\n  💰 TOTAL BASE REVENUE: ${total_fee:,}")
    print(f"  🎯 OPPORTUNITY REVENUE: ${total_opp_revenue:,}")
    print(f"  📈 COMBINED POTENTIAL: ${total_fee + total_opp_revenue:,}")
    
    # Top Opportunities
    print("\n🎯 TOP SERVICE OPPORTUNITIES")
    print("-" * 50)
    all_opps = []
    for client_opp in opportunities:
        for opp in client_opp.opportunities:
            all_opps.append((client_opp.client_name, opp.name, opp.estimated_revenue, opp.priority))
    
    # Group by opportunity type
    opp_summary = Counter(o[1] for o in all_opps)
    for opp_name, count in opp_summary.most_common(10):
        revenue = sum(o[2] for o in all_opps if o[1] == opp_name)
        print(f"  {opp_name:35} | {count:3} clients | ${revenue:,}")
    
    # Risk Flags
    print("\n⚠️  RISK FLAGS REQUIRING ATTENTION")
    print("-" * 50)
    for risk in risks:
        if risk.needs_partner_review:
            print(f"  🔴 {risk.client_name}")
            for flag in risk.flags:
                if flag.severity == 'High':
                    print(f"      - {flag.description}")
    
    # K-1 Network Insights
    if network.shared_partnerships:
        print("\n🔗 K-1 NETWORK INSIGHTS (Shared Partnerships)")
        print("-" * 50)
        for p in network.shared_partnerships[:10]:
            print(f"  {p.name[:40]:40} | {p.client_count} clients")
            for client in p.clients[:3]:
                print(f"      → {client}")
            if len(p.clients) > 3:
                print(f"      → ... and {len(p.clients) - 3} more")
    
    # Top 10 Tables
    print("\n📋 TOP 10 CLIENTS BY INCOME")
    print("-" * 50)
    income_sorted = sorted(returns, key=lambda x: float(x.income.total_income), reverse=True)
    for i, tr in enumerate(income_sorted[:10], 1):
        income = float(tr.income.total_income)
        print(f"  {i:2}. {tr.taxpayer.full_name:30} | ${income:,.0f}")
    
    print("\n📋 TOP 10 CLIENTS BY COMPLEXITY")
    print("-" * 50)
    score_map = {returns[i].client_id: scores[i] for i in range(len(returns))}
    complexity_sorted = sorted(returns, key=lambda x: score_map[x.client_id].total_score, reverse=True)
    for i, tr in enumerate(complexity_sorted[:10], 1):
        score = score_map[tr.client_id]
        print(f"  {i:2}. {tr.taxpayer.full_name:30} | Score: {score.total_score:3} | Fee: ${score.suggested_fee:,}")
    
    print("\n📋 TOP 10 CLIENTS BY K-1 COUNT")
    print("-" * 50)
    k1_sorted = sorted(returns, key=lambda x: len(x.income.k1_1065) + len(x.income.k1_1120s), reverse=True)
    for i, tr in enumerate(k1_sorted[:10], 1):
        k1_count = len(tr.income.k1_1065) + len(tr.income.k1_1120s)
        if k1_count == 0:
            break
        print(f"  {i:2}. {tr.taxpayer.full_name:30} | {k1_count} K-1s")
    
    print("\n" + "=" * 70)
    print("  ✅ ANALYTICS GENERATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()

