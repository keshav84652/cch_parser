"""
CCH Parser Core Module.

Provides readers and converters for parsing CCH tax software export files.
"""

from .reader import CCHReader, CCHDocument, CCHForm, CCHFormEntry, CCHField
from .converter import CCHConverter
from .mapping_loader import MappingLoader, get_mapping_loader

__all__ = [
    # Reader
    'CCHReader',
    'CCHDocument',
    'CCHForm',
    'CCHFormEntry',
    'CCHField',

    # Converter
    'CCHConverter',

    # Mapping
    'MappingLoader',
    'get_mapping_loader',
]
