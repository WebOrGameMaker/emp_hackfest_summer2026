import re
from typing import Dict, List, Optional, Tuple

from .. import taxonomy
from ..models import AnalysisEvidence, HazardAnalysis
from .base import empty_analysis

NAME = "demo"
TEXT_CEILING = 0.95
FUSION_CEILING = 0.96
FILENAME_CEILING = 0.78

DemoScenario = Dict[str, object]

DEMO_SCENARIOS: Dict[str, DemoScenario] = {
    "fallen-tree-4th-ave": {
        "category": "fallen_tree",
        "severity": "high",
        "location_type": "roadway",
        "obstruction": True,
        "vehicle_access": "blocked",
        "pedestrian_access": "limited",
        "confidence": 0.92,
        "summary": "A large tree is down across both lanes of the road.",
        "detections": [
            "tree across the road (0.97)",
            "foliage on the asphalt (0.93)",
            "lane markings covered (0.89)",
            "no emergency vehicle (0.81)",
        ],
    },
    "flooded-underpass": {
        "category": "flooding",
        "severity": "high",
        "location_type": "roadway",
        "obstruction": True,
        "vehicle_access": "blocked",
        "pedestrian_access": "blocked",
        "confidence": 0.91,
        "summary": "Deep standing water covers the road at an underpass.",
        "detections": [
            "water covering the road (0.95)",
            "curb underwater (0.88)",
            "reflection of the overpass (0.84)",
        ],
    },
    "signal-dark": {
        "category": "traffic_signal",
        "severity": "high",
        "location_type": "intersection",
        "obstruction": False,
        "vehicle_access": "limited",
        "pedestrian_access": "limited",
        "confidence": 0.89,
        "summary": "The traffic signal is dark in all directions at a four-way intersection.",
        "detections": [
            "unlit traffic signal (0.92)",
            "four-way intersection (0.9)",
            "crosswalk markings visible (0.86)",
        ],
    },
    "pothole-cluster": {
        "category": "pavement_damage",
        "severity": "moderate",
        "location_type": "roadway",
        "obstruction": False,
        "vehicle_access": "limited",
        "pedestrian_access": "open",
        "confidence": 0.87,
        "summary": "A cluster of deep potholes in the travel lane.",
        "detections": [
            "deep pothole (0.9)",
            "broken pavement (0.85)",
            "water in the hole (0.7)",
        ],
    },
    "debris-lane": {
        "category": "road_obstruction",
        "severity": "moderate",
        "location_type": "roadway",
        "obstruction": True,
        "vehicle_access": "limited",
        "pedestrian_access": "open",
        "confidence": 0.86,
        "summary": "Construction debris and a barrier are sitting in the right lane.",
        "detections": [
            "displaced barrier (0.89)",
            "debris in the lane (0.86)",
            "adjacent lane clear (0.8)",
        ],
    },
    "streetlight-out": {
        "category": "streetlight",
        "severity": "low",
        "location_type": "sidewalk",
        "obstruction": False,
        "vehicle_access": "open",
        "pedestrian_access": "open",
        "confidence": 0.83,
        "summary": "A streetlight is out over the walkway, leaving a dark gap between lit poles.",
        "detections": [
            "unlit streetlight (0.87)",
            "dark stretch of walkway (0.85)",
            "adjacent pole lit (0.78)",
        ],
    },
    "smoke-column": {
        "category": "fire_smoke",
        "severity": "high",
        "location_type": "public_space",
        "obstruction": False,
        "vehicle_access": "limited",
        "pedestrian_access": "limited",
        "confidence": 0.9,
        "summary": "Dark smoke is rising behind a building. No flames are visible from here.",
        "detections": [
            "smoke column (0.94)",
            "no visible flames (0.72)",
            "building in the foreground (0.83)",
        ],
    },
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("\u2019", "'")).strip()


def _matches(haystack: str, needle: str) -> bool:
    if " " in needle or "-" in needle:
        return needle in haystack
    return re.search(r"\b" + re.escape(needle) + r"\b", haystack) is not None


def _score_categories(text: str) -> List[Tuple[str, float, List[str]]]:
    # skip shorter terms already covered by a longer hit, e.g. "tree" after "tree down"
    results: List[Tuple[str, float, List[str]]] = []
    for category in taxonomy.CATEGORIES:
        hits = [term for term in category.terms if _matches(text, term)]
        hits.sort(key=len, reverse=True)
        accepted: List[str] = []
        for term in hits:
            if any(term in longer for longer in accepted):
                continue
            accepted.append(term)
        score = sum(category.terms[term] for term in accepted)
        score -= sum(
            weight for term, weight in category.negative_terms.items() if _matches(text, term)
        )
        if score > 0:
            results.append((category.key, score, accepted))
    results.sort(key=lambda row: row[1], reverse=True)
    return results


def _find_cue(text: str, cues: Dict[str, str]) -> Optional[Tuple[str, str]]:
    best: Optional[Tuple[str, str]] = None
    for cue, value in cues.items():
        if _matches(text, cue) and (best is None or len(cue) > len(best[0])):
            best = (cue, value)
    return best


def _severity_from_text(text: str, category: taxonomy.Category, evidence: List[AnalysisEvidence]) -> str:
    rank = float(taxonomy.SEVERITY_RANK[category.default_severity])
    delta = 0.0
    fired: List[str] = []
    for cue, weight in taxonomy.SEVERITY_CUES.items():
        if _matches(text, cue):
            delta += weight
            fired.append(cue)
    delta = max(-1.2, min(1.2, delta))
    if fired:
        direction = "raised" if delta > 0 else "lowered"
        evidence.append(AnalysisEvidence(
            field="severity",
            cue=", ".join(sorted(fired)[:3]),
            detail="Words like these {0} severity from the {1} baseline for {2}.".format(
                direction, category.default_severity, category.label.lower()
            ),
        ))
    return taxonomy.clamp_severity(rank + delta)


def _access_defaults(severity: str, location_type: str, obstruction: bool) -> Tuple[str, str]:
    if not obstruction:
        if location_type == "intersection":
            return "limited", "limited"
        return "open", "open"
    if location_type == "sidewalk":
        return "open", "blocked" if severity == "high" else "limited"
    if severity == "high":
        return "blocked", "limited"
    if severity == "moderate":
        return "limited", "open"
    return "open", "open"


def _compose_summary(
    category: taxonomy.Category,
    severity: str,
    location_type: str,
    obstruction: bool,
    vehicle_access: str,
    pedestrian_access: str,
) -> str:
    scale = {"high": "Major", "moderate": "", "low": "Minor"}[severity]
    place = {
        "roadway": "on the roadway",
        "intersection": "at the intersection",
        "sidewalk": "on the sidewalk",
        "highway": "on the highway",
        "park": "in a park",
        "public_space": "in a public space",
        "unknown": "at the reported location",
    }[location_type]
    head = "{0} {1}".format(scale, category.label.lower()).strip()
    sentence = "{0} {1}".format(head[0].upper() + head[1:], place)
    clauses: List[str] = []
    if obstruction:
        clauses.append("blocking the way")
    if vehicle_access == "blocked":
        clauses.append("vehicle access blocked")
    elif vehicle_access == "limited":
        clauses.append("vehicle access reduced")
    if pedestrian_access == "blocked":
        clauses.append("pedestrian access blocked")
    elif pedestrian_access == "limited":
        clauses.append("pedestrian access reduced")
    if clauses:
        sentence += "; " + ", ".join(clauses)
    return sentence + "."


def analyze_text(text: str) -> HazardAnalysis:
    normalized = _normalize(text)
    if not normalized:
        return empty_analysis("No description provided.")
    evidence: List[AnalysisEvidence] = []
    scores = _score_categories(normalized)
    if not scores or scores[0][1] < 1.5:
        analysis = empty_analysis("No recognized hazard type in the description.")
        analysis.provider = NAME
        analysis.summary = "Unclassified hazard awaiting review: \u201c{0}\u201d".format(text.strip()[:120])
        return analysis
    top_key, top_score, top_terms = scores[0]
    runner_up = scores[1][1] if len(scores) > 1 else 0.0
    margin = top_score - runner_up
    category = taxonomy.get(top_key)
    evidence.append(AnalysisEvidence(
        field="category",
        cue=", ".join(top_terms[:3]),
        detail="Best match is {0} (score {1:.1f}), {2:.1f} ahead of the next type.".format(
            category.label.lower(), top_score, margin
        ),
    ))
    severity = _severity_from_text(normalized, category, evidence)
    location_hit = _find_cue(normalized, taxonomy.LOCATION_CUES)
    location_type = category.default_location_type
    if location_hit:
        location_type = location_hit[1]
        evidence.append(AnalysisEvidence(
            field="location_type",
            cue=location_hit[0],
            detail="The report names a {0}.".format(location_type.replace("_", " ")),
        ))
    obstruction = category.implies_obstruction
    obstruction_cue = next((cue for cue in taxonomy.OBSTRUCTION_CUES if _matches(normalized, cue)), None)
    if obstruction_cue:
        obstruction = True
        evidence.append(AnalysisEvidence(
            field="obstruction",
            cue=obstruction_cue,
            detail="The description says the hazard is in the way.",
        ))
    vehicle_default, pedestrian_default = _access_defaults(severity, location_type, obstruction)
    vehicle_hit = _find_cue(normalized, taxonomy.VEHICLE_CUES)
    vehicle_access = vehicle_hit[1] if vehicle_hit else vehicle_default
    if vehicle_hit:
        evidence.append(AnalysisEvidence(
            field="vehicle_access",
            cue=vehicle_hit[0],
            detail="The description mentions how cars can get through.",
        ))
    pedestrian_hit = _find_cue(normalized, taxonomy.PEDESTRIAN_CUES)
    pedestrian_access = pedestrian_hit[1] if pedestrian_hit else pedestrian_default
    if pedestrian_hit:
        evidence.append(AnalysisEvidence(
            field="pedestrian_access",
            cue=pedestrian_hit[0],
            detail="The description mentions how people walking can get through.",
        ))
    # short reports identify a type but describe almost nothing
    specificity = 0.025 * min(3, sum(1 for hit in (location_hit, vehicle_hit, pedestrian_hit) if hit))
    word_count = len(normalized.split())
    if word_count < 5:
        brevity = -0.12
    elif word_count < 8:
        brevity = -0.06
    else:
        brevity = 0.0
    confidence = 0.38 + 0.05 * min(top_score, 8.0) + 0.045 * min(margin, 4.0) + specificity + brevity
    confidence = round(max(0.25, min(TEXT_CEILING, confidence)), 4)
    if brevity < 0:
        evidence.append(AnalysisEvidence(
            field="confidence",
            cue="short description",
            detail="Only {0} words, so the type is less certain from the text alone.".format(word_count),
        ))
    return HazardAnalysis(
        category=category.key,
        severity=severity,
        location_type=location_type,
        obstruction=obstruction,
        vehicle_access=vehicle_access,
        pedestrian_access=pedestrian_access,
        summary=_compose_summary(
            category, severity, location_type, obstruction, vehicle_access, pedestrian_access,
        ),
        confidence=confidence,
        evidence=evidence,
        provider=NAME,
    )


def _scenario_id(image_name: Optional[str]) -> Optional[str]:
    if not image_name:
        return None
    if image_name.startswith("demo:"):
        key = image_name.split(":", 1)[1]
        return key if key in DEMO_SCENARIOS else None
    return None


def analyze_scenario(scenario_id: str) -> HazardAnalysis:
    scenario = DEMO_SCENARIOS[scenario_id]
    detections = list(scenario.get("detections") or [])
    evidence = [
        AnalysisEvidence(
            field="category",
            cue=detection.split(" (")[0],
            detail="Seen in the demo photo.",
        )
        for detection in detections
    ]
    evidence.append(AnalysisEvidence(
        field="provider",
        cue="demo vision",
        detail=(
            "Demo photo reading for \u201c{0}\u201d. "
            "Set HAZARDMAP_AI_KEY to use a real vision model.".format(scenario_id)
        ),
    ))
    return HazardAnalysis(
        category=str(scenario["category"]),
        severity=str(scenario["severity"]),
        location_type=str(scenario["location_type"]),
        obstruction=bool(scenario["obstruction"]),
        vehicle_access=str(scenario["vehicle_access"]),
        pedestrian_access=str(scenario["pedestrian_access"]),
        summary=str(scenario["summary"]),
        confidence=float(scenario["confidence"]),
        evidence=evidence,
        provider=NAME,
    )


def analyze_image(image_b64: Optional[str], image_name: Optional[str]) -> HazardAnalysis:
    scenario_id = _scenario_id(image_name)
    if scenario_id:
        return analyze_scenario(scenario_id)
    if image_name:
        stem = re.sub(r"\.[a-z0-9]+$", "", image_name, flags=re.I)
        hint = _normalize(re.sub(r"[_\-.]+", " ", stem))
        scores = _score_categories(hint)
        if scores and scores[0][1] >= 2.5:
            derived = analyze_text(hint)
            derived.confidence = round(min(FILENAME_CEILING, derived.confidence * 0.85), 4)
            derived.evidence.insert(0, AnalysisEvidence(
                field="category",
                cue=image_name,
                detail="No vision model is configured, so the filename was used. Confidence is capped.",
            ))
            return derived
    analysis = empty_analysis(
        "A photo was submitted but no vision model is configured, so the image could not be classified. Add a description."
    )
    analysis.provider = NAME
    analysis.summary = "Photo report awaiting classification; no description supplied."
    return analysis


def _fuse(image: HazardAnalysis, text: HazardAnalysis) -> HazardAnalysis:
    agree = image.category == text.category
    primary = image if image.confidence >= text.confidence else text
    secondary = text if primary is image else image
    fused = primary.model_copy(deep=True)
    fused.evidence = list(image.evidence) + list(text.evidence)
    # prefer the modality that actually specified an attribute
    if fused.location_type in ("unknown", None) or (
        secondary.location_type not in ("unknown", None)
        and primary.location_type == taxonomy.get(primary.category).default_location_type
    ):
        fused.location_type = secondary.location_type
    for attr in ("vehicle_access", "pedestrian_access"):
        if getattr(fused, attr) == "unknown":
            setattr(fused, attr, getattr(secondary, attr))
    fused.obstruction = image.obstruction or text.obstruction
    # a sentence can say the road is closed; a photo often cannot
    fused.severity = text.severity if text.confidence >= 0.5 else fused.severity
    if agree:
        stronger = max(image.confidence, text.confidence)
        weaker = min(image.confidence, text.confidence)
        combined = stronger + 0.25 * weaker * (1.0 - stronger)
        fused.confidence = round(min(FUSION_CEILING, combined), 4)
        fused.evidence.append(AnalysisEvidence(
            field="confidence",
            cue="photo and text agree",
            detail="Photo and description both classified as {0}, which raises confidence.".format(
                taxonomy.get(fused.category).label.lower()
            ),
        ))
    else:
        fused.confidence = round(max(0.3, primary.confidence - 0.18), 4)
        fused.evidence.append(AnalysisEvidence(
            field="confidence",
            cue="photo and text disagree",
            detail=(
                "Photo suggested {0} while the description suggested {1}. "
                "Kept the stronger signal and reduced confidence.".format(
                    taxonomy.get(image.category).label.lower(),
                    taxonomy.get(text.category).label.lower(),
                )
            ),
        ))
    fused.summary = _compose_summary(
        taxonomy.get(fused.category), fused.severity, fused.location_type,
        fused.obstruction, fused.vehicle_access, fused.pedestrian_access,
    )
    fused.provider = NAME
    return fused


class DemoAnalyzer:
    name = NAME

    def analyze(
        self,
        text: Optional[str] = None,
        image_b64: Optional[str] = None,
        image_name: Optional[str] = None,
    ) -> HazardAnalysis:
        has_text = bool(text and text.strip())
        has_image = bool(image_b64 or _scenario_id(image_name))
        if has_text and has_image:
            return _fuse(analyze_image(image_b64, image_name), analyze_text(text or ""))
        if has_image:
            return analyze_image(image_b64, image_name)
        if has_text:
            return analyze_text(text or "")
        analysis = empty_analysis("Neither a photo nor a description was sent.")
        analysis.provider = NAME
        return analysis
