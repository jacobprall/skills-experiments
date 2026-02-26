"""Issue reference data loader with caching"""

import json
from pathlib import Path
from typing import Dict, Optional, Any


class IssueLoader:
    """Loads and caches issue reference data"""
    
    _cache: Optional[Dict[str, Any]] = None
    
    @classmethod
    def load_issues(cls) -> Dict[str, Any]:
        """
        Load and cache issues data from JSON file
        
        Returns:
            Dictionary mapping issue codes to issue information
        """
        if cls._cache is None:
            data_path = Path(__file__).parent.parent / "data" / "issues_ref.json"
            
            if not data_path.exists():
                raise FileNotFoundError(f"Issues reference file not found: {data_path}")
            
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cls._cache = {
                    issue["Code"]: issue
                    for issue in data.get("Issues", [])
                }
        
        return cls._cache
    
    @classmethod
    def get_issue_info(cls, code: str) -> Optional[Dict[str, Any]]:
        """
        Get issue information by code
        
        Args:
            code: The issue code (e.g., "SSC-EWI-SSIS0001")
            
        Returns:
            Dictionary with issue information or None if not found
        """
        issues = cls.load_issues()
        return issues.get(code)
    
    @classmethod
    def clear_cache(cls):
        """Clear the cached issues data"""
        cls._cache = None

