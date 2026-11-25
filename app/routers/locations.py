import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/locations", tags=["USA Locations"])

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "us_locations.json"

with _DATA_FILE.open("r", encoding="utf-8") as f:
    _US_LOCATIONS: dict = json.load(f)

_STATES_BY_NAME = {v["name"].lower(): k for k, v in _US_LOCATIONS.items()}
_STATES_LIST = [
    {
        "code": item["code"],
        "name": item["name"],
        "city_count": len(item["cities"]),
    }
    for item in sorted(_US_LOCATIONS.values(), key=lambda x: x["name"])
]


def resolve_us_state(state_query: str) -> Optional[dict]:
    """Resolve a US state entry by ISO code (e.g. 'TX') or full name (e.g. 'Texas')."""
    if not state_query:
        return None
    key = state_query.strip()
    upper = key.upper()
    if upper in _US_LOCATIONS:
        return _US_LOCATIONS[upper]
    code = _STATES_BY_NAME.get(key.lower())
    return _US_LOCATIONS.get(code) if code else None


@router.get("/states")
async def get_us_states():
    """Return all 50 US states + DC with city counts."""
    return {"states": _STATES_LIST, "total": len(_STATES_LIST)}


@router.get("/cities")
async def get_us_cities(
    state: str = Query(..., description="US state code (e.g. TX) or full name (e.g. Texas)"),
    q: Optional[str] = Query(None, description="Optional case-insensitive city search filter"),
):
    """Return all small and large cities/towns for a given US state."""
    entry = resolve_us_state(state)
    if not entry:
        raise HTTPException(status_code=404, detail=f"US state '{state}' not found")

    cities = entry["cities"]
    if q and q.strip():
        needle = q.strip().lower()
        cities = [c for c in cities if needle in c.lower()]

    return {
        "code": entry["code"],
        "name": entry["name"],
        "cities": cities,
        "total": len(cities),
    }


@router.get("/us")
async def get_all_us_locations():
    """Return complete state-to-cities map for all US states (51 states/DC, 16,400+ cities)."""
    return {"states": _US_LOCATIONS, "total_states": len(_US_LOCATIONS)}
