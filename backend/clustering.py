import math
from typing import List, Optional, Sequence, Tuple

from . import taxonomy, timeutil
from .models import Hazard, NearbyMatch, Report

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def evaluate(
    category: str,
    lat: float,
    lon: float,
    hazards: Sequence[Hazard],
    when: Optional[str] = None,
    search_multiplier: float = 3.0,
) -> List[NearbyMatch]:
    moment = when or timeutil.now_iso()
    matches: List[NearbyMatch] = []
    for hazard in hazards:
        if hazard.category != category:
            continue
        rules = taxonomy.get(category)
        distance = round(haversine_m(lat, lon, hazard.lat, hazard.lon), 1)
        if distance > rules.cluster_radius_m * search_multiplier:
            continue
        age_hours = timeutil.hours_between(hazard.last_reported_at, moment)
        within_distance = distance <= rules.cluster_radius_m
        within_window = age_hours <= rules.cluster_window_hours
        if within_distance and within_window:
            reason = (
                "Same type, {0:.0f}m away (within {1:.0f}m), last reported {2} ago "
                "(within {3:.0f}h).".format(
                    distance, rules.cluster_radius_m, _humanize_hours(age_hours),
                    rules.cluster_window_hours,
                )
            )
        elif not within_distance:
            reason = (
                "Same type, but {0:.0f}m away — outside the {1:.0f}m range for {2}.".format(
                    distance, rules.cluster_radius_m, rules.label.lower()
                )
            )
        else:
            reason = (
                "Same type and within range, but last reported {0} ago, "
                "outside the {1:.0f}h window.".format(
                    _humanize_hours(age_hours), rules.cluster_window_hours
                )
            )
        matches.append(NearbyMatch(
            hazard_id=hazard.id,
            category=hazard.category,
            label=hazard.label,
            icon=hazard.icon,
            distance_m=distance,
            report_count=hazard.report_count,
            confidence=hazard.confidence,
            minutes_since_last_report=round(age_hours * 60.0, 1),
            would_merge=within_distance and within_window,
            reason=reason,
        ))
    matches.sort(key=lambda match: match.distance_m)
    return matches


def choose(matches: Sequence[NearbyMatch]) -> Optional[NearbyMatch]:
    qualifying = [match for match in matches if match.would_merge]
    if not qualifying:
        return None
    return min(qualifying, key=lambda match: match.distance_m)


def centroid(reports: Sequence[Report]) -> Tuple[float, float]:
    if not reports:
        return (0.0, 0.0)
    total = sum(max(0.1, report.analysis.confidence) for report in reports)
    lat = sum(report.lat * max(0.1, report.analysis.confidence) for report in reports) / total
    lon = sum(report.lon * max(0.1, report.analysis.confidence) for report in reports) / total
    return (round(lat, 6), round(lon, 6))


def spread_m(reports: Sequence[Report], lat: float, lon: float) -> float:
    if len(reports) < 2:
        return 0.0
    distances = [haversine_m(lat, lon, report.lat, report.lon) for report in reports]
    return round(sum(distances) / len(distances), 1)


def dominant(values: Sequence[str], fallback: str) -> str:
    if not values:
        return fallback
    counts = {}
    for value in values:
        if not value or value == "unknown":
            continue
        counts[value] = counts.get(value, 0) + 1
    if not counts:
        return fallback
    return max(counts.items(), key=lambda item: item[1])[0]


def worst_severity(values: Sequence[str]) -> str:
    # safety-biased: one "blocked" beats three "open"
    if not values:
        return "moderate"
    return max(values, key=lambda value: taxonomy.SEVERITY_RANK.get(value, 2))


def worst_access(values: Sequence[str]) -> str:
    order = {"unknown": 0, "open": 1, "limited": 2, "blocked": 3}
    known = [value for value in values if value in order and value != "unknown"]
    if not known:
        return "unknown"
    return max(known, key=lambda value: order[value])


def _humanize_hours(hours: float) -> str:
    minutes = hours * 60.0
    if minutes < 1:
        return "moments"
    if minutes < 60:
        return "{0:.0f} min".format(minutes)
    if hours < 24:
        return "{0:.1f}h".format(hours)
    return "{0:.0f}d".format(hours / 24.0)
