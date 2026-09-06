import math
from typing import List, Sequence

from . import config, taxonomy, timeutil
from .models import ConfidenceBreakdown, ConfidenceContribution, Report


def _logit(probability: float) -> float:
    bounded = max(0.02, min(0.98, probability))
    return math.log(bounded / (1.0 - bounded))


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def score(reports: Sequence[Report], category: str, spread_m: float, last_reported_at: str) -> ConfidenceBreakdown:
    if not reports:
        return ConfidenceBreakdown(value=config.CONFIDENCE_FLOOR, base_ai_confidence=0.0, contributions=[])
    rules = taxonomy.get(category)
    contributions: List[ConfidenceContribution] = []
    base = sum(report.analysis.confidence for report in reports) / len(reports)
    base_delta = config.BASE_DAMPING * _logit(base)
    total = base_delta
    contributions.append(ConfidenceContribution(
        key="classification",
        label="Classification {0:.0f}%".format(base * 100),
        detail=(
            "Average classification confidence across {0} report(s). "
            "One confident reading is still only one observation.".format(len(reports))
        ),
        logit_delta=round(base_delta, 4),
    ))

    # count distinct reporters, not submissions
    reporters = {report.reporter.strip().lower() for report in reports}
    independent = max(1, len(reporters))
    duplicates = len(reports) - independent
    if independent > 1:
        bonus = 0.0
        for index in range(independent - 1):
            bonus += config.CORROBORATION_BONUS * (config.CORROBORATION_DECAY ** index)
        total += bonus
        contributions.append(ConfidenceContribution(
            key="corroboration",
            label="{0} reports from different people".format(independent),
            detail="{0} people reported the same hazard. Each additional person adds less than the one before.".format(independent),
            logit_delta=round(bonus, 4),
        ))
    else:
        contributions.append(ConfidenceContribution(
            key="corroboration",
            label="Single reporter",
            detail="Only one person has reported this so far.",
            logit_delta=0.0,
        ))

    if duplicates > 0:
        contributions.append(ConfidenceContribution(
            key="duplicates",
            label="{0} repeat report(s) discounted".format(duplicates),
            detail="Multiple reports from the same person count once.",
            logit_delta=0.0,
        ))

    photos = sum(1 for report in reports if report.has_photo)
    if photos:
        bonus = config.PHOTO_BONUS + config.PHOTO_EXTRA_BONUS * min(2, photos - 1)
        total += bonus
        contributions.append(ConfidenceContribution(
            key="photo",
            label="Photo evidence" if photos == 1 else "{0} photos".format(photos),
            detail="A photo is harder to fabricate than a description and can be reviewed later.",
            logit_delta=round(bonus, 4),
        ))

    if len(reports) > 1:
        tightness = max(0.0, 1.0 - (spread_m / rules.cluster_radius_m))
        bonus = config.TIGHT_CLUSTER_BONUS * tightness
        total += bonus
        contributions.append(ConfidenceContribution(
            key="proximity",
            label="Reports within {0:.0f}m of each other".format(spread_m),
            detail=(
                "Average distance from the hazard center, against a {0:.0f}m "
                "clustering radius for {1}.".format(rules.cluster_radius_m, rules.label.lower())
            ),
            logit_delta=round(bonus, 4),
        ))

    if len(reports) > 1:
        agreement = _attribute_agreement(reports)
        if agreement >= 0.75:
            bonus = config.AGREEMENT_BONUS * agreement
            total += bonus
            contributions.append(ConfidenceContribution(
                key="agreement",
                label="Reports describe it consistently",
                detail="{0:.0f}% agreement on severity and access impact.".format(agreement * 100),
                logit_delta=round(bonus, 4),
            ))
        else:
            penalty = config.DISAGREEMENT_PENALTY * (1.0 - agreement)
            total -= penalty
            contributions.append(ConfidenceContribution(
                key="agreement",
                label="Reports describe it differently",
                detail=(
                    "Only {0:.0f}% agreement on severity and access impact, "
                    "so these may not be the same hazard.".format(agreement * 100)
                ),
                logit_delta=round(-penalty, 4),
            ))

    age_hours = max(0.0, timeutil.hours_since(last_reported_at))
    half_life = max(1.0, rules.cluster_window_hours)
    decay = config.RECENCY_MAX_PENALTY * (1.0 - 2.0 ** (-age_hours / half_life))
    if decay > 0.01:
        total -= decay
        contributions.append(ConfidenceContribution(
            key="recency",
            label="Last reported {0} ago".format(_ago(age_hours)),
            detail=(
                "Confidence decays with a {0:.0f}h half-life for {1}, "
                "since it may already have been cleared.".format(half_life, rules.label.lower())
            ),
            logit_delta=round(-decay, 4),
        ))

    value = _sigmoid(total)
    capped = False
    cap_reason = ""
    if independent < 2 and value > config.SINGLE_REPORT_CEILING:
        value = config.SINGLE_REPORT_CEILING
        capped = True
        cap_reason = (
            "Capped at {0:.0f}% because a single report cannot score higher than that, "
            "even if the reading is very confident.".format(config.SINGLE_REPORT_CEILING * 100)
        )
    elif value > config.CONFIDENCE_CEILING:
        value = config.CONFIDENCE_CEILING
        capped = True
        cap_reason = (
            "Capped at {0:.0f}%. More reports raise confidence; they do not verify the hazard.".format(
                config.CONFIDENCE_CEILING * 100
            )
        )
    value = max(config.CONFIDENCE_FLOOR, value)
    return ConfidenceBreakdown(
        value=round(value, 4),
        base_ai_confidence=round(base, 4),
        contributions=contributions,
        capped=capped,
        cap_reason=cap_reason,
    )


def _attribute_agreement(reports: Sequence[Report]) -> float:
    fields = ("severity", "vehicle_access")
    ratios: List[float] = []
    for field_name in fields:
        values = [getattr(report.analysis, field_name) for report in reports]
        values = [value for value in values if value and value != "unknown"]
        if len(values) < 2:
            continue
        counts = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        ratios.append(max(counts.values()) / float(len(values)))
    if not ratios:
        return 1.0
    return sum(ratios) / len(ratios)


def _ago(hours: float) -> str:
    minutes = hours * 60.0
    if minutes < 2:
        return "moments"
    if minutes < 60:
        return "{0:.0f} minutes".format(minutes)
    if hours < 24:
        return "{0:.0f} hours".format(hours)
    return "{0:.0f} days".format(hours / 24.0)
