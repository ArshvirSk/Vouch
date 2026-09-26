"""Area activity router — India PRD §5 (ward-scoped civic/vendor discovery).

GET /area/activity — real ward-scoped activity for the home right rail's
"Active in Your Area" panel (and any future map view).

Accepts either:
  ?ward=Bandra West                 — exact (case-insensitive) ward name match
  ?pincode=400050                   — pincode → pilot-ward resolution
  ?lat=19.0596&lng=72.8295&radius_km=2 — geo match on ward centroids

and returns:
  - civic_count / vendor_count (all-time, in area)
  - in_verification_count (+ per-category split) — commitments whose
    evidence window closed and a jury is currently voting
  - commitments[] — id/category/ward/title plus the area centroid the pin
    should plot at (deterministic per-commitment offset so multiple pins in
    one ward don't stack on the same point)

The pilot geography model is ward/pincode-based (PRD §3: "Geography model:
ward/pincode-based, not city-based"), so commitments carry a free-text
`ward` and users a self-declared `ward`. Until per-commitment lat/lng
columns exist, geo queries resolve each commitment's ward through the
WARD_CENTROIDS table below and apply the haversine radius to that.
"""

import hashlib
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.commitment import Commitment, CommitmentCategory, CommitmentStatus

router = APIRouter(prefix="/area", tags=["area"])

# Pilot geography — PRD Phase 1 ward list, now extended to the full Mumbai
# metro spread so seeded commitments can land across the city. Ward name →
# representative centroid + covered pincodes. Keep in sync with the seeding
# script and the frontend's pilot-ward list.
WARD_CENTROIDS: dict[str, dict] = {
    # ── Western suburbs ──────────────────────────────────────────
    "Bandra West":     {"lat": 19.0596, "lng": 72.8295, "pincodes": ["400050"]},
    "Bandra East":     {"lat": 19.0639, "lng": 72.8483, "pincodes": ["400051"]},
    "Khar":            {"lat": 19.0726, "lng": 72.8364, "pincodes": ["400052"]},
    "Santacruz West":  {"lat": 19.0816, "lng": 72.8416, "pincodes": ["400054"]},
    "Vile Parle":      {"lat": 19.1003, "lng": 72.8426, "pincodes": ["400056", "400057"]},
    "Juhu":            {"lat": 19.0968, "lng": 72.8267, "pincodes": ["400049"]},
    "Andheri West":    {"lat": 19.1364, "lng": 72.8296, "pincodes": ["400058"]},
    "Andheri East":    {"lat": 19.1136, "lng": 72.8697, "pincodes": ["400069"]},
    "Jogeshwari":      {"lat": 19.1554, "lng": 72.8518, "pincodes": ["400060"]},
    "Goregaon":        {"lat": 19.1663, "lng": 72.8526, "pincodes": ["400062", "400063"]},
    "Malad":           {"lat": 19.1864, "lng": 72.8493, "pincodes": ["400064", "400067"]},
    "Kandivali":       {"lat": 19.2015, "lng": 72.8526, "pincodes": ["400067"]},
    "Borivali":        {"lat": 19.2307, "lng": 72.8567, "pincodes": ["400066", "400091"]},
    "Dahisar":         {"lat": 19.2519, "lng": 72.8618, "pincodes": ["400068"]},
    # ── Central / South Mumbai ───────────────────────────────────
    "Colaba":          {"lat": 18.9067, "lng": 72.8147, "pincodes": ["400005"]},
    "Fort":            {"lat": 18.9322, "lng": 72.8331, "pincodes": ["400001"]},
    "Marine Lines":    {"lat": 18.9440, "lng": 72.8230, "pincodes": ["400020"]},
    "Girgaon":         {"lat": 18.9517, "lng": 72.8156, "pincodes": ["400006"]},
    "Byculla":         {"lat": 18.9784, "lng": 72.8341, "pincodes": ["400027"]},
    "Worli":           {"lat": 19.0176, "lng": 72.8155, "pincodes": ["400018"]},
    "Lower Parel":     {"lat": 18.9977, "lng": 72.8273, "pincodes": ["400013"]},
    "Dadar":           {"lat": 19.0178, "lng": 72.8478, "pincodes": ["400014", "400028"]},
    "Mahim":           {"lat": 19.0380, "lng": 72.8430, "pincodes": ["400016"]},
    "Sion":            {"lat": 19.0406, "lng": 72.8656, "pincodes": ["400022"]},
    # ── Eastern suburbs ──────────────────────────────────────────
    "Kurla":           {"lat": 19.0728, "lng": 72.8826, "pincodes": ["400070", "400072"]},
    "Ghatkopar":       {"lat": 19.0863, "lng": 72.9081, "pincodes": ["400077"]},
    "Vikhroli":        {"lat": 19.1085, "lng": 72.9362, "pincodes": ["400079"]},
    "Bhandup":         {"lat": 19.1416, "lng": 72.9369, "pincodes": ["400078", "400042"]},
    "Mulund":          {"lat": 19.1726, "lng": 72.9425, "pincodes": ["400080"]},
    "Chembur":         {"lat": 19.0522, "lng": 72.9006, "pincodes": ["400071"]},
    "Powai":           {"lat": 19.1176, "lng": 72.9060, "pincodes": ["400076"]},
    # ── Extended metro ───────────────────────────────────────────
    "Vashi":           {"lat": 19.0771, "lng": 72.9986, "pincodes": ["400703"]},
    "Nerul":           {"lat": 19.0335, "lng": 73.0197, "pincodes": ["400706"]},
    "Thane":           {"lat": 19.2183, "lng": 72.9781, "pincodes": ["400601"]},
}

DEFAULT_RADIUS_KM = 2.0
EARTH_RADIUS_KM = 6371.0


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points, in kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _pin_offset(commitment_id: str) -> tuple[float, float]:
    """Deterministic ±0.004° (~±450 m) jitter per commitment so several
    commitments in one ward plot as separate pins. Pure hash of the id —
    stable across reloads, no extra DB columns."""
    digest = hashlib.sha256(commitment_id.encode()).digest()
    dx = ((digest[0] << 8 | digest[1]) / 65535 - 0.5) * 0.008
    dy = ((digest[2] << 8 | digest[3]) / 65535 - 0.5) * 0.008
    return dx, dy


def _resolve_area(
    ward: str | None,
    pincode: str | None,
    lat: float | None,
    lng: float | None,
) -> tuple[list[str] | None, float | None, float | None, float]:
    """Normalize the three ways of naming an area into (ward filter list,
    center lat, center lng, radius). Returns ward=None to mean "all wards"
    (used when the caller passes lat/lng directly)."""
    if ward:
        wanted = ward.strip()
        matches = [w for w in WARD_CENTROIDS if w.lower() == wanted.lower()]
        if not matches:
            # tolerate "bandra" → "Bandra West"-style partials
            matches = [w for w in WARD_CENTROIDS if wanted.lower() in w.lower()]
        if not matches:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Unknown ward '{ward}'. Supported pilot wards: "
                    + ", ".join(sorted(WARD_CENTROIDS))
                ),
            )
        return matches, None, None, DEFAULT_RADIUS_KM

    if pincode:
        pin = pincode.strip()
        matches = [w for w, v in WARD_CENTROIDS.items() if pin in v["pincodes"]]
        if not matches:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Pincode {pin} is outside the pilot area. Supported: "
                    + ", ".join(
                        f"{w} ({', '.join(v['pincodes'])})"
                        for w, v in sorted(WARD_CENTROIDS.items())
                    )
                ),
            )
        return matches, None, None, DEFAULT_RADIUS_KM

    if lat is not None and lng is not None:
        return None, lat, lng, DEFAULT_RADIUS_KM

    raise HTTPException(
        status_code=422,
        detail="Provide ?ward=…, ?pincode=…, or ?lat=…&lng=… (&radius_km=…)",
    )


@router.get("/activity")
async def get_area_activity(
    ward: str | None = Query(None, description="Ward name, e.g. 'Bandra West'"),
    pincode: str | None = Query(None, description="6-digit pincode, e.g. 400050"),
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    radius_km: float = Query(DEFAULT_RADIUS_KM, gt=0, le=50),
    scale_km: float | None = Query(
        None, gt=0, le=50,
        description="Override the ward-scoped match with a geo radius (km) "
        "centered on the ward centroid — pulls in neighboring wards. "
        "Used by the Nearby map for a wider view than the home panel.",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Ward-scoped activity counts + commitment pins — powers the home
    "Active in Your Area" panel and the Nearby map."""
    area_name: str | None = None
    ward_names, center_lat, center_lng, radius = _resolve_area(ward, pincode, lat, lng)
    if ward_names:
        area_name = ward_names[0]

    if scale_km is not None and ward_names:
        # Wider view: switch to geo mode centered on the ward centroid so
        # commitments from neighboring wards within scale_km are included.
        center = WARD_CENTROIDS[ward_names[0]]
        center_lat, center_lng = center["lat"], center["lng"]
        radius = scale_km
        ward_names = None

    # Base query: commitments that carry location metadata. Counts are
    # all-time (including resolved) so the panel reflects real cumulative
    # activity; the in_verification slice is what's live right now.
    query = select(Commitment).where(
        Commitment.ward.isnot(None),
        Commitment.category.in_([CommitmentCategory.CIVIC, CommitmentCategory.VENDOR]),
    )
    if ward_names is not None:
        # Case-insensitive ward match — ward strings come from free-text input
        query = query.where(
            func.lower(Commitment.ward).in_([w.lower() for w in ward_names])
        )

    rows = list((await db.execute(query)).scalars().all())

    # Geo mode: filter rows by haversine distance from the ward centroid.
    if ward_names is None and center_lat is not None and center_lng is not None:
        geo_rows = []
        for c in rows:
            info = WARD_CENTROIDS.get(c.ward or "")
            if not info:
                continue
            if _haversine_km(center_lat, center_lng, info["lat"], info["lng"]) <= radius:
                geo_rows.append(c)
        rows = geo_rows

    civic = sum(1 for c in rows if c.category == CommitmentCategory.CIVIC)
    vendor = sum(1 for c in rows if c.category == CommitmentCategory.VENDOR)
    in_verification = [c for c in rows if c.status == CommitmentStatus.IN_VERIFICATION]

    pins = []
    for c in rows:
        info = WARD_CENTROIDS.get(c.ward or "")
        if not info:
            continue
        dx, dy = _pin_offset(str(c.id))
        pins.append(
            {
                "id": str(c.id),
                "category": c.category.value,
                "title": c.title,
                "ward": c.ward,
                "status": c.status.value,
                "lat": round(info["lat"] + dy, 6),
                "lng": round(info["lng"] + dx, 6),
            }
        )

    return {
        "area": {
            "ward": area_name or (f"{lat:.4f}, {lng:.4f}" if lat is not None else None),
            "pincodes": (
                [p for w in ward_names for p in WARD_CENTROIDS[w]["pincodes"]]
                if ward_names
                else []
            ),
            "center": {
                "lat": center_lat if center_lat is not None
                else (WARD_CENTROIDS[ward_names[0]]["lat"] if ward_names else None),
                "lng": center_lng if center_lng is not None
                else (WARD_CENTROIDS[ward_names[0]]["lng"] if ward_names else None),
            },
            "radius_km": radius,
        },
        "civic_count": civic,
        "vendor_count": vendor,
        "in_verification_count": len(in_verification),
        "in_verification_civic": sum(
            1 for c in in_verification if c.category == CommitmentCategory.CIVIC
        ),
        "in_verification_vendor": sum(
            1 for c in in_verification if c.category == CommitmentCategory.VENDOR
        ),
        "pins": pins,
    }


@router.get("/wards")
async def list_supported_wards():
    """Pilot ward list with centroids + pincodes — for area pickers/maps."""
    return [
        {"ward": name, "lat": v["lat"], "lng": v["lng"], "pincodes": v["pincodes"]}
        for name, v in sorted(WARD_CENTROIDS.items())
    ]
