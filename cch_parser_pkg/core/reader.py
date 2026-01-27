
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator
from decimal import Decimal, InvalidOperation
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class CCHField:
    """Represents a single field in the CCH export"""
    number: str
    value: str
    is_memo: bool = False  # Fields ending with M are memo fields
    
    @property
    def as_decimal(self) -> Decimal:
        """Convert value to Decimal, handling currency formatting"""
        try:
            # Remove currency symbols, commas, and whitespace
            clean = self.value.replace(",", "").replace("$", "").strip()
            if not clean or clean == "":
                return Decimal("0")
            return Decimal(clean)
        except InvalidOperation:
            return Decimal("0")
    
    @property
    def as_bool(self) -> bool:
        """Convert value to boolean (X = True)"""
        return self.value.strip().upper() == "X"
    
    @property
    def as_date(self) -> Optional[datetime]:
        """Convert value to date"""
        value = self.value.strip()
        if not value:
            return None
        
        # Try common date formats
        formats = ["%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

@dataclass
class CCHFormEntry:
    """Represents a single entry within a form (e.g., one W-2)"""
    section: int
    entry: int
    fields: Dict[str, CCHField] = field(default_factory=dict)
    
    def get(self, field_num: str, default: str = "") -> str:
        """Get field value by number"""
        if field_num in self.fields:
            return self.fields[field_num].value
        return default
    
    def get_decimal(self, field_num: str) -> Decimal:
        """Get field as Decimal"""
        if field_num in self.fields:
            return self.fields[field_num].as_decimal
        return Decimal("0")
    
    def get_bool(self, field_num: str) -> bool:
        """Get field as boolean"""
        if field_num in self.fields:
            return self.fields[field_num].as_bool
        return False

@dataclass
class CCHForm:
    """Represents a form section in the CCH export (e.g., IRS-W2)"""
    code: str
    name: str
    entries: List[CCHFormEntry] = field(default_factory=list)

@dataclass
class CCHDocument:
    """Represents a complete CCH export document (one tax return)"""
    header: Dict[str, str] = field(default_factory=dict)
    forms: Dict[str, CCHForm] = field(default_factory=dict)
    
    @property
    def tax_year(self) -> int:
        return int(self.header.get("year", 0))
    
    @property
    def client_id(self) -> str:
        return self.header.get("client_id", "")
    
    @property
    def ssn(self) -> str:
        return self.header.get("ssn", "")
    
    def get_form(self, code: str) -> Optional[CCHForm]:
        """Get form by code"""
        return self.forms.get(code)
    
    def get_form_entries(self, code: str) -> List[CCHFormEntry]:
        """Get all entries for a form code"""
        form = self.forms.get(code)
        return form.entries if form else []

class CCHReader:
    """
    Reader for CCH tax software export files.
    Parses raw text into structured CCHDocument objects.
    """
    
    # Regex patterns for parsing
    HEADER_PATTERN = re.compile(
        r"\*\*BEGIN,(\d{4}):I:([^:]+):(\d+),([^,]+),([^,]*),([^,]*),(.*)$"
    )
    FORM_PATTERN = re.compile(r"\\@(\d+)\s*\\\s*(.+)$")
    SECTION_PATTERN = re.compile(r"\\:(\d+)")
    ENTRY_PATTERN = re.compile(r"\\&(\d+)")
    FIELD_PATTERN = re.compile(r"\.(\d+M?)\s+(.*)$")
    
    def __init__(self, mapping_file: Optional[str] = None):
        """
        Initialize reader with optional field mapping file.
        
        Args:
            mapping_file: Path to cch_mapping.json for field name lookups
        """
        self.mapping: Dict[str, Any] = {}
        if mapping_file:
            self.load_mapping(mapping_file)
    
    def load_mapping(self, filepath: str) -> None:
        """Load field mapping from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.mapping = json.load(f)
    
    def read_file(self, filepath: str) -> str:
        """Read CCH export file with proper encoding"""
        path = Path(filepath)
        
        # Helper to validate content
        def is_valid_cch(text: str) -> bool:
            # Check for header start in first 1000 chars
            return "**BEGIN" in text[:1000]

        # Try UTF-16LE first (common for CCH, but prone to false positives)
        try:
            with open(path, 'r', encoding='utf-16-le') as f:
                content = f.read()
                if content.startswith('\ufeff'):
                    content = content[1:]
                if is_valid_cch(content):
                    return content
        except Exception: 
            pass
        
        # Try UTF-8
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if is_valid_cch(content):
                    return content
        except Exception:
            pass
        
        # Fallback: latin-1 (always succeeds but checks validation)
        with open(path, 'r', encoding='latin-1') as f:
            content = f.read()
            # If we're here, we return whatever we have, or maybe prefer UTF-8 if valid?
            # But we already tried UTF-8.
            return content
    
    def parse_header(self, line: str) -> Optional[Dict[str, str]]:
        """Parse the header line of a CCH export"""
        match = self.HEADER_PATTERN.match(line.strip())
        if match:
            return {
                "year": match.group(1),
                "client_id": match.group(2),
                "sequence": match.group(3),
                "ssn": match.group(4),
                "office": match.group(5),
                "group": match.group(6),
                "location": match.group(7).strip()
            }
        return None
    
    def parse_lines(self, content: str) -> Iterator[CCHDocument]:
        """
        Parse CCH content and yield documents.
        Handles both single and multi-client files.
        """
        lines = content.split('\n')
        current_doc: Optional[CCHDocument] = None
        current_form: Optional[CCHForm] = None
        current_entry: Optional[CCHFormEntry] = None
        current_section = 1
        current_entry_num = 1
        
        for line in lines:
            line = line.rstrip('\r')
            
            # Check for new document header
            header = self.parse_header(line)
            if header:
                # Yield previous document if exists
                if current_doc:
                    if current_entry and current_form:
                        current_form.entries.append(current_entry)
                    yield current_doc
                
                current_doc = CCHDocument(header=header)
                current_form = None
                current_entry = None
                continue
            
            if not current_doc:
                continue
            
            # Check for form start
            form_match = self.FORM_PATTERN.match(line)
            if form_match:
                # Save previous entry
                if current_entry and current_form:
                    current_form.entries.append(current_entry)
                
                form_code = form_match.group(1)
                form_name = form_match.group(2).strip()
                
                # Check if form already exists (multiple entries)
                if form_code in current_doc.forms:
                    current_form = current_doc.forms[form_code]
                else:
                    current_form = CCHForm(code=form_code, name=form_name)
                    current_doc.forms[form_code] = current_form
                
                current_entry = None
                current_section = 1
                current_entry_num = 1
                continue
            
            # Check for section marker
            section_match = self.SECTION_PATTERN.match(line)
            if section_match:
                current_section = int(section_match.group(1))
                continue
            
            # Check for entry marker
            entry_match = self.ENTRY_PATTERN.match(line)
            if entry_match:
                # Save previous entry
                if current_entry and current_form:
                    current_form.entries.append(current_entry)
                
                current_entry_num = int(entry_match.group(1))
                current_entry = CCHFormEntry(
                    section=current_section,
                    entry=current_entry_num
                )
                continue
            
            field_match = self.FIELD_PATTERN.match(line)
            if field_match and current_entry:
                field_num = field_match.group(1)
                field_value = field_match.group(2).strip()
                is_memo = field_num.endswith('M')
                
                # Store memo fields with 'M' suffix to avoid overwriting regular fields
                # e.g., .54M is stored as "54M", separate from "54"
                if is_memo:
                    # Keep the 'M' suffix for memo fields to avoid collision
                    pass  # field_num already ends with 'M'
                
                # Only store if field doesn't exist OR if it's a non-memo overwriting a memo
                if field_num not in current_entry.fields:
                    current_entry.fields[field_num] = CCHField(
                        number=field_num,
                        value=field_value,
                        is_memo=is_memo
                    )
                elif not is_memo:
                    # Non-memo field takes precedence, but shouldn't happen normally
                    current_entry.fields[field_num] = CCHField(
                        number=field_num,
                        value=field_value,
                        is_memo=is_memo
                    )
        
        # Yield last document
        if current_doc:
            if current_entry and current_form:
                current_form.entries.append(current_entry)
            yield current_doc

    def parse_file(self, filepath: str) -> Optional[CCHDocument]:
        """Parse a single CCH export file"""
        content = self.read_file(filepath)
        docs = list(self.parse_lines(content))
        return docs[0] if docs else None
    
    def parse_multi_file(self, filepath: str) -> Iterator[CCHDocument]:
        """Parse a file containing multiple CCH exports"""
        content = self.read_file(filepath)
        yield from self.parse_lines(content)
