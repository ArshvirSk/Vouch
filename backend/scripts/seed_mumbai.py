"""Seed realistic Mumbai-wide activity into the Vouch database.

City-scale version: ~45 commitments (22 civic / 23 vendor) spread across
~31 real Mumbai areas — western suburbs, central/south, eastern suburbs
and the extended metro (Navi Mumbai, Thane) — so the map is populated at
city zoom, not bunched around one ward.

Idempotent: keyed on the "vouch_seed" handle prefix — a re-run removes the
previous seed's rows (users, commitments, evidence, votes, reputation
events, notifications) before inserting fresh ones. Existing real users
(e.g. your own account) are untouched.

Run: cd backend && python -m scripts.seed_mumbai
"""

import asyncio
import hashlib
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, ".")

from sqlalchemy import delete, select

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.commitment import Commitment, CommitmentJuror, CommitmentCategory, CommitmentStatus
from app.models.evidence import Evidence, EvidenceType
from app.models.vote import Vote, VoteChoice
from app.models.reputation import ReputationEvent, ReputationReason
from app.models.notification import Notification

NOW = datetime.utcnow()
AUTHOR_MET = 5.0
AUTHOR_BROKEN = -5.0
JUROR_ACCURATE = 2.0
JUROR_INACCURATE = -2.0

rng = random.Random(104)

# handle → (email, home area, reputation base, streak)
PEOPLE = {
    "meera.k":   ("meera.kulkarni@example.in",  "Bandra West",   61.0, 3),
    "rohan.s":   ("rohan.shetty@example.in",    "Bandra West",   48.5, 2),
    "farida.a":  ("farida.ansari@example.in",   "Bandra West",   72.0, 5),
    "jatin.p":   ("jatin.patel@example.in",     "Andheri West",  35.0, 1),
    "sana.q":    ("sana.qureshi@example.in",    "Bandra West",   55.5, 2),
    "vikram.d":  ("vikram.desai@example.in",    "Worli",         66.0, 4),
    "leena.m":   ("leena.mehta@example.in",     "Khar",          42.0, 2),
    "arjun.t":   ("arjun.thakur@example.in",    "Ghatkopar",     39.5, 1),
    "priya.n":   ("priya.nair@example.in",      "Chembur",       58.0, 3),
    "kabir.j":   ("kabir.joshi@example.in",     "Powai",         51.0, 2),
    "neha.r":    ("neha.rane@example.in",       "Dadar",         44.0, 2),
    "salim.b":   ("salim.bhai@example.in",      "Borivali",      47.0, 3),
    "deepa.v":   ("deepa.ven@example.in",       "Vashi",         53.0, 2),
    "omkar.g":   ("omkar.gawde@example.in",     "Thane",         40.0, 1),
    "ruchi.s":   ("ruchi.shah@example.in",      "Malad",         49.5, 2),
    "amol.k":    ("amol.kadam@example.in",      "Kurla",         38.0, 1),
    "tasneem.h": ("tasneem.h@example.in",       "Colaba",        62.0, 4),
    "gaurav.l":  ("gaurav.lad@example.in",      "Mulund",        45.0, 2),
}

# Real anchor coordinates per area (backend WARD_CENTROIDS mirrors this).
AREA_COORDS = {
    # Western suburbs
    "Bandra West": (19.0596, 72.8295), "Bandra East": (19.0639, 72.8483),
    "Khar": (19.0726, 72.8364), "Santacruz West": (19.0816, 72.8416),
    "Vile Parle": (19.1003, 72.8426), "Juhu": (19.0968, 72.8267),
    "Andheri West": (19.1364, 72.8296), "Andheri East": (19.1136, 72.8697),
    "Jogeshwari": (19.1554, 72.8518), "Goregaon": (19.1663, 72.8526),
    "Malad": (19.1864, 72.8493), "Kandivali": (19.2015, 72.8526),
    "Borivali": (19.2307, 72.8567), "Dahisar": (19.2519, 72.8618),
    # Central / South
    "Colaba": (18.9067, 72.8147), "Fort": (18.9322, 72.8331),
    "Marine Lines": (18.9440, 72.8230), "Girgaon": (18.9517, 72.8156),
    "Byculla": (18.9784, 72.8341), "Worli": (19.0176, 72.8155),
    "Lower Parel": (18.9977, 72.8273), "Dadar": (19.0178, 72.8478),
    "Mahim": (19.0380, 72.8430), "Sion": (19.0406, 72.8656),
    # Eastern suburbs
    "Kurla": (19.0728, 72.8826), "Ghatkopar": (19.0863, 72.9081),
    "Vikhroli": (19.1085, 72.9362), "Bhandup": (19.1416, 72.9369),
    "Mulund": (19.1726, 72.9425), "Chembur": (19.0522, 72.9006),
    "Powai": (19.1176, 72.9060),
    # Extended metro
    "Vashi": (19.0771, 72.9986), "Nerul": (19.0335, 73.0197),
    "Thane": (19.2183, 72.9781),
}

# Rotating invented civic figures — none are real politicians.
CIVIC_OFFICIALS = [
    ("Corporator Asha Fernandes", "Ward Corporator"),
    ("Corporator Imran Shaikh", "Ward Corporator"),
    ("Corporator Deepa Rane", "Ward Corporator"),
    ("Corporator Mahesh Salvi", "Ward Corporator"),
    ("Corporator Leena D'Souza", "Ward Corporator"),
    ("MLA Prakash Bhosale", "Legislator"),
    ("MLA Sunita Kamble", "Legislator"),
]

# Status mix — every filter tab gets multiple entries.
CIVIC_STATUSES = (
    [CommitmentStatus.OPEN] * 6
    + [CommitmentStatus.EVIDENCE_SUBMITTED] * 5
    + [CommitmentStatus.IN_VERIFICATION] * 4
    + [CommitmentStatus.MET] * 4
    + [CommitmentStatus.BROKEN] * 2
    + [CommitmentStatus.DISPUTED] * 1
)
VENDOR_STATUSES = (
    [CommitmentStatus.OPEN] * 6
    + [CommitmentStatus.EVIDENCE_SUBMITTED] * 5
    + [CommitmentStatus.IN_VERIFICATION] * 4
    + [CommitmentStatus.MET] * 5
    + [CommitmentStatus.BROKEN] * 2
    + [CommitmentStatus.DISPUTED] * 1
)

# ── Civic promise templates (area, promise-type, title bits) ─────────
# Types: road, drain, garbage, lights, water, park, footpath
CIVIC_TEMPLATES = [
    # (area, type, title, condition core)
    ("Bandra West", "road", "Resurface Linking Road (Ward 104)",
     "Carriageway resurfaced end-to-end and verified via geotagged photos of the completed stretch, ward engineering report, and at least 3 resident photo submissions."),
    ("Bandra East", "garbage", "Double garbage clearance frequency — Bharat Nagar (Ward 103)",
     "Twice-daily collection verifiable via ward supervisor's NFC-tapped pickup log and dated resident photos over any consecutive 14-day window."),
    ("Khar", "drain", "Desilt Khar subway drains before monsoon (Ward 101)",
     "All eight drain chambers along the subway desilted, verified via before/after photos of each chamber plus the contractor's silt-removal receipts."),
    ("Santacruz West", "lights", "Repair 14 dead streetlights on SV Road stretch (Ward 100)",
     "All 14 streetlights repaired and glowing after dark, verified via two geotagged night photos from opposite ends of the stretch."),
    ("Vile Parle", "park", "Renovate the Vaishnodevi garden walking track (Ward 60)",
     "Walking track relaid and gym equipment refurbished, verified via dated photos of each installed item against the sanctioned equipment list."),
    ("Juhu", "footpath", "Clear beach-access footpath encroachments (Ward 63)",
     "The 400m beach-access footpath cleared of permanent encroachments, verified via geotagged photos at four fixed points plus ward enforcement notice copies."),
    ("Andheri West", "road", "Fix pothole cluster on Lokhandwala back road (Ward 56)",
     "All potholes in the marked cluster filled and level-tested, verified via geotagged photos of each site plus the ward engineer's sign-off sheet."),
    ("Andheri East", "drain", "Widen the Marol nallah culvert (Ward 55)",
     "Culvert widened to the sanctioned 3m span, verified via engineering drawing match and geotagged construction-progress photos."),
    ("Jogeshwari", "water", "Restore morning water pressure on Majaswadi (Ward 46)",
     "Morning supply restored to 3-bar pressure for the full 6–9am window, verified via resident pressure-gauge readings across 10 households."),
    ("Goregaon", "park", "Revive the Goregaon tree-park walking plaza (Ward 41)",
     "Plaza relaid with paver blocks and lighting restored, verified via dated night photos and the ward works-completion certificate."),
    ("Malad", "garbage", "Fix missed collections in Malvani (Ward 35)",
     "Zero missed collections over any 21-day window, verified via the contractor's GPS-tracked pickup log plus a resident-complaint register showing none filed."),
    ("Kandivali", "lights", "Light the Kandivali station east footbridge (Ward 32)",
     "All 12 footbridge lights working, verified via night geotagged photos from both stairwells plus the electrical inspection report."),
    ("Borivali", "drain", "Clear cyclone debris from Magathane drains (Ward 29)",
     "All marked drain chambers cleared, verified via before/after geotagged photos and silt-disposal receipts from the designated ground."),
    ("Dahisar", "road", "Concrete-plate the Dahisar riverbank road (Ward 1)",
     "Full stretch plated and level-tested, verified via geotagged photos every 50m plus the ward engineer's completion note."),
    ("Colaba", "footpath", "Decongest the Colaba Causeway pavements (Ward 9)",
     "Hawking-zone markings installed and 90% of the marked footpath clear, verified via geotagged photos at six fixed points over one week."),
    ("Fort", "lights", "Restore heritage lanterns on Rampart Row (Ward 8)",
     "All 9 heritage lanterns restored and lit after dusk, verified via night photos and the heritage-committee sign-off."),
    ("Marine Lines", "garbage", "Add tide-line cleanups on Marine Drive promenade (Ward 7)",
     "Two tide-line cleanups weekly for a month, verified via dated before/after photos of three fixed promenade markers plus the contractor log."),
    ("Girgaon", "water", "Fix intermittent supply on Opera House slopes (Ward 6)",
     "Continuous evening supply restored, verified via resident-supplied timestamped tap videos from 8 buildings across one week."),
    ("Byculla", "park", "Rejuvenate the Byculla zoo-adjacent garden (Ward 20)",
     "Garden re-opened with working lights and repaired seating, verified via dated photos of each bench and light against the works list."),
    ("Worli", "drain", "Pump-station readiness at Worli sea-face outfall (Ward 21)",
     "Both dewatering pumps commissioned with BMC certificate, verified via certificate link and a photo of the units running."),
    ("Lower Parel", "road", "Resurface the Delisle Road stretch (Ward 22)",
     "Carriageway resurfaced end-to-end, verified via geotagged photos of the full stretch and the milling-depth report."),
    ("Dadar", "footpath", "Re-tile the Dadar TT circle footpaths (Ward 24)",
     "All four arms re-tiled with tactile paving, verified via geotagged photos of each arm plus the completion certificate."),
    ("Mahim", "garbage", "Clear the Mahim creek-adjacent garbage blackspot (Ward 26)",
     "Blackspot cleared and a weekly collection installed, verified via dated photos and the new pickup log entries."),
    ("Sion", "lights", "Repair Sion flyover approach lighting (Ward 27)",
     "All approach lights working, verified via night geotagged photos from both approaches."),
    ("Kurla", "drain", "Desilt the Kurla transport-agency drain line (Ward 31)",
     "The 1.2km drain line desilted, verified via section-wise before/after photos and disposal receipts."),
    ("Ghatkopar", "water", "Standardize tank timings in Ghatkopar East (Ward 30)",
     "Evening tank supply moved to the notified 6:30–8:30pm slot, verified via timestamped resident videos from 6 buildings."),
    ("Vikhroli", "park", "Fence and light the Vikhroli park periphery (Ward 28)",
     "Perimeter fencing completed and 16 pole lights working, verified via night photos and the works certificate."),
    ("Bhandup", "road", "Patch the Bhandup station road craters (Ward 26)",
     "All marked craters patched, verified via geotagged photos and the ward engineer sign-off."),
    ("Mulund", "footpath", "Clear Mulund check-nalla footpath encroachments (Ward 25)",
     "Marked footpath cleared, verified via geotagged photos at three fixed points after the enforcement drive."),
    ("Chembur", "garbage", "Institute daily garden-waste pickup in Chembur (Ward 23)",
     "Daily pickup running for two weeks, verified via the GPS pickup log and resident timestamped photos."),
    ("Powai", "lights", "Light the Powai lakefront jogging loop (Ward 39)",
     "All 22 loop lights working after dusk, verified via geotagged night photos at four points around the loop."),
    ("Vashi", "road", "Resurface the Vashi sector 10 internal roads (Sector 10)",
     "Internal roads resurfaced, verified via geotagged photos and the municipal completion note."),
    ("Nerul", "drain", "Desilt Nerul sector drains pre-monsoon (Sector 12)",
     "All sector drains desilted, verified via section photos and disposal receipts."),
    ("Thane", "park", "Restore the Upvan lake walkway (Ward 12)",
     "Walkway relaid and railings repaired, verified via dated photos along the full loop."),
]

VENDOR_TEMPLATES = [
    # (area, category, business, service, condition core)
    ("Bandra West", "interiors", "Precision Interiors", "kitchen renovation",
     "Kitchen handover complete with all agreed modules fitted, verified via customer walkthrough video and final-invoice copy."),
    ("Bandra East", "plumbing", "MetroPipe Solutions", "bathroom re-piping",
     "Both bathrooms re-piped with zero leaks across a 7-day pressure hold, verified via the plumber's pressure log and customer confirmation."),
    ("Khar", "pest", "ShieldShield Pest Care", "termite treatment",
     "Full-premise termite treatment with 90-day warranty card issued, verified via the treatment-zone diagram and warranty copy."),
    ("Santacruz West", "appliance", "CoolBreeze Services", "AC service contract",
     "All four units deep-serviced with before/after cooling checks recorded, verified via service reports signed by the customer."),
    ("Vile Parle", "catering", "Sundara Caterers", "engagement dinner",
     "Six-course dinner served hot for 80 guests in the agreed window, verified via event photos and the final bill matching the tasting quote."),
    ("Juhu", "photography", "Lumen Frames Studio", "portfolio shoot",
     "Gallery of 40 retouched images delivered within 10 days, verified via the gallery link timestamp."),
    ("Andheri West", "interiors", "Loft & Line Studio", "living-room false ceiling",
     "Ceiling finished, lighting working, site cleaned and handed over, verified via customer walkthrough video and completion invoice."),
    ("Andheri East", "moving", "SwiftShift Packers", "2BHK local move",
     "All 58 inventoried boxes delivered undamaged within the agreed 6-hour window, verified via the signed inventory sheet."),
    ("Jogeshwari", "electrical", "VoltCraft Electricals", "full-home rewiring",
     "Rewiring complete with the load test passing, verified via the electrical inspection certificate and customer walkthrough."),
    ("Goregaon", "appliance", "FixItNow Appliances", "washing machine repair",
     "Machine repaired with no drum noise across three full cycles, verified via customer video of the third cycle."),
    ("Malad", "tutoring", "MindSpark Academy", "Grade 10 board math coaching",
     "Twenty-four of twenty-four scheduled sessions delivered and a pre-board mock score of 75%+, verified via the session log and mock sheet."),
    ("Kandivali", "plumbing", "DrainWiz Plumbing", "sump pump install",
     "Sump pump installed with auto-float working, verified via a video of the float cycle and the installation invoice."),
    ("Borivali", "catering", "Thali House Catering", "housewarming lunch",
     "Eight-dish menu served for 60 guests on time, verified via event photos and the bill matching the quote."),
    ("Dahisar", "electrical", "BrightLine Electric", "solar panel install",
     "3kW rooftop array commissioned with net-meter approved, verified via the commissioning report and meter photo."),
    ("Colaba", "photography", "Harbour Light Films", "wedding highlight film",
     "5-minute highlight film delivered within 3 weeks, verified via the delivery link timestamp."),
    ("Fort", "moving", "Downtown Relocations", "office move",
     "42 workstations reassembled and network live by Monday 9am, verified via the signed handover checklist."),
    ("Marine Lines", "appliance", "SeaFace Refrigeration", "commercial fridge repair",
     "Fridge holding 4°C across a 48-hour log, verified via the temperature log and service invoice."),
    ("Girgaon", "tutoring", "Carnatic Notes Classes", "vocal music course",
     "All 16 weekly lessons delivered with a recorded recital submitted, verified via the lesson log and recording."),
    ("Byculla", "pest", "UrbanShield Pest Control", "cockroach gel treatment",
     "Kitchen and pantry treated with a 60-day follow-up done, verified via both service stickers and the invoice."),
    ("Worli", "interiors", "SeaLine Interiors", "bedroom wardrobe build",
     "Wardrobe installed with all shutters aligned within 2mm, verified via customer photos and the finish invoice."),
    ("Lower Parel", "moving", "Skyline Movers", "studio-apartment shift",
     "All items delivered same-day with zero damage claims, verified via the signed inventory."),
    ("Dadar", "electrical", "Dadar Duty Electric", "DGF inverter install",
     "Inverter installed and tested through a full power cut, verified via a customer video of the switchover."),
    ("Mahim", "tutoring", "Mahim Music Room", "guitar for beginners",
     "Twelve lessons delivered with a two-song recital recorded, verified via the lesson log and audio file."),
    ("Sion", "plumbing", "SionFlow Plumbers", "kitchen drain reline",
     "Drain relined with flow test passing, verified via the camera-inspection footage and invoice."),
    ("Kurla", "appliance", "KurlaCool AC Repair", "split-AC gas refill",
     "Both units regassed and cooling to 18°C in 20 minutes, verified via temperature readings logged on the service sheet."),
    ("Ghatkopar", "catering", "Ghatkopar Tiffin Co.", "weekly tiffin contract",
     "Twenty lunchboxes delivered on schedule across the trial week, verified via the delivery app log."),
    ("Vikhroli", "pest", "GreenZone Pest Services", "mosquito fogging contract",
     "Four weekly fogging rounds completed, verified via the society's signed visit register."),
    ("Bhandup", "interiors", "NestCraft Interiors", "full-home painting",
     "All nine rooms painted with snag list closed in a week, verified via the walkthrough video and final invoice."),
    ("Mulund", "appliance", "Mulund HomeServe", "microwave repair",
     "Microwave repaired with 90-day warranty, verified via the warranty card and test-heating video."),
    ("Chembur", "moving", "Chembur Cargo Packers", "piano relocation",
     "Piano moved and tuned after placement, verified via the tuner's certificate and delivery photos."),
    ("Powai", "catering", "Lakeside Bites", "corporate lunch spread",
     "Lunch for 45 delivered hot in two waves as agreed, verified via delivery timestamps and the bill."),
    ("Vashi", "tutoring", "Vashi Varsity Point", "JEE foundation course",
     "Thirty-two sessions delivered with a full mock series, verified via the attendance sheet and mock scores."),
    ("Nerul", "photography", "Nerul PixelWorks", "maternity shoot",
     "Edited gallery of 60 photos delivered in 2 weeks, verified via the gallery link."),
    ("Thane", "interiors", "LakeCity Interiors", "foyer + passage redesign",
     "Foyer and passage handed over with all fixtures working, verified via the walkthrough video and invoice."),
]

CIVIC_AREAS = [t[0] for t in CIVIC_TEMPLATES]
VENDOR_AREAS = [t[0] for t in VENDOR_TEMPLATES]

# Jitter so pins don't stack on area centroids.
def jitter():
    return (rng.uniform(-0.004, 0.004), rng.uniform(-0.004, 0.004))


def content_hash(title, desc, condition, deadline):
    raw = f"{title}|{desc or ''}|{condition}|{deadline.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def cleanup(db):
    rows = (await db.execute(select(User).where(User.handle.like("vouch_seed%")))).scalars().all()
    if not rows:
        return
    ids = [u.id for u in rows]
    commit_ids = (await db.execute(
        select(Commitment.id).where(Commitment.author_id.in_(ids))
    )).scalars().all()
    for stmt in (
        delete(Vote).where(Vote.commitment_id.in_(commit_ids)),
        delete(Evidence).where(Evidence.commitment_id.in_(commit_ids)),
        delete(CommitmentJuror).where(CommitmentJuror.commitment_id.in_(commit_ids)),
        delete(Notification).where(Notification.user_id.in_(ids)),
        delete(ReputationEvent).where(ReputationEvent.commitment_id.in_(commit_ids)),
        delete(ReputationEvent).where(ReputationEvent.user_id.in_(ids)),
        delete(Commitment).where(Commitment.id.in_(commit_ids)),
        delete(User).where(User.id.in_(ids)),
    ):
        await db.execute(stmt)
    await db.commit()


# Guarantee genuine city coverage: with 45 slots and 34 areas, every area
# gets ≥1 commitment (round-robin across regions), and 11 areas get a second.
CIVIC_N, VENDOR_N = 22, 23


def _all_areas_ordered():
    """All 34 areas, interleaved west→central→east→extended so the seeded
    set fills the whole map rather than clustering in one band."""
    west = [a for a in AREA_COORDS if a.startswith(("Bandra", "Khar", "Santacruz",
        "Vile Parle", "Juhu", "Andheri", "Jogeshwari", "Goregaon", "Malad",
        "Kandivali", "Borivali", "Dahisar"))]
    central = [a for a in AREA_COORDS if a in {"Colaba", "Fort", "Marine Lines",
        "Girgaon", "Byculla", "Worli", "Lower Parel", "Dadar", "Mahim", "Sion"}]
    east = [a for a in AREA_COORDS if a in {"Kurla", "Ghatkopar", "Vikhroli",
        "Bhandup", "Mulund", "Chembur", "Powai"}]
    ext = [a for a in AREA_COORDS if a in {"Vashi", "Nerul", "Thane"}]
    ordered = []
    buckets = [west, central, east, ext]
    i = 0
    while any(buckets):
        b = buckets[i % len(buckets)]
        if b:
            ordered.append(b.pop(0))
        i += 1
    return ordered


def _spread_pick(templates, n, areas):
    """Pick n templates covering the given areas in order (skipping areas
    whose template was already used), then wrap for a second pass."""
    by_area = {}
    for t in templates:
        by_area.setdefault(t[0], []).append(t)
    picks, used = [], set()
    while len(picks) < n:
        progressed = False
        for area in areas:
            if len(picks) >= n:
                break
            for t in by_area.get(area, []):
                if t not in used:
                    picks.append(t)
                    used.add(t)
                    progressed = True
                    break
        if not progressed:
            break
    return picks


def build_commitments():
    """Build the 22 civic + 23 vendor spec dicts covering every area."""
    areas = _all_areas_ordered()
    # Civic walks the area order from the top; vendor starts half-way around
    # so the two pools combined cover all 34 areas (45 slots → 11 areas get 2).
    half = len(areas) // 2
    civic_areas = areas
    vendor_areas = areas[half:] + areas[:half]
    civic = []
    civic_picks = _spread_pick(CIVIC_TEMPLATES, CIVIC_N, civic_areas)
    for i, (area, ptype, title, condition_core) in enumerate(civic_picks):
        status = CIVIC_STATUSES[i % len(CIVIC_STATUSES)]
        official, role = CIVIC_OFFICIALS[i % len(CIVIC_OFFICIALS)]
        ward_no = 100 + (i * 3) % 30  # invented but stable ward numbers
        ward_label = f"{area} (Ward {ward_no})" if not area.startswith(("Vashi", "Nerul", "Thane")) else area
        desc = {
            "road": "Civic works promise affecting daily commutes.",
            "drain": "Monsoon-preparedness works promised by the ward office.",
            "garbage": "Collection-frequency promise for the locality.",
            "lights": "Streetlight repair and illumination commitment.",
            "water": "Water-supply timing/restoration promise.",
            "park": "Public-space and park maintenance commitment.",
            "footpath": "Footpath clearance and pedestrian-access promise.",
        }[ptype]
        condition = f"{condition_core} Deadline within the committed window; all verification per the stated method."
        civic.append(dict(
            area=area, title=title, desc=desc, condition=condition,
            status=status, category="civic", official=official, role=role,
            ward=area, source=("sourced" if i % 4 == 0 else "crowd"),
        ))

    vendor = []
    vendor_picks = _spread_pick(VENDOR_TEMPLATES, VENDOR_N, vendor_areas)
    for i, (area, cat, business, service, condition_core) in enumerate(vendor_picks):
        status = VENDOR_STATUSES[i % len(VENDOR_STATUSES)]
        title = f"{service.title()} – {business}"
        desc = f"{business}, a {cat} business based in {area}, took on this {service} job under a written commitment."
        condition = f"{condition_core} Per the signed estimate; deadline per the agreed schedule."
        vendor.append(dict(
            area=area, title=title, desc=desc, condition=condition,
            status=status, category="vendor", official=business,
            role=f"{cat.capitalize()} — {area}", ward=None, source=None,
        ))

    return civic, vendor


async def main():
    async with AsyncSessionLocal() as db:
        print("Seeding Mumbai-wide activity…")
        await cleanup(db)

        people = {}
        for i, (handle, (email, ward, rep, streak)) in enumerate(PEOPLE.items()):
            u = User(
                handle=f"vouch_seed_{handle}",
                email=f"vouch_seed_{email}",
                ward=ward,
                reputation_score=rep,
                current_streak=streak,
                created_at=NOW - timedelta(days=60 + i * 3),
            )
            db.add(u)
            people[handle] = u
        await db.flush()
        handles = list(people.keys())

        civic_specs, vendor_specs = build_commitments()
        all_specs = civic_specs + vendor_specs
        counts = {"civic": 0, "vendor": 0}
        status_counts = {"civic": {}, "vendor": {}}
        region_seen = {"west": 0, "central": 0, "east": 0, "extended": 0}
        EXTENDED = {"Vashi", "Nerul", "Thane"}
        EAST = {"Kurla", "Ghatkopar", "Vikhroli", "Bhandup", "Mulund", "Chembur", "Powai"}
        # West = western suburbs; central = south/central Mumbai — partitioned
        # by latitude since the peninsula runs north-south.
        def region_of(area: str) -> str:
            if area in EXTENDED:
                return "extended"
            if area in EAST:
                return "east"
            return "west" if AREA_COORDS[area][0] >= 19.03 else "central"

        for idx, spec in enumerate(all_specs):
            area = spec["area"]
            base = AREA_COORDS[area]
            dy, dx = jitter()
            lat, lng = round(base[0] + dy, 6), round(base[1] + dx, 6)

            author_handle = handles[idx % len(handles)]
            author = people[author_handle]
            status = spec["status"]
            category = spec["category"]
            counts[category] += 1
            status_counts[category][status.value] = status_counts[category].get(status.value, 0) + 1

            region_seen[region_of(area)] += 1

            created_at = NOW - timedelta(days=rng.randint(5, 70))
            deadline_days = rng.choice([-25, -14, -6, 5, 12, 25, 40, 90])
            deadline = NOW + timedelta(days=deadline_days)
            resolved_at = (
                NOW - timedelta(days=rng.randint(1, 10))
                if status in (CommitmentStatus.MET, CommitmentStatus.BROKEN, CommitmentStatus.DISPUTED)
                else None
            )
            title = spec["title"]
            desc = spec["desc"]
            condition = spec["condition"]

            c = Commitment(
                author_id=author.id,
                title=title,
                description=desc,
                measurable_condition=condition,
                deadline=deadline,
                content_hash=content_hash(title, desc, condition, deadline),
                status=status,
                created_at=created_at,
                resolved_at=resolved_at,
                is_public=True,
                jury_pool_size=5,
                category=CommitmentCategory.CIVIC if category == "civic" else CommitmentCategory.VENDOR,
                official_name=spec["official"],
                official_role=spec["role"],
                ward=spec["ward"] if spec["ward"] else area,
                source_type=spec["source"],
                source_citation=("Ward citizens' meeting minutes, 2026" if spec["source"] == "sourced" and category == "civic" else None),
            )
            db.add(c)
            await db.flush()

            # 5 distinct jurors, excluding the author.
            juror_handles = [h for h in handles if h != author_handle]
            rng.shuffle(juror_handles)
            jurors = juror_handles[:5]
            for jh in jurors:
                db.add(CommitmentJuror(
                    commitment_id=c.id, juror_id=people[jh].id,
                    invited_at=created_at + timedelta(days=1),
                ))

            # Evidence on anything past Open.
            if status != CommitmentStatus.OPEN:
                n_ev = rng.randint(1, 3)
                for k in range(n_ev):
                    submitter = people[jurors[k % len(jurors)]]
                    ev_type = rng.choice(["image", "text", "link"])
                    content = {
                        "image": "Geotagged site photo on record — matches the stated verification method.",
                        "text": "Site check completed by a resident; observations noted against the measurable condition.",
                        "link": "Public record link (ward portal / service report) covering the claimed progress.",
                    }[ev_type]
                    db.add(Evidence(
                        commitment_id=c.id,
                        submitter_id=submitter.id,
                        type=EvidenceType(ev_type),
                        content=content,
                        content_hash=hashlib.sha256(f"{c.id}-{k}".encode()).hexdigest(),
                        submitted_at=deadline - timedelta(days=rng.randint(1, 5)),
                    ))

            # Votes on In Verification + resolved rows; verdict-aligned reputation.
            verdict = None
            if status == CommitmentStatus.MET:
                verdict = VoteChoice.MET
            elif status == CommitmentStatus.BROKEN:
                verdict = VoteChoice.BROKEN

            if status in (CommitmentStatus.IN_VERIFICATION, CommitmentStatus.MET,
                          CommitmentStatus.BROKEN, CommitmentStatus.DISPUTED):
                choices = []
                if status == CommitmentStatus.IN_VERIFICATION:
                    # live voting: mixed
                    choices = rng.choices(["met", "broken", "abstain"], weights=[3, 2, 1], k=5)
                elif status == CommitmentStatus.DISPUTED:
                    choices = ["met", "broken", "met", "broken", "abstain"]
                else:
                    choices = [verdict.value if verdict else "met"] * 3 + ["abstain", "met"]
                rng.shuffle(choices)
                for k, choice in enumerate(choices[:5]):
                    voter = people[jurors[k]]
                    reason = None if choice == "abstain" else "Evidence reviewed against the stated condition."
                    db.add(Vote(
                        commitment_id=c.id, juror_id=voter.id,
                        vote=VoteChoice(choice), reason=reason,
                        voted_at=(resolved_at or NOW) - timedelta(days=k + 1),
                    ))

                if verdict is not None:
                    author_delta = AUTHOR_MET if verdict == VoteChoice.MET else AUTHOR_BROKEN
                    db.add(ReputationEvent(
                        user_id=author.id,
                        delta=author_delta,
                        reason=(ReputationReason.COMMITMENT_KEPT if verdict == VoteChoice.MET
                                else ReputationReason.COMMITMENT_BROKEN),
                        commitment_id=c.id,
                        created_at=resolved_at,
                    ))
                    for k, choice in enumerate(choices[:5]):
                        if choice == "abstain":
                            continue
                        accurate = (choice == verdict.value)
                        db.add(ReputationEvent(
                            user_id=people[jurors[k]].id,
                            delta=JUROR_ACCURATE if accurate else JUROR_INACCURATE,
                            reason=(ReputationReason.JURY_ACCURATE if accurate
                                    else ReputationReason.JURY_INACCURATE),
                            commitment_id=c.id,
                            created_at=resolved_at,
                        ))

        await db.commit()

        print(f"  users:              {len(people)}")
        print(f"  civic commitments: {counts['civic']:>3}  {status_counts['civic']}")
        print(f"  vendor commitments:{counts['vendor']:>3}  {status_counts['vendor']}")
        print(f"  region spread:      {region_seen}")

        # Sanity: area coverage from the DB itself
        from collections import Counter
        rows = (await db.execute(select(Commitment.ward))).scalars().all()
        by_area = Counter(rows)
        print(f"  distinct areas with commitments: {len(by_area)}")
        missing = set(AREA_COORDS) - set(by_area)
        print(f"  areas without any commitment: {sorted(missing) if missing else 'none'}")
        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
