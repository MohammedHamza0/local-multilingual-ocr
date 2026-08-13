from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any

@dataclass
class PageVerdict:
    page: int
    verdict: str  # "COPY" | "OCR" | "REVIEW"
    reason: str
    dominant_script: str = "unknown"
    direction: str = "ltr"
    metrics: Dict[str, Any] = field(default_factory=dict)
    text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
