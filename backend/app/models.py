from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["critical", "high", "medium", "low"]
FindingStatus = Literal["open", "acknowledged", "resolved", "dismissed"]


class CostRecord(BaseModel):
    date: date
    service: str
    amount: float = Field(ge=0)
    account_id: str = "demo-operations"
    region: str = "global"


class ResourceRecord(BaseModel):
    resource_id: str
    name: str
    resource_type: str
    service: str
    region: str
    state: str
    monthly_cost: float = Field(ge=0)
    utilization_pct: float | None = None
    attached_to: str | None = None
    age_days: int = Field(default=0, ge=0)
    tags: dict[str, str] = Field(default_factory=dict)
    collected_at: datetime


class Finding(BaseModel):
    id: str
    severity: Severity
    finding_type: str
    title: str
    resource_id: str | None = None
    service: str
    region: str
    detected_at: datetime
    monthly_impact: float = Field(ge=0)
    evidence: str
    recommendation: str
    status: FindingStatus = "open"


class DashboardData(BaseModel):
    meta: dict[str, str]
    summary: dict[str, float | int]
    cost_series: list[dict[str, str | float]]
    service_breakdown: list[dict[str, str | float]]
    findings: list[Finding]
    resources: list[ResourceRecord]

