import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .. import config, taxonomy
from ..models import AnalysisEvidence, HazardAnalysis
from .demo import DemoAnalyzer

NAME = "openai"

SYSTEM_PROMPT = """You are the classification layer of HazardMap, a public-safety reporting system.

You receive one observation: a photo, a written description, or both.
Convert it into structured hazard data using ONLY the controlled vocabulary in
the schema. You are not verifying the hazard, only describing what the
observation supports.

Rules:
- Choose the single category that best matches. Use "other" if none fit.
- severity: "low" for cosmetic or low-risk, "moderate" for meaningful
  disruption, "high" for immediate danger or a fully blocked right of way.
- obstruction is true only if the hazard physically impedes passage.
- vehicle_access / pedestrian_access describe passability at the scene.
- summary: one clear, neutral sentence, so differently worded reports of the
  same hazard read alike.
- confidence: your genuine certainty in the category. Never exceed 0.95.
- evidence: 2-4 specific observations that drove your answer. For photos cite
  what you saw; for text cite the phrases you relied on.
"""

RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "category", "severity", "location_type", "obstruction",
        "vehicle_access", "pedestrian_access", "summary", "confidence", "evidence",
    ],
    "properties": {
        "category": {"type": "string", "enum": taxonomy.category_keys()},
        "severity": {"type": "string", "enum": list(taxonomy.SEVERITY_LEVELS)},
        "location_type": {"type": "string", "enum": list(taxonomy.LOCATION_TYPES)},
        "obstruction": {"type": "boolean"},
        "vehicle_access": {"type": "string", "enum": list(taxonomy.ACCESS_LEVELS)},
        "pedestrian_access": {"type": "string", "enum": list(taxonomy.ACCESS_LEVELS)},
        "summary": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["field", "cue", "detail"],
                "properties": {
                    "field": {"type": "string"},
                    "cue": {"type": "string"},
                    "detail": {"type": "string"},
                },
            },
        },
    },
}


def _as_data_url(image_b64: str) -> str:
    if image_b64.startswith("data:"):
        return image_b64
    return "data:image/jpeg;base64," + image_b64


def _build_messages(text: Optional[str], image_b64: Optional[str]) -> List[Dict[str, Any]]:
    content: List[Dict[str, Any]] = []
    if text and text.strip():
        content.append({"type": "text", "text": "Citizen description: {0}".format(text.strip())})
    if image_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": _as_data_url(image_b64), "detail": "low"},
        })
    if not content:
        content.append({"type": "text", "text": "No observation supplied."})
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


class OpenAIAnalyzer:
    name = NAME

    def __init__(self) -> None:
        self._fallback = DemoAnalyzer()

    def _request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = urllib.request.Request(
            "{0}/chat/completions".format(config.AI_BASE_URL.rstrip("/")),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {0}".format(config.AI_KEY),
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=config.AI_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))

    def analyze(
        self,
        text: Optional[str] = None,
        image_b64: Optional[str] = None,
        image_name: Optional[str] = None,
    ) -> HazardAnalysis:
        payload = {
            "model": config.AI_MODEL,
            "messages": _build_messages(text, image_b64),
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "hazard_analysis",
                    "strict": True,
                    "schema": RESPONSE_SCHEMA,
                },
            },
        }
        try:
            body = self._request(payload)
            raw = body["choices"][0]["message"]["content"]
            analysis = HazardAnalysis(**json.loads(raw))
            analysis.provider = NAME
            analysis.confidence = round(min(0.95, float(analysis.confidence)), 4)
            return analysis
        except (
            urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError,
            ValueError, TypeError, OSError,
        ):
            # never lose a report to an api problem
            degraded = self._fallback.analyze(text, image_b64, image_name)
            degraded.evidence.insert(0, AnalysisEvidence(
                field="provider",
                cue="fallback to demo analyzer",
                detail="The configured model could not be reached, so this report was classified locally instead.",
            ))
            return degraded
