from typing import Tuple, Optional, Dict

from ..utils import IssueLoader


class IssueLookupService:
    def __init__(self, lookup_function=None):
        self.lookup_function = lookup_function or self._default_lookup

    def _default_lookup(self, code: str) -> Optional[Dict]:
        return IssueLoader.get_issue_info(code)

    def get_effort_and_severity(self, issue_code: str) -> Tuple[float, str]:
        issue_info = self.lookup_function(issue_code)

        if not issue_info:
            return 0.0, 'Unknown'

        manual_effort = float(issue_info.get('ManualEffort', 0) or 0)
        severity = issue_info.get('Severity', 'Unknown')

        if manual_effort < 0:
            return 0.0, severity

        if 'EWI' in issue_code:
            return manual_effort / 60.0, severity

        return manual_effort, severity

