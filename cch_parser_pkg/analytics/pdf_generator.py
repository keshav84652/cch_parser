"""
PDF Generator for Analytics Report
"""
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

from ..models.return_data import TaxReturn
from .opportunities import ClientOpportunities
from .risks import ClientRisks
from .network import K1NetworkAnalysis
from .scoring import ScoreBreakdown


class AnalyticsPDF(FPDF):
    def header(self):
        # Logo or Title
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'Tax Intelligence Platform', 0, 1, 'L')
        self.set_font('Helvetica', 'I', 10)
        self.cell(0, 5, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'L')
        self.ln(10)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 14)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Helvetica', '', 11)
        self.multi_cell(0, 6, body)
        self.ln()

    def add_image(self, image_path: str, width: int = 180):
        if Path(image_path).exists():
            self.image(image_path, w=width)
            self.ln(5)
        else:
            self.set_text_color(255, 0, 0)
            self.cell(0, 10, f"Image not found: {Path(image_path).name}", 0, 1)
            self.set_text_color(0, 0, 0)


def generate_executive_pdf(
    returns: List[TaxReturn],
    scores: List[ScoreBreakdown],
    opportunities: List[ClientOpportunities],
    risks: List[ClientRisks],
    network: K1NetworkAnalysis,
    charts_dir: str,
    output_path: str
) -> str:
    """Generate the Executive Summary PDF"""
    if FPDF is None:
        print("fpdf2 not installed. Cannot generate PDF.")
        return ""
    
    pdf = AnalyticsPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- 1. OVERVIEW METRICS ---
    pdf.chapter_title('Executive Summary')
    
    total_revenue = sum(s.suggested_fee for s in scores)
    opp_revenue = sum(o.total_potential_revenue for o in opportunities)
    high_risk = sum(1 for r in risks if r.needs_partner_review)
    
    # 2-column layout for metrics
    col_width = 85
    pdf.set_font('Helvetica', '', 12)
    
    # Col 1
    x_start = pdf.get_x()
    pdf.cell(col_width, 8, f"Total Clients: {len(returns)}", 0, 1)
    pdf.cell(col_width, 8, f"Base Revenue: ${total_revenue:,.0f}", 0, 1)
    pdf.cell(col_width, 8, f"Opportunity Revenue: ${opp_revenue:,.0f}", 0, 1)
    
    # Col 2
    y_current = pdf.get_y()
    pdf.set_xy(x_start + col_width + 10, y_current - 24)
    pdf.cell(col_width, 8, f"Service Opportunities: {sum(len(o.opportunities) for o in opportunities)}", 0, 1)
    pdf.cell(col_width, 8, f"Risk Flags: {sum(len(r.flags) for r in risks)}", 0, 1)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(col_width, 8, f"Needs Review: {high_risk}", 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
    
    # --- 2. REVENUE OPPORTUNITIES ---
    pdf.chapter_title('Growth Opportunities')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 8, f"Combined Potential Revenue: ${total_revenue + opp_revenue:,.0f}", 0, 1)
    
    # Embed charts
    charts_path = Path(charts_dir)
    pdf.add_image(str(charts_path / "revenue_opportunities.png"))
    pdf.add_image(str(charts_path / "fee_tier_breakdown.png"))
    
    pdf.add_page()
    
    # --- 3. COMPLEXITY & INCOME ---
    pdf.chapter_title('Client Portfolio Analysis')
    pdf.add_image(str(charts_path / "complexity_vs_income.png"))
    pdf.add_image(str(charts_path / "complexity_histogram.png"))
    
    # --- 4. TOP LISTS ---
    pdf.add_page()
    pdf.chapter_title('Top 10 Clients by Income')
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(10, 8, "#", 1)
    pdf.cell(100, 8, "Client Name", 1)
    pdf.cell(40, 8, "Total Income", 1, 0, 'R')
    pdf.ln()
    
    pdf.set_font('Helvetica', '', 10)
    sorted_income = sorted(returns, key=lambda x: float(x.income.total_income), reverse=True)[:10]
    for i, tr in enumerate(sorted_income, 1):
        income = float(tr.income.total_income)
        pdf.cell(10, 8, str(i), 1)
        pdf.cell(100, 8, tr.taxpayer.full_name, 1)
        pdf.cell(40, 8, f"${income:,.0f}", 1, 0, 'R')
        pdf.ln()
        
    pdf.ln(10)
    
    pdf.chapter_title('Top 10 Clients by Complexity')
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(10, 8, "#", 1)
    pdf.cell(100, 8, "Client Name", 1)
    pdf.cell(20, 8, "Score", 1, 0, 'C')
    pdf.cell(30, 8, "Fee", 1, 0, 'R')
    pdf.ln()
    
    # Need score map
    score_map = {tr.client_id: s for tr, s in zip(returns, scores)}
    sorted_complexity = sorted(returns, key=lambda x: score_map[x.client_id].total_score, reverse=True)[:10]
    
    pdf.set_font('Helvetica', '', 10)
    for i, tr in enumerate(sorted_complexity, 1):
        score = score_map[tr.client_id]
        pdf.cell(10, 8, str(i), 1)
        pdf.cell(100, 8, tr.taxpayer.full_name, 1)
        pdf.cell(20, 8, str(score.total_score), 1, 0, 'C')
        pdf.cell(30, 8, f"${score.suggested_fee:,}", 1, 0, 'R')
        pdf.ln()
        
    # --- 5. K-1 NETWORK ---
    pdf.add_page()
    pdf.chapter_title('K-1 Partnership Network')
    pdf.add_image(str(charts_path / "top_partnerships.png"))
    
    if network.shared_partnerships:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 10, "Top Shared Investments", 0, 1)
        pdf.set_font('Helvetica', '', 10)
        
        for p in network.shared_partnerships[:8]:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, f"{p.name} ({p.client_count} clients)", 0, 1)
            pdf.set_font('Helvetica', '', 9)
            clients_str = ", ".join(p.clients[:4])
            if len(p.clients) > 4:
                clients_str += f", and {len(p.clients)-4} more"
            pdf.multi_cell(0, 5, f"   {clients_str}")
            pdf.ln(2)

    # --- 6. CHART APPENDIX ---
    pdf.add_page()
    pdf.chapter_title('Additional Charts')
    pdf.add_image(str(charts_path / "state_distribution.png"))
    pdf.add_image(str(charts_path / "filing_status_distribution.png"))
    pdf.add_image(str(charts_path / "income_by_source.png"))
    
    try:
        pdf.output(output_path)
        return output_path
    except Exception as e:
        print(f"Error saving PDF: {e}")
        return ""
