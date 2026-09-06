from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from . import taxonomy


class AnalysisEvidence(BaseModel):
    field: str
    cue: str
    detail: str = ""


class HazardAnalysis(BaseModel):
    category: str = Field(default=taxonomy.FALLBACK_CATEGORY)
    severity: str = Field(default="moderate")
    location_type: str = Field(default="unknown")
    obstruction: bool = False
    vehicle_access: str = Field(default="unknown")
    pedestrian_access: str = Field(default="unknown")
    summary: str = ""
    confidence: float = 0.5
    evidence: List[AnalysisEvidence] = Field(default_factory=list)
    provider: str = "demo"


class ReportSubmission(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    text: Optional[str] = None
    image_b64: Optional[str] = None
    image_name: Optional[str] = None
    reporter: Optional[str] = None
    # reuse the preview so submit stores what the reporter already saw
    analysis: Optional[HazardAnalysis] = None


class AnalyzeRequest(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    text: Optional[str] = None
    image_b64: Optional[str] = None
    image_name: Optional[str] = None


class Report(BaseModel):
    id: str
    hazard_id: str
    lat: float
    lon: float
    text: Optional[str] = None
    has_photo: bool = False
    photo_url: Optional[str] = None
    reporter: str = "Anonymous"
    created_at: str
    analysis: HazardAnalysis


class ConfidenceContribution(BaseModel):
    key: str
    label: str
    detail: str
    logit_delta: float


class ConfidenceBreakdown(BaseModel):
    value: float
    base_ai_confidence: float
    contributions: List[ConfidenceContribution] = Field(default_factory=list)
    capped: bool = False
    cap_reason: str = ""


class NearbyMatch(BaseModel):
    hazard_id: str
    category: str
    label: str
    icon: str
    distance_m: float
    report_count: int
    confidence: float
    minutes_since_last_report: float
    would_merge: bool
    reason: str


class Hazard(BaseModel):
    id: str
    category: str
    label: str
    icon: str
    severity: str
    lat: float
    lon: float
    location_type: str
    obstruction: bool
    vehicle_access: str
    pedestrian_access: str
    summary: str
    report_count: int
    photo_count: int
    confidence: float
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    first_reported_at: str
    last_reported_at: str
    spread_m: float = 0.0
    reports: List[Report] = Field(default_factory=list)
    place: str = ""


class SubmissionResult(BaseModel):
    report: Report
    hazard: Hazard
    merged: bool
    previous_confidence: Optional[float] = None
    previous_report_count: int = 0
    merge_explanation: str = ""


class AIStatus(BaseModel):
    provider: str
    is_demo: bool
    model: Optional[str] = None
    note: str = ""


class CategorySummary(BaseModel):
    key: str
    label: str
    icon: str
    blurb: str
    hazard_count: int = 0
    report_count: int = 0
    cluster_radius_m: float = 0.0
    cluster_window_hours: float = 0.0


class MetaResponse(BaseModel):
    ai: AIStatus
    categories: List[CategorySummary]
    severity_levels: List[str]
    hazard_count: int
    report_count: int
    map_center: List[float]
    demo_pin: List[float]
    thresholds: Dict[str, Any]
