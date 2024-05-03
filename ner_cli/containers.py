from dataclasses import dataclass
from typing import Optional
from pathlib import Path

@dataclass
class Collection:
    p_in: Path
    p_out: Path
    p_error: Path
    p_worker: Path
    p_log: Path
    error_count: int = 0
    file_count: int = 0
    continue_from: Optional[str] = None
    time_stamp: Optional[str] = None

@dataclass
class File:
    file: str
    p_in: Path
    p_out: Optional[Path]
    p_error: Path
    file_str: Optional[str] = None
    title_str: Optional[str] = None
    id: Optional[str] = None
    xml: Optional[str] = None
    xml_annotated: Optional[str] = None
    tp_url: Optional[str] = None