"""print what the live demo submission will produce."""

import base64

from backend import config, db, places
from backend.ai.demo import DemoAnalyzer
from backend.models import ReportSubmission

SCENARIO = "fallen-tree-4th-ave"
TEXT = "There is a massive tree down across the road near the intersection."


def main() -> None:
    lat, lon = config.DEMO_PIN
    analyzer = DemoAnalyzer()
    scene = (config.FRONTEND_DIR / "assets" / "scenes" / "{0}.svg".format(SCENARIO)).read_bytes()
    image = "data:image/svg+xml;base64," + base64.b64encode(scene).decode()
    image_name = "demo:{0}".format(SCENARIO)
    analysis = analyzer.analyze(text=TEXT, image_b64=image, image_name=image_name)
    print(
        "ANALYSIS   {0} / {1} / vehicle={2} / pedestrian={3} / {4:.0f}%".format(
            analysis.category, analysis.severity, analysis.vehicle_access,
            analysis.pedestrian_access, analysis.confidence * 100,
        )
    )
    print("\nNEARBY HAZARDS")
    for match in db.find_nearby(analysis.category, lat, lon):
        print(
            "  merge={0:<5} {1:>6.0f}m  n={2:<3} {3:.0f}%  {4}".format(
                str(match.would_merge), match.distance_m, match.report_count,
                match.confidence * 100, match.reason,
            )
        )
    result = db.add_report(
        ReportSubmission(
            lat=lat, lon=lon, text=TEXT, image_b64=image,
            image_name=image_name, reporter="demo.presenter", analysis=analysis,
        ),
        analysis,
        place=places.describe(lat, lon),
    )
    print("\nOUTCOME")
    print("  merged            {0}".format(result.merged))
    print("  reports           {0} -> {1}".format(result.previous_report_count, result.hazard.report_count))
    if result.previous_confidence is not None:
        print(
            "  confidence        {0:.0f}% -> {1:.0f}%".format(
                result.previous_confidence * 100, result.hazard.confidence * 100,
            )
        )
    print("  why               {0}".format(result.merge_explanation))
    breakdown = result.hazard.confidence_breakdown
    if breakdown is not None:
        print("\nCONFIDENCE BREAKDOWN")
        for contribution in breakdown.contributions:
            print(
                "  {0:+.3f}  {1:<38} {2}".format(
                    contribution.logit_delta, contribution.label, contribution.detail[:60],
                )
            )
        if breakdown.capped:
            print("  capped: {0}".format(breakdown.cap_reason))


if __name__ == "__main__":
    main()
