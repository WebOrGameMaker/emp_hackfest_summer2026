from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

SEVERITY_LEVELS = ("low", "moderate", "high")
SEVERITY_RANK = {"low": 1, "moderate": 2, "high": 3}

ACCESS_LEVELS = ("open", "limited", "blocked", "unknown")

LOCATION_TYPES = (
    "roadway",
    "intersection",
    "sidewalk",
    "highway",
    "park",
    "public_space",
    "unknown",
)


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    icon: str
    blurb: str
    cluster_radius_m: float
    cluster_window_hours: float
    terms: Dict[str, float] = field(default_factory=dict)
    default_severity: str = "moderate"
    default_location_type: str = "roadway"
    implies_obstruction: bool = False
    # "my cat is stuck in a tree" should not become a road hazard
    negative_terms: Dict[str, float] = field(default_factory=dict)


CATEGORIES: Tuple[Category, ...] = (
    Category(
        key="fallen_tree",
        label="Fallen Tree",
        icon="\U0001f333",
        blurb="Trees or large branches blocking a road or path.",
        cluster_radius_m=60.0,
        cluster_window_hours=6.0,
        default_severity="high",
        default_location_type="roadway",
        implies_obstruction=True,
        terms={
            "fallen tree": 5.0,
            "tree down": 5.0,
            "tree fell": 5.0,
            "downed tree": 5.0,
            "tree is down": 5.0,
            "uprooted": 3.5,
            "tree": 3.0,
            "trunk": 2.5,
            "branch": 2.5,
            "limb": 2.2,
            "foliage": 1.5,
        },
        negative_terms={
            "cat": 3.5,
            "kitten": 3.5,
            "squirrel": 3.5,
            "bird": 3.0,
            "kite": 3.0,
            "climbing": 2.5,
            "planting": 3.0,
            "trimming": 3.0,
            "tree service": 4.0,
            "christmas": 4.0,
        },
    ),
    Category(
        key="road_obstruction",
        label="Road Obstruction",
        icon="\U0001f6a7",
        blurb="Debris, stalled vehicles, or objects blocking the way.",
        cluster_radius_m=60.0,
        cluster_window_hours=6.0,
        default_severity="moderate",
        default_location_type="roadway",
        implies_obstruction=True,
        terms={
            "road obstruction": 5.0,
            "debris": 3.2,
            "stalled": 3.0,
            "obstruction": 3.0,
            "barrier": 2.4,
            "mattress": 2.4,
            "construction": 2.2,
            "spill": 2.2,
            "couch": 2.0,
            "cone": 1.6,
            "in the road": 1.6,
            "obstructing": 2.4,
        },
    ),
    Category(
        key="flooding",
        label="Flooding",
        icon="\U0001f4a7",
        blurb="Standing water covering a street or underpass.",
        cluster_radius_m=150.0,
        cluster_window_hours=12.0,
        default_severity="high",
        default_location_type="roadway",
        implies_obstruction=True,
        terms={
            "flooding": 5.0,
            "flooded": 5.0,
            "flood": 4.6,
            "standing water": 4.6,
            "high water": 4.2,
            "water main": 4.0,
            "submerged": 4.0,
            "inundated": 4.0,
            "overflow": 3.0,
            "storm drain": 3.0,
            "water": 2.4,
            "puddle": 2.0,
        },
        negative_terms={
            "drinking water": 3.0,
            "water bottle": 3.0,
            "sprinkler": 2.0,
        },
    ),
    Category(
        key="traffic_signal",
        label="Broken Traffic Signal",
        icon="\U0001f6a6",
        blurb="A traffic signal that is dark, flashing, or not working.",
        cluster_radius_m=40.0,
        cluster_window_hours=24.0,
        default_severity="high",
        default_location_type="intersection",
        terms={
            "traffic light": 5.0,
            "traffic signal": 5.0,
            "stoplight": 5.0,
            "stop light": 5.0,
            "signal is out": 4.6,
            "light is out": 3.4,
            "dark signal": 4.0,
            "not working": 2.0,
            "signal": 2.4,
            "flashing": 2.4,
            "intersection": 1.2,
        },
    ),
    Category(
        key="pavement_damage",
        label="Road Damage",
        icon="\U0001f573",
        blurb="Potholes, sinkholes, or failing pavement.",
        cluster_radius_m=30.0,
        cluster_window_hours=24.0,
        default_severity="moderate",
        default_location_type="roadway",
        terms={
            "pothole": 5.0,
            "sinkhole": 4.8,
            "road damage": 4.2,
            "pavement": 3.0,
            "buckled": 3.0,
            "asphalt": 2.6,
            "crumbling": 2.6,
            "manhole": 2.5,
            "crack": 2.4,
            "rut": 1.8,
        },
    ),
    Category(
        key="fire_smoke",
        label="Fire / Smoke",
        icon="\U0001f525",
        blurb="Active fire, smoke, or smoldering material.",
        cluster_radius_m=200.0,
        cluster_window_hours=2.0,
        default_severity="high",
        default_location_type="public_space",
        terms={
            "fire": 4.8,
            "flames": 5.0,
            "smoke": 4.4,
            "blaze": 4.4,
            "smoldering": 4.0,
            "burning": 3.8,
            "ember": 3.0,
        },
        negative_terms={
            "fire hydrant": 4.0,
            "fire station": 4.0,
            "fire lane": 3.0,
            "campfire": 2.5,
            "fireworks": 2.0,
            "no smoking": 3.0,
        },
    ),
    Category(
        key="streetlight",
        label="Broken Streetlight",
        icon="\U0001f4a1",
        blurb="A streetlight that is out or damaged.",
        cluster_radius_m=25.0,
        cluster_window_hours=48.0,
        default_severity="low",
        default_location_type="sidewalk",
        terms={
            "streetlight": 5.0,
            "street light": 5.0,
            "street lamp": 4.6,
            "lamp post": 4.0,
            "lamppost": 4.0,
            "no lighting": 3.2,
            "dark street": 3.0,
            "light out": 3.0,
            "burnt out": 2.6,
            "unlit": 3.0,
        },
    ),
    Category(
        key="other",
        label="Other Hazard",
        icon="\u26a0\ufe0f",
        blurb="A public-safety concern that does not fit the types above.",
        cluster_radius_m=50.0,
        cluster_window_hours=6.0,
        default_severity="moderate",
        default_location_type="public_space",
        terms={
            "hazard": 2.0,
            "dangerous": 1.6,
            "unsafe": 1.6,
        },
    ),
)

BY_KEY: Dict[str, Category] = {c.key: c for c in CATEGORIES}
FALLBACK_CATEGORY = "other"


def get(key: Optional[str]) -> Category:
    return BY_KEY.get(key or "", BY_KEY[FALLBACK_CATEGORY])


def category_keys() -> List[str]:
    return [c.key for c in CATEGORIES]


# attribute cues for the demo analyzer

SEVERITY_CUES: Dict[str, float] = {
    "massive": 1.0,
    "huge": 1.0,
    "enormous": 1.0,
    "giant": 1.0,
    "severe": 1.0,
    "impassable": 1.0,
    "completely blocked": 1.0,
    "completely blocking": 1.0,
    "all lanes": 1.0,
    "both lanes": 1.0,
    "emergency": 1.0,
    "dangerous": 0.6,
    "major": 0.6,
    "large": 0.6,
    "deep": 0.6,
    "big": 0.4,
    "spreading": 0.6,
    "minor": -1.0,
    "small": -0.8,
    "slight": -0.8,
    "tiny": -1.0,
    "little": -0.6,
    "minimal": -1.0,
    "partially": -0.4,
}

VEHICLE_CUES: Dict[str, str] = {
    "road closed": "blocked",
    "completely blocked": "blocked",
    "completely blocking": "blocked",
    "blocking the road": "blocked",
    "blocking both": "blocked",
    "both lanes": "blocked",
    "all lanes": "blocked",
    "impassable": "blocked",
    "cannot drive": "blocked",
    "can't drive": "blocked",
    "cars cannot": "blocked",
    "cars can't": "blocked",
    "no cars": "blocked",
    "blocking traffic": "blocked",
    "one lane": "limited",
    "single lane": "limited",
    "squeeze by": "limited",
    "squeeze past": "limited",
    "narrowed": "limited",
    "traffic is slow": "limited",
    "partially blocking": "limited",
    "sidewalk only": "open",
}

PEDESTRIAN_CUES: Dict[str, str] = {
    "sidewalk is blocked": "blocked",
    "sidewalk blocked": "blocked",
    "blocking the sidewalk": "blocked",
    "cannot walk": "blocked",
    "can't walk": "blocked",
    "no way around": "blocked",
    "walking in the street": "limited",
    "walk around": "limited",
    "step over": "limited",
    "climb over": "limited",
    "squeeze": "limited",
    "wheelchair": "limited",
}

LOCATION_CUES: Dict[str, str] = {
    "intersection": "intersection",
    "corner of": "intersection",
    "crosswalk": "intersection",
    "sidewalk": "sidewalk",
    "walkway": "sidewalk",
    "footpath": "sidewalk",
    "curb": "sidewalk",
    "highway": "highway",
    "freeway": "highway",
    "on-ramp": "highway",
    "off-ramp": "highway",
    "i-5": "highway",
    "park": "park",
    "trail": "park",
    "greenway": "park",
    "plaza": "public_space",
    "roadway": "roadway",
    "road": "roadway",
    "street": "roadway",
    "avenue": "roadway",
    "boulevard": "roadway",
    "lane": "roadway",
}

# avoid matching the bare word "block" (as in "on my block")
OBSTRUCTION_CUES: Tuple[str, ...] = (
    "blocking",
    "blocked",
    "blocks the",
    "obstruct",
    "obstructing",
    "obstructed",
    "in the way",
    "impassable",
    "road closed",
    "street closed",
    "lane closed",
    "across the road",
    "across the street",
    "across both",
    "cannot get through",
    "can't get through",
)


def clamp_severity(rank: float) -> str:
    rounded = int(round(max(1.0, min(3.0, rank))))
    for label, value in SEVERITY_RANK.items():
        if value == rounded:
            return label
    return "moderate"
