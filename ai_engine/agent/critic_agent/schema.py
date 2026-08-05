from pydantic import BaseModel
from typing import List, Optional

class Violation(BaseModel):
    rule: str
    severity: str
    details: str
    affected_day: Optional[int] = None
    suggested_fix: str

class CriticVerdict(BaseModel):
    passed: bool
    total_violations: int
    critical_count: int
    warning_count: int
    info_count: int
    violations: List[Violation]
    overall_score: float
    summary: str
