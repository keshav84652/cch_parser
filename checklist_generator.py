"""
CCH Tax Document Checklist Generator

Generates client document request checklists based on prior year tax data.
Analyzes forms present in CCH export to determine what documents to request.
"""

import json
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Try to import parser, but handle if not available
try:
    from parser import CCHParser, CCHDocument
    from models import TaxReturn
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False


@dataclass
class ChecklistItem:
    """Single item on the document checklist"""
    category: str
    document: str
    description: str
    source: str  # What prior year form triggered this
    priority: str = "Required"  # Required, Recommended, Optional
    notes: str = ""


@dataclass
class DocumentChecklist:
    """Complete document checklist for a client"""
    client_name: str
    tax_year: int
    generated_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    items: List[ChecklistItem] = field(default_factory=list)
    
    def add_item(self, category: str, document: str, description: str, 
                 source: str, priority: str = "Required", notes: str = ""):
        self.items.append(ChecklistItem(
            category=category,
            document=document,
            description=description,
            source=source,
            priority=priority,
            notes=notes
        ))
    
    def to_dict(self) -> Dict:
        return {
            "client_name": self.client_name,
            "tax_year": self.tax_year,
            "generated_date": self.generated_date,
            "items": [
                {
                    "category": item.category,
                    "document": item.document,
                    "description": item.description,
                    "source": item.source,
                    "priority": item.priority,
                    "notes": item.notes
                }
                for item in self.items
            ]
        }
    
    def to_markdown(self) -> str:
        """Generate markdown formatted checklist"""
        lines = [
            f"# Document Checklist for {self.client_name}",
            f"## Tax Year {self.tax_year}",
            f"*Generated: {self.generated_date}*",
            "",
            "Please provide the following documents for your tax return preparation:",
            ""
        ]
        
        # Group by category
        categories: Dict[str, List[ChecklistItem]] = {}
        for item in self.items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)
        
        for category, items in categories.items():
            lines.append(f"### {category}")
            lines.append("")
            for item in items:
                checkbox = "[ ]"
                priority_badge = ""
                if item.priority == "Optional":
                    priority_badge = " *(optional)*"
                elif item.priority == "Recommended":
                    priority_badge = " *(recommended)*"
                
                lines.append(f"- {checkbox} **{item.document}**{priority_badge}")
                lines.append(f"  - {item.description}")
                if item.notes:
                    lines.append(f"  - *Note: {item.notes}*")
            lines.append("")
        
        return "\n".join(lines)
    
    def to_html(self) -> str:
        """Generate HTML formatted checklist"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Document Checklist - {self.client_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; }}
        h3 {{ color: #2980b9; margin-top: 25px; }}
        .checklist {{ list-style: none; padding: 0; }}
        .checklist li {{ margin: 10px 0; padding: 10px; background: #f9f9f9; border-radius: 5px; }}
        .checklist input {{ margin-right: 10px; transform: scale(1.3); }}
        .document-name {{ font-weight: bold; color: #2c3e50; }}
        .description {{ color: #666; font-size: 0.9em; margin-left: 25px; }}
        .priority-optional {{ color: #95a5a6; font-style: italic; }}
        .priority-recommended {{ color: #f39c12; font-style: italic; }}
        .notes {{ color: #7f8c8d; font-size: 0.85em; margin-left: 25px; }}
        .generated {{ color: #95a5a6; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>Document Checklist</h1>
    <h2>{self.client_name} - Tax Year {self.tax_year}</h2>
    <p class="generated">Generated: {self.generated_date}</p>
    <p>Please provide the following documents for your tax return preparation:</p>
"""
        
        # Group by category
        categories: Dict[str, List[ChecklistItem]] = {}
        for item in self.items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)
        
        for category, items in categories.items():
            html += f"    <h3>{category}</h3>\n"
            html += "    <ul class=\"checklist\">\n"
            for item in items:
                priority_class = ""
                priority_text = ""
                if item.priority == "Optional":
                    priority_class = "priority-optional"
                    priority_text = " (optional)"
                elif item.priority == "Recommended":
                    priority_class = "priority-recommended"
                    priority_text = " (recommended)"
                
                html += f"""        <li>
            <input type="checkbox">
            <span class="document-name">{item.document}</span>
            <span class="{priority_class}">{priority_text}</span>
            <div class="description">{item.description}</div>
"""
                if item.notes:
                    html += f'            <div class="notes">Note: {item.notes}</div>\n'
                html += "        </li>\n"
            html += "    </ul>\n"
        
        html += """</body>
</html>"""
        return html


# Document rules based on form presence
DOCUMENT_RULES = {
    # Income Forms
    "180": {  # W-2
        "category": "Employment Income",
        "document": "Form W-2",
        "description": "Wage and Tax Statement from each employer",
        "priority": "Required"
    },
    "181": {  # 1099-INT
        "category": "Investment Income",
        "document": "Form 1099-INT",
        "description": "Interest income statements from banks and financial institutions",
        "priority": "Required"
    },
    "182": {  # 1099-DIV
        "category": "Investment Income",
        "document": "Form 1099-DIV",
        "description": "Dividend income statements from investments",
        "priority": "Required"
    },
    "183": {  # 1099-MISC
        "category": "Other Income",
        "document": "Form 1099-MISC",
        "description": "Miscellaneous income statements",
        "priority": "Required"
    },
    "184": {  # 1099-R
        "category": "Retirement Income",
        "document": "Form 1099-R",
        "description": "Distributions from retirement accounts, pensions, or annuities",
        "priority": "Required"
    },
    "185": {  # K-1 (1065)
        "category": "Partnership/Investment Income",
        "document": "Schedule K-1 (Form 1065)",
        "description": "Partner's share of income from partnerships",
        "priority": "Required",
        "notes": "May arrive late (March or later)"
    },
    "120": {  # K-1 (1120S)
        "category": "Partnership/Investment Income",
        "document": "Schedule K-1 (Form 1120-S)",
        "description": "Shareholder's share of income from S-Corporations",
        "priority": "Required",
        "notes": "May arrive late (March or later)"
    },
    "190": {  # SSA-1099
        "category": "Retirement Income",
        "document": "Form SSA-1099",
        "description": "Social Security Benefit Statement",
        "priority": "Required"
    },
    "267": {  # 1099-NEC
        "category": "Self-Employment Income",
        "document": "Form 1099-NEC",
        "description": "Non-employee compensation (freelance/contractor income)",
        "priority": "Required"
    },
    "761": {  # 1099-K
        "category": "Self-Employment Income",
        "document": "Form 1099-K",
        "description": "Payment card and third-party network transactions",
        "priority": "Required"
    },
    
    # Deduction Forms
    "206": {  # 1098
        "category": "Deductions - Home",
        "document": "Form 1098",
        "description": "Mortgage Interest Statement",
        "priority": "Required"
    },
    "622": {  # 1098-E
        "category": "Deductions - Education",
        "document": "Form 1098-E",
        "description": "Student Loan Interest Statement",
        "priority": "Required"
    },
    "208": {  # 1098-T
        "category": "Deductions - Education",
        "document": "Form 1098-T",
        "description": "Tuition Statement from educational institutions",
        "priority": "Required"
    },
    
    # Healthcare
    "624": {  # 1095-A
        "category": "Healthcare",
        "document": "Form 1095-A",
        "description": "Health Insurance Marketplace Statement",
        "priority": "Required"
    },
    "641": {  # 1095-C
        "category": "Healthcare",
        "document": "Form 1095-C",
        "description": "Employer-Provided Health Insurance Offer and Coverage",
        "priority": "Required"
    },
    "623": {  # 1099-SA
        "category": "Healthcare",
        "document": "Form 1099-SA",
        "description": "Distributions from HSA, Archer MSA, or Medicare Advantage MSA",
        "priority": "Required"
    },
    
    # Business
    "171": {  # C-1 (Schedule C)
        "category": "Self-Employment",
        "document": "Business Income and Expense Records",
        "description": "Profit and loss statement, income records, expense receipts",
        "priority": "Required"
    },
    "172": {  # C-2 (Schedule C expenses)
        "category": "Self-Employment",
        "document": "Business Expense Documentation",
        "description": "Receipts and records for business expenses",
        "priority": "Required"
    },
    
    # Rental Property
    "211": {  # E-1 (Schedule E)
        "category": "Rental Property",
        "document": "Rental Income and Expense Records",
        "description": "Rental income received, expenses, property taxes, insurance",
        "priority": "Required"
    },
    
    # Estimated Payments
    "311": {  # P-1
        "category": "Tax Payments",
        "document": "Estimated Tax Payment Records",
        "description": "Records of federal and state estimated tax payments made",
        "priority": "Required"
    }
}

# Additional documents to always request
STANDARD_DOCUMENTS = [
    {
        "category": "Personal Information",
        "document": "Photo ID",
        "description": "Copy of driver's license or state ID for taxpayer and spouse",
        "priority": "Required"
    },
    {
        "category": "Personal Information",
        "document": "Social Security Cards",
        "description": "For taxpayer, spouse, and all dependents",
        "priority": "Required"
    },
    {
        "category": "Personal Information",
        "document": "Prior Year Tax Return",
        "description": "Copy of last year's federal and state tax returns",
        "priority": "Recommended"
    }
]


class ChecklistGenerator:
    """
    Generates document checklists based on prior year CCH export data.
    """
    
    def __init__(self, mapping_file: Optional[str] = None):
        self.rules = DOCUMENT_RULES.copy()
        if mapping_file:
            self.load_additional_rules(mapping_file)
    
    def load_additional_rules(self, filepath: str):
        """Load additional rules from JSON file"""
        with open(filepath, 'r') as f:
            additional = json.load(f)
            self.rules.update(additional)
    
    def generate_from_forms(self, forms_present: Set[str], 
                            client_name: str, tax_year: int) -> DocumentChecklist:
        """
        Generate checklist based on form codes present in prior year.
        
        Args:
            forms_present: Set of form codes found in CCH export
            client_name: Client's name
            tax_year: Year for the new checklist
        """
        checklist = DocumentChecklist(
            client_name=client_name,
            tax_year=tax_year
        )
        
        # Add standard documents
        for doc in STANDARD_DOCUMENTS:
            checklist.add_item(**doc, source="Standard")
        
        # Add documents based on prior year forms
        added_docs = set()
        for form_code in forms_present:
            if form_code in self.rules and form_code not in added_docs:
                rule = self.rules[form_code]
                checklist.add_item(
                    category=rule["category"],
                    document=rule["document"],
                    description=rule["description"],
                    source=f"Prior year Form {form_code}",
                    priority=rule.get("priority", "Required"),
                    notes=rule.get("notes", "")
                )
                added_docs.add(form_code)
        
        # Sort items by category
        checklist.items.sort(key=lambda x: (x.category, x.priority != "Required"))
        
        return checklist
    
    def generate_from_cch_file(self, filepath: str, new_tax_year: int) -> DocumentChecklist:
        """
        Generate checklist from CCH export file.
        
        Args:
            filepath: Path to CCH export file
            new_tax_year: Tax year for the checklist
        """
        if not PARSER_AVAILABLE:
            raise ImportError("Parser module not available")
        
        parser = CCHParser()
        doc = parser.parse_file(filepath)
        tax_return = parser.to_tax_return(doc)
        
        forms_present = set(doc.forms.keys())
        
        return self.generate_from_forms(
            forms_present=forms_present,
            client_name=tax_return.taxpayer.full_name,
            tax_year=new_tax_year
        )
    
    def generate_from_cch_document(self, doc, new_tax_year: int) -> DocumentChecklist:
        """
        Generate checklist from parsed CCH document.
        
        Args:
            doc: CCHDocument object
            new_tax_year: Tax year for the checklist
        """
        if not PARSER_AVAILABLE:
            raise ImportError("Parser module not available")
        
        parser = CCHParser()
        tax_return = parser.to_tax_return(doc)
        forms_present = set(doc.forms.keys())
        
        return self.generate_from_forms(
            forms_present=forms_present,
            client_name=tax_return.taxpayer.full_name,
            tax_year=new_tax_year
        )


def main():
    """Example usage"""
    import sys
    
    # Demo with sample forms
    sample_forms = {"180", "181", "182", "184", "185", "206", "622", "624", "171"}
    
    generator = ChecklistGenerator()
    checklist = generator.generate_from_forms(
        forms_present=sample_forms,
        client_name="John S. Doe",
        tax_year=2024
    )
    
    # Output formats
    if len(sys.argv) > 1:
        format_type = sys.argv[1].lower()
        if format_type == "--html":
            print(checklist.to_html())
        elif format_type == "--json":
            print(json.dumps(checklist.to_dict(), indent=2))
        elif format_type == "--markdown" or format_type == "--md":
            print(checklist.to_markdown())
        else:
            print(checklist.to_markdown())
    else:
        print(checklist.to_markdown())
        print("\n" + "="*60)
        print("Use --html, --json, or --markdown for different output formats")


if __name__ == "__main__":
    main()
