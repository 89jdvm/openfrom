"""The compact who-can-apply code shipped to the browser."""
from tools.build_site_data import w_code
from tools.check_public_safe import MAX_STR
from tools.geo import COUNTRIES, REGIONS
from tools.who_can_apply import open_to


def limited(countries, regions=()):
    return {"scope": "limited", "countries": list(countries), "regions": list(regions), "utc": None}


def opens(code: str, country: str) -> bool:
    """The browser's reading of the code (site/src/geo.ts openTo), without time bands."""
    parts = dict(p.split(":", 1) for p in code.split(";") if ":" in p)
    regions = parts.get("R", "").split(",") if "R" in parts else []
    if "X" in parts:
        hit = country not in parts["X"].split(",")
    else:
        hit = country in parts.get("L", "").split(",")
    return hit or any(country in REGIONS[r] for r in regions)


def test_short_lists_stay_as_they_are():
    assert w_code(limited(["US", "CA"])) == "L:US,CA"


def test_countries_inside_a_listed_region_are_dropped():
    assert w_code(limited(["DE", "KE", "US"], ["EUROPE"])) == "L:KE,US;R:EUROPE"


def test_a_list_naming_most_of_the_world_ships_the_exceptions():
    shut = {"CU", "KP", "IR", "SY", "RU"}
    w = limited([c for c in COUNTRIES if c not in shut])
    code = w_code(w)
    assert code == "X:" + ",".join(c for c in COUNTRIES if c in shut)
    for c in COUNTRIES:
        assert opens(code, c) == (open_to(w, c) == "yes"), c


def test_no_list_breaks_the_guard_limit():
    every = list(COUNTRIES)
    for regions in ([], ["EMEA"], list(REGIONS)):
        covered = set().union(*(REGIONS[r] for r in regions))
        for n in range(len(every) + 1):
            w = limited(every[:n], regions) | {"utc": (-12.0, 14.0)}
            code = w_code(w)
            assert len(code) <= MAX_STR, (regions, n, len(code))
            for c in COUNTRIES:
                assert opens(code, c) == (c in every[:n] or c in covered), (regions, n, c)
