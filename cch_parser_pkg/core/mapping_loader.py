"""
MappingLoader - Loads YAML field mappings for CCH form parsing.

This provides a single source of truth for field number → field name mappings.
The converter uses this to look up fields dynamically instead of hard-coding.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class MappingLoader:
    """
    Loads and provides access to CCH field mappings from YAML.
    """
    
    def __init__(self, yaml_path: Optional[str] = None):
        """
        Initialize with path to cch_mapping.yaml.
        If no path provided, looks in default locations.
        """
        self.mappings: Dict[str, Any] = {}
        
        if yaml_path is None:
            # Try default locations
            possible_paths = [
                Path(__file__).parent.parent.parent / "mappings" / "cch_mapping.yaml",
                Path("mappings/cch_mapping.yaml"),
                Path("cch_mapping.yaml"),
            ]
            for p in possible_paths:
                if p.exists():
                    yaml_path = str(p)
                    break
        
        if yaml_path and Path(yaml_path).exists():
            self._load_yaml(yaml_path)
    
    def _load_yaml(self, yaml_path: str) -> None:
        """Load mappings from YAML file"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            self.mappings = yaml.safe_load(f) or {}
    
    def get_field_number(self, form_code: str, field_name: str) -> Optional[str]:
        """
        Get the field number for a given form and semantic field name.
        
        Args:
            form_code: CCH form code (e.g., "180" for W-2, "120" for K-1 1120S)
            field_name: Semantic name (e.g., "box1_wages", "corporation_name")
        
        Returns:
            Field number as string (e.g., "54", "34") or None if not found
        """
        form_key = f"form_{form_code}"
        if form_key in self.mappings:
            fields = self.mappings[form_key].get("fields", {})
            for num, info in fields.items():
                if isinstance(info, dict) and info.get("name") == field_name:
                    return num
        return None
    
    def get_field_info(self, form_code: str, field_num: str) -> Optional[Dict[str, Any]]:
        """
        Get field info by form code and field number.
        
        Returns dict with 'name', 'type', and optionally 'values'
        """
        form_key = f"form_{form_code}"
        if form_key in self.mappings:
            fields = self.mappings[form_key].get("fields", {})
            return fields.get(field_num)
        return None
    
    def get_form_fields(self, form_code: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all field mappings for a form.
        
        Returns dict of field_number -> field_info
        """
        form_key = f"form_{form_code}"
        return self.mappings.get(form_key, {}).get("fields", {})
    
    def get_form_name(self, form_code: str) -> str:
        """Get the human-readable form name"""
        form_key = f"form_{form_code}"
        return self.mappings.get(form_key, {}).get("name", f"Form {form_code}")
    
    def has_form(self, form_code: str) -> bool:
        """Check if a form mapping exists"""
        return f"form_{form_code}" in self.mappings
    
    # Convenience methods for common lookups
    def f(self, form_code: str, field_name: str) -> str:
        """
        Shorthand for get_field_number with fallback.
        Returns empty string if not found (safer for .get() calls)
        """
        return self.get_field_number(form_code, field_name) or ""


# Global singleton for easy access
_default_loader: Optional[MappingLoader] = None


def get_mapping_loader(yaml_path: Optional[str] = None) -> MappingLoader:
    """Get or create the default MappingLoader instance"""
    global _default_loader
    if _default_loader is None:
        _default_loader = MappingLoader(yaml_path)
    return _default_loader
