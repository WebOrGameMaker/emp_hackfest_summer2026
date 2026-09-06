from typing import Optional

try:
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol, runtime_checkable  # type: ignore

from ..models import HazardAnalysis


@runtime_checkable
class HazardAnalyzer(Protocol):
    name: str

    def analyze(
        self,
        text: Optional[str] = None,
        image_b64: Optional[str] = None,
        image_name: Optional[str] = None,
    ) -> HazardAnalysis:
        ...


def empty_analysis(reason: str) -> HazardAnalysis:
    from ..models import AnalysisEvidence

    return HazardAnalysis(
        category="other",
        severity="moderate",
        location_type="unknown",
        obstruction=False,
        vehicle_access="unknown",
        pedestrian_access="unknown",
        summary="Unclassified hazard. The type could not be determined.",
        confidence=0.3,
        evidence=[AnalysisEvidence(field="category", cue="no signal", detail=reason)],
    )
