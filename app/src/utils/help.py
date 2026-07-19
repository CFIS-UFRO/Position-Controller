"""Help-manual index loading and validation."""

import json
from functools import lru_cache
from typing import TypedDict

from src.utils.paths import get_help_index_file_path

# --------------------------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------------------------
class HelpManual(TypedDict):
    """Indexed help manual metadata."""

    id: str
    title: str
    file: str

# --------------------------------------------------------------------------------------------------
# Manual index
# --------------------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_help_manuals() -> list[HelpManual]:
    """Load and validate the configured help manuals."""
    index_file_path = get_help_index_file_path()
    data = json.loads(index_file_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Help index must contain a list: {index_file_path}")
    manuals = []
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError(f"Help index entries must contain objects: {index_file_path}")
        manual_id = entry.get("id")
        title = entry.get("title")
        file_path = entry.get("file")
        if (
            not isinstance(manual_id, str)
            or not manual_id
            or not isinstance(title, str)
            or not title
            or not isinstance(file_path, str)
            or not file_path
        ):
            raise ValueError(f"Help index entries require id, title, and file strings: {index_file_path}")
        manuals.append(HelpManual(id=manual_id, title=title, file=file_path))
    return manuals
