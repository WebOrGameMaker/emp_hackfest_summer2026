from typing import List, Tuple

GAZETTEER: List[Tuple[str, float, float]] = [
    ("4th Ave & Pike St", 47.6103, -122.3359),
    ("3rd Ave & Pine St", 47.6112, -122.3388),
    ("1st Ave & Union St", 47.6077, -122.3392),
    ("2nd Ave & Spring St", 47.6053, -122.3345),
    ("4th Ave & Madison St", 47.6048, -122.3305),
    ("Alaskan Way & Yesler Way", 47.6015, -122.3363),
    ("Pike Place Market", 47.6097, -122.3421),
    ("Westlake Park", 47.6109, -122.3376),
    ("Seattle Central Library", 47.6067, -122.3325),
    ("Benaroya Hall", 47.6083, -122.3369),
    ("5th Ave & Olive Way", 47.6132, -122.3348),
    ("Denny Way & Fairview Ave N", 47.6188, -122.3339),
    ("Denny Way & Westlake Ave N", 47.6183, -122.3395),
    ("Mercer St & Fairview Ave N", 47.6244, -122.3336),
    ("Mercer St & Dexter Ave N", 47.6242, -122.3419),
    ("Westlake Ave N & Thomas St", 47.6205, -122.3403),
    ("9th Ave N & Republican St", 47.6229, -122.3400),
    ("Terry Ave N & Harrison St", 47.6219, -122.3374),
    ("Boren Ave N & Valley St", 47.6259, -122.3373),
    ("Lake Union Park", 47.6275, -122.3363),
    ("Dexter Ave N & Aloha St", 47.6299, -122.3436),
    ("Aurora Ave N & Galer St", 47.6335, -122.3470),
    ("Taylor Ave N & Roy St", 47.6249, -122.3487),
    ("1st Ave N & Mercer St", 47.6247, -122.3555),
    ("Queen Anne Ave N & Roy St", 47.6252, -122.3568),
    ("5th Ave N & Broad St", 47.6215, -122.3494),
    ("Seattle Center", 47.6215, -122.3493),
    ("Space Needle", 47.6205, -122.3493),
    ("Thomas St & 5th Ave N", 47.6199, -122.3496),
    ("Harrison St & 6th Ave N", 47.6212, -122.3510),
    ("Broad St & 9th Ave N", 47.6228, -122.3524),
    ("Elliott Ave W & W Mercer Pl", 47.6262, -122.3620),
    ("Yesler Way & 4th Ave S", 47.6008, -122.3298),
    ("S Jackson St & Occidental Ave S", 47.5995, -122.3327),
    ("Pioneer Square", 47.6019, -122.3340),
    ("Boren Ave & Pike St", 47.6135, -122.3286),
    ("Broadway & E Pine St", 47.6152, -122.3208),
    ("12th Ave & E Madison St", 47.6136, -122.3163),
    ("Rainier Ave S & S Dearborn St", 47.5972, -122.3122),
    ("15th Ave E & E John St", 47.6197, -122.3125),
]


def nearest(lat: float, lon: float) -> str:
    if not GAZETTEER:
        return "{0:.4f}, {1:.4f}".format(lat, lon)
    # one degree of lon is shorter than lat; ~0.67 at seattle
    lon_scale = 0.67
    best_label = GAZETTEER[0][0]
    best_distance = float("inf")
    for label, place_lat, place_lon in GAZETTEER:
        d_lat = lat - place_lat
        d_lon = (lon - place_lon) * lon_scale
        distance = d_lat * d_lat + d_lon * d_lon
        if distance < best_distance:
            best_distance = distance
            best_label = label
    return best_label


def describe(lat: float, lon: float) -> str:
    return "Near {0}".format(nearest(lat, lon))
