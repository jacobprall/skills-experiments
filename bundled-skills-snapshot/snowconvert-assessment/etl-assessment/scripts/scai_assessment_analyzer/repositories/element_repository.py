import csv
from pathlib import Path
from typing import Dict, Tuple, Set, Optional

from ..models import Component


class ElementRepository:
    def __init__(self, file_path: str, excluded_subtypes: Set[str]):
        self.file_path = Path(file_path)
        self.excluded_subtypes = excluded_subtypes

    def load_components(self) -> Tuple[Dict[Tuple[str, str], Component], int]:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Elements file not found: {self.file_path}")

        components_by_key = {}
        excluded_count = 0

        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                component = self._create_component(row)
                if not component:
                    continue

                if component.subtype in self.excluded_subtypes:
                    excluded_count += 1
                    continue

                component_key = (component.file_name, component.full_name)
                components_by_key[component_key] = component

        return components_by_key, excluded_count

    @staticmethod
    def _create_component(row: Dict[str, str]) -> Optional[Component]:
        full_name = row.get('FullName', '').strip()
        file_name = row.get('FileName', '').strip()

        if not full_name or not file_name:
            return None

        return Component(
            full_name=full_name,
            file_name=file_name,
            technology=row.get('Technology', '').strip(),
            category=row.get('Category', '').strip(),
            subtype=row.get('Subtype', '').strip(),
            status=row.get('Status', '').strip(),
            entry_kind=row.get('Entry Kind', '').strip(),
            additional_info=row.get('Additional Info', '').strip()
        )

