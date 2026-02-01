from typing import Optional, Iterator
from .core.reader import CCHReader, CCHDocument
from .core.converter import CCHConverter
from .models.return_data import TaxReturn

class CCHParser:
    """
    Main entry point for CCH Parser.
    Combines reading and conversion logic.
    """

    def __init__(self, mapping_file: Optional[str] = None):
        self.reader = CCHReader(mapping_file)
        self.converter = CCHConverter()

    def parse_file(self, filepath: str) -> Optional[CCHDocument]:
        """Parse a single file"""
        return self.reader.parse_file(filepath)

    def parse_multi_file(self, filepath: str) -> Iterator[CCHDocument]:
        """Parse a multi-document file"""
        return self.reader.parse_multi_file(filepath)

    def to_tax_return(self, doc: CCHDocument) -> TaxReturn:
        """Convert document to TaxReturn."""
        return self.converter.convert(doc)
