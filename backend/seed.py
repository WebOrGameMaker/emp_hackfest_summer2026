import base64
from dataclasses import dataclass
from typing import Dict, List, Optional

from . import config, db, places, timeutil
from .ai.demo import DemoAnalyzer
from .models import ReportSubmission

SCENES_DIR = config.FRONTEND_DIR / "assets" / "scenes"


@dataclass(frozen=True)
class SeedReport:
    text: str
    lat: float
    lon: float
    reporter: str
    minutes_ago: float
    scenario: Optional[str] = None


# denny way & fairview — twelve wordings, one hazard
HERO_FALLEN_TREE: List[SeedReport] = [
    SeedReport(
        "Huge tree came down across Denny, completely blocking both lanes.",
        47.61879, -122.33392, "m.okafor", 95, "fallen-tree-4th-ave",
    ),
    SeedReport(
        "Tree down blocking traffic", 47.61884, -122.33385, "rjt", 88,
    ),
    SeedReport(
        "Massive branch blocking traffic near Fairview",
        47.61871, -122.33404, "sea_commuter", 81,
    ),
    SeedReport(
        "A huge tree fell near the intersection, cars can't get through.",
        47.61888, -122.33379, "dana.whitfield", 74,
    ),
    SeedReport(
        "Road blocked by a fallen tree", 47.61875, -122.33398, "kp_2019", 66,
    ),
    SeedReport(
        "Big tree across the road, impassable.",
        47.61882, -122.33388, "t.nakamura", 57, "fallen-tree-4th-ave",
    ),
    SeedReport(
        "There's a tree trunk in the roadway and people are turning around.",
        47.61868, -122.33409, "gwen.alvarez", 44,
    ),
    SeedReport(
        "Downed tree at Denny and Fairview. Sidewalk is blocked too.",
        47.61891, -122.33374, "northlake.neighbor", 33,
    ),
    # same reporter as report 2 — counted once
    SeedReport(
        "still not cleared, tree is down blocking the road",
        47.61886, -122.33383, "rjt", 24,
    ),
    SeedReport(
        "Uprooted tree lying across both lanes of Denny Way.",
        47.61877, -122.33395, "c.iyer", 16, "fallen-tree-4th-ave",
    ),
    SeedReport(
        "Tree is down, cannot get through.", 47.61873, -122.33401, "bwm", 9,
    ),
    SeedReport(
        "Large limb and trunk obstructing the roadway.",
        47.61885, -122.33390, "avery.l", 3,
    ),
]

# near DEMO_PIN so the live demo submission joins this cluster
DEMO_TARGET_FALLEN_TREE: List[SeedReport] = [
    SeedReport(
        "Tree down across 5th Ave N, blocking traffic.",
        47.62051, -122.34941, "j.moreau", 41,
    ),
    SeedReport(
        "Massive branch blocking traffic by the Space Needle",
        47.62064, -122.34958, "hstreetwalker", 27,
    ),
    SeedReport(
        "A huge tree fell near the intersection.",
        47.62045, -122.34936, "priya.r", 12,
    ),
]

# same type as the hero cluster but ~200m away, outside the 60m radius
NEAR_MISS_FALLEN_TREE: List[SeedReport] = [
    SeedReport(
        "Large branch down on the sidewalk, have to walk around it.",
        47.62060, -122.33390, "l.fontaine", 52,
    ),
]

OTHER_CLUSTERS: List[List[SeedReport]] = [
    # flooding under mercer
    [
        SeedReport(
            "Standing water flooding both lanes under the Mercer underpass.",
            47.62441, -122.33368, "d.ferraro", 130, "flooded-underpass",
        ),
        SeedReport(
            "Mercer is flooded and the water looks deep.",
            47.62449, -122.33355, "sound_transit_rider", 118,
        ),
        SeedReport(
            "Deep standing water on Mercer, cars are stalling out.",
            47.62435, -122.33377, "h.oyelaran", 96,
        ),
        SeedReport("flooded road", 47.62446, -122.33362, "anon_slu", 71),
        SeedReport(
            "Water main break, roadway completely submerged.",
            47.62438, -122.33371, "w.castellanos", 38, "flooded-underpass",
        ),
    ],
    # broken signal at 4th & pike
    [
        SeedReport(
            "The stoplight at 4th and Pike is completely dark.",
            47.61031, -122.33591, "e.brennan", 152, "signal-dark",
        ),
        SeedReport(
            "Traffic signal is out at the intersection and nobody knows who "
            "goes first.",
            47.61024, -122.33602, "marisol.q", 47,
        ),
    ],
    # debris in pioneer square
    [
        SeedReport(
            "Construction debris and a barrier sitting in the right lane.",
            47.60192, -122.33404, "o.lindqvist", 205, "debris-lane",
        ),
        SeedReport(
            "Debris obstructing the road.", 47.60186, -122.33412, "tf_walks", 176,
        ),
        SeedReport(
            "There's a mattress in the road blocking traffic.",
            47.60198, -122.33396, "s.abadi", 121,
        ),
        SeedReport(
            "Barrier knocked over, debris everywhere, one lane only.",
            47.60189, -122.33408, "j.kowalczyk", 58,
        ),
    ],
    # pavement on broadway
    [
        SeedReport(
            "Deep pothole in the travel lane on Broadway.",
            47.61521, -122.32081, "capitolhill.rider", 320, "pothole-cluster",
        ),
        SeedReport(
            "Big pothole here, cars are swerving around it.",
            47.61515, -122.32089, "n.desjardins", 244,
        ),
        SeedReport(
            "The pavement is crumbling and buckled along this stretch.",
            47.61527, -122.32074, "r.mbeki", 92,
        ),
    ],
    # two dark streetlights on the same block
    [
        SeedReport(
            "Streetlight is out on my block and it's really dark.",
            47.61968, -122.31251, "k.holloway", 410, "streetlight-out",
        ),
        SeedReport(
            "Street lamp burnt out, the sidewalk is unlit.",
            47.61974, -122.31244, "v.santoro", 198,
        ),
    ],
    # singles — most real reports arrive alone
    [
        SeedReport(
            "Street light out near the library walkway.",
            47.60671, -122.33248, "a.thibault", 275,
        )
    ],
    [
        SeedReport(
            "No lighting along this stretch of Dexter, feels unsafe walking "
            "home.",
            47.62991, -122.34361, "cyclist_dex", 505,
        )
    ],
    [
        SeedReport(
            "Small pothole on the street.", 47.60081, -122.32976, "b.osei", 362,
        )
    ],
    [
        SeedReport(
            "Smoke rising behind the building, no flames visible from here.",
            47.61352, -122.32861, "f.dominguez", 21, "smoke-column",
        )
    ],
    [
        SeedReport(
            "Storm drain overflow, puddle across the whole sidewalk.",
            47.60972, -122.34211, "market_regular", 84,
        )
    ],
    [
        SeedReport(
            "Stalled vehicle obstructing the right lane.",
            47.60151, -122.33632, "waterfront.watch", 35,
        )
    ],
    [
        SeedReport(
            "Traffic light flashing red at Broadway and Pine.",
            47.61519, -122.32079, "g.petrov", 63,
        )
    ],
    [
        SeedReport(
            "Broken glass all over the sidewalk, pretty dangerous.",
            47.61094, -122.33761, "westlake.daily", 143,
        )
    ],
]


def _all_reports() -> List[SeedReport]:
    reports: List[SeedReport] = []
    reports.extend(HERO_FALLEN_TREE)
    reports.extend(DEMO_TARGET_FALLEN_TREE)
    reports.extend(NEAR_MISS_FALLEN_TREE)
    for cluster in OTHER_CLUSTERS:
        reports.extend(cluster)
    return sorted(reports, key=lambda item: -item.minutes_ago)


_scene_cache: Dict[str, Optional[str]] = {}


def _scene_data_url(scenario: Optional[str]) -> Optional[str]:
    if not scenario:
        return None
    if scenario in _scene_cache:
        return _scene_cache[scenario]

    path = SCENES_DIR / "{0}.svg".format(scenario)
    value: Optional[str] = None
    if path.is_file():
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        value = "data:image/svg+xml;base64,{0}".format(encoded)
    _scene_cache[scenario] = value
    return value


def seed(force: bool = False) -> int:
    hazard_count, _ = db.counts()
    if hazard_count and not force:
        return 0

    analyzer = DemoAnalyzer()
    inserted = 0

    for item in _all_reports():
        image = _scene_data_url(item.scenario)
        image_name = "demo:{0}".format(item.scenario) if item.scenario else None
        analysis = analyzer.analyze(text=item.text, image_b64=image, image_name=image_name)
        db.add_report(
            ReportSubmission(
                lat=item.lat, lon=item.lon, text=item.text,
                image_b64=image, image_name=image_name, reporter=item.reporter,
            ),
            analysis,
            created_at=timeutil.ago(minutes=item.minutes_ago),
            place=places.describe(item.lat, item.lon),
        )
        inserted += 1

    return inserted


def reseed() -> int:
    db.reset()
    return seed(force=True)


if __name__ == "__main__":
    if db.ensure_healthy():
        print("Database file was unreadable and has been rebuilt.")
    count = seed()
    hazards, reports = db.counts()
    if count:
        print(
            "Seeded {0} reports, which clustered into {1} hazards.".format(
                count, hazards
            )
        )
    else:
        print(
            "Database already has {0} hazards from {1} reports; left "
            "untouched.".format(hazards, reports)
        )
