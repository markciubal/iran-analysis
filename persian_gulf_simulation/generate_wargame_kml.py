#!/usr/bin/env python3
"""
Persian Gulf Wargame KML Generator
===================================
Eight-CSG simulation of Iranian mass-missile attacks on US Carrier Strike Groups,
with US TLAM/JASSM counterstrikes against Iranian launch sites.

Key features
------------
- 8 US Carrier Strike Groups: Lincoln, Ford, GHW Bush + CSG Alpha/Bravo/Charlie/Delta/Echo
- Researched SM-6/SM-2/ESSM/RAM low/high magazine estimates per CSG (unclassified)
- US counterstrikes (TLAM Block IV / JASSM-ER) against 12 Iranian launch sites
- Launch sites deactivate after 25 cumulative US strike hits; inactive sites stop launching
- Each munition type has its own distinct color (KML AABBGGRR)
- Parabolic / sea-skim arcs broken into 2-point LineString segments with TimeSpan
- Staggered launch waves; flight duration from great-circle distance / munition speed
- Shahed-136 counts capped at 5,000 per scenario (post-50% preemptive strike; Iran inventory: 20,000–40,000 est.)
- Scenario D (Realistic) uses iran_detection_launch=True: Iran fires entire salvo on IAF radar detection,
  compressing all launches into 30 min so no pre-launch suppression is possible.

Armament sources: CRS RL33199; IISS Military Balance 2024; NAVSEA public briefs;
  USNI News deployment tracking; FAS.org; influenceofhistory.blogspot.com loadout analysis.

Scenarios (approximate totals after 5K Shahed cap)
---------
  A -- Low:       ~750 missiles + ~3,000 air drones + ~750 sea drones  =  ~4,800 total
  B -- Medium:  ~1,300 missiles + ~5,000 air drones + ~750 sea drones  =  ~8,250 total
  C -- High:    ~1,300 missiles + ~5,000 air drones + ~750 sea drones  =  ~7,565 total
  D -- Realistic: ~650 missiles + ~5,000 air drones + ~990 sea drones  =  ~7,250 total  [simultaneous detection-launch]
  E -- Iran Best: ~875 missiles + ~5,000 air drones + ~500 sea drones  =  ~6,750 total
  F -- USA Best:  ~660 missiles + ~1,000 air drones + ~000 sea drones  =  ~1,660 total

Output
------
  scenarios/scenario_low.kml
  scenarios/scenario_medium.kml
  scenarios/scenario_high.kml
  scenarios/scenario_realistic.kml
  scenarios/scenario_iran_best.kml
  scenarios/scenario_usa_best.kml
  wargame_master.kml
"""

import math, random, os
from datetime import datetime, timezone, timedelta

# ============================================================
# SIMULATION CLOCK
# ============================================================
SIM_START = datetime(2026, 3, 13, 6, 0, 0, tzinfo=timezone.utc)
CARRIER_SPEED_KMS = 20 * 1.852 / 3600   # 20 knots → km per second (0.010289 km/s)

def fmt_time(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def sim_time(offset_s):
    return SIM_START + timedelta(seconds=float(offset_s))

def csg_pos_at(csg, t_s):
    """Return (lon, lat) of csg at t_s seconds into simulation (20-knot due-west course)."""
    hdg = math.radians(csg.get("heading_deg", 220))
    d_km = CARRIER_SPEED_KMS * float(t_s)
    d_lat = d_km * math.cos(hdg) / 111.0
    d_lon = d_km * math.sin(hdg) / (111.0 * math.cos(math.radians(csg["lat"])))
    return csg["lon"] + d_lon, csg["lat"] + d_lat

# ============================================================
# GEOGRAPHY -- 8 US CARRIER STRIKE GROUPS
# ============================================================
# VLS loadout research (all unclassified, open-source estimates):
#
#  DDG-51 Flight II/IIA (90 VLS cells) — typical wartime load per ship:
#    SM-6: 8–16 rds   SM-2: 20–48 rds   ESSM: 32 rds (8 quad-cells × 4)
#    Tomahawk: 16 rds   ASROC: 8 rds   (remaining cells other loads)
#    Sources: influenceofhistory.blogspot.com; DTIC ADA620888; USNI News
#
#  DDG-51 Flight III (96 VLS cells) — SPY-6 radar, more SM-6 emphasis:
#    SM-6: 10–18 rds   SM-2: 20–44 rds   ESSM: 32–48 rds
#
#  CG-47 Ticonderoga (122 VLS cells) — standard load per CRS / seaforces.org:
#    SM-6: 12 rds   SM-2MR: 56 rds   SM-2ER: 3 rds   ESSM: 12 rds
#    SM-3: 10 rds   Tomahawk: 32 rds   ASROC: 6 rds
#
#  CVN self-defense (not in VLS): Phalanx 2–3×, RAM 2–4× Mk 49 (21 rds ea)
#    Ford-class: 3× Mk 49 RAM (63 rds) + SeaRAM  Nimitz: 2–4× Mk 49 (42–84 rds)

US_CSGS = [
    # ── Named CSGs ────────────────────────────────────────────────────────────
    # asset_value_usd: total replacement cost of all hulls + embarked air wing
    #   Nimitz CVN hull: ~$9B (CRS RL33524; FY2023 replacement estimate)
    #   Ford  CVN hull: ~$13.3B (actual CVN-78 program cost, CRS RL33524)
    #   Carrier air wing: ~$4B (F/A-18E/F ×44, E-2D ×5, EA-18G ×5, MH-60 etc.)
    #   Ticonderoga CG: ~$1.0B (FY2023 replacement; CG-47 class decommissioning value)
    #   DDG-51 Flight II/IIA: ~$1.8B  |  Flight III: ~$2.2B  |  DDG-1000: ~$4.4B
    {
        "name":    "USS Abraham Lincoln (CVN-72)",
        "lon": 56.5, "lat": 26.4,
        "heading_deg": 270,
        "class":   "Nimitz",
        "has_cruiser": False,
        "escorts": "3 × DDG-51 Flight IIA (DDG-77, DDG-111, DDG-121) — no cruiser",
        # 3 DDG-51 Flight IIA × floor/ceiling per ship
        "sm6_low":   24, "sm6_high":   48,   # 8–16 per DDG × 3
        "sm2_low":   60, "sm2_high":  144,   # 20–48 per DDG × 3
        "essm_low":  96, "essm_high": 128,   # ~32 per DDG × 3
        "ram_low":   42, "ram_high":   84,   # carrier 2–4 × Mk 49
        "tlam_est":  48,                      # 16 per DDG × 3
        # legacy midpoints
        "sm6_est": 35, "sm2_est": 100, "essm_est": 112, "ram_est": 63,
        # CVN-72 ($9B hull + $4B air wing) + 3 × DDG-51 IIA ($1.8B × 3)
        "asset_value_usd": 18_400_000_000,
        # CVN ship's company (~5,000) + air wing (~2,480) + 3 × DDG crew (~280 ea)
        "personnel": 8_320,
    },
    {
        "name":    "USS Gerald R. Ford (CVN-78)",
        "lon": 55.3, "lat": 25.9,
        "heading_deg": 270,
        "class":   "Ford",
        "has_cruiser": True,
        "escorts": "3 × DDG-51 Flight III + CG-60 USS Normandy (122 VLS)",
        # 3 DDG Flight III + Normandy cruiser
        "sm6_low":   36, "sm6_high":   66,   # 8–16×3 DDG + 12 CG
        "sm2_low":  119, "sm2_high":  203,   # 20–48×3 DDG + 59 CG (56+3)
        "essm_low":  96, "essm_high": 144,   # 32×3 DDG + 12 CG
        "ram_low":   63, "ram_high":  105,   # Ford 3×Mk49 + some DDG RAM
        "tlam_est":  80,                      # 16×3 DDG + 32 CG
        "sm6_est": 46, "sm2_est": 175, "essm_est": 120, "ram_est": 84,
        # CVN-78 ($13.3B hull + $4B air wing incl. ~44 F/A-18E/F @$70M, 5 E-2D @$220M, 5 EA-18G @$68M)
        # + 3 × DDG-51 Flight III ($2.2B × 3) + CG-60 ($1.0B)
        "asset_value_usd": 24_900_000_000,
        # CVN ship's company (~5,000) + air wing (~2,480) + 3 × DDG-51 III (~290 ea) + CG (~400)
        "personnel": 8_750,
    },
    {
        "name":    "USS George H.W. Bush (CVN-77)",
        "lon": 57.2, "lat": 26.8,
        "heading_deg": 270,
        "class":   "Nimitz",
        "has_cruiser": True,
        "escorts": "3 × DDG-51 Flight IIA + CG-55 USS Leyte Gulf (122 VLS)",
        "sm6_low":   36, "sm6_high":   60,
        "sm2_low":  119, "sm2_high":  203,
        "essm_low":  96, "essm_high": 144,
        "ram_low":   42, "ram_high":  105,
        "tlam_est":  80,
        "sm6_est": 44, "sm2_est": 170, "essm_est": 120, "ram_est": 84,
        # CVN-77 ($9B hull + $4B air wing) + 3 × DDG-51 IIA ($1.8B × 3) + CG-55 ($1.0B)
        "asset_value_usd": 19_400_000_000,
        "personnel": 8_720,   # 5,000 CVN + 2,480 air wing + 3×280 DDG + 400 CG
    },
    # ── Lettered CSGs A–E ─────────────────────────────────────────────────────
    {
        "name":    "CSG Alpha",
        "lon": 62.0, "lat": 22.5,   # Northern Arabian Sea
        "heading_deg": 270,
        "class":   "Nimitz",
        "has_cruiser": False,
        "escorts": "3 × DDG-51 Flight III (DESRON Alpha) — no cruiser",
        "sm6_low":   30, "sm6_high":   54,   # Flight III: 10–18 per DDG × 3
        "sm2_low":   60, "sm2_high":  132,
        "essm_low":  96, "essm_high": 144,
        "ram_low":   42, "ram_high":   84,
        "tlam_est":  48,
        "sm6_est": 42, "sm2_est": 96, "essm_est": 120, "ram_est": 63,
        # CVN ($9B hull + $4B air wing) + 3 × DDG-51 Flight III ($2.2B × 3)
        "asset_value_usd": 19_600_000_000,
        "personnel": 8_350,   # 5,000 CVN + 2,480 air wing + 3×290 DDG-51 III
    },
    {
        "name":    "CSG Bravo",
        "lon": 51.5, "lat": 27.0,   # Northern Gulf
        "heading_deg": 270,
        "class":   "Nimitz",
        "has_cruiser": True,
        "escorts": "3 × DDG-51 Flight IIA + CG-70 USS Lake Erie (122 VLS)",
        "sm6_low":   36, "sm6_high":   60,
        "sm2_low":  119, "sm2_high":  203,
        "essm_low":  96, "essm_high": 144,
        "ram_low":   42, "ram_high":  105,
        "tlam_est":  80,
        "sm6_est": 44, "sm2_est": 165, "essm_est": 120, "ram_est": 84,
        # CVN ($9B hull + $4B air wing) + 3 × DDG-51 IIA ($1.8B × 3) + CG-70 ($1.0B)
        "asset_value_usd": 19_400_000_000,
        "personnel": 8_720,   # 5,000 CVN + 2,480 air wing + 3×280 DDG + 400 CG
    },
    {
        "name":    "CSG Charlie",
        "lon": 53.5, "lat": 25.8,   # Central Gulf
        "heading_deg": 270,
        "class":   "Nimitz",
        "has_cruiser": False,
        "escorts": "4 × DDG-51 Flight IIA (DESRON Charlie) — no cruiser",
        # 4 DDGs → slightly larger magazine, no cruiser
        "sm6_low":   32, "sm6_high":   64,   # 8–16 per DDG × 4
        "sm2_low":   80, "sm2_high":  192,   # 20–48 per DDG × 4
        "essm_low": 128, "essm_high": 160,
        "ram_low":   42, "ram_high":   84,
        "tlam_est":  64,                      # 16 × 4 DDGs
        "sm6_est": 44, "sm2_est": 136, "essm_est": 144, "ram_est": 63,
        # CVN ($9B hull + $4B air wing) + 4 × DDG-51 IIA ($1.8B × 4)
        "asset_value_usd": 20_200_000_000,
        "personnel": 8_600,   # 5,000 CVN + 2,480 air wing + 4×280 DDG
    },
    {
        "name":    "CSG Delta",
        "lon": 56.0, "lat": 24.0,   # Central Gulf south
        "heading_deg": 270,
        "class":   "Ford",
        "has_cruiser": True,
        "escorts": "3 × DDG-51 Flight III + CG-65 USS Chosin (122 VLS)",
        "sm6_low":   42, "sm6_high":   66,   # 10–18×3 + 12 CG
        "sm2_low":  119, "sm2_high":  203,
        "essm_low":  96, "essm_high": 156,   # 32×3 + 12 CG + some extras
        "ram_low":   63, "ram_high":  105,   # Ford 3×Mk49
        "tlam_est":  80,
        "sm6_est": 54, "sm2_est": 172, "essm_est": 126, "ram_est": 84,
        # CVN-78 class ($13.3B hull + $4B air wing) + 3 × DDG-51 III ($2.2B × 3) + CG-65 ($1.0B)
        "asset_value_usd": 24_900_000_000,
        "personnel": 8_750,   # 5,000 CVN + 2,480 air wing + 3×290 DDG-51 III + 400 CG
    },
    {
        "name":    "CSG Echo",
        "lon": 59.0, "lat": 23.5,   # Eastern Gulf / Hormuz approaches
        "heading_deg": 270,
        "class":   "Nimitz",
        "has_cruiser": False,
        "escorts": "3 × DDG-51 Flight IIA + 1 × DDG-1000 Zumwalt (DESRON Echo)",
        # DDG-1000 focuses on strike (80 VLS, mostly Tomahawk), limited AAW
        "sm6_low":   24, "sm6_high":   48,
        "sm2_low":   60, "sm2_high":  144,
        "essm_low":  96, "essm_high": 128,
        "ram_low":   42, "ram_high":   84,
        "tlam_est": 128,                      # 16×3 DDG + 80 Zumwalt
        "sm6_est": 36, "sm2_est": 100, "essm_est": 112, "ram_est": 63,
        # CVN ($9B hull + $4B air wing) + 3 × DDG-51 IIA ($1.8B × 3) + DDG-1000 Zumwalt ($4.4B)
        "asset_value_usd": 22_800_000_000,
        "personnel": 8_460,   # 5,000 CVN + 2,480 air wing + 3×280 DDG + 140 DDG-1000
    },
]

TOTAL_CSG_PERSONNEL = sum(csg["personnel"] for csg in US_CSGS)
TOTAL_CSG_VALUE     = sum(csg["asset_value_usd"] for csg in US_CSGS)

# ── Strait of Hormuz column formation ────────────────────────────────────────
# 8 CSGs in single-file column transiting the strait, lead at (56.515, 26.622),
# heading 310° (NW into the Gulf), 15 km between ships.
_STRAIT_LEAD_LON, _STRAIT_LEAD_LAT = 56.515, 26.622
_STRAIT_HDG = 310
_STRAIT_SP  = 15   # km between ships (trail spacing)
_sd_lat = _STRAIT_SP * math.cos(math.radians(130)) / 111.0
_sd_lon = _STRAIT_SP * math.sin(math.radians(130)) / (111.0 * math.cos(math.radians(_STRAIT_LEAD_LAT)))
STRAIT_CSGS = []
for _si, _sc in enumerate(US_CSGS):
    _entry = dict(_sc)
    _entry["lon"] = round(_STRAIT_LEAD_LON + _si * _sd_lon, 4)
    _entry["lat"] = round(_STRAIT_LEAD_LAT + _si * _sd_lat, 4)
    _entry["heading_deg"] = _STRAIT_HDG
    STRAIT_CSGS.append(_entry)

# Weapon engagement ranges (km) — unclassified published figures
WPN_RANGES = {
    "SM-6":  240,
    "SM-2":  167,
    "ESSM":   50,
    "RAM":    15,
    "CIWS_AA": 1.5,
    "CIWS_SF": 2.5,
}

# ============================================================
# AIR SUPPORT — Israeli Air Force + US Carrier Air Wings
# ============================================================
# Israeli Air Force force estimates (Jane's DW 2024; FAS.org; IISS Military Balance 2024):
#   F-35I Adir:  50 delivered (140th "Golden Eagle" + 116th "Defenders of the South" sqns,
#                Nevatim AB; 25 more on order for 117th sqn); 75% MCR → 37 combat-ready;
#                with aerial refuelling range is limited only by pilot endurance;
#                2 × JDAM-ER internally stealth; source: Jane's DW 2024
#   F-15I Ra'am: 25 aircraft (F-15I+ MLU upgrade ongoing); combat radius ~1,600 km;
#                2 × Rampage ALCM (250 km) or 2 × SPICE-2000; source: Jane's DW 2024
#   F-16I Sufa:  97 aircraft as of Jul 2024 (Israel retired Barak-1 F-16s);
#                conformal fuel tanks; radius ~1,600 km; 2 × SPICE-250; source: Jane's DW
#   IAF tankers: 8 × Boeing 707 tanker-transport; KC-46A Pegasus approved to replace;
#                source: Jane's DW / FAS.org
#   Realistic Gulf sortie rate: 1 package/day × 3 days; F-35I 55 sorties (37×75%×2d),
#                F-15I 40, F-16I 73 (Gulf-capable) → ~168 sorties / ~336 munitions total
#
# US Carrier Air Wing (per CVN, USNI/NAVAIR; Jane's DW):
#   ~70 F/A-18E/F Super Hornet per CVW across 4 VFA sqns ($70 M each);
#   5 × EA-18G Growler ($68 M); 5 × E-2D Hawkeye ($220 M)
#   CAP: 4–6 F/A-18F always airborne; 6–8 × AIM-120C/D AMRAAM each
#   AIM-120C-8 FMS price: ~$2.46 M/rnd (incl. support); unit cost ~$1.8 M; source: Jane's DW
#   AIM-120D-3 FMS price: ~$3.03 M/rnd; unit cost ~$2.2 M
#   → ~200 AMRAAM shots/day per CSG × 8 CSGs = 1,600 shots/day
#   Air-launched strikes: SLAM-ER (AGM-84H, 280 km, $1.3 M) — 1–2 per F/A-18E
#   → ~40–60 SLAM-ER per CSG per day; 8 CSGs × 50 × 2 days ≈ 800 total SLAM-ER

# IAF launch bases (representative; Nevatim = F-35I; Hatzerim = F-15I; Ramon = F-16I)
IAF_BASES = [
    {"name": "Nevatim AB (F-35I)",  "lon": 34.99, "lat": 31.21,
     "aircraft": "F-35I Adir", "sorties": 55,  "munition": "JDAM-ER",      "per_sortie": 4},
    {"name": "Hatzerim AB (F-15I)", "lon": 34.67, "lat": 31.23,
     "aircraft": "F-15I Ra'am", "sorties": 40, "munition": "Rampage ALCM", "per_sortie": 4},
    {"name": "Ramon AB (F-16I)",    "lon": 34.74, "lat": 30.78,
     "aircraft": "F-16I Sufa",  "sorties": 73,  "munition": "SPICE-2000",  "per_sortie": 4},
]

IAF_MUNITIONS = {
    # AABBGGRR: bright lime/teal for IAF (distinct from US blues and Iran reds)
    "JDAM-ER": {
        "speed_km_s": 0.300, "peak_alt_m": 10_000, "sea_skim": False,
        "color": "cc00ff88", "width": 2,
        "label": "JDAM-ER (lime-teal — Israeli F-35I strike, 80 km glide bomb)",
        "cost_usd": 30_000,   # FY2023 JDAM kit + ER wing (~$30k per munition)
        "max_range_km": 80,
    },
    "Rampage ALCM": {
        "speed_km_s": 0.340, "peak_alt_m": 8_000, "sea_skim": False,
        "color": "cc00ffcc", "width": 2,
        "label": "Rampage ALCM (teal — Israeli F-15I standoff missile, 250 km)",
        "cost_usd": 500_000,  # Israeli-made; $400k–600k estimate
        "max_range_km": 250,
    },
    "SPICE-2000": {
        "speed_km_s": 0.250, "peak_alt_m": 9_000, "sea_skim": False,
        "color": "cc00ff44", "width": 2,
        "label": "SPICE-2000 (green — Israeli F-16I precision glide bomb, 100 km)",
        "cost_usd": 800_000,  # Rafael estimate; $600k–1M
        "max_range_km": 100,
    },
}

# US Carrier CAP intercept (AIM-120 AMRAAM) — cost factor, not KML-tracked
AIM120_COST_USD     = 1_800_000   # AIM-120C-8 unit cost ~$1.8M (FMS price $2.46M incl. support; Jane's DW 2024)
SLAM_ER_COST_USD    = 1_300_000   # AGM-84H/K FY2023
SLAM_ER_PER_CSG_DAY = 50          # SLAM-ER air-launched strikes per CSG per day
CAP_AMRAAM_PER_CSG_DAY = 200      # AIM-120 shots expended per CSG per day (CAP duty)
CAP_PK_VS_DRONE     = 0.65        # AIM-120 P(kill) vs Shahed-class drone
CAP_PK_VS_MISSILE   = 0.45        # AIM-120 P(kill) vs cruise/ballistic missile

IRAN_SITES = [
    {"name": "Bandar Abbas",  "lon": 56.27, "lat": 27.18, "type": "Coastal Battery"},
    {"name": "Qeshm Island",  "lon": 56.02, "lat": 26.74, "type": "Island Fortress"},
    {"name": "Jask",          "lon": 57.77, "lat": 25.64, "type": "Coastal Battery"},
    {"name": "Chahbahar",     "lon": 60.62, "lat": 25.29, "type": "Coastal Battery"},
    {"name": "Bushehr",       "lon": 50.84, "lat": 28.97, "type": "Naval Base"},
    {"name": "Khorramshahr",  "lon": 48.18, "lat": 30.44, "type": "Inland Battery"},
    {"name": "Shiraz",        "lon": 52.53, "lat": 29.59, "type": "Inland Battery"},
    {"name": "Isfahan",       "lon": 51.67, "lat": 32.66, "type": "Inland Battery"},
    {"name": "Kerman",        "lon": 57.09, "lat": 30.28, "type": "Inland Battery"},
    {"name": "Dezful",        "lon": 48.40, "lat": 32.38, "type": "Inland Battery"},
    {"name": "Minab",         "lon": 57.08, "lat": 27.09, "type": "Coastal Battery"},
    {"name": "Lar",           "lon": 54.33, "lat": 27.68, "type": "Inland Battery"},
]

# After 30 US strike hits a launch site is destroyed and stops launching
SITE_INACTIVATION_THRESHOLD = 30

# 1% of Shahed-136 carry AI / computer-vision terminal guidance.
# In terminal phase they re-acquire the target visually and maneuver to a
# tighter aim point, defeating CIWS lead-angle prediction — always break through.
AI_SHAHED_FRACTION = 0.01    # fraction of Shahed-136 that are AI-guided
AI_TERMINAL_FRAC   = 0.85    # fraction of flight at which AI re-acquisition begins

# ============================================================
# US STRIKE MUNITIONS (TLAM / JASSM-ER)
# ============================================================
# TLAM Block IV: ~885 km/h (0.246 km/s), range 1,600 km
#   Source: Naval Technology / Tomahawk Wikipedia
# JASSM-ER: ~1,040 km/h (0.289 km/s), range ~1,000 km, stealth profile
#   Source: AGM-158 Wikipedia / CSIS Missile Threat
# ============================================================
# COST ESTIMATES  (unclassified open-source, FY2023–2026 USD)
# ============================================================
# Iranian offensive munition unit costs (production/acquisition estimates):
#   Shahed-136:      CSIS/RUSI ~$20k–50k; median $20k used (mass-produced, domestic components)
#   IRGCN Sea Drone: $50k–150k estimate; median $100k
#   Shahab-3 MRBM:   CSIS/IISS ~$500k–1.5M; median $800k
#   Noor ASCM:       C-802 derivative; ~$300k–700k; median $500k
#   Fateh-110 SRBM:  ~$500k–1.2M; median $700k
#   Emad MRBM:       Maneuvering warhead; IISS ~$1.5M–3M; median $2M
#   Zolfaghar SRBM:  Precision; ~$700k–1.5M; median $1M
#   Khalij Fars ASBM: Anti-ship ballistic; ~$1M–3M; median $2M
#   CM-302 ASCM:     Supersonic; Chinese-derived; ~$1M–3M; median $2M
#   Fateh-313 SRBM:  Advanced precision; ~$600k–1.5M; median $800k
#
# US interceptor engagement costs (DoD FY2023 unit procurement + estimates):
#   SM-6:        $4.3M (DoD DAES FY2023)
#   SM-2:        $2.1M (DoD DAES FY2023)
#   ESSM Block 2:$1.5M (DoD FY2023)
#   RAM Block 2: $1.0M (DoD FY2023)
#   SeaRAM:      uses RAM rounds; ~$1.0M per engagement
#   Phalanx CIWS:~$50k per engagement (20mm ammunition + maintenance estimate)
#   Naval Mk-45: ~$10k per engagement (5-inch rounds; primarily surface drone deterrent)
#   Blended "SM-6/SM-2" engagement: ~$3.3M (typical mix per CBO analysis)
#   Blended "CIWS/SeaRAM" engagement: ~$800k (SeaRAM-dominated; RAM rounds)
#   Blended "Naval Gun/Phalanx" engagement: ~$50k
#
# US strike munition costs:
#   TLAM Block IV: ~$2.0M (DoD FY2023 Lot 25 contract; BGM-109)
#   JASSM-ER:      ~$1.4M (FY2023 multiyear contract; AGM-158B)

INTERCEPTOR_COSTS = {
    "SM-6 / SM-2":         3_300_000,   # blended engagement cost (SM-6/SM-2/ESSM mix)
    "CIWS / SeaRAM":         800_000,   # RAM-dominated; SeaRAM engagement
    "Naval Gun / Phalanx":    50_000,   # 5-inch rounds; surface threat deterrent
}

US_STRIKE_MUNITIONS = {
    "TLAM Block IV": {
        "speed_km_s": 0.246,
        "peak_alt_m": 250,
        "color":    "cc00ff66",   # AABBGGRR: B=00 G=ff R=66 → lime green (US anti-ground)
        "color_bt": "ff00ff88",   # brighter lime green, full alpha
        "width": 2,
        "label": "TLAM Block IV (lime green — US cruise missile strike on land targets)",
        "cost_usd": 2_000_000,   # DoD FY2023 Lot 25 BGM-109 contract
    },
    "JASSM-ER": {
        "speed_km_s": 0.289,
        "peak_alt_m": 200,
        "color":    "cc00aa00",   # AABBGGRR: B=00 G=aa R=00 → forest green (stealth, darker)
        "color_bt": "ff00cc00",   # brighter forest green, full alpha
        "width": 2,
        "label": "JASSM-ER (forest green — US stealth standoff strike on land targets)",
        "cost_usd": 1_400_000,   # FY2023 multiyear AGM-158B contract
    },
}

# ============================================================
# MUNITION LIBRARY
# ============================================================
MUNITIONS = {
    # Iran warm-color scale: yellow (cheap/legacy) → orange → red (advanced/dangerous)
    # AABBGGRR: all warm tones keep B=00, vary G from ff (yellow) to 00 (red), R=ff always.
    "Shahab-3 MRBM": {
        # Legacy MRBM — amber-orange (step 4 of 10)
        "speed_km_s": 1.40, "peak_alt_m": 280_000, "sea_skim": False,
        "color":    "cc0099ff",   # RGB(ff,99,00) amber-orange, 80% alpha
        "color_bt": "ff00aaff",   # brighter amber-orange, full alpha
        "width": 2, "width_bt": 3,
        "label": "Shahab-3 MRBM (amber-orange — legacy MRBM)",
        "cost_usd": 800_000,         # CSIS/IISS estimate; $500k–1.5M range
        # Expected damage/casualties PER BREAKTHROUGH HIT (probability-weighted):
        #   70% hits escort DDG (~280 crew, 40% KIA if ballistic hit) + 30% hits CVN (~5,000 crew, 4% KIA)
        "damage_per_hit_usd":         200_000_000,   # ~$200M: 35% P(mission kill escort @$1.8B) + CVN damage
        "kia_per_hit":                60,    # ~196 DDG × 0.7 + ~200 CVN × 0.3 weighted
        "wia_per_hit":               160,    # ~3× KIA (burns, blast, shrapnel)
        "collateral_usd_per_btk":  12_000_000,   # 12% stray × $100M avg tanker/bulk carrier
        "collateral_kia_per_btk":     2.4,  # 12% stray × 20 crew per vessel
        "n_arc_override": 26,    # high-arc ballistic: many segments for smooth parabola
    },
    "Noor ASCM": {
        # Anti-ship cruise missile — vivid red (anti-ship family)
        "speed_km_s": 0.28, "peak_alt_m": 120, "sea_skim": True,
        "color":    "cc0000ff",   # AABBGGRR: B=00 G=00 R=ff → pure red
        "color_bt": "ff0011ff",   # brighter red, full alpha
        "width": 2, "width_bt": 3,
        "label": "Noor ASCM (red — legacy anti-ship cruise, C-802 derivative)",
        "cost_usd": 500_000,         # C-802 derivative; $300k–700k estimate
        "damage_per_hit_usd":        150_000_000,   # Exocet-class 165kg warhead; ~$150M expected
        "kia_per_hit":                40,
        "wia_per_hit":               120,
        "collateral_usd_per_btk":   7_000_000,    # 8% stray × $87M avg vessel
        "collateral_kia_per_btk":     1.2,  # 8% stray × 15 crew
        "n_arc_override": 18,    # sea-skimming cruise: medium resolution
    },
    "Fateh-110 SRBM": {
        # Older SRBM — amber (step 3 of 10)
        "speed_km_s": 1.00, "peak_alt_m": 60_000, "sea_skim": False,
        "color":    "cc00bbff",   # RGB(ff,bb,00) amber
        "color_bt": "ff00ccff",
        "width": 2, "width_bt": 3,
        "label": "Fateh-110 SRBM (amber — legacy SRBM)",
        "cost_usd": 700_000,         # $500k–1.2M estimate
        "damage_per_hit_usd":        180_000_000,   # 450kg warhead; higher than ASCM
        "kia_per_hit":                55,
        "wia_per_hit":               150,
        "collateral_usd_per_btk":  12_000_000,
        "collateral_kia_per_btk":     2.4,
        "n_arc_override": 24,    # ballistic arc
    },
    "Emad MRBM": {
        # Maneuvering MRBM — red (step 9 of 10, very advanced)
        "speed_km_s": 1.50, "peak_alt_m": 350_000, "sea_skim": False,
        "color":    "cc0011ff",   # RGB(ff,11,00) deep red
        "color_bt": "ff0022ff",   # bright red
        "width": 3, "width_bt": 4,
        "label": "Emad MRBM (red — maneuvering MRBM, advanced)",
        "cost_usd": 2_000_000,       # maneuvering warhead; IISS $1.5M–3M estimate
        "damage_per_hit_usd":        250_000_000,   # maneuvering terminal; very hard to defeat
        "kia_per_hit":                70,
        "wia_per_hit":               180,
        "collateral_usd_per_btk":  10_000_000,
        "collateral_kia_per_btk":     1.8,
        "n_arc_override": 28,    # highest-arc MRBM: most segments
    },
    "Zolfaghar SRBM": {
        # Precision SRBM — orange-red (step 6 of 10)
        "speed_km_s": 1.20, "peak_alt_m": 130_000, "sea_skim": False,
        "color":    "cc0066ff",   # RGB(ff,66,00) orange-red
        "color_bt": "ff0077ff",
        "width": 3, "width_bt": 4,
        "label": "Zolfaghar SRBM (orange-red — precision SRBM)",
        "cost_usd": 1_000_000,       # precision guidance; $700k–1.5M estimate
        "damage_per_hit_usd":        220_000_000,   # 600kg precision warhead
        "kia_per_hit":                65,
        "wia_per_hit":               175,
        "collateral_usd_per_btk":  10_000_000,
        "collateral_kia_per_btk":     2.0,
        "n_arc_override": 24,    # ballistic arc
    },
    "Khalij Fars ASBM": {
        # Anti-ship ballistic missile — deep crimson (anti-ship family)
        "speed_km_s": 1.30, "peak_alt_m": 90_000, "sea_skim": False,
        "color":    "cc0022ff",   # AABBGGRR: B=00 G=22 R=ff → deep crimson red
        "color_bt": "ff0033ff",   # brighter crimson, full alpha
        "width": 3, "width_bt": 4,
        "label": "Khalij Fars ASBM (crimson — anti-ship ballistic, EO/IR seeker)",
        "cost_usd": 2_000_000,       # anti-ship ballistic; $1M–3M estimate
        # Designed specifically to kill carriers; 70% DDG screen hit + 30% CVN penetration
        "damage_per_hit_usd":        350_000_000,   # ~$350M: high P(mission kill) on carrier or escort
        "kia_per_hit":               120,    # terminal dive + shaped charge optimized vs ship armor
        "wia_per_hit":               300,
        "collateral_usd_per_btk":  12_000_000,
        "collateral_kia_per_btk":     2.4,
        "n_arc_override": 26,    # anti-ship ballistic: steep terminal dive needs resolution
    },
    "CM-302 Supersonic ASCM": {
        # Fastest sea-skimming supersonic ASCM — dark maroon-red (anti-ship family, most dangerous)
        "speed_km_s": 1.00, "peak_alt_m": 80, "sea_skim": True,
        "color":    "cc0044ff",   # AABBGGRR: B=00 G=44 R=ff → dark scarlet (distinct from Noor/KF)
        "color_bt": "ff0055ff",   # brighter scarlet, full alpha
        "width": 4, "width_bt": 5,
        "label": "CM-302 Supersonic ASCM (scarlet — Mach 3 anti-ship, most dangerous)",
        "cost_usd": 2_000_000,       # Chinese-derived supersonic; $1M–3M estimate
        # Mach 3 impact velocity; warhead ~250kg but kinetic energy adds lethality
        "damage_per_hit_usd":        220_000_000,
        "kia_per_hit":                80,
        "wia_per_hit":               200,
        "collateral_usd_per_btk":   7_000_000,    # 7% stray × $100M
        "collateral_kia_per_btk":     1.05,
        "n_arc_override": 20,    # fast sea-skimmer: high resolution for evasive path
    },
    "Fateh-313 SRBM": {
        # Advanced precision SRBM — red-orange (step 7 of 10)
        "speed_km_s": 1.10, "peak_alt_m": 75_000, "sea_skim": False,
        "color":    "cc0055ff",   # RGB(ff,55,00) red-orange
        "color_bt": "ff0066ff",
        "width": 4, "width_bt": 5,
        "label": "Fateh-313 SRBM (red-orange — advanced precision SRBM)",
        "cost_usd": 800_000,         # advanced precision; $600k–1.5M estimate
        "damage_per_hit_usd":        200_000_000,
        "kia_per_hit":                62,
        "wia_per_hit":               165,
        "collateral_usd_per_btk":  10_000_000,
        "collateral_kia_per_btk":     2.0,
        "n_arc_override": 24,    # ballistic arc
    },
    "Shahed-136": {
        # Cheap loitering munition swarm — pure yellow (drone family)
        "speed_km_s": 0.052,
        "peak_alt_m": 280,
        "sea_skim":   True,
        "color":    "cc00ffff",   # AABBGGRR: B=00 G=ff R=ff → pure yellow
        "color_bt": "ff00ffff",   # full-alpha pure yellow
        "width": 1, "width_bt": 2,
        "label": "Shahed-136 Loitering Munition (yellow — cheap swarm drone)",
        "cost_usd": 20_000,          # CSIS/RUSI ~$10k–50k; median $20k (mass-produced)
        # Small 36kg warhead; most damage is to sensors/CIWS/topside equipment
        "damage_per_hit_usd":         15_000_000,   # ~$15M: mostly electronics/radar damage
        "kia_per_hit":                 5,
        "wia_per_hit":                20,
        "collateral_usd_per_btk":   4_000_000,    # 5% stray × $80M avg commercial vessel
        "collateral_kia_per_btk":     0.75,  # 5% stray × 15 crew
        "n_arc_override": 10,    # slow drone: temporal resolution more important than spatial
        "interceptor_style": "us_ciws",
        "t_int_range":  (0.92, 0.99),
        "react_range":  (5, 15),
        "sites": ["Bandar Abbas", "Qeshm Island", "Jask", "Chahbahar",
                  "Bushehr", "Minab", "Lar"],
    },
    "IRGCN Sea Drone": {
        # Slow surface drone — amber yellow (drone family, distinct from Shahed)
        "speed_km_s": 0.022,
        "peak_alt_m": 1.0,
        "sea_skim":   True,
        "color":    "cc00ccff",   # AABBGGRR: B=00 G=cc R=ff → amber-yellow (darker than Shahed)
        "color_bt": "ff00ddff",   # brighter amber, full alpha
        "width": 2, "width_bt": 3,
        "label": "IRGCN Sea Drone (amber-yellow — surface drone)",
        "cost_usd": 100_000,         # $50k–150k estimate based on IRGCN procurement patterns
        # Surface drone; small charge; primarily sensor/deck damage if hull not penetrated
        "damage_per_hit_usd":          5_000_000,   # ~$5M: sensor/topside damage; low lethality
        "kia_per_hit":                 3,
        "wia_per_hit":                10,
        "collateral_usd_per_btk":   8_000_000,    # 10% stray (waves push off course) × $80M
        "collateral_kia_per_btk":     1.0,   # 10% × 10 avg crew on commercial vessel
        "n_arc_override": 8,     # slowest weapon: 8 segments sufficient
        "interceptor_style": "us_naval_gun",
        "t_int_range":  (0.80, 0.98),
        "react_range":  (15, 45),
        "sites": ["Bandar Abbas", "Qeshm Island", "Jask", "Chahbahar",
                  "Bushehr", "Minab", "Lar"],
    },
    "Fattah-1 HGV": {
        # Hypersonic Glide Vehicle — magenta/purple (beyond the red scale; next-generation threat)
        # Fattah-1: Mach 13–15 terminal, skip-glide trajectory, range 1,400 km
        # Sources: IRGCN announcement Jun 2023; CSIS Missile Threat; Jane's DW 2024
        # SM-6 Block IA: ~2% P(k) vs HGV (radar track loss during glide maneuvers)
        "speed_km_s": 4.0,          # average speed including glide phase (~Mach 12 equiv.)
        "peak_alt_m": 80_000,       # skip-glide at 80 km (lower ceiling than MRBM)
        "sea_skim":   False,
        "color":    "ccff00ff",     # AABBGGRR: magenta (B=ff, G=00, R=ff) — beyond red scale
        "color_bt": "ffff22ff",
        "width": 4, "width_bt": 5,
        "label": "Fattah-1 HGV (magenta — hypersonic glide vehicle, near-uninterceptable)",
        "cost_usd": 3_000_000,      # estimate; Iran hasn't disclosed; $2M–5M range
        "damage_per_hit_usd":       400_000_000,   # kinetic energy + 580 kg warhead; likely mission-kills any escort
        "kia_per_hit":              100,
        "wia_per_hit":              250,
        "collateral_usd_per_btk": 15_000_000,
        "collateral_kia_per_btk":   3.0,
        "n_arc_override": 28,
        "intercept_prob_override":  0.05,   # ~5% P(k) vs SM-6 Block IA against HGV
        "t_int_range":  (0.90, 0.97),
        "react_range":  (20, 40),
    },
}

# ============================================================
# SINGLE-SHOT PROBABILITY OF KILL (SSPK) — Open-source estimates
# ============================================================
# Sources: Wilkening (Science & Global Security 2000); CSBA Salvo Competition (2015);
# RAND Multilayer BMD; DOT&E FY2018/2022; JINSA Shielded by Fire (Aug 2025);
# FPRI Shallow Ramparts (Oct 2025); Red Sea/Houthi campaign data (2023-2025);
# MDA design goals (0.80-0.90 per shot); Vice Adm. McLane (2024): ~50% vs complex targets.
MUNITION_SSPK = {
    "Shahab-3 MRBM":         {"interceptor": "SM-6 SBT",        "sspk": 0.65, "notes": "Non-maneuvering, large RCS; SM-6 SBT favored over SM-2 at Mach 3-4 terminal"},
    "Noor ASCM":             {"interceptor": "ESSM / RAM Blk2",  "sspk": 0.80, "notes": "Sea-skimmer compresses radar acq; ESSM 0.75-0.85, RAM 0.85-0.95, CIWS 0.40-0.65"},
    "Fateh-110 SRBM":        {"interceptor": "SM-6 SBT",        "sspk": 0.65, "notes": "Short warning window; predictable trajectory; SM-6 SBT primary"},
    "Emad MRBM":             {"interceptor": "SM-6 SBT",        "sspk": 0.45, "notes": "MaRV terminal maneuvering degrades Pk ~0.10-0.20; documented PAC-3 MSE defeat"},
    "Zolfaghar SRBM":        {"interceptor": "SM-6 SBT",        "sspk": 0.50, "notes": "Mach 5+ compresses window; terminal maneuvering; PAC-3 defeat documented (JINSA 2025)"},
    "Khalij Fars ASBM":      {"interceptor": "SM-6 SBT",        "sspk": 0.60, "notes": "EO/IR seeker; shorter range than DF-21D; 100% SM-6 intercept rate vs Houthi ASBMs (small n)"},
    "CM-302 Supersonic ASCM":{"interceptor": "SM-6",            "sspk": 0.55, "notes": "Mach 2-3 sea-skimmer; only SM-6 viable (SM-2 speed-limited); compressed 3-5s terminal window"},
    "Fateh-313 SRBM":        {"interceptor": "SM-6 SBT",        "sspk": 0.60, "notes": "Advanced precision SRBM; solid fuel; moderate terminal maneuvering"},
    "Shahed-136":            {"interceptor": "RAM Blk2 / CIWS", "sspk": 0.83, "notes": "RAM Blk2 95% trials; CIWS 0.55-0.75; cost-exchange drives Mk45/gun use at ~$20K/drone"},
    "IRGCN Sea Drone":       {"interceptor": "CIWS / Mk38",     "sspk": 0.80, "notes": "Surface engagement mode; thin unarmored hull; Mk38 25mm primary; swarm saturation main risk"},
    "Fattah-1 HGV":          {"interceptor": "SM-6 (terminal)", "sspk": 0.20, "notes": "Mach 13-15; near-uninterceptable; Fattah-2 not intercepted in June 2025 conflict (WANA/JINSA)"},
}

# ============================================================
# SCENARIOS  (scaled to 8 CSGs, post-50%-pre-strike degradation)
# ============================================================
# All scenario n_missiles values reflect a 50% reduction from pre-strike
# inventory, modelling a US/IAF suppression campaign before the main attack.
#
# ── Iran Pre-Strike Inventory Estimates (March 2026 context) ────────────────
#
# Shahed-136 / loitering munitions (all variants incl. Shahed-131/149):
#   Pre-strike Low:  ~40,000  (RUSI Nov 2023: 1,700–2,400 original + 400/day
#                    production × 2 yr; minus ~2,200 exported to Russia)
#   Pre-strike High: ~80,000  (Israeli intelligence estimate; Iran's own Jan 2026
#                    claim; IDF: ~400/day production; source: DefenceSecurityAsia
#                    Feb 2026; CNBC Mar 2026)
#   Post-50% strike: 20,000–40,000 drones available
#
# Ballistic missiles (all types, post-June-2025-conflict reconstitution):
#   Pre-strike Low:  ~1,500  (Alma Research Feb 2026; 19FortyFive Feb 2026:
#                    "1,500 missiles ready"; post-Apr+Oct 2024 exchange losses
#                    ~380 fired, then partially replenished)
#   Pre-strike High: ~2,500  (IDF intelligence estimate Feb 2026; CENTCOM
#                    Gen. McKenzie 2022: "3,000+" pre-war; FDD Feb 2026)
#     By type (IISS Military Balance 2024 / CSIS Missile Threat 2024):
#       Shahab-3 MRBM:    25–50   (NASIC 2017; most converted to Ghadr-1 variants)
#       Emad MRBM:        50–100  (operational since 2015; limited production)
#       Fateh-110 SRBM:   500–800 (solid-fuelled; core tactical system since 2004)
#       Fateh-313 SRBM:   200–400 (500 km range; operational since 2015)
#       Zolfaghar SRBM:   100–200 (700 km; first used operationally 2017)
#       Khalij Fars ASBM: 50–100  (300 km quasi-ballistic; operational 2014)
#       Fattah-1 HGV:     20–50   (very limited; complex production; used Oct 2024)
#   Post-50% strike: 750–1,250 ballistic missiles available
#
# Anti-Ship Cruise Missiles:
#   Noor (C-802 derivative): Pre-strike 200–400 (IISS 2024; 60 on Qeshm 1997 +
#                    coastal batteries; source: Jane's DW 2024)
#   CM-302 supersonic: Pre-strike 0–30 (STILL UNDER NEGOTIATION with China as of
#                    Mar 2026; not yet operationally deployed; source: JINSA Mar 2026)
#   Post-50% strike: Noor 100–200; CM-302 0–15
#
# IRGCN Surface Drones:
#   Pre-strike: ~500–800 (after IRIS Shahid Bagheri drone carrier destroyed in
#               Operation Epic Fury 2025–2026; ONI/USNI News 2024 "several hundred")
#   Post-50% strike: 250–400 available
#
SCENARIOS = {
    "low": {
        "label": "Scenario A -- Low Capability (8 CSGs)",
        "description": (
            "SITUATION: Iran executes a limited retaliatory probe using exclusively legacy munitions "
            "from its pre-2020 inventory. After absorbing approximately 50% inventory losses to "
            "US pre-emptive strikes, the IRGC deploys only the most widely dispersed assets "
            "remaining. This scenario establishes the floor of Iranian offensive capability and "
            "tests whether legacy systems can penetrate a fully-alerted 8-CSG Aegis screen.\n\n"
            "PHASE 1 — DRONE SWARM (T+0 to T+60 min): 665 Shahed-136 loitering munitions depart "
            "from dispersed coastal cells across a 600 km frontage between Bushehr and Chahbahar. "
            "Each drone navigates autonomously via GPS-waypoint routing at ~185 km/h and 100–150 m "
            "AGL, using terrain masking along the Zagros foothills before descending over the Gulf. "
            "The aggregate track density across 665 slow-movers overwhelms automated CIWS "
            "engagement queuing; CIWS engages at max rate but cannot clear every track before "
            "saturation. 135 IRGCN surface drones sprint from Qeshm Island and Bandar Abbas "
            "harbor, using the island's radar shadow to approach inner-screen DDGs unseen.\n\n"
            "PHASE 2 — BALLISTIC AND CRUISE SALVO (concurrent): 106 Shahab-3 MRBMs lift from "
            "hardened tunnels at Isfahan and Dezful on steep lofted trajectories peaking at "
            "~280 km altitude. Re-entry at Mach 6–7 compresses SM-6 engagement windows to "
            "40–90 seconds per missile. Terminal CEP is poor (~500 m) but 500 kg warheads make "
            "near-misses devastating against unarmored escort hulls. 80 Noor anti-ship cruise "
            "missiles (C-802 derivative, 165 kg shaped-charge warhead) depart at sea-skimming "
            "altitude (5–10 m AGL), approaching end-on to defeat over-the-horizon radar "
            "acquisition until inside Phalanx range. 79 Fateh-110 SRBMs complete the salvo.\n\n"
            "US RESPONSE: 160 TLAM/JASSM rounds targeting coastal batteries — Bandar Abbas, "
            "Qeshm Island, Jask, Minab — are launched in the first 40 minutes. Primary Shahed "
            "launch cells and ASCM coastal batteries are prioritized; several sites go silent "
            "before exhausting their full quotas.\n\n"
            "ASSESSMENT: Legacy munitions allow Aegis to achieve the highest intercept rate of "
            "any Iran-offensive scenario (~69% SSPK). Shahab-3's predictable terminal phase "
            "gives SM-6 high-confidence fire solutions. Nevertheless, 335 breakthrough munitions "
            "cause concentrated damage across multiple escort destroyers. The low total count "
            "(1,065) is the binding constraint — post-strike inventory limits Iran to a single "
            "moderate-sized salvo with no follow-on capacity.\n\n"
            "265 missiles + 665 air drones + 135 sea drones = 1,065 total | "
            "~730 intercepted | ~335 breakthrough."
        ),
        "n_missiles":    4800,          # ~3,000 Shaheds (post-50% strike; 6,000 pre-strike)
        "intercept_cap": 4000,
        "intercept_rate": 0.688,
        "wave_s":         3600,
        "n_arc":           14,
        "n_sm6":           20,
        "n_us_strikes_per_csg": 20,   # 20 × 8 CSGs = 160 total strikes
        "munitions": [
            {"name": "Shahed-136",      "weight": 0.625},   # 665/1065
            {"name": "IRGCN Sea Drone", "weight": 0.127},   # 135/1065
            {"name": "Shahab-3 MRBM",  "weight": 0.099},   # 106/1065
            {"name": "Noor ASCM",       "weight": 0.075},   # 80/1065
            {"name": "Fateh-110 SRBM",  "weight": 0.074},   # 79/1065
        ],
    },
    "medium": {
        "label": "Scenario B -- Medium Capability (8 CSGs)",
        "description": (
            "SITUATION: Iran deploys its second-generation precision missile arsenal alongside "
            "a full-scale drone swarm. This scenario reflects Iran's assessed post-strike "
            "'realistic high' available inventory: modern maneuvering ballistic missiles paired "
            "with mass drone saturation to degrade layered defenses before precision rounds "
            "arrive. All 8 CSGs are engaged simultaneously.\n\n"
            "DRONE LAYER: 1,335 Shahed-136 and 200 IRGCN surface drones launch in a rolling "
            "swarm across the breadth of the Gulf, flooding all 8 CSG CIWS nodes concurrently. "
            "RAM and SeaRAM fire continuously during the first 30 minutes, drawing down close-in "
            "magazines before the ballistic threat arrives. ESSM handles mid-altitude cruise "
            "threats but its 50 km engagement zone is quickly exhausted by sheer track density.\n\n"
            "PRECISION MISSILE LAYER: 200 Emad MRBMs (Shahab-3 derivative with maneuvering "
            "re-entry vehicle; range 1,700 km, 750 kg warhead) execute 3–4g terminal evasive "
            "maneuvers, degrading SM-6 SSPK from ~90% to ~72% through expanded search windows. "
            "264 Zolfaghar SRBMs (700 km range, GPS+inertial, ~10 m CEP) arrive in salvos of "
            "4–6 per CSG, saturating the Aegis fire control queue. 201 Khalij Fars anti-ship "
            "ballistic missiles (300 km range, EO/IR terminal seeker) track the CVNs directly. "
            "Their Mach 10+ terminal velocity provides only 25–35 seconds of SM-6 intercept "
            "opportunity per missile in this engagement geometry — the primary kill mechanism "
            "against carrier-sized targets.\n\n"
            "US RESPONSE: 240 TLAM/JASSM rounds suppress coastal sites. Inland batteries at "
            "Isfahan, Kerman, and Shiraz remain active throughout; IAF packages engage them "
            "from T+120 min onward.\n\n"
            "ASSESSMENT: The drone/ballistic combination produces the first large-scale CSG "
            "damage events. With 793 breakthrough rounds distributed across 8 hulls, the "
            "statistical probability of mission-killing at least 2–3 escort DDGs exceeds 80%. "
            "The Khalij Fars ASBM is the primary carrier threat, each requiring a 2-round "
            "SM-6 salvo for confident kill — rapidly exhausting magazines.\n\n"
            "665 missiles + 1,335 air drones + 200 sea drones = 2,200 total | "
            "~1,407 intercepted | ~793 breakthrough."
        ),
        "n_missiles":    8250,          # ~5,000 Shaheds (post-50% strike; 5K cap per scenario)
        "intercept_cap": 4000,
        "intercept_rate": 0.645,
        "wave_s":         3600,
        "n_arc":           12,
        "n_sm6":           20,
        "n_us_strikes_per_csg": 30,   # 30 × 8 = 240 total
        "munitions": [
            {"name": "Shahed-136",       "weight": 0.607},   # 1335/2200
            {"name": "IRGCN Sea Drone",  "weight": 0.091},   # 200/2200
            {"name": "Emad MRBM",        "weight": 0.091},   # 200/2200
            {"name": "Zolfaghar SRBM",   "weight": 0.120},   # 264/2200
            {"name": "Khalij Fars ASBM", "weight": 0.091},   # 201/2200
        ],
    },
    "realistic": {
        "label": "Scenario D -- Realistic: Simultaneous Detection-Launch (8 CSGs)",
        "description": (
            "SITUATION: Iran's integrated air-defense network detects inbound Israeli Air Force "
            "strike packages — F-35I Adirs, F-15I Ra'ams, and F-16I Sufas — crossing into "
            "Iranian radar coverage over the Negev and Jordan Valley. The IRGC Air Defense "
            "commander, under standing doctrine (Karari Command Center, openly described in IRGC "
            "press releases through 2024), immediately authorises a full offensive salvo: every "
            "available TEL, coastal battery, and drone cell is ordered to fire within minutes.\n\n"
            "SIMULTANEOUS LAUNCH (T=0, compressed 0–30 min window): Iran commits its full "
            "post-preemption inventory in a single compressed salvo lasting approximately "
            "30 minutes — far shorter than the 60-minute drone-first doctrine of other scenarios. "
            "Drones and ballistic/cruise missiles launch concurrently, not in sequential echelons. "
            "The rationale is operationally sound: Iran correctly anticipates that each minute of "
            "delay after detection allows further IAF packages to close, and that simultaneous "
            "multi-type saturation degrades Aegis fire-control more than sequential echelons.\n\n"
            "TACTICAL IMPLICATION — NO PRE-LAUNCH SUPPRESSION: The TLAM/JASSM strike packages "
            "launched from US CSGs take 45–90 minutes to reach Iranian sites. IAF aircraft, "
            "detected the moment they triggered Iran's launch, will not reach their targets "
            "for another 10–20 minutes. Every Iranian launch site is ACTIVE for the full "
            "compressed salvo window. The pre-emptive suppression that degrades other scenarios "
            "provides zero benefit here — Iran fires its full inventory before a single US or "
            "IAF munition lands.\n\n"
            "COMPRESSED SATURATION EFFECT: With ~5,000 Shahed-136 drones, ~1,000 IRGCN surface "
            "drones, and all ballistic/cruise missiles in the air within 30 minutes, Aegis radar "
            "and SM-6 fire-control channels face maximum simultaneous track density earlier in the "
            "engagement. CIWS magazines are consumed faster. The intercept rate degrades to ~58% "
            "vs ~63% in the phased scenario — a modest difference but compounded over thousands "
            "of rounds.\n\n"
            "US/IAF STRIKES: 240 TLAM/JASSM rounds and three IAF packages engage all 12 sites "
            "but arrive only after Iran's complete inventory is airborne. Sites are destroyed "
            "systematically — they simply have no missiles left to launch. The counterstrikes "
            "serve to prevent any follow-on salvo, not to suppress this one.\n\n"
            "This scenario represents the intelligence community's most credible assessment "
            "of Iranian launch behavior given post-2024 conflict doctrine disclosures and "
            "the observed Iranian salvo in April 2024 (170 drones + 30 cruise missiles + "
            "110 ballistic missiles fired simultaneously at Israel)."
        ),
        "n_missiles":    7250,           # 5,000 Shaheds + proportional missiles (5K cap)
        "intercept_cap": 4000,
        "intercept_rate": 0.580,         # lower: compressed launch reduces Aegis reaction time
        "wave_s":         3600,          # used for US strike launch window; not Iranian launches
        "n_arc":           10,
        "n_sm6":           16,
        "n_us_strikes_per_csg": 30,
        "iran_detection_launch": True,   # Iran fires on IAF detection — no phase separation
        "iran_launch_window_s":  1800,   # all Iranian launches within T=0 to T+30 min
        "munitions": [
            {"name": "Shahed-136",       "weight": 0.690},   # ~5,000 Shaheds
            {"name": "IRGCN Sea Drone",  "weight": 0.137},   # ~990 surface drones
            {"name": "Emad MRBM",        "weight": 0.058},   # ~420 Emad MRBMs
            {"name": "Zolfaghar SRBM",   "weight": 0.058},   # ~420 Zolfaghar
            {"name": "Khalij Fars ASBM", "weight": 0.057},   # ~415 Khalij Fars
        ],
    },
    "high": {
        "label": "Scenario C -- High Capability / CAP HIT (8 CSGs)",
        "description": (
            "SITUATION: Iran fires near-maximum available post-strike inventory in a single "
            "compressed salvo, deliberately breaching the Aegis 4,000-round intercept capacity "
            "ceiling. This scenario tests the fundamental arithmetic limit of layered missile "
            "defense: when incoming track count exceeds the total intercept magazine across "
            "all 8 CSGs, no amount of per-shot SSPK improvement prevents breakthroughs.\n\n"
            "DRONE SATURATION (T+0 to T+60 min): 2,665 Shahed-136 at full 50% post-strike "
            "inventory inundate all 8 Aegis groups simultaneously. With each CSG facing "
            "~333 drones, CIWS magazines are fully exhausted within the first 25–30 minutes. "
            "RAM/SeaRAM racks fire continuously until depleted. ESSM becomes the primary "
            "close-in defense once CIWS is Winchester. 265 IRGCN surface drones exploit "
            "the CIWS exhaustion window to close on escorts unopposed by automated systems, "
            "forcing DDG crews to engage with deck-mounted small arms and 5-inch gun.\n\n"
            "BALLISTIC MASS SALVO (concurrent with drones): 697 Fateh-313 SRBMs (range "
            "500 km, CEP &lt;10 m, GPS/GLONASS terminal guidance) launch from dispersed sites "
            "in a compressed 20-minute window designed to overwhelm Aegis track files. "
            "402 Emad MRBMs provide the deep-strike component, targeting CVNs from ranges "
            "beyond SM-2 intercept. The combined ballistic track density at any given SM-6 "
            "radar exceeds 40 simultaneous tracks — the published limit for SPY-1D(V).\n\n"
            "INTERCEPT CAPACITY EXCEEDED: At 4,030 total tracks against a system-wide "
            "magazine of ~4,000 intercept rounds (SM-6 + SM-2 + ESSM + RAM across 8 "
            "CSGs), the cap is mathematically breached. Even at theoretical 100% SSPK, "
            "the last ~30–2,046 rounds have no interceptor to meet them.\n\n"
            "US RESPONSE: 320 TLAM/JASSM strikes target all 12 launch sites. Most coastal "
            "batteries are suppressed by T+60 min, but the ballistic salvo was already "
            "in flight before the first impacts. Inland sites at Isfahan and Dezful absorb "
            "strikes but continue launching from dispersed TELs during the suppression.\n\n"
            "ASSESSMENT: This is a catastrophic outcome for the US fleet. Multiple CSGs are "
            "destroyed (10+ hits each). The post-strike environment would see the US "
            "operating with severely reduced carrier aviation capacity for months.\n\n"
            "1,100 missiles + 2,665 air drones + 265 sea drones = 4,030 total | "
            "~1,984 intercepted | ~2,046 breakthrough [INTERCEPT CAP HIT]."
        ),
        "n_missiles":    7565,          # ~5,000 Shaheds (post-50% strike; 5K cap)
        "intercept_cap": 4000,
        "intercept_rate": 0.496,
        "wave_s":         3600,
        "n_arc":           10,
        "n_sm6":           16,
        "n_us_strikes_per_csg": 40,   # 40 × 8 = 320 total
        "munitions": [
            {"name": "Shahed-136",      "weight": 0.661},   # 2665/4030
            {"name": "IRGCN Sea Drone", "weight": 0.066},   # 266/4030
            {"name": "Fateh-313 SRBM",  "weight": 0.173},   # 697/4030
            {"name": "Emad MRBM",       "weight": 0.100},   # 402/4030
        ],
    },
    "iran_best": {
        "label": "Scenario E -- Best Case Iran / CAP HIT (8 CSGs)",
        "description": (
            "SITUATION: Iran achieves maximum operational coordination — full inventory "
            "commitment, synchronized multi-domain launch, and prolonged 90-minute salvo "
            "duration that exhausts US interceptor magazines before the final waves arrive. "
            "This represents the assessed upper bound of Iranian offensive capacity after "
            "50% pre-strike attrition. It is the worst-case planning scenario for US "
            "carrier strike group survivability.\n\n"
            "DRONE TSUNAMI (T+0 to T+90 min): 4,000 Shahed-136 drones — Iran's full "
            "remaining inventory commitment — launch in rolling waves from 12 sites across "
            "a 1,200 km coastal frontage. Rather than a single spike, the waves are "
            "staggered in 15-minute packets to prevent US CIWS from recovering between "
            "engagements. By T+30 min, all 8 CSG CIWS systems are Winchester. By T+45 min, "
            "RAM/SeaRAM racks are expended. From T+45 min onward, the only close-in "
            "defense is ESSM (50 km range, not optimized for low-slow targets) and "
            "5-inch naval gun. 400 IRGCN surface drones provide persistent harassment of "
            "inner-screen DDGs, forcing gun engagements that further distract Aegis from "
            "the ballistic track picture.\n\n"
            "PRECISION MISSILE SURGE (T+30 to T+90 min): 335 Emad MRBMs, 335 Khalij Fars "
            "ASBMs, and 330 Fateh-313 SRBMs launch from inland sites after the drone wave "
            "has consumed close-in defensive capacity. These arrive during the CIWS-exhausted "
            "window, facing only SM-6/SM-2 (already partially depleted by the first-wave "
            "drone engagements). The Khalij Fars ASBM is the primary carrier-killer: its "
            "EO/IR seeker acquires the CVN flight deck at 45 km altitude and maneuvers "
            "to hit the island structure or flight deck arresting gear.\n\n"
            "INTERCEPT CAP BREACH: The 4,000-round system-wide magazine is exhausted by "
            "approximately T+60 min. The final 1,400 missiles/drones arrive against a "
            "fleet that has shot its last interceptor. US counterstrikes (320 TLAM/JASSM) "
            "destroyed most coastal sites by T+75 min — too late to stop the inland salvo "
            "already in flight.\n\n"
            "ASSESSMENT: Catastrophic fleet loss. Historical comparison: the 1945 "
            "Kamikaze campaign at Okinawa sank 34 ships and damaged 386 more using "
            "~1,465 aircraft over 82 days. This scenario delivers a comparable volume "
            "against 8 CSGs in under 90 minutes.\n\n"
            "1,000 missiles + 4,000 air drones + 400 sea drones = 5,400 total | "
            "~1,981 intercepted | ~3,419 breakthrough [INTERCEPT CAP HIT]."
        ),
        "n_missiles":    6750,          # ~5,000 Shaheds — maximum available (5K cap)
        "intercept_cap": 4000,
        "intercept_rate": 0.370,
        "wave_s":         5400,
        "n_arc":            8,
        "n_sm6":           12,
        "n_us_strikes_per_csg": 40,   # 40 × 8 = 320 total
        "munitions": [
            {"name": "Shahed-136",       "weight": 0.741},   # 4000/5400
            {"name": "IRGCN Sea Drone",  "weight": 0.074},   # 400/5400
            {"name": "Emad MRBM",        "weight": 0.062},   # 335/5400
            {"name": "Khalij Fars ASBM", "weight": 0.062},   # 335/5400
            {"name": "Fateh-313 SRBM",   "weight": 0.061},   # 330/5400
        ],
    },
    "usa_best": {
        "label": "Scenario F -- Best Case USA (8 CSGs)",
        "description": (
            "SITUATION: US pre-emptive strikes have degraded Iranian capabilities to the "
            "minimum viable threshold — approximately 30% of pre-crisis inventory remains "
            "operational. Iranian command-and-control is disrupted, launches are poorly "
            "coordinated, and salvos arrive in small uncoordinated packets rather than "
            "synchronized waves. This scenario benchmarks maximum US defensive performance.\n\n"
            "IRANIAN CAPABILITY: 665 total munitions launched from surviving sites: "
            "400 Shahed-136 drones arrive in staggered groups of 10–20 rather than "
            "coordinated mass waves, giving CIWS clear engagements between groups. "
            "65 IRGCN surface drones attempt to close but are detected early and "
            "engaged by DDG 5-inch guns at 15+ km, well outside naval gun effective range. "
            "200 legacy missiles — Shahab-3 MRBMs, Noor ASCMs, Fateh-110 SRBMs — are "
            "the only ballistic/cruise component. Without coordination with the drone "
            "wave, they arrive into fully-loaded CIWS and maximum SM-6 availability.\n\n"
            "US DEFENSIVE PERFORMANCE: Fully-alerted Aegis with SPY-6 (Ford-class) and "
            "SPY-1D(V) achieves 93% intercept rate. Shahab-3 terminal phases are tracked "
            "from 1,200 km out by E-2D Hawkeye; SM-6 engages at 240 km with high "
            "confidence. Noor sea-skimmers are detected by DDG SPY-1D at 45 km and "
            "meet dual Phalanx engagement. SeaRAM mops up surviving drones. ESSM is "
            "barely used — SM-6 clears the threat at standoff.\n\n"
            "US COUNTERSTRIKE: 480 TLAM/JASSM strikes — the heaviest strike package of "
            "any scenario — systematically eliminate all 12 Iranian launch sites. With "
            "60 rounds per CSG, each site receives 3–5× the 25-hit destruction threshold. "
            "All sites are inactivated by T+75 min; no follow-on salvo is possible.\n\n"
            "ASSESSMENT: Only ~51 rounds break through, causing minor damage to 2–3 "
            "escort destroyers with no CVN hits. All 8 CSGs remain fully operational. "
            "Iran's launch network is effectively dismantled by T+90 min. This scenario "
            "validates the strategic case for pre-emptive action: catching Iran's missiles "
            "on the ground is decisively superior to intercepting them in flight.\n\n"
            "200 missiles + 400 air drones + 65 sea drones = 665 total | "
            "~614 intercepted | ~51 breakthrough — fleet intact."
        ),
        "n_missiles":    1660,          # ~1,000 Shaheds (Iran badly degraded post-strike)
        "intercept_cap": 4000,
        "intercept_rate": 0.932,
        "wave_s":         3600,
        "n_arc":           16,
        "n_sm6":           24,
        "n_us_strikes_per_csg": 60,
        "munitions": [
            {"name": "Shahed-136",      "weight": 0.602},   # 400/665
            {"name": "IRGCN Sea Drone", "weight": 0.098},   # 65/665
            {"name": "Shahab-3 MRBM",  "weight": 0.150},   # 100/665
            {"name": "Noor ASCM",       "weight": 0.090},   # 60/665
            {"name": "Fateh-110 SRBM",  "weight": 0.060},   # 40/665
        ],
    },

    # ==============================================================
    # PHASED SCENARIOS G, H, I
    # Doctrine: drone swarm launches first (Phase 1, hr 0–1) to exhaust
    # CIWS / RAM / ESSM.  Ballistic and cruise missiles follow (Phase 2,
    # hr 1–2), arriving while defenses are depleted.
    # Iran's stated "layered saturation" doctrine mirrors this sequence.
    # Intercept rates are worse than uncoordinated equivalents because
    # CIWS magazines are partially empty when missiles arrive.
    # ==============================================================
    "drone_first_low": {
        "label": "Scenario G -- Drone-First Low (Phased Assault)",
        "description": (
            "SITUATION: Iran employs its documented 'multi-echelon saturation' doctrine "
            "with legacy munitions. IRGCN tactical doctrine publicly describes sequential "
            "drone/missile launch sequences; this scenario applies that concept at minimum "
            "post-strike inventory. The key innovation vs. Scenario A (Low) is temporal "
            "separation: drones deplete CIWS magazines first, then legacy missiles arrive "
            "into a degraded defensive environment.\n\n"
            "PHASE 1 — DRONE/SURFACE SWARM (T+0 to T+60 min): All 665 Shahed-136 "
            "drones and 135 surface drones launch simultaneously. Unlike uncoordinated "
            "Scenario A, launch timing is compressed to ensure the entire drone wave "
            "engages within the same 60-minute window, maximizing CIWS saturation overlap. "
            "Phalanx systems engage at maximum cyclic rate. RAM/SeaRAM draws down by "
            "T+35–45 min. When CIWS begins reloading at T+50 min, there is a critical "
            "3–8 minute gap — precisely when the Phase 2 ballistic missiles are scheduled "
            "to enter inner defense zones.\n\n"
            "PHASE 2 — LEGACY MISSILE SALVO (T+60 to T+120 min): 265 missiles launch "
            "from surviving sites during the drone wave's final phase, timed to arrive "
            "while CIWS is reloading. Shahab-3 MRBMs, Noor sea-skimming ASCMs, and "
            "Fateh-110 SRBMs engage during the post-CIWS gap. Without the overwhelming "
            "track density of Scenario B or D, SM-6 has more available channels per "
            "missile — but the CIWS depletion effect still degrades intercept rate "
            "from 69% (Scenario A uncoordinated) to 65% (Scenario G phased).\n\n"
            "PHASING BONUS: The 4% intercept rate reduction equates to ~43 additional "
            "breakthroughs vs. the equivalent uncoordinated attack. Against 8 CSGs, "
            "43 extra hits changes 2–3 'damaged' outcomes to 'mission-killed'.\n\n"
            "265 missiles + 665 air drones + 135 sea drones = 1,065 total | "
            "~690 intercepted | ~375 breakthrough (43 more than uncoordinated Scenario A)."
        ),
        "n_missiles":    5600,          # ~3,500 Shaheds (drone-first emphasis)
        "intercept_cap": 4000,
        "intercept_rate": 0.650,   # worse than uncoordinated A (0.688) — CIWS preoccupied
        "wave_s":         7200,    # total scenario: 2 hours (covers both phases)
        "phase1_end_s":   3600,    # drones launch in first hour
        "phase2_start_s": 3600,    # missiles begin after all drones are airborne
        "phase2_dur_s":   3600,    # missile launch window: second hour
        "n_arc":           14,
        "n_sm6":           20,
        "n_us_strikes_per_csg": 20,
        "munitions": [
            {"name": "Shahed-136",      "weight": 0.625},   # 665/1065
            {"name": "IRGCN Sea Drone", "weight": 0.127},   # 135/1065
            {"name": "Shahab-3 MRBM",  "weight": 0.099},   # 105/1065
            {"name": "Noor ASCM",       "weight": 0.075},   # 80/1065
            {"name": "Fateh-110 SRBM",  "weight": 0.074},   # 80/1065
        ],
    },
    "drone_first_medium": {
        "label": "Scenario H -- Drone-First Medium (Phased Assault)",
        "description": (
            "SITUATION: Iran applies phased doctrine at medium capability — 1,335 Shahed "
            "drones fully exhaust all CIWS capacity before the precision missile layer "
            "arrives. This is the most tactically sophisticated medium-capability Iranian "
            "scenario and approximates doctrinal outputs from IRGCN war-gaming publications "
            "obtained through open-source intelligence.\n\n"
            "PHASE 1 — CIWS EXHAUSTION (T+0 to T+60 min): 1,335 Shahed-136 and 200 "
            "surface drones attack in three rolling sub-waves of ~450 drones each, "
            "separated by 15-minute intervals. The sub-wave timing is critical: "
            "each wave exhausts the remaining CIWS ammunition before the next arrives, "
            "preventing reload. By T+55 min, all 8 CSG Phalanx systems are Winchester "
            "and RAM/SeaRAM racks are empty. Only ESSM (50 km, limited drone track "
            "discrimination) and SM-6 (overkill cost-per-drone ~$4.3M vs $20k threat) "
            "remain available for close-in defense.\n\n"
            "PHASE 2 — PRECISION STRIKE (T+60 to T+120 min): 665 precision missiles "
            "launch from inland sites after confirming the drone wave is through the "
            "outer defense rings. 200 Emad MRBMs with maneuvering RVs arrive into a "
            "CIWS-naked fleet. 264 Zolfaghar SRBMs saturate SM-6 fire control channels. "
            "201 Khalij Fars ASBMs — the primary CVN killers — acquire carrier flight "
            "decks at terminal descent with no close-in backup remaining.\n\n"
            "COORDINATION PENALTY FOR US: The phasing adds ~200 breakthrough rounds vs. "
            "uncoordinated Scenario B (793→892), representing an additional 2–4 escort "
            "destroyers mission-killed and significantly higher CVN damage probability.\n\n"
            "US RESPONSE: 240 TLAM/JASSM strikes, but with perfect timing impossible "
            "during a 2-hour engagement, several launches occur from partially-suppressed "
            "sites. Coastal batteries suppressed by T+50 min cannot stop the inland salvo.\n\n"
            "665 missiles + 1,335 air drones + 200 sea drones = 2,200 total | "
            "~1,308 intercepted | ~892 breakthrough (99 more than Scenario B)."
        ),
        "n_missiles":    8250,          # ~5,000 Shaheds (drone-first; 5K cap per scenario)
        "intercept_cap": 4000,
        "intercept_rate": 0.600,   # worse than uncoordinated B (0.645)
        "wave_s":         7200,
        "phase1_end_s":   3600,
        "phase2_start_s": 3600,
        "phase2_dur_s":   3600,
        "n_arc":           12,
        "n_sm6":           20,
        "n_us_strikes_per_csg": 30,
        "munitions": [
            {"name": "Shahed-136",       "weight": 0.607},   # 1335/2200
            {"name": "IRGCN Sea Drone",  "weight": 0.091},   # 200/2200
            {"name": "Emad MRBM",        "weight": 0.091},   # 200/2200
            {"name": "Zolfaghar SRBM",   "weight": 0.120},   # 264/2200
            {"name": "Khalij Fars ASBM", "weight": 0.091},   # 201/2200
        ],
    },
    "drone_first_high": {
        "label": "Scenario I -- Drone-First High Saturation (Phased Assault)",
        "description": (
            "SITUATION: Iran combines maximum drone employment with precision missile mass "
            "in a 2-hour phased assault. Unlike Scenario C (High, uncoordinated), the "
            "phasing is deliberate and operationally significant: the drone wave arrives "
            "60 minutes before the ballistic layer, ensuring CIWS capacity reaches zero "
            "before the first missile enters close-in defensive range. This is the "
            "worst-case phased scenario and the most operationally sophisticated.\n\n"
            "PHASE 1 — TOTAL CIWS EXHAUSTION (T+0 to T+60 min): 2,665 Shaheds "
            "and 265 surface drones attack in a continuous rolling stream. Track density "
            "peaks at ~333 simultaneous Shahed contacts per CSG. Phalanx engages at "
            "maximum 4,500 rpm but with 333 tracks, engagement queuing is impossible — "
            "the system can only engage one track at a time. RAM fires all 63–105 rounds "
            "per CSG in the first 20 minutes. SeaRAM exhausted by T+25 min. "
            "ESSM begins engaging Shaheds at 50 km — a $1.5M round vs a $20k drone. "
            "By T+45 min, all CIWS systems are Winchester. The last 15 minutes of the "
            "drone wave arrives completely uncontested by close-in systems.\n\n"
            "PHASE 2 — UNCONTESTED MISSILE SURGE (T+60 to T+120 min): 697 Fateh-313 "
            "SRBMs and 402 Emad MRBMs launch from inland batteries. They fly into a "
            "fleet with zero Phalanx, zero RAM, and SM-6 magazines already partially "
            "depleted by drone engagements during Phase 1. Intercept rate collapses to "
            "46% — the lowest of any scenario — as SM-6 is the last line of defense "
            "against threats originally designed for multi-layer engagement.\n\n"
            "US COUNTERSTRIKE: 320 TLAM/JASSM destroy most coastal sites by T+90 min. "
            "However, the Phase 2 ballistic salvo launched from inland sites at T+60 "
            "is already in flight — suppression came 30 minutes too late.\n\n"
            "ASSESSMENT: Fleet-wide catastrophic damage. Phase coordination reduces "
            "intercept rate from 46% (vs. 50% uncoordinated) producing ~324 additional "
            "breakthroughs vs Scenario C. All 8 CSGs face mission-kill probability >70%.\n\n"
            "1,100 missiles + 2,665 air drones + 265 sea drones = 4,030 total | "
            "~1,842 intercepted | ~2,188 breakthrough."
        ),
        "n_missiles":    7565,          # ~5,000 Shaheds (drone-first; 5K cap)
        "intercept_cap": 4000,
        "intercept_rate": 0.460,   # worst intercept rate — CIWS exhausted by drones
        "wave_s":         7200,
        "phase1_end_s":   3600,
        "phase2_start_s": 3600,
        "phase2_dur_s":   3600,
        "n_arc":           10,
        "n_sm6":           16,
        "n_us_strikes_per_csg": 40,
        "munitions": [
            {"name": "Shahed-136",      "weight": 0.661},   # 2665/4030
            {"name": "IRGCN Sea Drone", "weight": 0.066},   # 266/4030
            {"name": "Fateh-313 SRBM",  "weight": 0.173},   # 697/4030
            {"name": "Emad MRBM",       "weight": 0.100},   # 402/4030
        ],
    },
    "coordinated_strike": {
        "label": "Scenario G -- US/IAF Coordinated First Strike (Perfect Timing)",
        "description": (
            "SITUATION: The United States and Israel achieve true time-on-target synchronization "
            "for the opening strike window. All US TLAM/JASSM packages and Israeli Air Force "
            "munitions are pre-launched (missiles in flight before T=0) and arrive on Iranian "
            "launch sites within the first 5 minutes of the conflict timeline. This tests the "
            "maximum impact of pre-emptive suppression on Iran's launch capacity.\n\n"
            "STRIKE EXECUTION: 400 TLAM/JASSM rounds (50 per CSG × 8 CSGs) were launched "
            "hours before T=0, timing their flights to impact Iranian sites at T+0 to T+5 min. "
            "Simultaneously, the Israeli Air Force executes three coordinated packages:\n"
            "  - Nevatim AB (F-35I Adir): 55 sorties × 2 JDAM-ER = 110 precision strikes "
            "    on coastal battery control nodes at &lt;80 km standoff range\n"
            "  - Hatzerim AB (F-15I Ra'am): 40 sorties × 2 Rampage ALCM = 80 standoff strikes "
            "    at 250 km range against ballistic missile TEL storage and hardened tunnels\n"
            "  - Ramon AB (F-16I Sufa): 73 sorties × 2 SPICE-2000 = 146 precision glide bomb "
            "    strikes on dispersed launch sites\n\n"
            "SUPPRESSION EFFECT: Sites receiving 25+ hits in the T+0 to T+5 window go silent "
            "before their TELs can position and launch. Multiple coastal batteries are destroyed "
            "before the first Shahed drone is airborne. Iranian OOB is reduced from the notional "
            "1,935 total to a degraded subset as site-suppressed launches are eliminated.\n\n"
            "RESIDUAL IRANIAN STRIKE: Missiles already on launchers and partially-committed "
            "drone sorties launch despite incoming US/IAF fires — 1,935 total planned, "
            "but surviving site launches represent the actual salvo. US intercept rate "
            "rises to 78% as fewer tracks overwhelm Aegis and SM-6 has more engagement "
            "time per track.\n\n"
            "COMPARISON TO SCENARIO D: Same Iranian OOB as Realistic, but strike timing "
            "produces ~280 fewer breakthroughs (441 vs. 713) — validating the strategic "
            "value of precisely-timed pre-emptive action over reactive defense.\n\n"
            "1,935 total (same OOB as Realistic) | ~1,494 intercepted | ~441 breakthrough."
        ),
        "n_missiles":    7250,          # ~5,000 Shaheds (same OOB as realistic; 5K cap)
        "intercept_cap": 4000,
        "intercept_rate": 0.780,   # higher P(k): fewer missiles, less CIWS saturation
        "wave_s":         3600,
        "n_arc":           10,
        "n_sm6":           20,     # fewer breakthroughs → SM-6 not exhausted early
        "n_us_strikes_per_csg": 50,  # 50 × 8 CSGs = 400 total; pre-loaded strike packages
        "us_strike_timing": "perfect",   # all impacts arrive at t=0±300s
        "iaf_timing": "perfect",         # IAF coordinated in same opening window
        "munitions": [
            {"name": "Shahed-136",       "weight": 0.690},   # same mix as realistic
            {"name": "IRGCN Sea Drone",  "weight": 0.137},
            {"name": "Emad MRBM",        "weight": 0.058},
            {"name": "Zolfaghar SRBM",   "weight": 0.058},
            {"name": "Khalij Fars ASBM", "weight": 0.057},
        ],
    },

    # ------------------------------------------------------------------
    # SCENARIO H — Iranian Intelligence-Driven Focused Salvo
    # ------------------------------------------------------------------
    "focused_salvo": {
        "label": "Scenario H -- Iranian Focused Salvo (All Fire on CVN-78 Ford)",
        "description": (
            "SITUATION: Iranian intelligence — likely from space-based electro-optical "
            "reconnaissance, signals intelligence intercepts, and commercial satellite "
            "imagery analysis — confirms the precise position of USS Gerald R. Ford "
            "(CVN-78), the fleet's most advanced carrier and de facto task force flagship. "
            "Iran elects to concentrate ALL 1,935 available munitions on this single "
            "target rather than distributing across 8 CSGs. The other 7 carrier strike "
            "groups are not engaged.\n\n"
            "TACTICAL RATIONALE: Sinking or disabling CVN-78 would deliver maximum "
            "strategic shock — removing the Ford-class's ANB-3 nuclear propulsion, "
            "Advanced Weapons Elevator, Electromagnetic Aircraft Launch System (EMALS), "
            "and Advanced Arresting Gear (AAG), all irreplaceable in a conflict timeframe. "
            "Iran's assessment: it is better to certainly kill one carrier than probably "
            "damage eight. Loss of CVN-78 would degrade US carrier aviation capability "
            "for 2–5 years during repair.\n\n"
            "FORD'S DEFENSIVE CAPACITY: CVN-78 has 3× Mk 49 RAM launchers (63 rounds) "
            "plus SeaRAM. Escorts — 3× DDG-51 Flight III plus CG-60 USS Normandy — "
            "provide SM-6 (66 rounds), SM-2 (203 rounds), ESSM (144 rounds). Total "
            "magazine is substantial but designed for a distributed threat environment, "
            "not 1,935 incoming tracks simultaneously. Ford's 6-ship screen will exhaust "
            "its 66 SM-6 rounds against the first ~40 ballistic tracks, leaving remaining "
            "threats for SM-2 and CIWS engagement only.\n\n"
            "DRONE SATURATION: 1,335 Shaheds target Ford's specific GPS coordinates. "
            "CIWS and RAM are exhausted within 25 minutes. From T+25 min onward, "
            "breakthroughs reach the hull and flight deck continuously.\n\n"
            "OUTCOME: Same Iranian OOB as Scenario D (Realistic), but concentrated on "
            "one hull. CVN-78 is mission-killed with high probability. The other 7 CSGs "
            "are undamaged and available for counter-strike operations.\n\n"
            "1,935 total (all fire on CVN-78) | ~1,222 intercepted | ~713 breakthrough "
            "concentrated on one target."
        ),
        "n_missiles":    7250,          # ~5,000 Shaheds — all on one hull (5K cap)
        "intercept_cap": 4000,
        "intercept_rate": 0.634,  # same P(k) as realistic
        "wave_s":         3600,
        "n_arc":           10,
        "n_sm6":           16,
        "n_us_strikes_per_csg": 30,
        "focus_csg": "USS Gerald R. Ford (CVN-78)",   # all Iranian fire on this hull
        "munitions": [
            {"name": "Shahed-136",       "weight": 0.690},
            {"name": "IRGCN Sea Drone",  "weight": 0.137},
            {"name": "Emad MRBM",        "weight": 0.058},
            {"name": "Zolfaghar SRBM",   "weight": 0.058},
            {"name": "Khalij Fars ASBM", "weight": 0.057},
        ],
    },

    # ------------------------------------------------------------------
    # SCENARIO I — Hypersonic Threat (Fattah-1 HGV Deployment)
    # ------------------------------------------------------------------
    "hypersonic_threat": {
        "label": "Scenario I -- Hypersonic Threat (Fattah-1 HGV + Realistic Mix)",
        "description": (
            "SITUATION: Iran operationalizes the Fattah-1 hypersonic glide vehicle — "
            "announced by IRGCN in June 2023, claimed Mach 13–15, range 1,400 km. "
            "If operational as claimed, the Fattah-1 represents a fundamental challenge "
            "to layered ballistic missile defense: its skip-glide trajectory defeats "
            "AEGIS SPY-1/SPY-6 track prediction, and SM-6 Block IA has no reliable "
            "intercept solution against Mach 13+ maneuvering hypersonic targets.\n\n"
            "HYPERSONIC GLIDE VEHICLE THREAT PROFILE: The Fattah-1 launches on a "
            "depressed trajectory to ~80 km altitude (vs. ~280 km for Shahab-3), "
            "then glides at Mach 13–15 with 3–4g lateral maneuvering capability. "
            "Three critical implications:\n"
            "  1. SHORT FLIGHT TIME: At Mach 13 and 1,400 km range, time-of-flight is "
            "     ~6 minutes — halving the SM-6 engagement window vs. a Shahab-3 MRBM.\n"
            "  2. UNPREDICTABLE TERMINAL PATH: Skip-glide creates radar track "
            "     discontinuities that defeat AEGIS fire control prediction algorithms.\n"
            "  3. INTERCEPT ALTITUDE: Gliding at 40–60 km altitude is above CIWS/RAM "
            "     ceiling and at the edge of SM-6 Block IA endo-atmospheric envelope — "
            "     P(k) ~5% vs. ~90% for conventional ballistic TBMs.\n\n"
            "SCENARIO COMPOSITION: 168 Fattah-1 HGVs replace a fraction of the Realistic "
            "scenario's ballistic layer. The remaining mix of Emad MRBMs, Zolfaghar SRBMs, "
            "and Khalij Fars ASBMs is unchanged. Drones are identical to Scenario D. "
            "The hypersonic component is nearly uninterceptable: only 5% are killed by "
            "SM-6, meaning 160 of 168 HGVs reach their targets. At 80,000 m peak altitude "
            "and 4 km/s terminal velocity, kinetic impact energy alone (no explosive warhead "
            "required) is sufficient to mission-kill an escort-class hull.\n\n"
            "ASSESSMENT: The hypersonic layer alone causes more kills than the entire "
            "non-HGV ballistic component combined. Breakthrough count rises from 713 "
            "(Realistic) to ~820 (+107), with additional hits concentrated on "
            "previously-underserved targets. Source: CSIS Missile Threat / Jane's DW "
            "2024 / IRGCN June 2023 public announcement.\n\n"
            "1,935 total | ~1,115 intercepted | ~820 breakthrough (168 near-uninterceptable HGVs)."
        ),
        "n_missiles":    7250,          # ~5,000 Shaheds + HGV layer (5K cap)
        "intercept_cap": 4000,
        "intercept_rate": 0.634,
        "wave_s":         3600,
        "n_arc":           10,
        "n_sm6":           16,
        "n_us_strikes_per_csg": 30,
        "munitions": [
            {"name": "Shahed-136",       "weight": 0.690},   # ~7,000 Shaheds
            {"name": "IRGCN Sea Drone",  "weight": 0.137},   # 265/1935
            {"name": "Fattah-1 HGV",    "weight": 0.087},   # 168/1935
            {"name": "Emad MRBM",        "weight": 0.029},   # 56/1935
            {"name": "Zolfaghar SRBM",   "weight": 0.029},   # 56/1935
            {"name": "Khalij Fars ASBM", "weight": 0.028},   # 55/1935
        ],
    },

    # ------------------------------------------------------------------
    # SCENARIO J — Pure Ballistic Barrage
    # ------------------------------------------------------------------
    "ballistic_barrage": {
        "label": "Scenario J -- Pure Ballistic Barrage (No Drones, SM-6 Undistracted)",
        "description": (
            "SITUATION: Iran conducts a pure ballistic strike with no drone component — "
            "a scenario that might occur if drone inventory was exhausted in a prior "
            "engagement phase or if Iran assesses that launching drones against fully-alerted "
            "CIWS is wasteful. This tests a fundamentally different threat geometry: "
            "without CIWS saturation, SM-6 operates at maximum efficiency, but every "
            "breakthrough carries far greater destructive power than a Shahed drone.\n\n"
            "THREAT COMPOSITION (600 missiles, no drones): The ballistic mix maximizes "
            "warhead payload — all selected munitions carry 450–750 kg unitary warheads:\n"
            "  - Shahab-3 MRBM (15%, 90 rounds): 500 kg warhead, Mach 6–7 terminal, "
            "    high-arc parabolic trajectory; legacy but still lethal on escort hits\n"
            "  - Emad MRBM (20%, 120 rounds): 750 kg warhead, maneuvering RV, "
            "    primary CVN-killer threat in this scenario\n"
            "  - Zolfaghar SRBM (25%, 150 rounds): 450 kg, GPS precision &lt;10m CEP, "
            "    targets command nodes and flight deck structures\n"
            "  - Khalij Fars ASBM (25%, 150 rounds): EO/IR terminal seeker discriminates "
            "    carrier from escort; purpose-built for this engagement\n"
            "  - Fateh-313 SRBM (15%, 90 rounds): 450 kg GPS precision; targets "
            "    communications and radar arrays\n\n"
            "US DEFENSIVE ADVANTAGE: Without drone saturation, CIWS magazines are fully "
            "available throughout the engagement. SM-6 radar is not competing with 1,335 "
            "slow Shahed tracks — all fire control channels are dedicated to ballistic "
            "threats. This raises intercept rate from ~63% (Realistic) to ~85%. SM-2 "
            "engages mid-altitude threats below SM-6 range. ESSM has no role.\n\n"
            "HOWEVER — EACH HIT IS CATASTROPHIC: The 90 breakthrough rounds are all "
            "heavy unitary warheads. No $20k drones in the breakthrough count — every "
            "hit is a 450–750 kg shaped-charge or kinetic-penetrating warhead designed "
            "to defeat armored deck structures. Expected damage per hit is 2–4× greater "
            "than the mixed scenarios. Even at 15% breakthrough rate, catastrophic "
            "hull losses are probable.\n\n"
            "ASSESSMENT: Iran fires fewer rounds but achieves higher-value hits per "
            "breakthrough. The ballistic-only approach is optimal when drone inventory "
            "is exhausted — trading quantity for per-hit lethality.\n\n"
            "600 ballistic missiles (no drones) | ~510 intercepted | ~90 breakthrough "
            "(all heavy warhead capable of mission-kill)."
        ),
        "n_missiles":     600,
        "intercept_cap": 4000,
        "intercept_rate": 0.850,   # undistracted SM-6/SM-2; no CIWS pre-exhaustion
        "wave_s":         1800,    # 30-minute rapid volley
        "n_arc":           12,
        "n_sm6":           20,     # full magazine available; no CIWS trades
        "n_us_strikes_per_csg": 30,
        "munitions": [
            {"name": "Shahab-3 MRBM",    "weight": 0.15},
            {"name": "Emad MRBM",        "weight": 0.20},
            {"name": "Zolfaghar SRBM",   "weight": 0.25},
            {"name": "Khalij Fars ASBM", "weight": 0.25},
            {"name": "Fateh-313 SRBM",   "weight": 0.15},
        ],
    },

    # ------------------------------------------------------------------
    # SCENARIO K — ASCM Swarm (Sea-Skimming Saturation)
    # ------------------------------------------------------------------
    "ascm_swarm": {
        "label": "Scenario K -- ASCM Swarm (1,000 Sea-Skimming Anti-Ship Missiles)",
        "description": (
            "SITUATION: Iran executes a pure anti-ship cruise missile swarm — no ballistic "
            "missiles, no drones — using maximum available ASCM inventory plus maximum "
            "theoretical capacity from ship-launched and submarine-launched platforms. "
            "NOTE: This scenario exceeds Iran's estimated post-strike ASCM inventory "
            "(post-50%: ~100–215 Noor; CM-302 not yet delivered per JINSA Mar 2026). "
            "It models a theoretical maximum ASCM commitment assuming all coastal, "
            "surface, and submarine platforms fire simultaneously.\n\n"
            "MISSILE COMPOSITION:\n"
            "  - 600 Noor ASCM (C-802 derivative): Iran's primary sea-skimming anti-ship "
            "    missile. 165 kg shaped-charge warhead designed to penetrate ship hull "
            "    below the waterline. Subsonic (~0.9 Mach), sea-skimming at 5–10 m AGL. "
            "    Launched from Bandar Abbas, Jask, Qeshm, and Minab coastal batteries, "
            "    IRGCN frigates, and fast-attack craft. Iran has held Noor exercises "
            "    targeting carrier-sized inflatable targets in the Gulf.\n"
            "  - 400 CM-302 Supersonic ASCM (if delivered): Mach 3 sea-skimmer with "
            "    250 kg warhead — a Chinese-derived Ramjet-powered anti-ship missile "
            "    negotiated by Iran but not yet operationally deployed. At Mach 3 and "
            "    5 m AGL, CIWS has &lt;1.5 seconds of engagement time from radar acquisition "
            "    to impact. SM-6 has poor target discrimination against sea-level targets "
            "    approaching end-on in radar clutter.\n\n"
            "DEFENSIVE CHALLENGE: CIWS/SeaRAM is the primary defense against sea-skimmers "
            "— SM-6's radar performance degrades significantly tracking low-altitude "
            "sea-skimming targets in Gulf surface clutter. However, at 1,000 simultaneous "
            "ASCM tracks, CIWS saturation occurs rapidly. Phalanx engages at minimum "
            "range (~1.5 km for air threats) with limited engagement time per target. "
            "Against Mach 3 CM-302, the Phalanx radar-to-fire cycle is compressed from "
            "the nominal 1.5 seconds to under 0.5 seconds — too fast for reliable tracking.\n\n"
            "ASSESSMENT: 450 breakthroughs, all sea-skimming ASCMs with shaped-charge "
            "warheads designed for maximum hull penetration. This is the scenario "
            "most analogous to the 1982 Falklands (Exocet) or 1967 Eilat sinking. "
            "Each hit has a high probability of flooding and progressive loss of buoyancy.\n\n"
            "1,000 ASCMs (600 Noor + 400 CM-302) | ~550 intercepted | ~450 breakthrough."
        ),
        "n_missiles":    1000,
        "intercept_cap": 4000,
        "intercept_rate": 0.550,   # CIWS/SeaRAM-dominated; saturates at high volume
        "wave_s":         3600,
        "n_arc":           12,
        "n_sm6":           10,     # SM-6 less effective vs sea-skimmers; fewer shots taken
        "n_us_strikes_per_csg": 30,
        "munitions": [
            {"name": "Noor ASCM",              "weight": 0.60},   # 1,200 Noor
            {"name": "CM-302 Supersonic ASCM", "weight": 0.40},   # 800 CM-302
        ],
    },

    # ------------------------------------------------------------------
    # SCENARIO L — Shore-Based Layered Defense (THAAD + Patriot + Aegis)
    # ------------------------------------------------------------------
    "strait_transit": {
        "label": "Scenario M -- Strait of Hormuz Column Transit (Maximum Threat)",
        "description": (
            "SITUATION: All 8 CSGs transit the Strait of Hormuz in single-file column — "
            "the only navigable deep-water channel (38–96 km wide, main shipping lane "
            "12 km wide per IISS Military Balance 2024). Lead ship USS Abraham Lincoln "
            "is at 26.622°N, 56.515°E heading 310° (northwest into the Gulf), with all "
            "8 hulls 15 km apart in trail formation. This is the highest-threat tactical "
            "geometry possible: all 12 Iranian coastal batteries can engage the entire "
            "column, with standoff distances as short as 35 km.\n\n"
            "GEOGRAPHY: Bandar Abbas (Iran's primary naval base and Shahed launch hub) "
            "is &lt;40 km from the lead ship's initial position. Qeshm Island sits inside "
            "the strait itself — its batteries can fire from multiple aspect angles "
            "simultaneously, defeating single-bearing countermeasure deployment. "
            "Jask (57.77°E) is 85 km from the column's tail — within Noor ASCM "
            "engagement range for the entire transit duration.\n\n"
            "TACTICAL DISADVANTAGE FOR US:\n"
            "  1. COMPRESSED REACTION TIME: At &lt;40 km standoff, ASCM flight time is "
            "     under 80 seconds. SM-6 needs 2–3 minutes to engage at maximum range — "
            "     close-range engagement windows are cut to 20–35 seconds per missile.\n"
            "  2. NO EVASIVE MANEUVER: The strait's 12 km shipping lane leaves ships "
            "     with &lt;3 km lateral deviation room — Khalij Fars ASBM EO/IR seekers "
            "     cannot be defeated by evasion at these widths.\n"
            "  3. COLUMN GEOMETRY: 8 hulls in trail creates a 120 km long target "
            "     string. Every Iranian coastal battery can engage any ship in the "
            "     column simultaneously, maximizing overlap of coverage zones.\n"
            "  4. CHAFF INEFFECTIVE: At close range and high relative speed, chaff "
            "     bloom dispersal time exceeds ASCM terminal homing lock-on window.\n\n"
            "INTERCEPT RATE: Drops to 55% (vs. 63% in open water Realistic scenario) "
            "due to compressed engagement windows and multi-aspect threat geometry.\n\n"
            "HISTORICAL NOTE: The USS Stark (FFG-31) was struck by two Exocet missiles "
            "at 37 km range in 1987 with no successful intercept. The column geometry "
            "in this scenario presents standoffs 50% shorter than the Stark incident.\n\n"
            "1,935 total | ~1,057 intercepted | ~878 breakthrough (165 more than Scenario D)."
        ),
        "n_missiles":    7250,          # ~5,000 Shaheds (strait engagement; 5K cap)
        "intercept_cap": 4000,
        "intercept_rate": 0.550,   # short standoff → compressed intercept windows
        "wave_s":         3600,
        "n_arc":           10,
        "n_sm6":           14,     # less reaction time; fewer SM-6 shots per engagement
        "n_us_strikes_per_csg": 30,
        "csg_fleet": STRAIT_CSGS,   # 8 CSGs in column at strait entrance
        "munitions": [
            {"name": "Shahed-136",       "weight": 0.690},
            {"name": "IRGCN Sea Drone",  "weight": 0.137},
            {"name": "Emad MRBM",        "weight": 0.058},
            {"name": "Zolfaghar SRBM",   "weight": 0.058},
            {"name": "Khalij Fars ASBM", "weight": 0.057},
        ],
    },
    "shore_based_defense": {
        "label": "Scenario L -- Shore-Based Layered Defense (THAAD + PAC-3 + Aegis)",
        "description": (
            "SITUATION: US pre-deploys shore-based ballistic missile defense assets to the "
            "Gulf region before hostilities — a real capability available as of 2024. "
            "THAAD batteries at UAE Al Dhafra AB, Saudi Arabia Prince Sultan AB, and Qatar "
            "Al Udeid AB (all confirmed by CENTCOM 2024 posture statement) add a high-altitude "
            "ballistic intercept tier. Patriot PAC-3 MSE batteries at Kuwait Ali Al Salem "
            "and Bahrain Isa AB cover the medium-altitude ballistic layer. Combined with "
            "Aegis afloat, this creates a genuine three-tier layered defense architecture.\n\n"
            "DEFENSIVE ARCHITECTURE:\n"
            "  TIER 1 — THAAD (Terminal High Altitude Area Defense): Engages ballistic "
            "  targets at 150–200 km altitude, providing 'above the atmosphere' kill above "
            "  AEGIS/SM-6 ceiling. THAAD's hit-to-kill kinetic interceptor has assessed "
            "  P(k) ~85% vs. short-range and medium-range ballistic missiles in non-"
            "  stressed (non-swarming) environment. Each AN/TPY-2 radar provides 1,000+ km "
            "  search range — detects Iranian MRBM launches from midpoint of Zagros range.\n"
            "  TIER 2 — Patriot PAC-3 MSE: Engages ballistic targets at 30–80 km altitude, "
            "  filling the gap between THAAD (high) and Aegis SM-6 (mid). PAC-3 MSE "
            "  provides active radar seeker with 'hit-to-kill' kinetic final intercept. "
            "  Assessed P(k) ~70–80% vs. Shahab-3/Emad class at this tier.\n"
            "  TIER 3 — Aegis SM-6/SM-2/ESSM: Unchanged from other scenarios.\n\n"
            "COMBINED EFFECT: The three-tier architecture creates shoot-look-shoot "
            "opportunities: if THAAD misses, PAC-3 takes a shot; if PAC-3 misses, SM-6 "
            "takes a shot. Combined P(k) rises from ~63% (Aegis alone) to ~85% (all tiers). "
            "Intercept capacity jumps from 4,000 to 6,000 — THAAD and Patriot add "
            "~2,000 additional intercept slots beyond the Aegis magazine. Same Iranian OOB "
            "as Scenario D (Realistic): 1,935 total.\n\n"
            "ASSESSMENT: Shore-based layered defense reduces breakthroughs from 713 "
            "(Realistic) to 301 — a 58% reduction in damage. This validates the strategic "
            "investment in THAAD regional deployment (FMS approval: Saudi Arabia $15B, "
            "UAE multiple systems per DSCA). The 301 remaining breakthroughs are almost "
            "entirely drones and sea-skimmers that defeat the ballistic intercept tiers.\n\n"
            "Sources: CENTCOM 2024 posture statement; DSCA THAAD Saudi FMS; Jane's DW 2024.\n\n"
            "1,935 total | ~1,634 intercepted | ~301 breakthrough (58% fewer than Scenario D)."
        ),
        "n_missiles":    7250,          # ~5,000 Shaheds (5K cap; layered defense scenario)
        "intercept_cap": 6000,     # THAAD + Patriot adds ~2,000 extra intercept slots
        "intercept_rate": 0.850,   # layered P(k): THAAD (~85% vs TBM) + Patriot + Aegis
        "wave_s":         3600,
        "n_arc":           10,
        "n_sm6":           20,     # Aegis not exhausted as much; SM-6 focused
        "n_us_strikes_per_csg": 30,
        "munitions": [
            {"name": "Shahed-136",       "weight": 0.690},
            {"name": "IRGCN Sea Drone",  "weight": 0.137},
            {"name": "Emad MRBM",        "weight": 0.058},
            {"name": "Zolfaghar SRBM",   "weight": 0.058},
            {"name": "Khalij Fars ASBM", "weight": 0.057},
        ],
    },
}

# ============================================================
# MATH / GEO HELPERS
# ============================================================

def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def lerp(a, b, t):
    return a + t * (b - a)


def arc_points(lon1, lat1, lon2, lat2, peak_alt_m, n, sea_skim):
    pts = []
    for i in range(n + 1):
        t = i / n
        lon = lerp(lon1, lon2, t)
        lat = lerp(lat1, lat2, t)
        if sea_skim:
            alt = max(5.0, peak_alt_m * (1 + 0.5 * math.sin(math.pi * t)))
        else:
            alt = max(10.0, peak_alt_m * 4 * t * (1 - t))
        pts.append((lon, lat, alt))
    return pts


def coords2(p1, p2):
    return (f"{p1[0]:.6f},{p1[1]:.6f},{p1[2]:.1f} "
            f"{p2[0]:.6f},{p2[1]:.6f},{p2[2]:.1f}")


def circle_ring(clon, clat, radius_km, n=72):
    R = 6371.0
    pts = []
    for i in range(n + 1):
        theta = 2 * math.pi * i / n
        dlat  = math.degrees(radius_km / R * math.cos(theta))
        dlon  = math.degrees(radius_km / R * math.sin(theta)
                              / math.cos(math.radians(clat)))
        pts.append((clon + dlon, clat + dlat))
    return " ".join(f"{lo:.6f},{la:.6f},0" for lo, la in pts)


def weighted_choice(items, rng):
    total = sum(m["weight"] for m in items)
    r, cumsum = rng.random() * total, 0.0
    for item in items:
        cumsum += item["weight"]
        if r <= cumsum:
            return item
    return items[-1]


def safe_id(name):
    return ("mun_" + name.lower()
            .replace(" ", "_").replace("-", "_")
            .replace("/", "_").replace("(", "").replace(")", ""))


def _kml_to_css(kml_hex):
    """Convert 8-char AABBGGRR KML colour to CSS #RRGGBB."""
    return f"#{kml_hex[6:8]}{kml_hex[4:6]}{kml_hex[2:4]}"


# ── Project-wide HTML popup colour palette ────────────────────────────────────
_C_ACTIVE      = "#00dd66"   # green       – healthy / active
_C_OPERATIONAL = "#66cc22"   # lime        – operational (minor damage)
_C_DEGRADED    = "#ffaa00"   # amber       – degraded
_C_NEUTRALIZED = "#ff2222"   # red         – destroyed (CSG/site)
_C_INTERCEPT   = "#00ffaa"   # bright cyan – kill confirmed
_C_BT          = "#ff3333"   # vivid red   – breakthrough / impact
_C_AI          = "#ff5500"   # orange-red  – AI-guided threat
_C_US_CSG      = "#3399ff"   # blue        – US carrier group
_C_IRAN_SITE   = "#ff6600"   # orange      – Iranian launch site
_C_US_STRIKE   = "#00ff66"   # lime green  – US TLAM / JASSM
_C_LABEL       = "#7fa8cc"   # muted blue  – row label text
_C_DATA        = "#e8f0ff"   # near-white  – default data value
_C_DIM         = "#445566"   # dark        – footnote / dim info

# Black BalloonStyle injected into every KML <Style> block
_BB = (
    '<BalloonStyle>'
    '<bgColor>ff000000</bgColor>'
    '<textColor>ffe8f0ff</textColor>'
    '<text>$[description]</text>'
    '</BalloonStyle>'
)


def _html_popup(title, accent, rows, footer=None):
    """Return a CDATA-wrapped dark-theme HTML popup for KML description bubbles.

    accent : CSS colour string for the accent bar/title  e.g. '#ff4444'
    rows   : list of (label, value) or (label, value, value_colour) tuples
    footer : optional plain-text footnote string
    """
    tr_parts = []
    for row in rows:
        label = row[0];  val = row[1]
        vc    = row[2] if len(row) > 2 else _C_DATA
        tr_parts.append(
            f'<tr>'
            f'<td style="color:{_C_LABEL};padding:3px 12px 3px 0;'
            f'white-space:nowrap;vertical-align:top">{label}</td>'
            f'<td style="color:{vc};font-weight:bold">{val}</td>'
            f'</tr>'
        )
    footer_html = (
        f'<div style="margin-top:8px;padding-top:6px;border-top:1px solid {accent}44;'
        f'color:{_C_DIM};font-size:11px">{footer}</div>'
        if footer else ""
    )
    return (
        "<![CDATA["
        # negative margin bleeds the div to the balloon edges (GE adds ~15 px padding)
        f'<div style="background:#000000;color:{_C_DATA};'
        f'font-family:\'Courier New\',Courier,monospace;'
        f'padding:14px 16px;margin:-15px -15px -20px -15px;'
        f'border-left:4px solid {accent};border-top:3px solid {accent}">'
        f'<div style="color:{accent};font-weight:bold;font-size:13px;'
        f'letter-spacing:2px;margin-bottom:9px;padding-bottom:5px;'
        f'border-bottom:1px solid {accent}66">{title}</div>'
        f'<table style="width:100%;border-collapse:collapse">'
        + "".join(tr_parts)
        + f'</table>{footer_html}</div>'
        "]]>"
    )

# ============================================================
# KML STYLE BLOCK
# ============================================================

def kml_styles():
    ICON_ARROW   = "http://maps.google.com/mapfiles/kml/shapes/triangle.png"
    ICON_PLANE   = "http://maps.google.com/mapfiles/kml/shapes/airports.png"
    ICON_FERRY   = "http://maps.google.com/mapfiles/kml/shapes/ferry.png"
    ICON_STAR    = "http://maps.google.com/mapfiles/kml/shapes/star.png"
    ICON_CIRCLE  = "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"

    _DRONE_SCALES = {"Fattah-1 HGV": 1.5,
                     "Emad MRBM": 1.3, "Khalij Fars ASBM": 1.3, "CM-302 Supersonic ASCM": 1.3,
                     "Shahab-3 MRBM": 1.1, "Zolfaghar SRBM": 1.1, "Fateh-313 SRBM": 1.1,
                     "Fateh-110 SRBM": 1.0, "Noor ASCM": 1.0,
                     "Shahed-136": 0.7, "IRGCN Sea Drone": 0.7}

    def icon_block(href, color, scale):
        return (f"<IconStyle><color>{color}</color><scale>{scale}</scale>"
                f"<Icon><href>{href}</href></Icon></IconStyle>"
                f"<LabelStyle><scale>0</scale></LabelStyle>")

    parts = []

    for mname, mdef in MUNITIONS.items():
        sid   = safe_id(mname)
        sc    = _DRONE_SCALES.get(mname, 1.0)
        if mname == "Shahed-136":
            icon = ICON_PLANE
        elif mname == "IRGCN Sea Drone":
            icon = ICON_FERRY
        else:
            icon = ICON_ARROW
        ib    = icon_block(icon, mdef["color"], sc)
        ib_bt = icon_block(icon, mdef["color_bt"], min(sc * 1.15, 2.0))
        parts.append(f"""
  <Style id="{sid}">
    {ib}
    <LineStyle><color>{mdef['color']}</color><width>{mdef['width']}</width></LineStyle>
  </Style>
  <Style id="{sid}_bt">
    {ib_bt}
    <LineStyle><color>{mdef['color_bt']}</color><width>{mdef['width_bt']}</width></LineStyle>
  </Style>""")

    # Shahed-136 AI terminal redirect — white precision icon
    parts.append(f"""
  <Style id="shahed_ai_terminal">
    {icon_block(ICON_PLANE, "ffffffff", 0.9)}
    <LineStyle><color>ffffffff</color><width>3</width></LineStyle>
  </Style>""")

    # IAF munition styles (lime/teal family)
    for mname, mdef in IAF_MUNITIONS.items():
        sid = safe_id(mname) + "_iaf"
        ib  = icon_block(ICON_PLANE, mdef["color"], 0.9)
        parts.append(f"""
  <Style id="{sid}">
    {ib}
    <LineStyle><color>{mdef['color']}</color><width>{mdef['width']}</width></LineStyle>
  </Style>""")

    # US strike munition styles
    for sname, sdef in US_STRIKE_MUNITIONS.items():
        sid = safe_id(sname)
        ib  = icon_block(ICON_ARROW, sdef["color"], 1.0)
        parts.append(f"""
  <Style id="{sid}">
    {ib}
    <LineStyle><color>{sdef['color']}</color><width>{sdef['width']}</width></LineStyle>
  </Style>""")

    # US interceptor tracks — all blue family; SM-6/SM-2 (star), CIWS/NavGun (circle)
    # AABBGGRR blue tones: B=ff keeps all tracks in blue family
    # us_lo:  light steel blue  RGB(136,204,255) = ff cc 88 → "aaffcc88"  (unchanged)
    # us_mid: cornflower blue   RGB( 68,136,255) = ff 88 44 → "bbff8844"  (unchanged)
    # us_hi:  deep navy blue    RGB(  0, 68,255) = ff 44 00 → "eeff4400"  (unchanged)
    # us_ciws: bright sky blue  RGB(  0,153,255) = ff 99 00 → "bbff9900"  (was teal)
    # us_naval_gun: azure blue  RGB( 51,153,255) = ff 99 33 → "bbff9933"  (was seafoam)
    for sid, width, color, icon, sc in [
        ("us_lo",        2, "aaffcc88", ICON_STAR,   0.8),
        ("us_mid",       3, "bbff8844", ICON_STAR,   0.8),
        ("us_hi",        4, "eeff4400", ICON_STAR,   0.8),
        ("us_ciws",      2, "bbff9900", ICON_CIRCLE, 0.6),
        ("us_naval_gun", 2, "bbff9933", ICON_CIRCLE, 0.6),
    ]:
        ib = icon_block(icon, color, sc)
        parts.append(f"""
  <Style id="{sid}">
    {ib}
    <LineStyle><color>{color}</color><width>{width}</width></LineStyle>
  </Style>""")

    parts.append("""
  <Style id="us_defense_ring">
    <!-- SM-6 240 km — deep navy blue: RGB(00,22,ff) AABBGGRR=77ff2200 -->
    <LineStyle><color>77ff2200</color><width>1</width></LineStyle>
    <PolyStyle><color>0aff2200</color><fill>1</fill><outline>1</outline></PolyStyle>
  </Style>
  <Style id="us_defense_ring_sm2">
    <!-- SM-2 167 km — cornflower blue: RGB(44,88,ff) AABBGGRR=55ff8844 -->
    <LineStyle><color>55ff8844</color><width>1</width></LineStyle>
    <PolyStyle><color>05ff8844</color><fill>1</fill><outline>1</outline></PolyStyle>
  </Style>
  <Style id="us_defense_ring_essm">
    <!-- ESSM 50 km — sky blue: RGB(00,aa,ff) AABBGGRR=88ffaa00 -->
    <LineStyle><color>88ffaa00</color><width>1</width></LineStyle>
    <PolyStyle><color>08ffaa00</color><fill>1</fill><outline>1</outline></PolyStyle>
  </Style>
  <Style id="us_defense_ring_ram">
    <!-- RAM 15 km — cyan: RGB(00,cc,ff) AABBGGRR=aaffcc00 -->
    <LineStyle><color>aaffcc00</color><width>1</width></LineStyle>
    <PolyStyle><color>0affcc00</color><fill>1</fill><outline>1</outline></PolyStyle>
  </Style>
  <Style id="us_defense_ring_hit">
    <!-- SM-6 DEGRADED — warm orange outline signals damage: RGB(ff,66,00) AABBGGRR=cc0066ff -->
    <LineStyle><color>cc0066ff</color><width>2</width></LineStyle>
    <PolyStyle><color>220066ff</color><fill>1</fill><outline>1</outline></PolyStyle>
  </Style>
  <Style id="us_defense_ring_sm2_hit">
    <!-- SM-2 DEGRADED — orange: RGB(ff,88,00) AABBGGRR=880088ff -->
    <LineStyle><color>880088ff</color><width>1</width></LineStyle>
    <PolyStyle><color>110088ff</color><fill>1</fill><outline>1</outline></PolyStyle>
  </Style>
  <Style id="us_defense_ring_essm_hit">
    <!-- ESSM DEGRADED — amber: RGB(ff,aa,00) AABBGGRR=aa00aaff -->
    <LineStyle><color>aa00aaff</color><width>1</width></LineStyle>
    <PolyStyle><color>0a00aaff</color><fill>1</fill><outline>1</outline></PolyStyle>
  </Style>
  <Style id="us_defense_ring_ram_hit">
    <!-- RAM DEGRADED — yellow-amber: RGB(ff,cc,00) AABBGGRR=bb00ccff -->
    <LineStyle><color>bb00ccff</color><width>1</width></LineStyle>
    <PolyStyle><color>0a00ccff</color><fill>1</fill><outline>1</outline></PolyStyle>
  </Style>
  <Style id="us_csg_marker">
    <IconStyle>
      <color>ffffffff</color><scale>1.4</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/paddle/wht-stars.png</href></Icon>
    </IconStyle>
    <LabelStyle><color>ffffffff</color><scale>1.0</scale></LabelStyle>
  </Style>
  <Style id="us_csg_hit_marker">
    <IconStyle>
      <color>ff0060ff</color><scale>1.8</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/paddle/red-circle.png</href></Icon>
    </IconStyle>
    <LabelStyle><color>ff0060ff</color><scale>1.1</scale></LabelStyle>
  </Style>
  <Style id="us_csg_neutralized_marker">
    <IconStyle>
      <color>ff222222</color><scale>1.6</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/paddle/grn-circle.png</href></Icon>
    </IconStyle>
    <LabelStyle><color>ff444444</color><scale>1.0</scale></LabelStyle>
  </Style>
  <Style id="iran_site_marker">
    <IconStyle>
      <color>ff0000ff</color><scale>1.0</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/paddle/red-stars.png</href></Icon>
    </IconStyle>
    <LabelStyle><color>ff0000ff</color><scale>0.8</scale></LabelStyle>
  </Style>
  <Style id="iran_site_inactive">
    <IconStyle>
      <color>ff666666</color><scale>0.8</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/paddle/grn-circle.png</href></Icon>
    </IconStyle>
    <LabelStyle><color>ff888888</color><scale>0.7</scale></LabelStyle>
  </Style>
  <Style id="intercept_marker">
    <!-- US kill point — bright blue star: RGB(00,88,ff) AABBGGRR=ffff8800 -->
    <IconStyle>
      <color>ffff8800</color><scale>0.9</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/star.png</href></Icon>
    </IconStyle>
    <LabelStyle><color>ffff8800</color><scale>0.6</scale></LabelStyle>
  </Style>
  <Style id="impact_marker">
    <!-- Iranian breakthrough impact — warm red target: RGB(ff,00,00) AABBGGRR=ff0000ff -->
    <IconStyle>
      <color>ff0000ff</color><scale>1.3</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/target.png</href></Icon>
    </IconStyle>
    <LabelStyle><color>ff0000ff</color><scale>0.9</scale></LabelStyle>
  </Style>
  <Style id="us_strike_impact_marker">
    <!-- US TLAM/JASSM strike impact — deep blue star: RGB(00,44,ff) AABBGGRR=ffff4400 -->
    <IconStyle>
      <color>ffff4400</color><scale>1.0</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/star.png</href></Icon>
    </IconStyle>
    <LabelStyle><color>ffff4400</color><scale>0.6</scale></LabelStyle>
  </Style>
  <Style id="strike_icon">
    <!-- IAF strike impact on active site — lime star -->
    <IconStyle>
      <color>ff00ff88</color><scale>1.0</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/star.png</href></Icon>
    </IconStyle>
    <LabelStyle><color>ff00ff88</color><scale>0.6</scale></LabelStyle>
  </Style>
  <Style id="dead_icon">
    <!-- IAF strike on already-inactivated site — grey cross -->
    <IconStyle>
      <color>ff888888</color><scale>0.7</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/cross.png</href></Icon>
    </IconStyle>
    <LabelStyle><color>ff888888</color><scale>0.5</scale></LabelStyle>
  </Style>
  <Style id="iaf_base_marker">
    <IconStyle>
      <color>ff00ff88</color><scale>1.2</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/paddle/blu-stars.png</href></Icon>
    </IconStyle>
    <LabelStyle><color>ff00ff88</color><scale>0.9</scale></LabelStyle>
  </Style>""")

    # ── Health-color styles for US CSGs: green (intact) → red (neutralized) ──
    # AABBGGRR: R rises 0→255, G falls 255→0 across 10 damage levels
    _US_ICON = "http://maps.google.com/mapfiles/kml/paddle/wht-stars.png"
    for _n in range(11):
        if _n == 10:
            _c = "ff000000"  # fully neutralized → black
        else:
            _f = _n / 10
            _r = int(255 * _f);  _g = int(255 * (1.0 - _f))
            _c = f"ff00{_g:02x}{_r:02x}"
        parts.append(
            f'  <Style id="us_h_{_n}">'
            f'<IconStyle><color>{_c}</color><scale>1.4</scale>'
            f'<Icon><href>{_US_ICON}</href></Icon></IconStyle>'
            f'<LabelStyle><color>{_c}</color><scale>1.0</scale></LabelStyle>'
            f'</Style>'
        )

    # ── Health-color styles for Iranian sites: blue (active) → orange (destroyed) ──
    # AABBGGRR: B falls 255→0, G rises 0→128, R rises 0→255 across 30 levels
    _IR_ICON         = "http://maps.google.com/mapfiles/kml/paddle/red-stars.png"
    _IR_ICON_DESTROY = "http://maps.google.com/mapfiles/kml/paddle/wht-stars.png"
    for _n in range(31):
        if _n == 30:
            _c    = "ffffffff"  # fully destroyed → white
            _icon = _IR_ICON_DESTROY
        else:
            _f    = _n / 30
            _r    = int(255 * _f);  _g = int(128 * _f);  _b = int(255 * (1.0 - _f))
            _c    = f"ff{_b:02x}{_g:02x}{_r:02x}"
            _icon = _IR_ICON
        parts.append(
            f'  <Style id="ir_h_{_n}">'
            f'<IconStyle><color>{_c}</color><scale>1.25</scale>'
            f'<Icon><href>{_icon}</href></Icon></IconStyle>'
            f'<LabelStyle><color>{_c}</color><scale>1.25</scale></LabelStyle>'
            f'</Style>'
        )

    _raw = "\n".join(parts)
    # Inject black BalloonStyle into every Style block so all popups are fully black
    return _raw.replace("</Style>", f"{_BB}</Style>")

# ============================================================
# GX:TRACK BUILDER  (one Placemark per munition, animated icon)
# ============================================================

def _geodetic_bearing(lon1, lat1, lon2, lat2):
    """Compass bearing in degrees (CW from north) from point 1 to point 2."""
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlon   = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def gx_track(style_id_val, pts, t_pts_s, label, desc_first=""):
    """Return a list containing a single gx:Track Placemark string.
    Includes <gx:angles> at each waypoint so icons face the direction of travel.
    """
    n = len(pts)
    # Compute per-point compass heading from successive positions
    bearings = []
    for k in range(n):
        if k < n - 1:
            b = _geodetic_bearing(pts[k][0], pts[k][1], pts[k+1][0], pts[k+1][1])
        else:
            b = bearings[-1] if bearings else 0.0
        bearings.append(b)

    when_coords = ""
    for (lon, lat, alt), t, brg in zip(pts, t_pts_s, bearings):
        when_coords += (
            f"<when>{fmt_time(sim_time(t))}</when>"
            f"<gx:coord>{lon:.5f} {lat:.5f} {max(0.0, alt):.0f}</gx:coord>"
            f"<gx:angles>{brg:.1f} 0 0</gx:angles>"
        )
    desc_tag  = f"<description>{desc_first}</description>" if desc_first else ""
    t_begin   = fmt_time(sim_time(t_pts_s[0]))
    t_end     = fmt_time(sim_time(t_pts_s[-1]))
    time_span = f"<TimeSpan><begin>{t_begin}</begin><end>{t_end}</end></TimeSpan>"
    return [
        f"      <Placemark>"
        f"<name>{label}</name>"
        f"<styleUrl>#{style_id_val}</styleUrl>"
        + time_span
        + desc_tag
        + f"<gx:Track>"
          f"<altitudeMode>absolute</altitudeMode>"
        + when_coords
        + f"</gx:Track>"
          f"</Placemark>"
    ]

# ============================================================
# FIXED LAYERS
# ============================================================

_CSG_NEUTRALIZATION_HITS = 10   # hits that neutralize a CSG

def gen_us_forces(first_hit_s=None, tenth_hit_s=None, latest_s=3600,
                  csg_fleet=None, hits_timeline=None):
    first_hit_s    = first_hit_s    or {}
    tenth_hit_s    = tenth_hit_s    or {}
    hits_timeline  = hits_timeline  or {}
    if csg_fleet is None:
        csg_fleet = US_CSGS
    out = []

    for csg in csg_fleet:
        lon, lat = csg["lon"], csg["lat"]
        name     = csg["name"]
        fh       = first_hit_s.get(name)
        th       = tenth_hit_s.get(name)

        ring_sm6  = circle_ring(lon, lat, WPN_RANGES["SM-6"])
        ring_sm2  = circle_ring(lon, lat, WPN_RANGES["SM-2"])
        ring_essm = circle_ring(lon, lat, WPN_RANGES["ESSM"])
        ring_ram  = circle_ring(lon, lat, WPN_RANGES["RAM"])

        def ring_pm(label, style, coords, span_tag):
            return (f"""    <Placemark>
      <name>{label}</name><styleUrl>#{style}</styleUrl>
      {span_tag}
      <Polygon><tessellate>1</tessellate>
        <outerBoundaryIs><LinearRing>
          <coordinates>{coords}</coordinates>
        </LinearRing></outerBoundaryIs>
      </Polygon>
    </Placemark>""")

        # ── Defense engagement rings (ground-level polygons, all four states) ──
        s1_end = f"<end>{fmt_time(sim_time(fh))}</end>" if fh is not None else ""
        s1 = f"<TimeSpan>{s1_end}</TimeSpan>" if s1_end else ""
        out.append(ring_pm(f"{name} -- SM-6 240 km",  "us_defense_ring",      ring_sm6,  s1))
        out.append(ring_pm(f"{name} -- SM-2 167 km",  "us_defense_ring_sm2",  ring_sm2,  s1))
        out.append(ring_pm(f"{name} -- ESSM  50 km",  "us_defense_ring_essm", ring_essm, s1))
        out.append(ring_pm(f"{name} -- RAM   15 km",  "us_defense_ring_ram",  ring_ram,  s1))

        if fh is None:
            continue

        fh_str      = fmt_time(sim_time(fh))
        s2_end      = f"<end>{fmt_time(sim_time(th))}</end>" if th is not None else ""
        s2          = f"<TimeSpan><begin>{fh_str}</begin>{s2_end}</TimeSpan>"
        out.append(ring_pm(f"{name} -- SM-6 [DEGRADED]", "us_defense_ring_hit",      ring_sm6,  s2))
        out.append(ring_pm(f"{name} -- SM-2 [DEGRADED]", "us_defense_ring_sm2_hit",  ring_sm2,  s2))
        out.append(ring_pm(f"{name} -- ESSM [DEGRADED]", "us_defense_ring_essm_hit", ring_essm, s2))
        out.append(ring_pm(f"{name} -- RAM  [DEGRADED]", "us_defense_ring_ram_hit",  ring_ram,  s2))

    # ── CSG icon tracks: health-colored, freeze on neutralization ────────────
    for csg in csg_fleet:
        csg_hits = hits_timeline.get(csg["name"], [])
        out.append(_build_csg_damage_track(
            csg, csg_hits, _CSG_NEUTRALIZATION_HITS, latest_s))

    return "\n".join(out)


_ALTITUDE_MAX_M = 100_000.0  # 100 km starting altitude for asset icon tracks

def _damage_phases(hit_times, n_hits_max, end_s):
    """Return list of (t_start, t_end, n_hits_before) phases.
    Each phase covers the period between two consecutive hit events.
    """
    hits   = sorted(hit_times[:n_hits_max])
    phases = []
    t_prev = 0.0
    for idx, hit_t in enumerate(hits):
        if hit_t > t_prev:
            phases.append((t_prev, hit_t, idx))
        t_prev = hit_t
    phases.append((t_prev, end_s, len(hits)))
    return phases


def _build_damage_track(lon, lat, hit_times, n_hits_max, style_prefix, label, end_s):
    """One gx:Track Placemark per damage phase.  Each phase uses a health-
    colored style (style_prefix + '_h_N') and holds a fixed (lon, lat) position
    while the icon altitude drops as hits accumulate.
    style_prefix : 'ir' for Iranian sites  (ir_h_0 … ir_h_25, blue→orange)
    """
    out = []
    for t_start, t_end, n_hits in _damage_phases(hit_times, n_hits_max, end_s):
        health_pct = round(100 * (1 - n_hits / n_hits_max))
        status     = ("ACTIVE"       if n_hits == 0
                      else "OPERATIONAL" if n_hits < n_hits_max // 2
                      else "DEGRADED"    if n_hits < n_hits_max
                      else "DESTROYED")
        status_col = (_C_ACTIVE      if n_hits == 0
                      else _C_OPERATIONAL if n_hits < n_hits_max // 2
                      else _C_DEGRADED    if n_hits < n_hits_max
                      else _C_NEUTRALIZED)
        desc = _html_popup(f"◈ IRAN SITE — {label}", _C_IRAN_SITE, [
            ("Status",    status,                          status_col),
            ("Health",    f"{health_pct}%",               status_col),
            ("Hits",      f"{n_hits} / {n_hits_max}",     _C_DEGRADED),
        ])
        wc = (
            f"\n      <when>{fmt_time(sim_time(t_start))}</when>"
            f"\n      <gx:coord>{lon:.4f} {lat:.4f} 0</gx:coord>"
            f"\n      <gx:angles>0 0 0</gx:angles>"
            f"\n      <when>{fmt_time(sim_time(t_end))}</when>"
            f"\n      <gx:coord>{lon:.4f} {lat:.4f} 0</gx:coord>"
            f"\n      <gx:angles>0 0 0</gx:angles>"
        )
        _site_label = f'{label}  ({health_pct}%)'
        out.append(
            f'  <Placemark><name>{_site_label}</name>'
            f'<styleUrl>#{style_prefix}_h_{n_hits}</styleUrl>'
            f'<description>{desc}</description>'
            f'<TimeSpan>'
            f'<begin>{fmt_time(sim_time(t_start))}</begin>'
            f'<end>{fmt_time(sim_time(t_end))}</end>'
            f'</TimeSpan>'
            f'<gx:Track><altitudeMode>clampToGround</altitudeMode>'
            + wc + f'\n  </gx:Track></Placemark>\n'
        )
    return "".join(out)


def _build_csg_damage_track(csg, hit_times, n_hits_max, end_s):
    """One gx:Track per damage phase for a CSG.  The icon moves west with the
    ship AND changes color green→red while descending to 0 as hits accumulate.
    Uses 'us_h_N' styles.
    """
    hdg_deg = csg.get("heading_deg", 270)
    out     = []
    for t_start, t_end, n_hits in _damage_phases(hit_times, n_hits_max, end_s):
        lo0, la0   = csg_pos_at(csg, t_start)
        # Freeze position on neutralization — no further movement
        if n_hits >= n_hits_max:
            lo1, la1 = lo0, la0
        else:
            lo1, la1 = csg_pos_at(csg, t_end)
        health_pct = round(100 * (1 - n_hits / n_hits_max))
        status     = ("COMBAT READY" if n_hits == 0
                      else "OPERATIONAL" if n_hits < 4
                      else "DEGRADED"    if n_hits < n_hits_max
                      else "DESTROYED")
        status_col = (_C_ACTIVE      if n_hits == 0
                      else _C_OPERATIONAL if n_hits < 4
                      else _C_DEGRADED    if n_hits < n_hits_max
                      else _C_NEUTRALIZED)
        desc = _html_popup(f"⚓ {csg['name']}", _C_US_CSG, [
            ("Class",    csg.get("class", "CVN"),                        _C_US_CSG),
            ("Escorts",  csg.get("escorts", "—"),                        _C_DATA),
            ("Status",   status,                                          status_col),
            ("Health",   f"{health_pct}%",                               status_col),
            ("Hits",     f"{n_hits} / {n_hits_max}",                    _C_DEGRADED),
            ("SM-6",     f"{csg['sm6_low']}–{csg['sm6_high']} rds (240 km)",  _C_US_CSG),
            ("SM-2",     f"{csg['sm2_low']}–{csg['sm2_high']} rds (167 km)",  _C_US_CSG),
            ("ESSM",     f"{csg['essm_low']}–{csg['essm_high']} rds (50 km)", _C_US_CSG),
            ("RAM",      f"{csg['ram_low']}–{csg['ram_high']} rds (15 km)",   _C_US_CSG),
        ])
        wc = (
            f"\n      <when>{fmt_time(sim_time(t_start))}</when>"
            f"\n      <gx:coord>{lo0:.4f} {la0:.4f} 0</gx:coord>"
            f"\n      <gx:angles>{hdg_deg:.1f} 0 0</gx:angles>"
            f"\n      <when>{fmt_time(sim_time(t_end))}</when>"
            f"\n      <gx:coord>{lo1:.4f} {la1:.4f} 0</gx:coord>"
            f"\n      <gx:angles>{hdg_deg:.1f} 0 0</gx:angles>"
        )
        _csg_label = f'{csg["name"]}  ({health_pct}%)'
        out.append(
            f'  <Placemark><name>{_csg_label}</name>'
            f'<styleUrl>#us_h_{n_hits}</styleUrl>'
            f'<description>{desc}</description>'
            f'<TimeSpan>'
            f'<begin>{fmt_time(sim_time(t_start))}</begin>'
            f'<end>{fmt_time(sim_time(t_end))}</end>'
            f'</TimeSpan>'
            f'<gx:Track><altitudeMode>clampToGround</altitudeMode>'
            + wc + f'\n  </gx:Track></Placemark>\n'
        )
    return "".join(out)


def gen_iran_sites(site_inactive_at=None, site_hits_timeline=None, end_s=7200):
    """Render each launch site as a health-colored gx:Track icon (blue→white)
    that changes color as US strikes land, positioned at _ALTITUDE_MAX_M.
    """
    site_inactive_at   = site_inactive_at   or {}
    site_hits_timeline = site_hits_timeline or {}
    out = []
    for s in IRAN_SITES:
        lon, lat  = s["lon"], s["lat"]
        site_hits = site_hits_timeline.get(s["name"], [])
        out.append(_build_damage_track(
            lon, lat, site_hits, SITE_INACTIVATION_THRESHOLD,
            "ir", s["name"], end_s))
    return "\n".join(out)

# ============================================================
# US COUNTERSTRIKE PRE-COMPUTATION
# ============================================================

def compute_us_strikes(scenario_key, rng):
    """
    Pre-compute US TLAM/JASSM strike events against Iranian launch sites.

    Strikes are weighted by inverse distance (closer = higher strike priority)
    and give coastal/island sites a 1.5× bonus (primary Shahed/ASCM launchers).

    Returns
    -------
    strike_events : list of dicts
        Each dict: csg, site, munition, dist_km, launch_s, impact_s
    site_inactive_at : dict[str -> float]
        Maps site name to the impact_s of the 25th hit (inactivation moment).
        Sites that never reach 25 hits are absent from the dict.
    """
    sc = SCENARIOS[scenario_key]
    n_per_csg = sc.get("n_us_strikes_per_csg", 20)

    # Collect raw hit times per site before sorting
    site_raw = {s["name"]: [] for s in IRAN_SITES}

    for csg in US_CSGS:
        # Compute distance-weighted probability for each site
        weights = []
        for site in IRAN_SITES:
            d = haversine_km(csg["lon"], csg["lat"], site["lon"], site["lat"])
            coastal_bonus = 1.5 if site["type"] in ("Coastal Battery", "Island Fortress") else 1.0
            w = coastal_bonus / max(d, 50)
            weights.append(w)
        total_w = sum(weights)
        weights = [w / total_w for w in weights]

        for _ in range(n_per_csg):
            # Weighted site selection
            r, cum = rng.random(), 0.0
            tgt_site = IRAN_SITES[-1]
            for k, site in enumerate(IRAN_SITES):
                cum += weights[k]
                if r <= cum:
                    tgt_site = site
                    break

            dist_km = haversine_km(csg["lon"], csg["lat"],
                                   tgt_site["lon"], tgt_site["lat"])
            # JASSM-ER for sites within 1,000 km; TLAM Block IV beyond
            if dist_km <= 1000:
                munition, speed = "JASSM-ER", US_STRIKE_MUNITIONS["JASSM-ER"]["speed_km_s"]
            else:
                munition, speed = "TLAM Block IV", US_STRIKE_MUNITIONS["TLAM Block IV"]["speed_km_s"]

            flight_s = dist_km / speed
            if sc.get("us_strike_timing") == "perfect":
                # Pre-launched to arrive in the opening 5-minute window.
                # launch_s is negative (missiles were in the air before t=0).
                impact_s = rng.uniform(0, 300)
                launch_s = impact_s - flight_s
            else:
                # US strikes concentrated in first 60% of scenario wave
                launch_s = rng.uniform(0, sc["wave_s"] * 0.6)
                impact_s = launch_s + flight_s

            site_raw[tgt_site["name"]].append({
                "csg": csg, "site": tgt_site, "munition": munition,
                "dist_km": dist_km, "launch_s": launch_s, "impact_s": impact_s,
            })

    # Sort each site's events by impact time; compute inactivation moment
    site_inactive_at = {}
    all_events = []
    for site_name, evts in site_raw.items():
        evts.sort(key=lambda e: e["impact_s"])
        all_events.extend(evts)
        if len(evts) >= SITE_INACTIVATION_THRESHOLD:
            site_inactive_at[site_name] = evts[SITE_INACTIVATION_THRESHOLD - 1]["impact_s"]

    # Build sorted hit-time lists per site (for altitude-degradation tracks)
    site_hits_timeline = {
        sn: sorted(e["impact_s"] for e in evts)
        for sn, evts in site_raw.items() if evts
    }
    return all_events, site_inactive_at, site_hits_timeline


def gen_us_strike_kml(strike_events, site_inactive_at, n_arc=8):
    """
    Build KML track segments and impact markers for US TLAM/JASSM strikes.
    Only renders strikes that land BEFORE or AT inactivation (wasted strikes
    beyond the threshold are omitted to reduce file size).
    """
    segs_by_type   = {m: [] for m in US_STRIKE_MUNITIONS}
    impacts        = []
    hit_counter    = {}   # site_name -> running hit count for labelling

    # Sort all events by launch time for consistent ordering
    for ev in sorted(strike_events, key=lambda e: e["launch_s"]):
        site_name = ev["site"]["name"]
        hit_counter[site_name] = hit_counter.get(site_name, 0) + 1
        hit_num = hit_counter[site_name]

        # Only render up to SITE_INACTIVATION_THRESHOLD hits per site
        if hit_num > SITE_INACTIVATION_THRESHOLD:
            continue

        csg      = ev["csg"]
        site     = ev["site"]
        munition = ev["munition"]
        mdef     = US_STRIKE_MUNITIONS[munition]
        launch_s = ev["launch_s"]
        impact_s = ev["impact_s"]
        dist_km  = ev["dist_km"]

        pts    = arc_points(csg["lon"], csg["lat"], site["lon"], site["lat"],
                            mdef["peak_alt_m"], n_arc, True)
        t_pts  = [launch_s + (k / n_arc) * (impact_s - launch_s) for k in range(n_arc + 1)]
        style  = safe_id(munition)
        label  = f"{munition} {csg['name']} → {site_name} #{hit_num}"
        desc   = (f"US strike -- {munition} | {csg['name']} to {site_name} | "
                  f"{dist_km:.0f} km | impact T+{impact_s/60:.1f} min | "
                  f"hit #{hit_num}/{SITE_INACTIVATION_THRESHOLD}")

        segs_by_type[munition] += gx_track(style, pts, t_pts, label, desc)

        inact_tag = ""
        if site_inactive_at.get(site_name) is not None and hit_num == SITE_INACTIVATION_THRESHOLD:
            inact_tag = " [SITE DESTROYED]"

        impacts.append(
            f"      <Placemark>"
            f"<name>US Strike #{hit_num} → {site_name}{inact_tag}</name>"
            f"<styleUrl>#us_strike_impact_marker</styleUrl>"
            f"<description>{_html_popup('◉ US STRIKE', _C_US_STRIKE, [('Munition', munition, _C_US_STRIKE), ('Target', site_name, _C_IRAN_SITE), ('Hit count', f'{hit_num} / {SITE_INACTIVATION_THRESHOLD}', _C_DEGRADED), ('Time', f'T+{impact_s/60:.1f} min', _C_US_STRIKE)])}</description>"
            f"<TimeStamp><when>{fmt_time(sim_time(impact_s))}</when></TimeStamp>"
            f"<Point><altitudeMode>clampToGround</altitudeMode>"
            f"<coordinates>{site['lon']:.5f},{site['lat']:.5f},0</coordinates>"
            f"</Point></Placemark>"
        )

    return segs_by_type, impacts

# ============================================================
# SCENARIO GENERATOR
# ============================================================

def compute_iaf_strikes(scenario_key, rng, site_inactive_at):
    """
    Generate Israeli Air Force strike events against Iranian launch sites.

    Each aircraft makes 2 passes per sortie (circle-back attack):
      - Pass 1: drops PASS1_ROUNDS munitions on the chosen target
      - Pass 2: 20-40 min later, picks a fresh (live) target and drops PASS2_ROUNDS more
    If the original target is already destroyed, the aircraft redirects to the
    highest-priority surviving site rather than going home empty.

    Returns (all_events, iaf_site_hits_timeline) where iaf_site_hits_timeline is
    a dict[site_name -> sorted list of impact_s] for merging into the combined
    site damage model.
    """
    sc           = SCENARIOS[scenario_key]
    wave_s       = sc["wave_s"]
    pkg_days     = min(3, math.ceil(wave_s / 86_400)) if wave_s > 3_600 else 1
    PASS1_ROUNDS = 2
    PASS2_ROUNDS = 2
    TURNAROUND_S = (20 * 60, 40 * 60)   # seconds
    all_events   = []
    iaf_hits   = {s["name"]: [] for s in IRAN_SITES}
    _destroyed = set(site_inactive_at.keys())  # sites already gone before IAF arrives

    for base in IAF_BASES:
        mname     = base["munition"]
        mdef      = IAF_MUNITIONS[mname]
        n_sorties = base["sorties"] * pkg_days
        max_rng   = mdef["max_range_km"]
        speed     = mdef["speed_km_s"]

        eligible = []
        for site in IRAN_SITES:
            dist = haversine_km(base["lon"], base["lat"], site["lon"], site["lat"])
            if dist <= 2_500 and dist >= max_rng:
                eligible.append((site, dist))
        if not eligible:
            continue

        base_weights = [1.5 if s["type"] in ("Coastal Battery", "Island Fortress") else 1.0
                        for s, _ in eligible]
        total_w = sum(base_weights)
        base_weights = [w / total_w for w in base_weights]

        def _pick_live_target(excluded_name=None):
            """Pick a weighted-random eligible site that is not yet destroyed."""
            live = [(s, d, w) for (s, d), w in zip(eligible, base_weights)
                    if s["name"] not in _destroyed and s["name"] != excluded_name]
            if not live:
                # every eligible site is gone — fall back to any eligible site
                live = [(s, d, w) for (s, d), w in zip(eligible, base_weights)]
            if not live:
                return None, None
            sites_l, dists_l, ws_l = zip(*live)
            tw = sum(ws_l)
            norm = [w / tw for w in ws_l]
            idx = rng.choices(range(len(sites_l)), weights=norm, k=1)[0]
            return sites_l[idx], dists_l[idx]

        for _ in range(n_sorties):
            # ── Pass 1 ────────────────────────────────────────────────────────
            tgt1, dist1 = _pick_live_target()
            if tgt1 is None:
                rng.uniform(0, 1)   # consume RNG for determinism
                rng.uniform(0, 1)
                continue
            flight1 = dist1 / speed
            if sc.get("iaf_timing") == "perfect":
                impact1 = rng.uniform(0, 300)
                launch1 = impact1 - flight1
            else:
                launch1 = rng.uniform(3600, wave_s * 0.85)
                impact1 = launch1 + flight1
            for _ in range(PASS1_ROUNDS):
                all_events.append({
                    "base": base, "site": tgt1, "munition": mname,
                    "dist_km": dist1, "launch_s": launch1, "impact_s": impact1,
                    "pass_num": 1,
                })
                iaf_hits[tgt1["name"]].append(impact1)

            # ── Pass 2 (circle-back) ──────────────────────────────────────────
            turnaround = rng.uniform(*TURNAROUND_S)
            tgt2, dist2 = _pick_live_target(excluded_name=tgt1["name"])
            if tgt2 is None:
                continue
            flight2 = dist2 / speed
            launch2 = launch1 + turnaround
            impact2 = launch2 + flight2
            for _ in range(PASS2_ROUNDS):
                all_events.append({
                    "base": base, "site": tgt2, "munition": mname,
                    "dist_km": dist2, "launch_s": launch2, "impact_s": impact2,
                    "pass_num": 2,
                })
                iaf_hits[tgt2["name"]].append(impact2)

    iaf_site_hits_timeline = {k: sorted(v) for k, v in iaf_hits.items() if v}
    return all_events, iaf_site_hits_timeline


def gen_iaf_kml(iaf_events, site_inactive_at):
    """Return per-munition segment dict and impact placemarks for IAF strikes."""
    segs_by_mun = {m: [] for m in IAF_MUNITIONS}
    impacts     = []

    for ev in sorted(iaf_events, key=lambda e: e["launch_s"]):
        base     = ev["base"]
        site     = ev["site"]
        mname    = ev["munition"]
        mdef     = IAF_MUNITIONS[mname]
        launch_s = ev["launch_s"]
        impact_s = ev["impact_s"]
        dist_km  = ev["dist_km"]
        n_arc    = 12

        pts   = arc_points(base["lon"], base["lat"], site["lon"], site["lat"],
                           mdef["peak_alt_m"], n_arc, mdef["sea_skim"])
        t_pts = [launch_s + (k / n_arc) * (impact_s - launch_s) for k in range(n_arc + 1)]

        style  = safe_id(mname) + "_iaf"
        label  = f"IAF {mname} — {base['name']} → {site['name']}"
        desc   = (f"IAF Strike | {base['aircraft']} | {mname} | "
                  f"{base['name']} → {site['name']} | "
                  f"{dist_km:.0f} km | launch T+{launch_s/60:.1f} min")

        segs_by_mun[mname] += gx_track(style, pts, t_pts, label, desc)

        already_dead = site["name"] in site_inactive_at
        impact_icon  = "dead_icon" if already_dead else "strike_icon"
        impacts.append(
            f'    <Placemark><name>{mname} → {site["name"]}</name>'
            f'<styleUrl>#{impact_icon}</styleUrl>'
            f'<TimeStamp><when>{fmt_time(sim_time(impact_s))}</when></TimeStamp>'
            f'<description>{desc}</description>'
            f'<Point><coordinates>{site["lon"]:.5f},{site["lat"]:.5f},0</coordinates>'
            f'</Point></Placemark>\n'
        )

    return segs_by_mun, impacts


def gen_tour(tenth_hit_s, dur_s, sc_label):
    """
    Generate a <gx:Tour> element that orbits the Persian Gulf battlespace.

    Pacing:
      - One complete 360° orbit every simulated hour (36 steps × 10°).
      - When a CSG accumulates 10 breakthrough hits it is considered heavily
        damaged; the camera breaks from the main orbit, zooms into that CSG,
        circles it slowly, then returns to the main orbit at the same heading.
      - Intro: top-down descent into tactical view.
      - Outro: wide pullback with a slow final revolution.
    """
    CTR_LON, CTR_LAT  = 55.5, 26.5   # mid-Persian Gulf engagement centroid
    ORBIT_RANGE_M     = 780_000       # LookAt range during main orbit
    ORBIT_TILT        = 45            # degrees from vertical (45° gives drama)
    WIDE_RANGE_M      = 2_000_000     # opening / closing wide shot
    CSG_CLOSE_M       =  80_000       # zoom range when circling a hit CSG
    CSG_MID_M         = 250_000       # approach range on the way in
    SECS_PER_HOUR     = 14            # real seconds per simulated hour (1 orbit)
    STEPS_PER_ROT     = 36            # 10° per step → smooth 360°

    n_hours   = math.ceil(dur_s / 3600)
    step_dur  = SECS_PER_HOUR / STEPS_PER_ROT   # ~0.39 s per 10° step

    def _fly(lon, lat, range_m, tilt, heading, duration, mode="smooth"):
        return (
            f'      <gx:FlyTo>'
            f'<gx:duration>{duration:.2f}</gx:duration>'
            f'<gx:flyToMode>{mode}</gx:flyToMode>'
            f'<LookAt>'
            f'<longitude>{lon:.5f}</longitude>'
            f'<latitude>{lat:.5f}</latitude>'
            f'<altitude>0</altitude>'
            f'<range>{range_m:.0f}</range>'
            f'<tilt>{tilt:.1f}</tilt>'
            f'<heading>{heading:.1f}</heading>'
            f'<altitudeMode>relativeToGround</altitudeMode>'
            f'</LookAt>'
            f'</gx:FlyTo>\n'
        )

    def _wait(sec):
        return f'      <gx:Wait><gx:duration>{sec:.2f}</gx:duration></gx:Wait>\n'

    def _time_update(t_sim_s):
        """Emit a gx:AnimatedUpdate that advances the time slider to t_sim_s."""
        ts = fmt_time(sim_time(t_sim_s))
        return (
            f'      <gx:AnimatedUpdate>'
            f'<gx:duration>0.1</gx:duration>'
            f'<Update><targetHref/><Change>'
            f'<Placemark targetId="time_cursor">'
            f'<TimeStamp><when>{ts}</when></TimeStamp>'
            f'</Placemark>'
            f'</Change></Update>'
            f'</gx:AnimatedUpdate>\n'
        )

    pl = []   # playlist elements

    # Sync time slider to simulation start
    pl.append(_time_update(0))

    # ── Intro: fall from orbit into tactical view ─────────────────────────────
    pl.append(_fly(CTR_LON, CTR_LAT, 3_500_000, 0,  0, 5.0, "bounce"))
    pl.append(_wait(1.0))
    pl.append(_fly(CTR_LON, CTR_LAT, ORBIT_RANGE_M, ORBIT_TILT, 0, 5.0))
    pl.append(_wait(1.5))

    current_heading = 0.0

    # ── Main loop: one 360° rotation per simulated hour ──────────────────────
    for hour in range(n_hours):
        t_start = hour * 3600
        t_end   = min((hour + 1) * 3600, dur_s)

        pl.append(_time_update(t_start))

        # CSGs that cross the tenth-hit threshold during this hour
        destroyed = sorted(
            [(ts, nm) for nm, ts in tenth_hit_s.items() if t_start <= ts < t_end],
            key=lambda x: x[0]
        )

        # Complete one full 360° orbit for this simulated hour
        for step in range(STEPS_PER_ROT):
            h = (current_heading + step * 10.0) % 360.0
            pl.append(_fly(CTR_LON, CTR_LAT, ORBIT_RANGE_M, ORBIT_TILT, h, step_dur))
        current_heading = (current_heading + 360.0) % 360.0
        pl.append(_time_update(t_end))

        # Zoom into every CSG that was heavily hit this hour
        for _, csg_name in destroyed:
            csg = next((c for c in US_CSGS if c["name"] == csg_name), None)
            if csg is None:
                continue
            approach_hdg = (current_heading + 60.0) % 360.0

            # Wide approach: put the CSG in context of surrounding waters
            pl.append(_fly(csg["lon"], csg["lat"], CSG_MID_M, 38, approach_hdg, 4.0))
            pl.append(_wait(1.0))
            # Zoom in close
            pl.append(_fly(csg["lon"], csg["lat"], CSG_CLOSE_M, 65, approach_hdg, 3.0))
            pl.append(_wait(1.5))
            # Orbit the stricken CSG: 8 × 45° steps (full 360°)
            for q in range(8):
                qh = (approach_hdg + q * 45.0) % 360.0
                pl.append(_fly(csg["lon"], csg["lat"], CSG_CLOSE_M, 68, qh, 1.5))
            pl.append(_wait(1.0))
            # Pull back to main orbit heading
            pl.append(_fly(CTR_LON, CTR_LAT, ORBIT_RANGE_M, ORBIT_TILT,
                           current_heading, 5.0))
            pl.append(_wait(0.5))

    # ── Outro: wide pullback + slow final revolution ──────────────────────────
    pl.append(_fly(CTR_LON, CTR_LAT, WIDE_RANGE_M, 20, current_heading, 5.0, "bounce"))
    pl.append(_wait(2.0))
    for step in range(12):   # 12 × 30° = one slow final orbit at wide view
        h = (current_heading + step * 30.0) % 360.0
        pl.append(_fly(CTR_LON, CTR_LAT, WIDE_RANGE_M, 18, h, 2.5))
    pl.append(_wait(2.0))

    return (
        f'  <gx:Tour>\n'
        f'    <name>Battle Tour — {sc_label}</name>\n'
        f'    <description>'
        f'Camera orbits the Persian Gulf once per simulated hour. '
        f'Zooms into CSGs when they receive 10+ breakthrough hits. '
        f'Total orbit time: ~{n_hours * SECS_PER_HOUR // 60} min real playback.'
        f'</description>\n'
        f'    <gx:Playlist>\n'
        + ''.join(pl) +
        f'    </gx:Playlist>\n'
        f'  </gx:Tour>\n'
    )


def generate_scenario(scenario_key, seed=42):
    rng = random.Random(seed)
    sc  = SCENARIOS[scenario_key]

    n_missiles    = sc["n_missiles"]
    cap           = sc["intercept_cap"]
    munitions     = sc["munitions"]
    wave_s        = sc["wave_s"]
    n_arc         = sc["n_arc"]
    n_sm6         = sc["n_sm6"]
    csg_fleet     = sc.get("csg_fleet", US_CSGS)

    # Phased launch timing (defaults keep backward-compat for scenarios A–F)
    # Drones (Shahed-136, IRGCN Sea Drone) launch in phase 1; all others in phase 2.
    DRONE_TYPES  = {"Shahed-136", "IRGCN Sea Drone"}
    phase1_end   = sc.get("phase1_end_s",   wave_s)  # end of drone launch window
    phase2_start = sc.get("phase2_start_s", 0)        # start of missile launch window
    phase2_dur   = sc.get("phase2_dur_s",   wave_s)  # duration of missile launch window

    # ================================================================
    # PHASE 0 — US counterstrikes (consumes RNG first, deterministically)
    # ================================================================
    strike_events, site_inactive_at, site_hits_timeline = compute_us_strikes(scenario_key, rng)
    iaf_events, iaf_site_hits = compute_iaf_strikes(scenario_key, rng, site_inactive_at)

    # Merge IAF hits into site_hits_timeline and recompute site_inactive_at
    for sname, times in iaf_site_hits.items():
        merged = sorted(site_hits_timeline.get(sname, []) + times)
        site_hits_timeline[sname] = merged
        if len(merged) >= SITE_INACTIVATION_THRESHOLD:
            site_inactive_at[sname] = merged[SITE_INACTIVATION_THRESHOLD - 1]

    n_intercepted  = min(round(n_missiles * sc["intercept_rate"]), cap)
    intercepted_set = set(rng.sample(range(n_missiles), n_intercepted))

    us_style = {
        "low": "us_lo", "medium": "us_mid", "high": "us_hi",
        "realistic": "us_mid", "iran_best": "us_hi", "usa_best": "us_lo",
        "drone_first_low": "us_lo", "drone_first_medium": "us_mid", "drone_first_high": "us_hi",
        "coordinated_strike": "us_lo",
        "focused_salvo": "us_mid", "hypersonic_threat": "us_mid",
        "ballistic_barrage": "us_lo", "ascm_swarm": "us_lo", "shore_based_defense": "us_mid",
        "strait_transit": "us_mid",
    }[scenario_key]

    # focused_salvo: all Iranian fire directed at a single named CSG
    _focus_name   = sc.get("focus_csg")
    _focus_csg    = next((c for c in US_CSGS if c["name"] == _focus_name), None)

    # Per-munition collections for nested folder output
    _mnames       = [m["name"] for m in sc["munitions"]]
    missile_segs  = {mn: [] for mn in _mnames}
    intercept_pts = {mn: [] for mn in _mnames}
    impact_pts    = {mn: [] for mn in _mnames}
    sm6_segs      = {"SM-6 / SM-2": [], "CIWS / SeaRAM": [], "Naval Gun / Phalanx": []}
    latest_s      = 0.0

    # ================================================================
    # PHASE 1 — Pre-simulate every missile
    # ================================================================
    site_pools = {}
    for m in munitions:
        mn   = m["name"]
        mdef = MUNITIONS[mn]
        allowed = mdef.get("sites")
        if allowed:
            pool = [s for s in IRAN_SITES if s["name"] in allowed]
        else:
            pool = IRAN_SITES
        site_pools[mn] = pool

    events = []
    for i in range(n_missiles):
        mname = weighted_choice(munitions, rng)["name"]
        mdef  = MUNITIONS[mname]
        _csg_roll = rng.choice(csg_fleet)
        csg = _focus_csg if _focus_csg else _csg_roll

        # Generate launch time
        if sc.get("iran_detection_launch"):
            # Iran fires everything simultaneously on IAF radar detection —
            # no phase separation between drones and missiles.
            # All launches compressed into a short window so every site fires
            # before a single US/IAF munition lands (~45-90 min flight time).
            _iw = sc.get("iran_launch_window_s", 1800)
            launch_s = rng.uniform(0, _iw)
        elif mname in DRONE_TYPES:
            launch_s = rng.uniform(0, phase1_end)
        else:
            launch_s = rng.uniform(phase2_start, phase2_start + phase2_dur)

        # Filter site pool: only use sites that are still active at launch_s
        full_pool = site_pools[mname]
        active_pool = [s for s in full_pool
                       if site_inactive_at.get(s["name"], float("inf")) > launch_s]
        if not active_pool:
            # All allowed sites destroyed — consume RNG consistently to preserve sequence
            _ = rng.random()                # would-be site choice
            _ = rng.uniform(-0.25, 0.25)   # tgt_lon jitter
            _ = rng.uniform(-0.25, 0.25)   # tgt_lat jitter
            _ = rng.uniform(0.88, 1.12)    # peak jitter
            _ = rng.random()               # AI roll
            if i in intercepted_set:
                _ = rng.random()           # t_int_frac
                _ = rng.uniform(60, 90)    # react_s
            events.append(None)
            continue

        site    = rng.choice(active_pool)
        # Project CSG position at estimated impact time (one-iteration lead-target)
        _est_dist   = haversine_km(site["lon"], site["lat"], csg["lon"], csg["lat"])
        _est_impact = launch_s + _est_dist / mdef["speed_km_s"]
        _clon, _clat = csg_pos_at(csg, _est_impact)
        tgt_lon = _clon + rng.uniform(-0.25, 0.25)
        tgt_lat = _clat + rng.uniform(-0.25, 0.25)
        dist_km  = haversine_km(site["lon"], site["lat"], tgt_lon, tgt_lat)
        flight_s = dist_km / mdef["speed_km_s"]
        peak     = mdef["peak_alt_m"] * rng.uniform(0.88, 1.12)

        # AI/computer-vision terminal guidance: 1% of Shahed-136 only.
        # Always consumes one RNG call per event to keep sequence deterministic.
        is_ai = (mname == "Shahed-136" and rng.random() < AI_SHAHED_FRACTION)
        if is_ai:
            # Tighter terminal lock-on: ±0.05° vs normal ±0.25° scatter
            _ai_impact = launch_s + flight_s
            _ai_lon, _ai_lat = csg_pos_at(csg, _ai_impact)
            ai_tgt_lon = _ai_lon + rng.uniform(-0.05, 0.05)
            ai_tgt_lat = _ai_lat + rng.uniform(-0.05, 0.05)
        else:
            ai_tgt_lon = tgt_lon
            ai_tgt_lat = tgt_lat

        is_int = (i in intercepted_set) and not is_ai  # AI drones always break through
        # Per-munition intercept probability override (e.g., Fattah-1 HGV ~5% P(k))
        if "intercept_prob_override" in mdef:
            is_int = rng.random() < mdef["intercept_prob_override"]
        if is_int:
            lo, hi   = mdef.get("t_int_range",
                                 (0.70, 0.92) if mdef["sea_skim"] else (0.55, 0.85))
            t_int_frac = rng.uniform(lo, hi)
            rlo, rhi = mdef.get("react_range", (60, 90))
            react_s  = rng.uniform(rlo, rhi)
        else:
            t_int_frac = None
            react_s    = None
        events.append({
            "i": i, "mname": mname, "mdef": mdef, "site": site, "csg": csg,
            "tgt_lon": tgt_lon, "tgt_lat": tgt_lat, "dist_km": dist_km,
            "flight_s": flight_s, "launch_s": launch_s, "peak": peak,
            "is_int": is_int, "t_int_frac": t_int_frac, "react_s": react_s,
            "is_ai": is_ai, "ai_tgt_lon": ai_tgt_lon, "ai_tgt_lat": ai_tgt_lat,
        })

    # Remove suppressed (None) entries
    events = [e for e in events if e is not None]
    actual_launched = len(events)

    # ================================================================
    # PHASE 2 — Build per-CSG sorted hit timeline
    # ================================================================
    hits_timeline = {c["name"]: [] for c in csg_fleet}
    for ev in events:
        if not ev["is_int"]:   # both normal BT and AI-guided drones count as hits
            hits_timeline[ev["csg"]["name"]].append(ev["launch_s"] + ev["flight_s"])
    for name in hits_timeline:
        hits_timeline[name].sort()

    first_hit_s = {n: times[0]  for n, times in hits_timeline.items() if times}
    tenth_hit_s = {n: times[9]  for n, times in hits_timeline.items() if len(times) >= 10}

    # ================================================================
    # PHASE 3 — Generate Iranian missile KML
    # ================================================================
    for ev in events:
        i        = ev["i"]
        mname    = ev["mname"]
        mdef     = ev["mdef"]
        site     = ev["site"]
        csg      = ev["csg"]
        tgt_lon  = ev["tgt_lon"]
        tgt_lat  = ev["tgt_lat"]
        dist_km  = ev["dist_km"]
        flight_s = ev["flight_s"]
        launch_s = ev["launch_s"]
        peak     = ev["peak"]
        src_lon, src_lat = site["lon"], site["lat"]

        # Per-munition arc resolution: slow/flat weapons use fewer segments;
        # high-arc ballistics use more for smooth parabola rendering.
        n_arc_ev = mdef.get("n_arc_override", n_arc)

        if ev["is_int"]:
            t_int_frac = ev["t_int_frac"]
            react_s    = ev["react_s"]
            n_shown    = max(2, round(t_int_frac * n_arc_ev))
            pts        = arc_points(src_lon, src_lat, tgt_lon, tgt_lat,
                                    peak, n_arc_ev, mdef["sea_skim"])
            pts_shown  = pts[:n_shown + 1]
            t_pts      = [launch_s + (k / n_arc_ev) * flight_s for k in range(n_shown + 1)]
            t_int_s    = t_pts[-1]
            latest_s   = max(latest_s, t_int_s)
            int_lon, int_lat, int_alt = pts_shown[-1]

            t_fire_s   = max(0.0, t_int_s - react_s)
            csg_neut_s = tenth_hit_s.get(csg["name"])
            csg_active = (csg_neut_s is None or t_fire_s < csg_neut_s)

            int_style  = mdef.get("interceptor_style", us_style)
            is_ciws    = (int_style == "us_ciws")
            is_gun     = (int_style == "us_naval_gun")
            int_peak   = max(int_alt * 1.1, 50) if is_ciws else max(int_alt * 1.15, 8_000)
            int_cat    = ("CIWS / SeaRAM" if is_ciws
                          else "Naval Gun / Phalanx" if is_gun
                          else "SM-6 / SM-2")

            _mc = _kml_to_css(mdef["color"])
            desc = _html_popup("◈ INTERCEPTED", _C_INTERCEPT, [
                ("Munition",    mname,                         _mc),
                ("Origin",      site["name"],                  _C_IRAN_SITE),
                ("Target",      csg["name"],                   _C_US_CSG),
                ("Range",       f"{dist_km:.0f} km"),
                ("Flight time", f"{flight_s/60:.1f} min"),
                ("Kill time",   f"T+{t_int_s/60:.1f} min",    _C_INTERCEPT),
                ("Altitude",    f"{int_alt:.0f} m"),
                ("Weapon",      int_cat,                       _C_US_CSG),
            ])

            missile_segs[mname] += gx_track(
                safe_id(mname), pts_shown, t_pts, f"{mname} #{i}", desc)

            if csg_active:
                _fire_lon, _fire_lat = csg_pos_at(csg, t_fire_s)
                sm6_pts   = arc_points(_fire_lon, _fire_lat, int_lon, int_lat,
                                       int_peak, n_sm6, False)
                sm6_t_pts = [t_fire_s + (k / n_sm6) * react_s for k in range(n_sm6 + 1)]
                sm6_segs[int_cat] += gx_track(
                    int_style, sm6_pts, sm6_t_pts,
                    f"{'CIWS' if is_ciws else 'Gun' if is_gun else 'SM-6'} #{i}")

            _sspk_entry = MUNITION_SSPK.get(mname, {})
            _sspk_intcp = _sspk_entry.get("interceptor", "\u2014")
            _sspk_label = f"{round(_sspk_entry.get('sspk', 0) * 100)}%  ({_sspk_intcp})"
            intercept_pts[mname].append(
                f"      <Placemark>"
                f"<name>Kill #{i}</name><styleUrl>#intercept_marker</styleUrl>"
                f"<description>{_html_popup('◈ KILL CONFIRMED', _C_INTERCEPT, [('Munition', mname, _mc), ('Altitude', f'{int_alt:.0f} m'), ('Time', f'T+{t_int_s/60:.1f} min', _C_INTERCEPT), ('System', int_cat, _C_US_CSG), ('SSPK', _sspk_label, _C_INTERCEPT)])}</description>"
                f"<TimeStamp><when>{fmt_time(sim_time(t_int_s))}</when></TimeStamp>"
                f"<Point><altitudeMode>absolute</altitudeMode>"
                f"<coordinates>{int_lon:.5f},{int_lat:.5f},{int_alt:.0f}</coordinates>"
                f"</Point></Placemark>"
            )

        else:
            if ev["is_ai"]:
                # ── AI-guided terminal: approach arc + redirect segment ──────────
                # Phase 1: normal golden-yellow Shahed arc for first AI_TERMINAL_FRAC
                n_appr  = max(2, round(AI_TERMINAL_FRAC * n_arc))
                pts_full = arc_points(src_lon, src_lat, tgt_lon, tgt_lat,
                                      peak, n_arc, mdef["sea_skim"])
                pts_appr = pts_full[:n_appr + 1]
                t_pts_appr = [launch_s + (k / n_arc) * flight_s
                               for k in range(n_appr + 1)]
                wp_t = t_pts_appr[-1]          # time at re-acquisition waypoint
                wp   = pts_appr[-1]            # (lon, lat, alt) at waypoint

                # Phase 2: computer-vision lock-on to tighter aim point (white arc)
                ai_lon, ai_lat = ev["ai_tgt_lon"], ev["ai_tgt_lat"]
                t_terminal = flight_s * (1 - AI_TERMINAL_FRAC) * 0.9  # slight speed-up
                t_end_s    = wp_t + t_terminal
                t_pts_term = [wp_t + (k / 8) * t_terminal for k in range(9)]
                pts_term   = arc_points(wp[0], wp[1], ai_lon, ai_lat,
                                        max(wp[2] * 0.5, 20), 8, True)

                latest_s = max(latest_s, t_end_s)

                _mc = _kml_to_css(mdef["color_bt"])
                desc_appr = _html_popup("⚠ AI-GUIDED BREAKTHROUGH", _C_AI, [
                    ("Munition",     f"{mname} [Computer-Vision]", _mc),
                    ("Origin",       site["name"],                 _C_IRAN_SITE),
                    ("Target",       csg["name"],                  _C_US_CSG),
                    ("Range",        f"{dist_km:.0f} km"),
                    ("Re-acquires",  f"{AI_TERMINAL_FRAC*100:.0f}% of flight"),
                    ("Impact",       f"T+{t_end_s/60:.1f} min",   _C_AI),
                    ("Note",         "CIWS lead-angle defeated",   _C_NEUTRALIZED),
                ])
                missile_segs[mname] += gx_track(
                    safe_id(mname) + "_bt", pts_appr, t_pts_appr,
                    f"{mname} #{i} [AI]", desc_appr)
                missile_segs[mname] += gx_track(
                    "shahed_ai_terminal", pts_term, t_pts_term,
                    f"{mname} #{i} [AI-REDIRECT]")

                impact_pts[mname].append(
                    f"      <Placemark>"
                    f"<name>AI IMPACT #{i} -- {mname} [CV]</name>"
                    f"<styleUrl>#impact_marker</styleUrl>"
                    f"<description>{_html_popup('⚠ AI IMPACT', _C_AI, [('Munition', f'{mname} [CV]', _mc), ('From', site['name'], _C_IRAN_SITE), ('On', csg['name'], _C_US_CSG), ('Mode', 'Computer-vision terminal lock-on', _C_AI)])}</description>"
                    f"<TimeStamp><when>{fmt_time(sim_time(t_end_s))}</when></TimeStamp>"
                    f"<Point><altitudeMode>clampToGround</altitudeMode>"
                    f"<coordinates>{ai_lon:.5f},{ai_lat:.5f},0</coordinates>"
                    f"</Point></Placemark>"
                )
            else:
                # ── Normal breakthrough ──────────────────────────────────────────
                pts     = arc_points(src_lon, src_lat, tgt_lon, tgt_lat,
                                     peak, n_arc_ev, mdef["sea_skim"])
                t_pts   = [launch_s + (k / n_arc_ev) * flight_s for k in range(n_arc_ev + 1)]
                t_end_s = launch_s + flight_s
                latest_s = max(latest_s, t_end_s)

                _mc = _kml_to_css(mdef["color_bt"])
                desc = _html_popup("✦ BREAKTHROUGH", _C_BT, [
                    ("Munition",    mname,                       _mc),
                    ("Origin",      site["name"],                _C_IRAN_SITE),
                    ("Target",      csg["name"],                 _C_US_CSG),
                    ("Range",       f"{dist_km:.0f} km"),
                    ("Flight time", f"{flight_s/60:.1f} min"),
                    ("Impact",      f"T+{t_end_s/60:.1f} min",  _C_BT),
                ])

                missile_segs[mname] += gx_track(
                    safe_id(mname) + "_bt", pts, t_pts,
                    f"{mname} #{i} [BT]", desc)

                impact_pts[mname].append(
                    f"      <Placemark>"
                    f"<name>IMPACT #{i} -- {mname}</name><styleUrl>#impact_marker</styleUrl>"
                    f"<description>{_html_popup('✦ IMPACT', _C_BT, [('Munition', mname, _mc), ('From', site['name'], _C_IRAN_SITE), ('On', csg['name'], _C_US_CSG)])}</description>"
                    f"<TimeStamp><when>{fmt_time(sim_time(t_end_s))}</when></TimeStamp>"
                    f"<Point><altitudeMode>clampToGround</altitudeMode>"
                    f"<coordinates>{tgt_lon:.5f},{tgt_lat:.5f},0</coordinates>"
                    f"</Point></Placemark>"
                )

    # ================================================================
    # PHASE 4 — Generate US counterstrike KML
    # ================================================================
    strike_segs, strike_impacts = gen_us_strike_kml(strike_events, site_inactive_at)
    iaf_segs, iaf_impacts = gen_iaf_kml(iaf_events, site_inactive_at)

    n_sites_destroyed = len(site_inactive_at)
    sites_destroyed_names = ", ".join(sorted(site_inactive_at.keys())) or "none"

    dur_min = latest_s / 60.0
    actual_intercepted  = sum(1 for e in events if e["is_int"])
    actual_ai           = sum(1 for e in events if e["is_ai"])
    actual_breakthrough = actual_launched - actual_intercepted

    # ── Cost accounting ──────────────────────────────────────────────────────
    iran_cost = sum(MUNITIONS[e["mname"]]["cost_usd"] for e in events)

    intercept_by_cat = {cat: 0 for cat in INTERCEPTOR_COSTS}
    for e in events:
        if e["is_int"]:
            mdef = MUNITIONS[e["mname"]]
            style = mdef.get("interceptor_style", "")
            cat = ("CIWS / SeaRAM"         if style == "us_ciws"
                   else "Naval Gun / Phalanx" if style == "us_naval_gun"
                   else "SM-6 / SM-2")
            intercept_by_cat[cat] += 1
    us_intercept_cost = sum(INTERCEPTOR_COSTS[c] * n for c, n in intercept_by_cat.items())

    us_strike_cost = sum(US_STRIKE_MUNITIONS[e["munition"]]["cost_usd"]
                         for e in strike_events)

    # ── Breakthrough damage: ship/aircraft losses + casualties ───────────────
    breakthroughs = [e for e in events if not e["is_int"]]
    us_ship_damage = sum(MUNITIONS[e["mname"]]["damage_per_hit_usd"] for e in breakthroughs)
    # Cap ship damage at total CSG replacement value (can't lose more than you have)
    us_ship_damage = min(us_ship_damage, TOTAL_CSG_VALUE)

    us_mil_kia = int(sum(MUNITIONS[e["mname"]]["kia_per_hit"] for e in breakthroughs))
    us_mil_wia = int(sum(MUNITIONS[e["mname"]]["wia_per_hit"] for e in breakthroughs))
    # Cap casualties at total personnel at risk
    us_mil_kia = min(us_mil_kia, TOTAL_CSG_PERSONNEL)
    us_mil_wia = min(us_mil_wia, TOTAL_CSG_PERSONNEL - us_mil_kia)

    # ── Per-CSG damage breakdown ──────────────────────────────────────────────
    csg_breakdown = {}
    for csg in csg_fleet:
        cname = csg["name"]
        bt_hits = [e for e in breakthroughs if e["csg"]["name"] == cname]
        n_hits  = len(bt_hits)
        dmg_usd = sum(MUNITIONS[e["mname"]]["damage_per_hit_usd"] for e in bt_hits)
        kia     = int(sum(MUNITIONS[e["mname"]]["kia_per_hit"] for e in bt_hits))
        wia     = int(sum(MUNITIONS[e["mname"]]["wia_per_hit"] for e in bt_hits))
        status  = ("DESTROYED" if cname in tenth_hit_s
                   else "DAMAGED" if cname in first_hit_s
                   else "INTACT")
        csg_breakdown[cname] = {
            "hits": n_hits, "damage_usd": dmg_usd, "kia": kia, "wia": wia,
            "status": status, "asset_value_usd": csg["asset_value_usd"],
            "personnel": csg["personnel"],
        }

    # ── Per-munition Iranian offensive cost breakdown ─────────────────────────
    iran_cost_by_munition = {}
    for e in events:
        mn = e["mname"]
        iran_cost_by_munition[mn] = iran_cost_by_munition.get(mn, 0) + MUNITIONS[mn]["cost_usd"]

    # ── Collateral damage to Gulf commercial/allied shipping ─────────────────
    # Missiles that stray off target or whose debris/shrapnel hits nearby vessels.
    # Persian Gulf: ~55 transits/day through Hormuz; dense tanker/LNG/container traffic.
    collateral_usd = sum(MUNITIONS[e["mname"]]["collateral_usd_per_btk"]
                         for e in breakthroughs)
    collateral_kia = sum(MUNITIONS[e["mname"]]["collateral_kia_per_btk"]
                         for e in breakthroughs)

    # ── Air support costs ────────────────────────────────────────────────────
    # IAF strike munition cost
    iaf_cost = sum(IAF_MUNITIONS[e["munition"]]["cost_usd"] for e in iaf_events)

    # Carrier CAP AIM-120 expenditure (cost only; not geometrically simulated)
    scenario_days = max(1, round(dur_min / (60 * 8)))  # ~8-hr ops day
    cap_amraam_total = CAP_AMRAAM_PER_CSG_DAY * len(US_CSGS) * scenario_days
    cap_amraam_cost  = cap_amraam_total * AIM120_COST_USD

    # Carrier SLAM-ER air-launched strikes
    slam_er_total = SLAM_ER_PER_CSG_DAY * len(US_CSGS) * scenario_days
    slam_er_cost  = slam_er_total * SLAM_ER_COST_USD

    total_us_cost = (us_intercept_cost + us_strike_cost + us_ship_damage
                     + cap_amraam_cost + slam_er_cost + iaf_cost)

    # Exchange ratio: US total strategic cost / Iran offensive cost
    exchange_ratio = total_us_cost / max(1, iran_cost)

    def fmt_cost(usd):
        if usd >= 1e9:
            return f"${usd/1e9:.2f}B"
        return f"${usd/1e6:.1f}M"

    def fmt_fleet(usd):
        return f"${usd/1e9:.1f}B"

    ibc = intercept_by_cat
    cost_block = (
        f"── Cost Estimates (open-source; FY2023 USD) ──────────────────────────────\n"
        f"Fleet at risk (8 CSGs):    {fmt_fleet(TOTAL_CSG_VALUE)}"
        f"  (hulls + air wings incl. F/A-18E/F, E-2D, EA-18G; {TOTAL_CSG_PERSONNEL:,} personnel)\n"
        f"\n"
        f"Iran offensive munitions:  {fmt_cost(iran_cost)}"
        f"  ({actual_launched:,} rounds × weighted unit cost)\n"
        f"\n"
        f"── US / Coalition Expenditure ─────────────────────────────────────────────\n"
        f"VLS interceptors:          {fmt_cost(us_intercept_cost)}"
        f"  ({ibc['SM-6 / SM-2']:,} SM-6/SM-2 @$3.3M"
        f" | {ibc['CIWS / SeaRAM']:,} CIWS/SeaRAM @$800k"
        f" | {ibc['Naval Gun / Phalanx']:,} Naval Gun @$50k)\n"
        f"Carrier CAP (AIM-120):     {fmt_cost(cap_amraam_cost)}"
        f"  ({cap_amraam_total:,} AIM-120C/D @$1.2M — F/A-18F CAP duty, ~{scenario_days}d)\n"
        f"VLS strikes (TLAM/JASSM):  {fmt_cost(us_strike_cost)}"
        f"  ({len(strike_events):,} rounds)\n"
        f"Air-launched strikes (SLAM-ER): {fmt_cost(slam_er_cost)}"
        f"  ({slam_er_total:,} AGM-84H @$1.3M — F/A-18E carrier strikes)\n"
        f"IAF strikes (F-35I/F-15I/F-16I): {fmt_cost(iaf_cost)}"
        f"  ({len(iaf_events):,} Rampage/SPICE/JDAM-ER — Israeli air support)\n"
        f"US ship/aircraft damage:   {fmt_cost(us_ship_damage)}"
        f"  ({actual_breakthrough:,} hits; probability-weighted per munition type)\n"
        f"  Estimated US military casualties: {us_mil_kia:,} KIA / {us_mil_wia:,} WIA\n"
        f"  (capped at {TOTAL_CSG_PERSONNEL:,} total personnel at risk)\n"
        f"\n"
        f"Collateral — Gulf shipping:{fmt_cost(collateral_usd)}"
        f"  damage | ~{int(collateral_kia):,} civilian KIA\n"
        f"  (tankers, LNG/container ships, allied navies — stray rounds + debris)\n"
        f"\n"
        f"Total coalition cost:      {fmt_cost(total_us_cost)}"
        f"  (VLS + CAP + strikes + SLAM-ER + IAF + ship damage; excl. collateral)\n"
        f"Exchange ratio:            {exchange_ratio:.1f}:1  "
        f"(Coalition spends ${exchange_ratio:.1f} for every $1 Iran spends)\n"
        f"Cost per Iranian kill:     "
        f"{fmt_cost(us_intercept_cost / max(1, actual_intercepted))} per VLS intercept"
    )

    _n_neut   = sum(1 for c in csg_fleet if c["name"] in tenth_hit_s)
    _n_dmg    = sum(1 for c in csg_fleet if c["name"] in first_hit_s
                    and c["name"] not in tenth_hit_s)
    _n_intact = len(csg_fleet) - _n_neut - _n_dmg

    costs = {
        "iran_cost": iran_cost,
        "us_intercept_cost": us_intercept_cost,
        "us_strike_cost": us_strike_cost,
        "us_ship_damage": us_ship_damage,
        "total_us_cost": total_us_cost,
        "exchange_ratio": exchange_ratio,
        "intercept_by_cat": intercept_by_cat,
        "us_mil_kia": us_mil_kia,
        "us_mil_wia": us_mil_wia,
        "collateral_usd": collateral_usd,
        "collateral_kia": int(collateral_kia),
        "n_sites_destroyed": n_sites_destroyed,
        "n_csg_neutralized": _n_neut,
        "n_csg_damaged": _n_dmg,
        "n_csg_intact": _n_intact,
        "actual_launched": actual_launched,
        "actual_intercepted": actual_intercepted,
        "actual_breakthrough": actual_breakthrough,
        "cap_hit": actual_intercepted >= cap,
        "csg_breakdown": csg_breakdown,
        "iran_cost_by_munition": iran_cost_by_munition,
        "iaf_cost": iaf_cost,
        "us_strike_cost": us_strike_cost,
        "us_intercept_cost": us_intercept_cost,
    }

    # ── Per-CSG Battle Damage Assessment table ──────────────────────────────────
    _col = max(len(c["name"]) for c in csg_fleet)
    _hdr = (f"{'CSG':<{_col}} | {'Hits':>5} | {'Status':<10} | "
            f"{'First Hit':>12} | {'Destroyed at':>13}")
    _div = "-" * len(_hdr)
    _tbl_rows = [_div, _hdr, _div]
    for _c in csg_fleet:
        _cn   = _c["name"]
        _hits = len(hits_timeline.get(_cn, []))
        _fh   = first_hit_s.get(_cn)
        _th   = tenth_hit_s.get(_cn)
        _status = "DESTROYED" if _th else ("DAMAGED" if _fh else "INTACT")
        _fh_s   = f"T+{_fh/60:5.1f} min" if _fh is not None else "---"
        _th_s   = f"T+{_th/60:5.1f} min" if _th is not None else "---"
        _tbl_rows.append(
            f"{_cn:<{_col}} | {_hits:>5} | {_status:<13} | {_fh_s:>12} | {_th_s:>12}")
    _tbl_rows.append(_div)
    _tbl_rows.append(
        f"FLEET RESULT: {_n_neut} DESTROYED | {_n_dmg} DAMAGED | {_n_intact} INTACT")
    _tbl_rows.append(_div)
    csg_table = "\n".join(_tbl_rows)

    # ── Analytical narrative (generated from computed simulation values) ─────────
    _int_pct   = round(100 * actual_intercepted / max(1, actual_launched))
    _bt_pct    = round(100 * actual_breakthrough / max(1, actual_launched))
    _supp      = n_missiles - actual_launched
    _supp_pct  = round(100 * _supp / max(1, n_missiles))
    _cap_flag  = actual_intercepted >= cap
    _vls_head  = max(0, cap - actual_intercepted)
    _cpk       = fmt_cost(us_intercept_cost / max(1, actual_intercepted))
    _destroyed_csgs = [c["name"] for c in csg_fleet if c["name"] in tenth_hit_s]
    _damaged_csgs   = [c["name"] for c in csg_fleet
                       if c["name"] in first_hit_s and c["name"] not in tenth_hit_s]
    _fh_times  = sorted(first_hit_s.values())  if first_hit_s  else []
    _th_times  = sorted(tenth_hit_s.values()) if tenth_hit_s else []

    def _para(*lines): return "\n".join(lines)

    # ── I. Executive Summary ─────────────────────────────────────────────────
    _cap_note = (" VLS INTERCEPT CEILING BREACHED — final salvo phases"
                 " faced under-defended terminal approaches." if _cap_flag else "")
    _I = _para(
        "══ I. EXECUTIVE SUMMARY ══════════════════════════════════════════════════",
        f"Iran commits {actual_launched:,} munitions against 8 US Carrier Strike Groups"
        f" (intended: {n_missiles:,}; {_supp:,} suppressed pre-launch [{_supp_pct}%]).",
        f"US/Coalition AEGIS defenses engage {actual_intercepted:,} rounds — an intercept"
        f" rate of {_int_pct}%.",
        f"{actual_breakthrough:,} rounds ({_bt_pct}%) breach the defensive envelope and"
        f" reach fleet positions.{_cap_note}",
        f"Engagement duration: ~{dur_min:.0f} minutes."
        f" Iranian launch network: {n_sites_destroyed}/12 sites destroyed.",
        f"Fleet outcome: {_n_neut} CSG(s) DESTROYED (≥10 hits)"
        f" | {_n_dmg} DAMAGED | {_n_intact} INTACT.",
    )

    # ── II. Offensive Capability Assessment ─────────────────────────────────
    _ai_note = (f" {actual_ai:,} AI-guided Shahed-136 terminal variants"
                f" ({round(100*actual_ai/max(1,actual_launched), 1)}% of salvo)"
                f" achieve guaranteed breakthroughs by defeating CIWS lead-angle prediction."
                if actual_ai > 0 else "")
    _supp_clause = (
        f"Preemptive US/IAF strikes suppress {_supp:,} ({_supp_pct}%) of Iran's"
        f" intended {n_missiles:,}-round salvo before launch — eliminating"
        f" {n_sites_destroyed} of 12 launch complexes"
        + (f" ({sites_destroyed_names})" if n_sites_destroyed > 0 else "")
        + f". {actual_launched:,} rounds reach flight."
        if _supp > 0
        else f"All {n_missiles:,} planned rounds reach flight — no pre-launch suppression achieved."
    )
    _II = _para(
        "══ II. OFFENSIVE CAPABILITY ASSESSMENT ══════════════════════════════════",
        _supp_clause,
        f"Iran expends {fmt_cost(iran_cost)} in offensive munitions"
        f" (weighted unit cost across {actual_launched:,} rounds)."
        + _ai_note,
        f"Surviving sites maintain continuous salvo pressure for ~{dur_min:.0f} min,"
        f" maximising sensor saturation and CIWS magazine consumption.",
    )

    # ── III. Defensive Performance Analysis ─────────────────────────────────
    _vls_note = (
        f"CRITICAL: Aegis VLS ceiling (~{cap:,} intercepts) was reached — subsequent"
        f" volleys faced degraded intercept probability as magazines approached depletion."
        if _cap_flag else
        f"VLS headroom remaining: {_vls_head:,} intercepts"
        f" ({round(100*_vls_head/max(1,cap))}% of capacity) — defense posture sustainable."
    )
    _III = _para(
        "══ III. DEFENSIVE PERFORMANCE ANALYSIS ═══════════════════════════════════",
        f"Aegis achieves a {_int_pct}% intercept rate"
        f" ({actual_intercepted:,} of {actual_launched:,} rounds engaged).",
        f"SM-6/SM-2 mid-course: {ibc['SM-6 / SM-2']:,} kills"
        f" | CIWS/SeaRAM terminal: {ibc['CIWS / SeaRAM']:,} kills"
        f" | Naval Gun: {ibc['Naval Gun / Phalanx']:,} kills.",
        f"Cost per intercept: {_cpk} (SM-6 @$3.3M dominant; CIWS @$800k supplemental).",
        _vls_note,
    )

    # ── IV. Fleet Damage Assessment ──────────────────────────────────────────
    _fh_str = f"T+{_fh_times[0]/60:.0f} min" if _fh_times else "—"
    _th_str = f"T+{_th_times[0]/60:.0f} min" if _th_times else "—"
    _dest_clause = ""
    if _n_neut > 0:
        _dest_clause = (
            f" Destroyed CSGs (≥10 hits, mission-killed): {', '.join(_destroyed_csgs)}."
            f" First CSG destroyed at {_th_str}."
            f" Each lost hull represents ~{TOTAL_CSG_PERSONNEL // 8:,} personnel at risk"
            f" and the permanent loss of ~90 embarked aircraft."
        )
    _dmg_clause = (
        f" Damaged CSGs (1–9 hits): {', '.join(_damaged_csgs)} —"
        f" mission-degraded; reduced sortie rate, likely port evacuation."
        if _damaged_csgs else ""
    )
    _IV = _para(
        "══ IV. FLEET DAMAGE ASSESSMENT ══════════════════════════════════════════",
        f"{actual_breakthrough:,} rounds ({_bt_pct}% of salvo) penetrate"
        f" to fleet engagement range. First impact on any CSG: {_fh_str}.",
        f"Fleet status: {_n_neut} DESTROYED | {_n_dmg} DAMAGED | {_n_intact} INTACT"
        f" (of 8 CSGs)." + _dest_clause + _dmg_clause,
    )

    # ── V. Cost-Exchange Analysis ─────────────────────────────────────────────
    _V = _para(
        "══ V. COST-EXCHANGE ANALYSIS ════════════════════════════════════════════",
        f"Iran offensive expenditure:      {fmt_cost(iran_cost)}"
        f" ({actual_launched:,} rounds × weighted unit cost)",
        f"US VLS interceptors:             {fmt_cost(us_intercept_cost)}"
        f" ({ibc['SM-6 / SM-2']:,} SM-6/SM-2 + {ibc['CIWS / SeaRAM']:,} CIWS + {ibc['Naval Gun / Phalanx']:,} Gun)",
        f"US counterstrikes (TLAM/JASSM):  {fmt_cost(us_strike_cost)}"
        f" ({len(strike_events):,} rounds)",
        f"US ship/aircraft damage:         {fmt_cost(us_ship_damage)}",
        f"US total coalition cost:         {fmt_cost(total_us_cost)}",
        f"Exchange ratio:                  {exchange_ratio:.1f}:1"
        f" — coalition spends ${exchange_ratio:.1f} for every $1 of Iranian outlay.",
        f"US military casualties:          {us_mil_kia:,} KIA / {us_mil_wia:,} WIA",
        f"Collateral (Gulf shipping):      {fmt_cost(collateral_usd)}"
        f" | ~{int(collateral_kia):,} civilian KIA",
    )

    # ── VI. Strategic Assessment ──────────────────────────────────────────────
    if _n_neut >= 4:
        _strat = (
            "Fleet combat effectiveness falls below the 50% threshold — a strategic"
            " catastrophe without precedent in post-1945 naval warfare. US carrier"
            " aviation over the Persian Gulf is forfeit for 12–24 months pending"
            " hull replacement. Iran achieves its core A2/AD objective: the permanent"
            " denial of carrier-based strike capacity within the Gulf littoral."
            " Comparable in scale to the destruction of Force Z (HMS Prince of Wales"
            " and Repulse) in December 1941, but delivered in under two hours."
        )
    elif _n_neut >= 2:
        _strat = (
            f"{_n_neut} carrier groups destroyed — a historically unprecedented loss"
            " for the US Navy in the missile era. Remaining CSGs will almost certainly"
            " reposition outside ASCM range (~600–800 km), fundamentally constraining"
            " tactical aviation reach over Iranian territory. Iran achieves partial A2/AD"
            " success: US cannot sustain carrier-based air operations in the Gulf without"
            " accepting unacceptable risk to surviving hulls."
        )
    elif _n_neut == 1:
        _strat = (
            "A single carrier group destroyed — the first such loss since the Battle of"
            " Leyte Gulf (1944). Political and operational consequences are severe:"
            " remaining CSGs will likely assume a defensive posture pending Presidential"
            " and SECDEF authorization to continue offensive operations. Iran demonstrates"
            " the credibility of its A2/AD doctrine at the cost of its offensive missile"
            " stockpile."
        )
    elif _n_dmg >= 3:
        _strat = (
            "No CSGs destroyed but fleet combat power is materially degraded."
            f" {_n_dmg} damaged escorts require port evacuation, reducing the strike"
            " envelope by 30–50% until replacements arrive."
            " Iran fails its primary objective but imposes significant operational costs"
            f" — {exchange_ratio:.1f}:1 exchange ratio confirms the strategic tax of"
            " defending against mass-missile attack."
        )
    else:
        _strat = (
            "Fleet emerges largely intact. Iran's offensive expenditure fails to achieve"
            " A2/AD denial objectives. US retains full carrier aviation capacity;"
            " follow-on strike packages can proceed without attrition-driven delays."
            f" At {exchange_ratio:.1f}:1, US coalition costs vastly outstrip Iranian"
            " outlay — validating the cost-exchange logic of saturation attack doctrine"
            " even when operationally unsuccessful."
        )
    _VI = _para(
        "══ VI. STRATEGIC ASSESSMENT ═════════════════════════════════════════════",
        _strat,
    )

    stats = (
        "\n\n".join([_I, _II, _III, _IV, _V, _VI])
        + f"\n\n══ PER-CSG BATTLE DAMAGE ASSESSMENT ═════════════════════════════════════\n"
        + csg_table
        + f"\n\n══ COST DETAIL ══════════════════════════════════════════════════════════\n"
        + cost_block
    )

    legend_lines = [
        "COLOR LEGEND",
        "============",
        "IRAN OFFENSIVE",
        "  Drones (yellow family):",
        "    Shahed-136 air drone        = YELLOW",
        "    IRGCN surface drone         = AMBER-YELLOW",
        "    AI-guided Shahed terminal   = WHITE (re-acquisition arc only)",
        "  Anti-ship missiles (red family):",
        "    Noor ASCM (subsonic)        = VIVID RED",
        "    Khalij Fars ASBM            = CRIMSON RED",
        "    CM-302 Supersonic ASCM      = SCARLET RED",
        "  Ballistic missiles (warm tones):",
        "    Fateh-110 / Fateh-313 SRBM  = AMBER",
        "    Shahab-3 MRBM               = AMBER-ORANGE",
        "    Zolfaghar SRBM              = ORANGE-RED",
        "    Emad MRBM                   = DEEP RED",
        "    Fattah-1 HGV                = MAGENTA (hypersonic, beyond red scale)",
        "",
        "US / COALITION",
        "  Anti-ground strikes (green family):",
        "    TLAM Block IV               = LIME GREEN",
        "    JASSM-ER                    = FOREST GREEN",
        "    IAF JDAM-ER                 = LIME-TEAL",
        "    IAF Rampage ALCM            = TEAL",
        "    IAF SPICE-2000              = DARK GREEN",
        "  Interceptors (blue family):",
        "    SM-6 / SM-2 (low scenario)  = LIGHT STEEL BLUE (star icon)",
        "    SM-6 / SM-2 (medium)        = CORNFLOWER BLUE (star icon)",
        "    SM-6 / SM-2 (high scenario) = NAVY BLUE (star icon)",
        "    CIWS / SeaRAM               = SKY BLUE (circle icon)",
        "    Naval Gun / Phalanx         = AZURE BLUE (circle icon)",
        "",
        "MARKERS",
        "  Orange star   = intercept kill point",
        "  Red target    = Iranian missile impact",
        "  Blue star     = US strike impact on Iranian site",
    ]
    for mname, mdef in MUNITIONS.items():
        if any(m["name"] == mname for m in sc["munitions"]):
            legend_lines.append(f"  [{mname}] {mdef['label']}")
    legend = "\n".join(legend_lines)

    tour_kml = gen_tour(tenth_hit_s, dur_min * 60, sc["label"])

    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"
     xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document id="doc_main">
  <name>{sc['label']}</name>
  <LookAt>
    <longitude>55.5</longitude>
    <latitude>26.5</latitude>
    <altitude>0</altitude>
    <range>900000</range>
    <tilt>45</tilt>
    <heading>0</heading>
    <altitudeMode>relativeToGround</altitudeMode>
  </LookAt>
  <description>{sc['description']}

{stats}

{legend}

Simulation start: {fmt_time(SIM_START)}
Use the Google Earth timeline slider to animate the attack.
Play the "Battle Tour" entry in the Places panel for an automated camera flythrough.</description>
{kml_styles()}

{tour_kml}

  <Folder>
    <name>US Forces -- 8 Carrier Strike Groups</name><visibility>1</visibility>
{gen_us_forces(first_hit_s, tenth_hit_s, latest_s, csg_fleet, hits_timeline)}
  </Folder>

  <Folder>
    <name>Iranian Launch Network ({n_sites_destroyed} sites destroyed)</name><visibility>1</visibility>
{gen_iran_sites(site_inactive_at, site_hits_timeline, latest_s)}
  </Folder>

  <Folder>
    <name>US Counterstrikes -- {len(strike_events)} TLAM/JASSM / {n_sites_destroyed} sites destroyed</name><visibility>1</visibility><open>0</open>
{"".join(f'''    <Folder>
      <name>{mtype} ({len(segs)} tracks)</name><open>0</open>
{"".join(segs)}
    </Folder>''' for mtype, segs in strike_segs.items() if segs)}
    <Folder>
      <name>Strike Impact Points ({len(strike_impacts)})</name><open>0</open>
{"".join(strike_impacts)}
    </Folder>
  </Folder>

  <Folder>
    <name>Iranian Munitions -- {actual_launched} launched / {actual_intercepted} intercepted / {actual_breakthrough} breakthrough</name><visibility>1</visibility><open>0</open>
{"".join(f'''    <Folder>
      <name>{mn} ({len(missile_segs[mn])} track-segs)</name><open>0</open>
{"".join(missile_segs[mn])}
    </Folder>''' for mn in _mnames if missile_segs[mn])}
  </Folder>

  <Folder>
    <name>US Interceptor Tracks -- {actual_intercepted} kills</name><visibility>1</visibility><open>0</open>
{"".join(f'''    <Folder>
      <name>{cat} ({len(segs)} track-segs)</name><open>0</open>
{"".join(segs)}
    </Folder>''' for cat, segs in sm6_segs.items() if segs)}
  </Folder>

  <Folder>
    <name>Intercept Kill Points -- {actual_intercepted}</name><visibility>1</visibility><open>0</open>
{"".join(f'''    <Folder>
      <name>{mn} kills ({len(intercept_pts[mn])})</name><open>0</open>
{"".join(intercept_pts[mn])}
    </Folder>''' for mn in _mnames if intercept_pts[mn])}
  </Folder>

  <Folder>
    <name>Breakthrough Impacts -- {actual_breakthrough}</name><visibility>1</visibility><open>0</open>
{"".join(f'''    <Folder>
      <name>{mn} impacts ({len(impact_pts[mn])})</name><open>0</open>
{"".join(impact_pts[mn])}
    </Folder>''' for mn in _mnames if impact_pts[mn])}
  </Folder>

  <Folder>
    <name>IAF Air Support -- {len(iaf_events)} strikes (F-35I/F-15I/F-16I)</name><visibility>1</visibility><open>0</open>
    <Folder>
      <name>IAF Bases</name><open>0</open>
{"".join(f'''      <Placemark><name>{b["name"]}</name><styleUrl>#iaf_base_marker</styleUrl>
      <description>{b["aircraft"]} | {b["sorties"]} sorties | {b["per_sortie"]} {b["munition"]}/sortie</description>
      <Point><coordinates>{b["lon"]:.4f},{b["lat"]:.4f},0</coordinates></Point></Placemark>''' for b in IAF_BASES)}
    </Folder>
{"".join(f'''    <Folder>
      <name>{mtype} ({len(segs)} tracks)</name><open>0</open>
{"".join(segs)}
    </Folder>''' for mtype, segs in iaf_segs.items() if segs)}
    <Folder>
      <name>IAF Impact Points ({len(iaf_impacts)})</name><open>0</open>
{"".join(iaf_impacts)}
    </Folder>
  </Folder>

  <Placemark id="time_cursor">
    <name/>
    <visibility>0</visibility>
    <TimeStamp><when>{fmt_time(sim_time(0))}</when></TimeStamp>
    <Point><coordinates>55.5,26.5,0</coordinates></Point>
  </Placemark>

</Document>
</kml>"""

    return kml, actual_launched, actual_intercepted, actual_breakthrough, dur_min, costs

# ============================================================
# MASTER KML
# ============================================================

def generate_master(stats):
    entries = []
    for key, (label, n, ki, kb, dur) in stats.items():
        entries.append(
            f"\n  <NetworkLink>"
            f"<name>{label}  [{ki}/{n} intercepted | {kb} breakthrough | ~{dur:.0f} min]</name>"
            f"<visibility>0</visibility>"
            f"<Link><href>scenarios/scenario_{key}.kml</href></Link>"
            f"</NetworkLink>"
        )

    legend_lines = ["Global color legend (all scenarios):"]
    for mdef in MUNITIONS.values():
        legend_lines.append(f"  {mdef['label']}")
    for sdef in US_STRIKE_MUNITIONS.values():
        legend_lines.append(f"  {sdef['label']}")
    legend_lines.append("  US SM-6 interceptors = white | CIWS = lime green")
    legend_lines.append("  Amber/cyan-green tracks = US TLAM/JASSM strikes outbound to Iran sites")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>Persian Gulf Wargame -- All Scenarios (8 CSGs)</name>
  <description>Eight-CSG simulation of Iranian mass-missile attacks on US Carrier Strike Groups.
US TLAM/JASSM counterstrikes destroy Iranian launch sites after 25 hits each.

Toggle scenarios with the folder checkboxes.
Use the Google Earth timeline slider to animate missile flights, intercepts, and impacts.
Each munition type has a distinct color; breakthrough tracks are brighter/thicker.
Amber/cyan-green arcs = US outbound TLAM/JASSM strikes; sites go gray when destroyed.

8 Carrier Strike Groups:
  USS Abraham Lincoln (CVN-72) | USS Gerald R. Ford (CVN-78) | USS George H.W. Bush (CVN-77)
  CSG Alpha (Arabian Sea) | CSG Bravo (N. Gulf) | CSG Charlie (C. Gulf)
  CSG Delta (S. Gulf) | CSG Echo (Hormuz approaches)

Armament estimates (unclassified, open-source):
  SM-6 per CSG: 24–66 rds (240 km)  |  SM-2: 60–203 rds (167 km)
  ESSM: 96–160 rds (50 km)           |  RAM: 42–105 rds (15 km)
  TLAM strike capacity: 48–128 rds per CSG
  Sources: CRS RL33199; IISS Military Balance 2024; influenceofhistory.blogspot.com

── Simultaneous launch (A–F) ──────────────────────────────────────────────────
Scenario A -- Low:       2,130 total   69% kill    ~665 breakthrough  US fires 160 strikes
Scenario B -- Medium:    4,400 total   65% kill  ~1,562 breakthrough  US fires 240 strikes
Scenario C -- High:      8,060 total   CAP HIT   ~4,060 breakthrough  US fires 320 strikes
Scenario D -- Realistic: 3,870 total   63% kill  ~1,417 breakthrough  US fires 240 strikes
Scenario E -- Iran Best: 10,800 total  CAP HIT   ~6,800 breakthrough  US fires 320 strikes
Scenario F -- USA Best:   1,330 total  93% kill      ~90 breakthrough  US fires 480 strikes  (all 12 sites destroyed)
── Phased launch: drones first (hr 0–1), then missiles (hr 1–2) ───────────────
Scenario G -- Drone-First Low:    2,130 total  65% kill    ~745 breakthrough  (+80 vs A)
Scenario H -- Drone-First Medium: 4,400 total  60% kill  ~1,760 breakthrough  (+198 vs B)
Scenario I -- Drone-First High:   8,060 total  46% kill  ~4,352 breakthrough  (+290 vs C, CIWS exhausted)

{chr(10).join(legend_lines)}

Simulation clock starts: {fmt_time(SIM_START)}</description>
{"".join(entries)}
</Document>
</kml>"""

# ============================================================
# LEGEND PNG GENERATOR
# ============================================================

def _kml_color_to_rgb(kml_hex):
    """Convert AABBGGRR KML hex string to (R,G,B) tuple."""
    kml_hex = kml_hex.lstrip("#")
    if len(kml_hex) == 8:
        # aa bb gg rr
        r = int(kml_hex[6:8], 16)
        g = int(kml_hex[4:6], 16)
        b = int(kml_hex[2:4], 16)
        return (r, g, b)
    return (128, 128, 128)


def generate_legend_png(scenario_key, sc, costs, n_launched, n_int, n_bt, dur_min, out_dir):
    """
    Generate a standalone PNG legend card for a scenario.
    Saved to out_dir/legend_<scenario_key>.png.
    Requires Pillow (pip install Pillow).
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None   # Pillow not installed — skip silently

    # ── Layout constants ─────────────────────────────────────────────────────
    W           = 540
    PAD         = 14
    SWATCH_W    = 22
    SWATCH_H    = 14
    ROW_H       = 22
    TITLE_H     = 36
    STATS_H     = 90
    SECTION_H   = 20
    BG          = (18, 22, 38)        # dark navy background
    FG          = (230, 230, 230)     # light grey text
    ACCENT      = (80, 160, 255)      # blue accent for headers
    DIVIDER     = (50, 55, 75)        # subtle horizontal rule colour

    # ── Font setup ───────────────────────────────────────────────────────────
    def _load_font(size, bold=False):
        """Try system fonts; fall back to PIL default."""
        candidates = []
        if bold:
            candidates = [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/calibrib.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
        else:
            candidates = [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/calibri.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    font_title  = _load_font(15, bold=True)
    font_header = _load_font(11, bold=True)
    font_body   = _load_font(11)
    font_small  = _load_font(10)

    # ── Build munition rows for this scenario ────────────────────────────────
    mun_rows = []   # (color_rgb, label_text)
    for mname, mdef in MUNITIONS.items():
        if any(m["name"] == mname for m in sc["munitions"]):
            rgb   = _kml_color_to_rgb(mdef["color_bt"])
            label = mdef["label"].split("(")[0].strip()
            mun_rows.append((rgb, label))

    # US anti-ground strikes
    for _, sdef in US_STRIKE_MUNITIONS.items():
        rgb   = _kml_color_to_rgb(sdef["color"])
        label = sdef["label"].split("(")[0].strip()
        mun_rows.append((rgb, label))

    # Fixed interceptor entries
    interceptor_rows = [
        ((136, 204, 255), "SM-6 / SM-2  (low scenario)"),
        ((68,  136, 255), "SM-6 / SM-2  (medium)"),
        ((0,    68, 255), "SM-6 / SM-2  (high scenario)"),
        ((0,   153, 255), "CIWS / SeaRAM"),
        ((51,  153, 255), "Naval Gun / Phalanx"),
    ]

    # ── Compute total image height ────────────────────────────────────────────
    H = (PAD + TITLE_H + PAD + STATS_H + PAD
         + SECTION_H + len(mun_rows) * ROW_H
         + SECTION_H + len(interceptor_rows) * ROW_H
         + PAD)

    img  = Image.new("RGBA", (W, H), BG + (240,))
    draw = ImageDraw.Draw(img)

    y = PAD

    # ── Title ─────────────────────────────────────────────────────────────────
    label_text = sc["label"]
    draw.text((PAD, y), label_text, font=font_title, fill=ACCENT)
    y += TITLE_H

    # ── Stats block ──────────────────────────────────────────────────────────
    draw.line([(PAD, y), (W - PAD, y)], fill=DIVIDER, width=1)
    y += 6

    def fc(usd):
        return f"${usd/1e9:.2f}B" if usd >= 1e9 else f"${usd/1e6:.1f}M"

    stat_lines = [
        f"Launched: {n_launched:,}   |   Intercepted: {n_int:,}   |   Breakthrough: {n_bt:,}",
        f"Duration: ~{dur_min:.0f} min   |   Iran cost: {fc(costs['iran_cost'])}   |   Coalition total: {fc(costs['total_us_cost'])}",
        f"US casualties: {costs['us_mil_kia']:,} KIA / {costs['us_mil_wia']:,} WIA   |   Exchange ratio: {costs['exchange_ratio']:.1f}:1",
        f"Sites destroyed: {costs.get('n_sites_destroyed', 0)}/12   |   Ship/aircraft damage: {fc(costs['us_ship_damage'])}",
    ]
    for sl in stat_lines:
        draw.text((PAD, y), sl, font=font_small, fill=FG)
        y += 20
    y += 4
    draw.line([(PAD, y), (W - PAD, y)], fill=DIVIDER, width=1)
    y += 8

    # ── Munition section ──────────────────────────────────────────────────────
    draw.text((PAD, y), "IRANIAN / THREAT MUNITIONS", font=font_header, fill=ACCENT)
    y += SECTION_H

    for rgb, lbl in mun_rows:
        draw.rectangle([PAD, y + 2, PAD + SWATCH_W, y + 2 + SWATCH_H], fill=rgb)
        draw.text((PAD + SWATCH_W + 8, y + 1), lbl, font=font_body, fill=FG)
        y += ROW_H

    y += 4
    draw.line([(PAD, y), (W - PAD, y)], fill=DIVIDER, width=1)
    y += 8

    # ── Interceptor / US section ───────────────────────────────────────────────
    draw.text((PAD, y), "US / COALITION RESPONSE", font=font_header, fill=ACCENT)
    y += SECTION_H

    for rgb, lbl in interceptor_rows:
        draw.rectangle([PAD, y + 2, PAD + SWATCH_W, y + 2 + SWATCH_H], fill=rgb)
        draw.text((PAD + SWATCH_W + 8, y + 1), lbl, font=font_body, fill=FG)
        y += ROW_H

    y += PAD

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path = os.path.join(out_dir, f"legend_{scenario_key}.png")
    img.save(out_path, "PNG")
    return out_path


# ============================================================
# SUMMARY KMZ
# ============================================================

def _fc(usd):
    """Format USD value as $XB or $XM."""
    return f"${usd/1e9:.2f}B" if usd >= 1e9 else f"${usd/1e6:.1f}M"


def generate_summary_kmz(stats, all_costs, out_dir, legend_png_path=None):
    """
    Generate a self-contained KMZ file with:
      - A Placemark at the geographic center of Iran
      - A rich dark-themed HTML description bubble with all-scenario data
      - A ScreenOverlay showing the legend image
    Saved to out_dir/wargame_summary.kmz
    """
    import zipfile

    IRAN_LON, IRAN_LAT = 53.688, 32.427   # geographic center of Iran

    # ── Color constants (same as main script) ─────────────────────────────────
    C_BG      = "#000000"
    C_ACCENT  = "#3399ff"
    C_LABEL   = "#7fa8cc"
    C_DATA    = "#e8f0ff"
    C_GREEN   = "#00dd66"
    C_YELLOW  = "#ffaa00"
    C_RED     = "#ff2222"
    C_ORANGE  = "#ff6600"
    C_DIM     = "#445566"
    C_IRAN    = "#ff6600"
    C_US      = "#3399ff"

    def _status_color(kb, n):
        """Color based on breakthrough ratio."""
        ratio = kb / max(1, n)
        if ratio < 0.15:
            return C_GREEN
        elif ratio < 0.35:
            return C_YELLOW
        elif ratio < 0.55:
            return C_ORANGE
        else:
            return C_RED

    def _grad(value, lo, hi, invert=False):
        """Interpolate CSS hex color on red→yellow→green gradient.
        invert=False: high value → red (bad).  invert=True: high value → green (good).
        Green=#00dd66  Yellow=#ffaa00  Red=#ff2222
        """
        if hi <= lo:
            return C_LABEL
        t = max(0.0, min(1.0, (value - lo) / (hi - lo)))
        if invert:
            t = 1.0 - t
        # t=0 → green, t=0.5 → yellow, t=1 → red
        if t <= 0.5:
            f = t * 2.0
            r = int(255 * f)
            g = int(221 + (170 - 221) * f)
            b = int(102 * (1.0 - f))
        else:
            f = (t - 0.5) * 2.0
            r = 255
            g = int(170 * (1.0 - f) + 34 * f)
            b = int(34 * f)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ── Build per-scenario rows ────────────────────────────────────────────────
    scenario_rows = []
    for key in (
                # Most → least realistic / probable
                "low",               # A – conservative baseline, most likely
                "realistic",         # D – combined-arms realistic
                "usa_best",          # F – best-case US conditions
                "medium",            # B – moderate Iranian capability
                "ballistic_barrage", # J – plausible pure-ballistic salvo
                "drone_first_low",   # G – phased assault, low scale
                "focused_salvo",     # H – concentrated on single CVN
                "coordinated_strike",# US/IAF coordinated first-strike
                "ascm_swarm",        # K – pure ASCM swarm
                "shore_based_defense",# L – THAAD+PAC-3 layered defense
                "drone_first_medium",# H – phased assault, medium
                "strait_transit",    # M – Hormuz column transit
                "high",              # C – high Iranian capability / CAP hit
                "hypersonic_threat", # I – Fattah-1 HGV mix
                "drone_first_high",  # I – phased assault, high saturation
                "iran_best",         # E – Iran best-case / least realistic
            ):
        if key not in stats:
            continue
        label, n, ki, kb, dur = stats[key]
        costs = all_costs.get(key, {})
        sc_col = _status_color(kb, n)
        int_pct = round(100 * ki / max(1, n))
        bt_pct  = round(100 * kb / max(1, n))
        scenario_rows.append((label, n, ki, kb, dur, costs, sc_col, int_pct, bt_pct))

    # ── Iranian offensive cost breakdown (aggregate across all scenarios) ─────
    # Show per-munition totals for the "realistic" scenario as a representative sample
    _ref_key   = "realistic" if "realistic" in all_costs else next(iter(all_costs))
    _ref_costs = all_costs[_ref_key]
    _icbm      = _ref_costs.get("iran_cost_by_munition", {})
    # pre-compute ranges for Iranian munition table gradients
    _iran_items = sorted(_icbm.items(), key=lambda x: -x[1])
    _iran_n_vals    = [round(c / max(1, MUNITIONS.get(mn, {}).get("cost_usd", 1)))
                       for mn, c in _iran_items]
    _iran_unit_vals = [MUNITIONS.get(mn, {}).get("cost_usd", 0) for mn, _ in _iran_items]
    _iran_tot_vals  = [c for _, c in _iran_items]
    _in_lo, _in_hi  = min(_iran_n_vals),    max(_iran_n_vals)
    _iu_lo, _iu_hi  = min(_iran_unit_vals), max(_iran_unit_vals)
    _it_lo, _it_hi  = min(_iran_tot_vals),  max(_iran_tot_vals)

    # Helper: table cell with gradient background, always-readable dark text
    _TD_PAD = "padding:3px 7px;font-size:11px;border-bottom:1px solid #00000022"
    def _gcell(text, col, align="right", bold=False, extra=""):
        fw = "font-weight:bold;" if bold else ""
        return (f'<td style="background:{col};color:#111;{fw}'
                f'text-align:{align};{_TD_PAD};{extra}">{text}</td>')

    iran_mun_rows_html = ""
    for (mn, cost), n_fired, unit in zip(_iran_items, _iran_n_vals, _iran_unit_vals):
        mdef = MUNITIONS.get(mn, {})
        mc   = _kml_to_css(mdef.get("color", "ff888888"))
        iran_mun_rows_html += (
            f'<tr>'
            f'<td style="color:{mc};padding:2px 8px 2px 0;white-space:nowrap;font-size:11px">{mn}</td>'
            + _gcell(f'{n_fired:,}',       _grad(n_fired, _in_lo, _in_hi))
            + _gcell(f'${unit/1e3:.0f}K',  _grad(unit,    _iu_lo, _iu_hi))
            + _gcell(f'${cost/1e6:.1f}M',  _grad(cost,    _it_lo, _it_hi), bold=True)
            + f'</tr>\n'
        )
    # Cost summary row values for the reference scenario
    _iaf_c  = _ref_costs.get("iaf_cost", 0)
    _vls_c  = _ref_costs.get("us_intercept_cost", 0)
    _str_c  = _ref_costs.get("us_strike_cost", 0)
    _ship_c = _ref_costs.get("us_ship_damage", 0)
    _iran_c = _ref_costs.get("iran_cost", 0)
    _tot_c  = _ref_costs.get("total_us_cost", 0)

    def _fmtc(v):
        return f"${v/1e9:.2f}B" if v >= 1e9 else f"${v/1e6:.1f}M"

    iran_cost_summary_html = (
        f'<tr><td style="color:{C_LABEL};font-size:11px;padding:2px 8px 2px 0">Iran offensive total</td>'
        f'<td colspan="3" style="color:{C_IRAN};font-weight:bold;font-size:11px;text-align:right">{_fmtc(_iran_c)}</td></tr>\n'
        f'<tr><td style="color:{C_DIM};font-size:10px;padding:2px 8px 2px 12px" colspan="4">'
        f'US VLS intercept: {_fmtc(_vls_c)} &nbsp;·&nbsp; '
        f'VLS strikes: {_fmtc(_str_c)} &nbsp;·&nbsp; '
        f'IAF munitions: {_fmtc(_iaf_c)} &nbsp;·&nbsp; '
        f'Ship damage: {_fmtc(_ship_c)} &nbsp;·&nbsp; '
        f'<b style="color:{C_US}">US total: {_fmtc(_tot_c)}</b>'
        f'</td></tr>\n'
    )

    # ── Per-CSG damage table (aggregate: sum across all scenarios) ─────────────
    csg_agg = {}   # csg_name -> {hits, damage_usd, kia, wia, n_neutralized, n_scenarios}
    for key, c in all_costs.items():
        for cname, bd in c.get("csg_breakdown", {}).items():
            if cname not in csg_agg:
                csg_agg[cname] = {"hits": 0, "damage_usd": 0, "kia": 0, "wia": 0,
                                  "n_neutralized": 0, "n_damaged": 0, "n_scenarios": 0,
                                  "asset_value_usd": bd["asset_value_usd"],
                                  "personnel": bd["personnel"]}
            ag = csg_agg[cname]
            ag["hits"]        += bd["hits"]
            ag["damage_usd"]  += bd["damage_usd"]
            ag["kia"]         += bd["kia"]
            ag["wia"]         += bd["wia"]
            ag["n_scenarios"] += 1
            if bd["status"] == "DESTROYED": ag["n_neutralized"] += 1
            elif bd["status"] == "DAMAGED":   ag["n_damaged"]     += 1

    n_sc = len(all_costs)
    # pre-compute averages for gradient ranges
    _csg_computed = {}
    for cname, ag in csg_agg.items():
        _csg_computed[cname] = {
            "avg_hits": ag["hits"]       / max(1, ag["n_scenarios"]),
            "avg_dmg":  ag["damage_usd"] / max(1, ag["n_scenarios"]),
            "avg_kia":  ag["kia"]        / max(1, ag["n_scenarios"]),
            "avg_wia":  ag["wia"]        / max(1, ag["n_scenarios"]),
            "neut_pct": 100 * ag["n_neutralized"] / max(1, n_sc),
            "dmg_pct":  100 * ag["n_damaged"]     / max(1, n_sc),
        }
    _ch_lo,  _ch_hi  = (min(v["avg_hits"] for v in _csg_computed.values()),
                        max(v["avg_hits"] for v in _csg_computed.values()))
    _cd_lo,  _cd_hi  = (min(v["avg_dmg"]  for v in _csg_computed.values()),
                        max(v["avg_dmg"]  for v in _csg_computed.values()))
    _ck_lo,  _ck_hi  = (min(v["avg_kia"]  for v in _csg_computed.values()),
                        max(v["avg_kia"]  for v in _csg_computed.values()))
    _cw_lo,  _cw_hi  = (min(v["avg_wia"]  for v in _csg_computed.values()),
                        max(v["avg_wia"]  for v in _csg_computed.values()))
    _cn_lo,  _cn_hi  = (min(v["neut_pct"] for v in _csg_computed.values()),
                        max(v["neut_pct"] for v in _csg_computed.values()))

    csg_rows_html = ""
    for cname, ag in csg_agg.items():
        cv = _csg_computed[cname]
        avg_hits = cv["avg_hits"]; avg_dmg = cv["avg_dmg"]
        avg_kia  = cv["avg_kia"]; avg_wia  = cv["avg_wia"]
        neut_pct = cv["neut_pct"]; dmg_pct = cv["dmg_pct"]
        csg_rows_html += (
            f'<tr>'
            f'<td style="color:{C_ACCENT};padding:2px 7px 2px 0;white-space:nowrap;font-size:11px">{cname}</td>'
            f'<td style="color:{C_DATA};padding:2px 7px 2px 0;text-align:right;font-size:11px">${ag["asset_value_usd"]/1e9:.1f}B</td>'
            f'<td style="color:{C_DATA};padding:2px 7px 2px 0;text-align:right;font-size:11px">{ag["personnel"]:,}</td>'
            + _gcell(f'{avg_hits:.1f}',        _grad(avg_hits, _ch_lo, _ch_hi))
            + _gcell(f'${avg_dmg/1e6:.0f}M',   _grad(avg_dmg,  _cd_lo, _cd_hi), bold=True)
            + _gcell(f'{avg_kia:.0f}',          _grad(avg_kia,  _ck_lo, _ck_hi))
            + _gcell(f'{avg_wia:.0f}',          _grad(avg_wia,  _cw_lo, _cw_hi))
            + _gcell(f'{neut_pct:.0f}%✕ {dmg_pct:.0f}%⚠', _grad(neut_pct, _cn_lo, _cn_hi), bold=True)
            + f'</tr>\n'
        )

    # ── SSPK table rows — gradient: high SSPK = green (good for defender) ──────
    sspk_rows_html = ""
    for mname, sp in MUNITION_SSPK.items():
        pct     = round(sp["sspk"] * 100)
        bar_w   = max(4, pct)
        bar_col = _grad(sp["sspk"], 0.0, 1.0, invert=True)  # high SSPK = green (defender succeeds)
        sspk_rows_html += (
            f'<tr>'
            f'<td style="color:{C_LABEL};padding:2px 10px 2px 0;white-space:nowrap;font-size:11px">{mname}</td>'
            f'<td style="color:{C_LABEL};padding:2px 10px 2px 0;white-space:nowrap;font-size:11px">{sp["interceptor"]}</td>'
            + _gcell(f'{pct}%', bar_col, bold=True,
                     extra=f'min-width:{bar_w + 20}px;text-align:center')
            + f'<td style="color:{C_DIM};font-size:10px;max-width:220px;padding:2px 4px">{sp["notes"]}</td>'
            f'</tr>\n'
        )

    # ── Scenario table rows ────────────────────────────────────────────────────
    TD  = f'padding:3px 7px 3px 0;text-align:right;border-bottom:1px solid {C_DIM}22;font-size:11px'
    TDL = f'padding:3px 7px 3px 0;text-align:left;border-bottom:1px solid {C_DIM}22;font-size:11px'

    def _csg_cell(neut, dmg, intact):
        """Color-coded 'N/D/I' compact CSG status."""
        parts = []
        if neut:  parts.append(f'<span style="color:{C_RED};font-weight:bold">{neut}✕</span>')
        if dmg:   parts.append(f'<span style="color:{C_YELLOW}">{dmg}⚠</span>')
        if intact:parts.append(f'<span style="color:{C_GREEN}">{intact}✓</span>')
        return " ".join(parts) if parts else f'<span style="color:{C_GREEN}">8✓</span>'

    # ── Pre-compute per-column ranges for gradient coloring ───────────────────
    def _rng(vals):
        v = [x for x in vals if x is not None]
        return (min(v), max(v)) if v else (0, 1)

    _all_n       = [r[1] for r in scenario_rows]
    _all_ip      = [r[7] for r in scenario_rows]
    _all_bt      = [r[8] for r in scenario_rows]
    _all_dur     = [r[4] for r in scenario_rows]
    _all_sites   = [r[5].get("n_sites_destroyed", 0) for r in scenario_rows]
    _all_iran_c  = [r[5].get("iran_cost", 0)         for r in scenario_rows]
    _all_ship_c  = [r[5].get("us_ship_damage", 0)    for r in scenario_rows]
    _all_us_c    = [r[5].get("total_us_cost", 0)     for r in scenario_rows]
    _all_exr     = [r[5].get("exchange_ratio", 0)     for r in scenario_rows]
    _all_kia     = [r[5].get("us_mil_kia", 0)        for r in scenario_rows]
    _all_wia     = [r[5].get("us_mil_wia", 0)        for r in scenario_rows]
    _all_civ     = [r[5].get("collateral_kia", 0)    for r in scenario_rows]

    _n_lo,  _n_hi  = _rng(_all_n)
    _ip_lo, _ip_hi = _rng(_all_ip)
    _bt_lo, _bt_hi = _rng(_all_bt)
    _dr_lo, _dr_hi = _rng(_all_dur)
    _si_lo, _si_hi = _rng(_all_sites)
    _ir_lo, _ir_hi = _rng(_all_iran_c)
    _sh_lo, _sh_hi = _rng(_all_ship_c)
    _us_lo, _us_hi = _rng(_all_us_c)
    _ex_lo, _ex_hi = _rng(_all_exr)
    _ki_lo, _ki_hi = _rng(_all_kia)
    _wi_lo, _wi_hi = _rng(_all_wia)
    _cv_lo, _cv_hi = _rng(_all_civ)

    sc_rows_html = ""
    for label, n, ki, kb, dur, costs, sc_col, int_pct, bt_pct in scenario_rows:
        exr      = costs.get("exchange_ratio", 0)
        iran_cv  = costs.get("iran_cost", 0)
        ship_cv  = costs.get("us_ship_damage", 0)
        us_cv    = costs.get("total_us_cost", 0)
        kia      = costs.get("us_mil_kia", 0)
        wia      = costs.get("us_mil_wia", 0)
        sites    = costs.get("n_sites_destroyed", 0)
        neut     = costs.get("n_csg_neutralized", 0)
        dmg      = costs.get("n_csg_damaged", 0)
        intact   = costs.get("n_csg_intact", 8)
        cap      = costs.get("cap_hit", False)
        civ_kia  = costs.get("collateral_kia", 0)
        ibc      = costs.get("intercept_by_cat", {})
        sm6_n    = ibc.get("SM-6 / SM-2", 0)
        ciws_n   = ibc.get("CIWS / SeaRAM", 0)
        gun_n    = ibc.get("Naval Gun / Phalanx", 0)
        cap_tag  = ' <span style="background:#ff0000;color:#fff;font-size:8px;padding:1px 3px">CAP✕</span>' if cap else ""
        sc_rows_html += (
            f'<tr>'
            f'<td style="color:{C_ACCENT};white-space:nowrap;{TDL}">{label}</td>'
            + _gcell(f'{n:,}',        _grad(n,       _n_lo,  _n_hi))
            + _gcell(f'{int_pct}%',   _grad(int_pct, _ip_lo, _ip_hi, True), bold=True)
            + _gcell(f'{bt_pct}%{cap_tag}', _grad(bt_pct, _bt_lo, _bt_hi), bold=True)
            + _gcell(f'{dur:.0f} m',  _grad(dur,     _dr_lo, _dr_hi))
            + f'<td style="{TD}">{_csg_cell(neut, dmg, intact)}</td>'
            + _gcell(f'{sites}/12',   _grad(sites,   _si_lo, _si_hi, True))
            + _gcell(_fc(iran_cv),    _grad(iran_cv, _ir_lo, _ir_hi))
            + _gcell(_fc(ship_cv),    _grad(ship_cv, _sh_lo, _sh_hi))
            + _gcell(_fc(us_cv),      _grad(us_cv,   _us_lo, _us_hi))
            + _gcell(f'{exr:.1f}:1',  _grad(exr,     _ex_lo, _ex_hi), bold=True)
            + _gcell(f'{kia:,}',      _grad(kia,     _ki_lo, _ki_hi))
            + _gcell(f'{wia:,}',      _grad(wia,     _wi_lo, _wi_hi))
            + _gcell(f'{civ_kia:,}',  _grad(civ_kia, _cv_lo, _cv_hi))
            + f'<td style="color:{C_DATA};font-size:10px;{TD}">SM6:{sm6_n} CIWS:{ciws_n} Gun:{gun_n}</td>'
            + f'</tr>\n'
        )

    desc_html = (
        "<![CDATA["
        f'<div style="background:{C_BG};color:{C_DATA};'
        f'font-family:\'Courier New\',Courier,monospace;'
        f'padding:16px 18px;margin:-15px -15px -20px -15px;'
        f'border-left:4px solid {C_ACCENT};border-top:3px solid {C_ACCENT}">'

        # Title
        f'<div style="color:{C_ACCENT};font-weight:bold;font-size:15px;'
        f'letter-spacing:3px;margin-bottom:12px;padding-bottom:6px;'
        f'border-bottom:2px solid {C_ACCENT}66">◈ PERSIAN GULF WARGAME — SCENARIO SUMMARY</div>'

        # Subtitle
        f'<div style="color:{C_LABEL};font-size:11px;margin-bottom:14px">'
        f'8 US Carrier Strike Groups vs. Iranian Mass-Missile Attack &nbsp;|&nbsp; '
        f'Simulation clock: {fmt_time(SIM_START)} UTC &nbsp;|&nbsp; '
        f'16 scenarios modeled</div>'

        # Scenario comparison table
        f'<div style="color:{C_ACCENT};font-weight:bold;font-size:12px;'
        f'letter-spacing:1px;margin-bottom:6px;border-bottom:1px solid {C_ACCENT}44;padding-bottom:3px">'
        f'SCENARIO COMPARISON</div>'
        f'<div style="overflow-x:auto">'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<tr style="border-bottom:2px solid {C_ACCENT}55">'
        f'<th style="color:{C_LABEL};text-align:left;padding:2px 7px 4px 0;font-size:11px">Scenario</th>'
        f'<th style="color:{C_LABEL};text-align:right;padding:2px 7px 4px 0;font-size:11px">Launched</th>'
        f'<th style="color:{C_GREEN};text-align:right;padding:2px 7px 4px 0;font-size:11px">Intercept%</th>'
        f'<th style="color:{C_RED};text-align:right;padding:2px 7px 4px 0;font-size:11px">Breakthr%</th>'
        f'<th style="color:{C_LABEL};text-align:right;padding:2px 7px 4px 0;font-size:11px">Dur</th>'
        f'<th style="color:{C_LABEL};text-align:right;padding:2px 7px 4px 0;font-size:11px">CSGs ✕⚠✓</th>'
        f'<th style="color:{C_YELLOW};text-align:right;padding:2px 7px 4px 0;font-size:11px">Sites/12</th>'
        f'<th style="color:{C_IRAN};text-align:right;padding:2px 7px 4px 0;font-size:11px">Iran $</th>'
        f'<th style="color:{C_RED};text-align:right;padding:2px 7px 4px 0;font-size:11px">Ship Dmg</th>'
        f'<th style="color:{C_US};text-align:right;padding:2px 7px 4px 0;font-size:11px">US Total $</th>'
        f'<th style="color:{C_RED};text-align:right;padding:2px 7px 4px 0;font-size:11px">Exch</th>'
        f'<th style="color:{C_RED};text-align:right;padding:2px 7px 4px 0;font-size:11px">US KIA</th>'
        f'<th style="color:{C_YELLOW};text-align:right;padding:2px 7px 4px 0;font-size:11px">US WIA</th>'
        f'<th style="color:{C_DIM};text-align:right;padding:2px 7px 4px 0;font-size:11px">Civ KIA</th>'
        f'<th style="color:{C_LABEL};text-align:right;padding:2px 7px 4px 0;font-size:11px">Interceptors</th>'
        f'</tr>\n'
        + sc_rows_html +
        f'</table></div>'

        # Iranian offensive cost breakdown (reference scenario)
        f'<div style="color:{C_ACCENT};font-weight:bold;font-size:12px;'
        f'letter-spacing:1px;margin:16px 0 6px;border-bottom:1px solid {C_ACCENT}44;padding-bottom:3px">'
        f'IRANIAN OFFENSIVE COSTS — {_ref_key.upper()} SCENARIO (REFERENCE)</div>'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<tr style="border-bottom:1px solid {C_ACCENT}44">'
        f'<th style="color:{C_LABEL};text-align:left;padding:2px 8px 4px 0;font-size:11px">Munition</th>'
        f'<th style="color:{C_LABEL};text-align:right;padding:2px 8px 4px 0;font-size:11px">Rounds</th>'
        f'<th style="color:{C_LABEL};text-align:right;padding:2px 8px 4px 0;font-size:11px">Unit Cost</th>'
        f'<th style="color:{C_IRAN};text-align:right;padding:2px 8px 4px 0;font-size:11px">Total Cost</th>'
        f'</tr>\n'
        + iran_mun_rows_html
        + iran_cost_summary_html
        + f'</table>'

        # CSG damage table (averaged across all scenarios)
        f'<div style="color:{C_ACCENT};font-weight:bold;font-size:12px;'
        f'letter-spacing:1px;margin:16px 0 6px;border-bottom:1px solid {C_ACCENT}44;padding-bottom:3px">'
        f'CSG DAMAGE &amp; CASUALTIES — AVERAGED ACROSS ALL SCENARIOS</div>'
        f'<div style="overflow-x:auto">'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<tr style="border-bottom:2px solid {C_ACCENT}44">'
        f'<th style="color:{C_LABEL};text-align:left;padding:2px 7px 4px 0;font-size:11px">CSG</th>'
        f'<th style="color:{C_LABEL};text-align:right;padding:2px 7px 4px 0;font-size:11px">Asset Value</th>'
        f'<th style="color:{C_LABEL};text-align:right;padding:2px 7px 4px 0;font-size:11px">Personnel</th>'
        f'<th style="color:{C_LABEL};text-align:right;padding:2px 7px 4px 0;font-size:11px">Avg Hits</th>'
        f'<th style="color:{C_RED};text-align:right;padding:2px 7px 4px 0;font-size:11px">Avg Damage</th>'
        f'<th style="color:{C_RED};text-align:right;padding:2px 7px 4px 0;font-size:11px">Avg KIA</th>'
        f'<th style="color:{C_YELLOW};text-align:right;padding:2px 7px 4px 0;font-size:11px">Avg WIA</th>'
        f'<th style="color:{C_LABEL};text-align:right;padding:2px 7px 4px 0;font-size:11px">Destroyed/Damaged%</th>'
        f'</tr>\n'
        + csg_rows_html +
        f'</table></div>'

        # SSPK table
        f'<div style="color:{C_ACCENT};font-weight:bold;font-size:12px;'
        f'letter-spacing:1px;margin:16px 0 6px;border-bottom:1px solid {C_ACCENT}44;padding-bottom:3px">'
        f'SINGLE-SHOT Pk (SSPK) — OPEN-SOURCE ESTIMATES</div>'
        f'<div style="color:{C_DIM};font-size:10px;margin-bottom:8px">'
        f'Sources: Wilkening (S&amp;GS 2000) · CSBA Salvo Competition (2015) · RAND BMD · '
        f'DOT&amp;E FY2018/2022 · JINSA/FPRI (2025) · Red Sea ops data</div>'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<tr style="border-bottom:1px solid {C_ACCENT}44">'
        f'<th style="color:{C_LABEL};text-align:left;padding:2px 10px 4px 0;font-size:11px">Munition</th>'
        f'<th style="color:{C_LABEL};text-align:left;padding:2px 10px 4px 0;font-size:11px">Best Interceptor</th>'
        f'<th style="color:{C_LABEL};text-align:left;padding:2px 10px 4px 0;font-size:11px">SSPK</th>'
        f'<th style="color:{C_LABEL};text-align:left;padding:2px 10px 4px 0;font-size:11px">Notes</th>'
        f'</tr>\n'
        + sspk_rows_html +
        f'</table>'

        # Footer / sources
        f'<div style="margin-top:12px;padding-top:8px;border-top:1px solid {C_ACCENT}33;'
        f'color:{C_DIM};font-size:10px">'
        f'All SSPK estimates unclassified open-source. Classified values not available. '
        f'Standard doctrine: 2 interceptors per ballistic threat (cumulative Pk 0.75–0.94). '
        f'Magazine depth is the binding operational constraint. '
        f'Exchange ratio = US total cost ÷ Iran offensive cost.'
        f'</div>'

        f'</div>'
        "]]>"
    )

    # ── Build the KML ──────────────────────────────────────────────────────────
    screen_overlay = ""
    legend_img_name = ""
    if legend_png_path and os.path.exists(legend_png_path):
        legend_img_name = "images/" + os.path.basename(legend_png_path)
        screen_overlay = (
            f'  <ScreenOverlay>'
            f'<name>Scenario Legend</name>'
            f'<Icon><href>{legend_img_name}</href></Icon>'
            f'<overlayXY x="0" y="1" xunits="fraction" yunits="fraction"/>'
            f'<screenXY x="0.01" y="0.99" xunits="fraction" yunits="fraction"/>'
            f'<rotationXY x="0" y="0" xunits="fraction" yunits="fraction"/>'
            f'<size x="0" y="0" xunits="fraction" yunits="fraction"/>'
            f'</ScreenOverlay>'
        )

    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"
     xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
  <name>Persian Gulf Wargame — Summary</name>
  <LookAt>
    <longitude>{IRAN_LON}</longitude>
    <latitude>{IRAN_LAT}</latitude>
    <altitude>0</altitude>
    <range>1800000</range>
    <tilt>0</tilt>
    <heading>0</heading>
    <altitudeMode>relativeToGround</altitudeMode>
  </LookAt>
  <Style id="iran_center">
    <IconStyle>
      <color>ff0066ff</color>
      <scale>1.6</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/paddle/red-stars.png</href></Icon>
    </IconStyle>
    <LabelStyle><color>ff0066ff</color><scale>1.3</scale></LabelStyle>
    <BalloonStyle>
      <bgColor>ff000000</bgColor>
      <textColor>ffe8f0ff</textColor>
      <text>$[description]</text>
    </BalloonStyle>
  </Style>
  <Placemark>
    <name>Persian Gulf Wargame — All Scenarios</name>
    <styleUrl>#iran_center</styleUrl>
    <description>{desc_html}</description>
    <Point>
      <altitudeMode>clampToGround</altitudeMode>
      <coordinates>{IRAN_LON},{IRAN_LAT},0</coordinates>
    </Point>
  </Placemark>
{screen_overlay}
</Document>
</kml>"""

    # ── Package as KMZ ────────────────────────────────────────────────────────
    kmz_path = os.path.join(out_dir, "wargame_summary.kmz")
    with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", kml_content.encode("utf-8"))
        if legend_png_path and os.path.exists(legend_png_path):
            zf.write(legend_png_path, legend_img_name)
    return kmz_path


# ============================================================
# ENTRY POINT
# ============================================================

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    out  = os.path.join(base, "scenarios")
    os.makedirs(out, exist_ok=True)

    seeds = {"low": 42, "medium": 7, "high": 13, "realistic": 99,
             "iran_best": 77, "usa_best": 11,
             "drone_first_low": 55, "drone_first_medium": 66, "drone_first_high": 88,
             "coordinated_strike": 99,   # same seed as realistic for direct comparison
             "focused_salvo": 99, "hypersonic_threat": 99,  # comparable to realistic
             "ballistic_barrage": 33, "ascm_swarm": 44, "shore_based_defense": 99,
             "strait_transit": 99}
    stats = {}
    all_costs = {}

    for key in ("low", "medium", "high", "realistic", "iran_best", "usa_best",
                "drone_first_low", "drone_first_medium", "drone_first_high",
                "coordinated_strike",
                "focused_salvo", "hypersonic_threat", "ballistic_barrage",
                "ascm_swarm", "shore_based_defense", "strait_transit"):
        print(f"  Generating {key} ...")
        kml, n, ki, kb, dur, costs = generate_scenario(key, seed=seeds[key])
        path = os.path.join(out, f"scenario_{key}.kml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(kml)
        size_mb = os.path.getsize(path) / 1_048_576
        sc = SCENARIOS[key]
        stats[key] = (sc["label"], n, ki, kb, dur)
        all_costs[key] = costs
        png_path = generate_legend_png(key, sc, costs, n, ki, kb, dur, out)
        if png_path:
            print(f"    legend -> {png_path}")

        def _fc(usd):
            return f"${usd/1e9:.2f}B" if usd >= 1e9 else f"${usd/1e6:.1f}M"

        ibc = costs["intercept_by_cat"]
        print(f"    {key}: {n} launched | {ki} intercepted | {kb} breakthrough | "
              f"~{dur:.0f} min | {size_mb:.1f} MB -> {path}")
        print(f"      Iran offensive: {_fc(costs['iran_cost'])}"
              f" | US: {_fc(costs['us_intercept_cost'])} intercept"
              f" ({ibc['SM-6 / SM-2']} SM-6, {ibc['CIWS / SeaRAM']} CIWS, {ibc['Naval Gun / Phalanx']} NavGun)"
              f" + {_fc(costs['us_strike_cost'])} strikes"
              f" + {_fc(costs['us_ship_damage'])} ship/a/c damage"
              f" = {_fc(costs['total_us_cost'])} total | ratio {costs['exchange_ratio']:.1f}:1")
        print(f"      US casualties: {costs['us_mil_kia']:,} KIA / {costs['us_mil_wia']:,} WIA"
              f" | Civilian collateral: {_fc(costs['collateral_usd'])} / {costs['collateral_kia']:,} KIA")

    master = os.path.join(base, "wargame_master.kml")
    with open(master, "w", encoding="utf-8") as fh:
        fh.write(generate_master(stats))
    print(f"  Master -> {master}")
    # ── Summary KMZ ───────────────────────────────────────────────────────────
    # Use the "realistic" scenario legend as the representative legend image
    legend_for_kmz = os.path.join(out, "legend_realistic.png")
    kmz_path = generate_summary_kmz(stats, all_costs, base, legend_for_kmz)
    print(f"  Summary KMZ -> {kmz_path}")
    print("Done.")


if __name__ == "__main__":
    main()
