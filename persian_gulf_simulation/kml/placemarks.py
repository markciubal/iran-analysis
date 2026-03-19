"""
kml/placemarks.py — KML placemark builders for agents, BMs, Stingers, and LZs.

Contains: agent_to_placemarks, bm_to_placemarks, stinger_wez_placemark,
          stinger_shot_placemark, lz_hover_zone_placemark, lz_marker_placemark,
          _stinger_wez_desc, _lz_hover_desc, _stinger_shot_desc, _stinger_arc_coords.
"""

from persian_gulf_simulation.config import (
    STINGER_WEZ_KM, STINGER_PK, STINGER_HOVER_PK, STINGER_HP, LZ_DROP_WINDOW_S,
    LZ_HOVER_RADIUS_KM, OSPREY_ALT_M, STINGER_ARC_PEAK_M, STINGER_ARC_SECS,
    DEATH_RISE_STEPS, DEATH_RISE_ALT_M,
    IRAN_BM_SALVO_STEP, IRAN_BM_FLIGHT_STEPS, IRAN_BM_PEAK_ALT_M,
    IRAN_BM_LETHAL_M, IRAN_BM_CEP_FATEH_M, IRAN_BM_CEP_ZOLFAGHAR_M,
    MV22_CAPACITY,
)
from persian_gulf_simulation.simulation.spatial import (
    dist_km, ts, ts_offset, ts_hhmm,
)
from persian_gulf_simulation.kml.styles import _hp_style, _circle_coords_deg
from persian_gulf_simulation.kml.descriptions import (
    _card, _alive_badge, _pct,
)


def _stinger_wez_desc(st):
    return _card(f"STINGER WEZ  {st.agent_id}", "#d29922", [
        ("Type",             "Weapons Engagement Zone"),
        ("MANPADS",          f"{st.agent_id}  HP {st.hp}/{STINGER_HP}"),
        ("Radius",           f"{STINGER_WEZ_KM} km"),
        ("Pk — Transit",     f"{STINGER_PK}  (outbound/inbound Osprey)"),
        ("Pk — Hover",       f'<span style="color:#f85149;font-weight:bold">'
                              f'{STINGER_HOVER_PK}</span>  ({LZ_DROP_WINDOW_S}s drop window)'),
        ("Status",           _alive_badge(st.hp > 0, "ACTIVE", "DESTROYED")),
    ])


def stinger_wez_placemark(st):
    pts = _circle_coords_deg(st.lon, st.lat, STINGER_WEZ_KM)
    coord_str = " ".join(f"{lon:.6f},{lat:.6f},0" for lon, lat in pts)
    desc = _stinger_wez_desc(st)
    t_begin = ts(0)
    timespan = (f"<TimeSpan><begin>{t_begin}</begin>"
                f"<end>{ts(st.dead_step)}</end></TimeSpan>"
                if st.dead_step is not None
                else f"<TimeSpan><begin>{t_begin}</begin></TimeSpan>")
    return f"""    <Placemark>
      <name>{st.agent_id} WEZ ({STINGER_WEZ_KM:.1f} km)</name>
      <description>{desc}</description>
      {timespan}
      <styleUrl>#stinger_wez</styleUrl>
      <Polygon>
        <altitudeMode>clampToGround</altitudeMode>
        <outerBoundaryIs><LinearRing>
          <coordinates>{coord_str}</coordinates>
        </LinearRing></outerBoundaryIs>
      </Polygon>
    </Placemark>"""


def _lz_hover_desc(lz_name, lz, n_teams_per_drop):
    return _card(f"LZ {lz_name} — HELICOPTER DROP ZONE", "#00ffff", [
        ("LZ Name",          lz_name),
        ("Coordinates",      f"{lz[0]:.4f}°E  {lz[1]:.4f}°N"),
        ("Hover Radius",     f"{LZ_HOVER_RADIUS_KM} km"),
        ("Drop Window",      f'<span style="color:#f85149;font-weight:bold">'
                              f'{LZ_DROP_WINDOW_S} seconds</span>'),
        ("Stinger Pk",       f'<span style="color:#f85149;font-weight:bold">'
                              f'{STINGER_HOVER_PK}</span>  during drop  '
                              f'(vs {STINGER_PK} in transit)'),
        ("Capacity/Drop",    f"~{n_teams_per_drop} fireteams  ({n_teams_per_drop * 4} men)"),
        ("Aircraft",         f"MV-22B Osprey  (450 km/h)"),
        ("Role",             "Vertical Assault / Heliborne Insertion"),
    ])


def lz_hover_zone_placemark(lz, lz_name, n_teams_per_drop):
    """Circle polygon marking the Osprey hover / drop zone at each LZ."""
    pts = _circle_coords_deg(lz[0], lz[1], LZ_HOVER_RADIUS_KM)
    coord_str = " ".join(f"{lon:.6f},{lat:.6f},0" for lon, lat in pts)
    desc = _lz_hover_desc(lz_name, lz, n_teams_per_drop)
    return f"""    <Placemark>
      <name>LZ {lz_name} Hover Zone</name>
      <description>{desc}</description>
      <styleUrl>#lz_hover_zone</styleUrl>
      <Polygon>
        <altitudeMode>clampToGround</altitudeMode>
        <outerBoundaryIs><LinearRing>
          <coordinates>{coord_str}</coordinates>
        </LinearRing></outerBoundaryIs>
      </Polygon>
    </Placemark>"""


def lz_marker_placemark(lz, lz_name, n_teams_per_drop):
    """Point marker at LZ centre with description card."""
    desc = _lz_hover_desc(lz_name, lz, n_teams_per_drop)
    return f"""    <Placemark>
      <name>LZ {lz_name}</name>
      <description>{desc}</description>
      <styleUrl>#lz_marker</styleUrl>
      <Point>
        <altitudeMode>clampToGround</altitudeMode>
        <coordinates>{lz[0]:.6f},{lz[1]:.6f},0</coordinates>
      </Point>
    </Placemark>"""


def _stinger_shot_desc(shot, idx):
    pk_label = "Hover (drop window)" if shot["pk"] >= STINGER_HOVER_PK else "Transit"
    result_html = (
        '<span style="color:#f85149;font-weight:bold">&#10007; HIT — AIRCRAFT DESTROYED</span>'
        if shot["hit"] else
        '<span style="color:#8b949e">&#10003; MISSED — missile expended</span>'
    )
    return _card(f"STINGER LAUNCH #{idx + 1}  ·  {shot['st_id']}", "#d29922", [
        ("Firing Unit",    shot["st_id"]),
        ("Target",         shot["ov_id"]),
        ("Engagement",     f'<span style="color:#d29922">{pk_label}  (Pk={shot["pk"]})</span>'),
        ("Result",         result_html),
        ("Time",           ts_hhmm(shot["step"])),
        ("Origin",         f"{shot['st_lon']:.4f}°E  {shot['st_lat']:.4f}°N"),
        ("Target Pos",     f"{shot['ov_lon']:.4f}°E  {shot['ov_lat']:.4f}°N"),
        ("Range",          f"{dist_km(shot['st_lon'], shot['st_lat'], shot['ov_lon'], shot['ov_lat']):.2f} km"),
    ])


def _stinger_arc_coords(shot, n_pts=20):
    """Parabolic arc from Stinger (ground) to Osprey (flight altitude).
    Miss trajectories overshoot the target by 20% to show the near-miss."""
    st_lon, st_lat = shot["st_lon"], shot["st_lat"]
    ov_lon, ov_lat = shot["ov_lon"], shot["ov_lat"]
    # Misses: extend endpoint 20% past target
    if not shot["hit"]:
        dx, dy = ov_lon - st_lon, ov_lat - st_lat
        ov_lon += dx * 0.20
        ov_lat += dy * 0.20
    start_alt = 5.0           # Stinger at ~5 m AGL
    end_alt   = OSPREY_ALT_M  # Osprey cruise altitude
    coords = []
    for i in range(n_pts):
        t   = i / (n_pts - 1)
        lon = st_lon + (ov_lon - st_lon) * t
        lat = st_lat + (ov_lat - st_lat) * t
        # Linear interpolation of base altitude + parabolic bump at apex
        base = start_alt + (end_alt - start_alt) * t
        arc  = 4.0 * STINGER_ARC_PEAK_M * t * (1.0 - t)
        coords.append((lon, lat, base + arc))
    return coords


def stinger_shot_placemark(shot, idx):
    """3D parabolic missile trajectory LineString with TimeSpan."""
    coords = _stinger_arc_coords(shot)
    coord_str = " ".join(f"{lon:.6f},{lat:.6f},{alt:.1f}" for lon, lat, alt in coords)
    style = "#stinger_hit" if shot["hit"] else "#stinger_miss"
    label = f"{'HIT' if shot['hit'] else 'MISS'} — {shot['st_id']} → {shot['ov_id']}"
    desc  = _stinger_shot_desc(shot, idx)
    t_begin = ts_offset(shot["step"], 0)
    t_end   = ts_offset(shot["step"], STINGER_ARC_SECS)
    return f"""    <Placemark>
      <name>{label}</name>
      <description>{desc}</description>
      <styleUrl>{style}</styleUrl>
      <TimeSpan><begin>{t_begin}</begin><end>{t_end}</end></TimeSpan>
      <LineString>
        <altitudeMode>relativeToGround</altitudeMode>
        <extrude>0</extrude>
        <coordinates>{coord_str}</coordinates>
      </LineString>
    </Placemark>"""


def _bm_polygon(center_lon, center_lat, radius_km, style_id, name, t_begin, t_end=None,
                extrude_height_m=None):
    """Polygon circle for CEP / kill-radius display.

    When extrude_height_m is set the polygon is extruded to that altitude
    (relativeToGround) forming a cylinder whose height equals the diameter.
    Otherwise the polygon is clamped flat to the ground.
    """
    pts = _circle_coords_deg(center_lon, center_lat, radius_km)
    if extrude_height_m:
        alt_m     = int(extrude_height_m)
        coord_str = " ".join(f"{lon:.6f},{lat:.6f},{alt_m}" for lon, lat in pts)
        geom = (
            "<Polygon>\n"
            "        <extrude>1</extrude>\n"
            "        <altitudeMode>relativeToGround</altitudeMode>\n"
            f"        <outerBoundaryIs><LinearRing>\n"
            f"          <coordinates>{coord_str}</coordinates>\n"
            "        </LinearRing></outerBoundaryIs>\n"
            "      </Polygon>"
        )
    else:
        coord_str = " ".join(f"{lon:.6f},{lat:.6f},0" for lon, lat in pts)
        geom = (
            "<Polygon>\n"
            "        <altitudeMode>clampToGround</altitudeMode>\n"
            f"        <outerBoundaryIs><LinearRing>\n"
            f"          <coordinates>{coord_str}</coordinates>\n"
            "        </LinearRing></outerBoundaryIs>\n"
            "      </Polygon>"
        )
    timespan = (f"<TimeSpan><begin>{t_begin}</begin><end>{t_end}</end></TimeSpan>"
                if t_end else
                f"<TimeSpan><begin>{t_begin}</begin></TimeSpan>")
    return f"""    <Placemark>
      <name>{name}</name>
      {timespan}
      <styleUrl>#{style_id}</styleUrl>
      {geom}
    </Placemark>"""


def bm_to_placemarks(bm, bm_outcome_map):
    """gx:Track for an Iranian SRBM with parabolic altitude arc, CEP ring, and kill-radius circle.

    Visualization layers per missile:
      1. gx:Track — animated parabolic arc from launch to impact/intercept
      2. CEP ring  — yellow circle at planned target, shown from launch until dead
      3. Kill-radius — red filled circle at actual impact point, persists after hit
      4. Dead icon   — star (impact) or cross-hairs (intercept) at terminal position
    """
    if not bm.track:
        return []

    target_lon, target_lat = bm.lz
    dead_s  = bm.dead_step
    outcome = bm_outcome_map.get(bm.agent_id)  # "hit" | "intercepted" | None

    bm_launch   = bm.launch_step if bm.launch_step is not None else IRAN_BM_SALVO_STEP
    bm_peak_alt = bm.peak_alt_m  if bm.peak_alt_m  is not None else IRAN_BM_PEAK_ALT_M

    # Style + type label match generate_wargame_kml.py MUNITIONS dict:
    #   75,000 m → Fateh-313 SRBM  (deep orange-red, cc0055ff)
    #  130,000 m → Zolfaghar SRBM  (orange,           cc0066ff)
    is_zolfaghar = bm_peak_alt >= 100_000
    bm_style   = "bm_zolfaghar" if is_zolfaghar else "bm_fateh313"
    bm_type    = "Zolfaghar SRBM" if is_zolfaghar else "Fateh-313 SRBM"
    cep_m      = IRAN_BM_CEP_ZOLFAGHAR_M if is_zolfaghar else IRAN_BM_CEP_FATEH_M
    # Use a minimum visible radius of 50 m so the CEP ring is clickable at map scale
    cep_km     = max(cep_m, 50) / 1000.0
    lethal_km  = IRAN_BM_LETHAL_M / 1000.0

    # ── 1. Missile trajectory (gx:Track, parabolic altitude) ─────────────────
    # Only include track points from launch step onwards — before launch the BM
    # sits at the (possibly elevated) launch site with alt=0 in absolute mode,
    # which places it underground at Iranian highland sites (e.g. Shiraz ~1,486 m).
    whens  = []
    coords = []
    for step, lon, lat, _ in bm.track:
        if step < bm_launch:
            continue   # skip pre-launch idle phase
        if dead_s is not None and step > dead_s:
            break
        flight_step = step - bm_launch
        t   = min(1.0, flight_step / IRAN_BM_FLIGHT_STEPS)
        alt = int(bm_peak_alt * 4.0 * t * (1.0 - t))
        whens.append(f"<when>{ts(step)}</when>")
        coords.append(f"<gx:coord>{lon:.6f} {lat:.6f} {alt}</gx:coord>")

    if not whens:
        return []

    whens_str  = "\n          ".join(whens)
    coords_str = "\n          ".join(coords)
    t_launch   = ts(bm_launch)
    t_dead     = ts(dead_s) if dead_s is not None else None

    alive_pm = f"""    <Placemark>
      <name>{bm_type} {bm.agent_id}</name>
      <styleUrl>#{bm_style}</styleUrl>
      <gx:Track>
        <altitudeMode>relativeToGround</altitudeMode>
        {whens_str}
        {coords_str}
      </gx:Track>
    </Placemark>"""

    pms = [alive_pm]

    # ── 2. CEP ring — appears at launch, disappears at dead_step ─────────────
    # Shows the accuracy envelope around the planned target.
    pms.append(_bm_polygon(
        target_lon, target_lat, cep_km,
        style_id="bm_cep",
        name=f"{bm_type} {bm.agent_id}  CEP {cep_m} m",
        t_begin=t_launch,
        t_end=t_dead,
    ))

    # ── 3. Dead icon + kill-radius circle (only after impact/intercept) ───────
    # Impacts flash red → orange → yellow (4 cycles × 8 s each), then settle to red.
    # Intercepts show a static cross-hairs only.
    _FLASH_S    = 15   # seconds per colour phase
    _FLASH_REPS = 6    # cycles of red → orange → yellow before settling (6×3×15 = 270 s)
    _ICON_STYLES   = ["bm_hit",         "bm_hit_orange",         "bm_hit_yellow"]
    _CIRCLE_STYLES = ["bm_kill_radius", "bm_kill_radius_orange", "bm_kill_radius_yellow"]

    if dead_s is not None:
        recs = [r for r in bm.track if r[0] <= dead_s]
        if recs:
            _, flon, flat, _ = recs[-1]
            is_intercept = (outcome == "intercepted") or \
                           dist_km(flon, flat, target_lon, target_lat) > 0.1

            if is_intercept:
                # Static intercept marker — no flash
                pms.append(f"""    <Placemark>
      <name>{bm_type} {bm.agent_id}  &#x2715; INTERCEPTED</name>
      <styleUrl>#bm_intercepted</styleUrl>
      <TimeSpan><begin>{ts(dead_s)}</begin></TimeSpan>
      <Point>
        <altitudeMode>relativeToGround</altitudeMode>
        <coordinates>{flon:.6f},{flat:.6f},0</coordinates>
      </Point>
    </Placemark>""")
            else:
                impact_label = f"{bm_type} {bm.agent_id}  &#x26A0; IMPACT"
                circle_name  = f"{bm_type} {bm.agent_id}  Kill Radius {IRAN_BM_LETHAL_M} m"

                # Flash sequence: _FLASH_REPS cycles of red → orange → yellow
                for rep in range(_FLASH_REPS):
                    for ci in range(3):
                        t0 = ts_offset(dead_s, (rep * 3 + ci)     * _FLASH_S)
                        t1 = ts_offset(dead_s, (rep * 3 + ci + 1) * _FLASH_S)
                        pms.append(f"""    <Placemark>
      <name>{impact_label}</name>
      <styleUrl>#{_ICON_STYLES[ci]}</styleUrl>
      <TimeSpan><begin>{t0}</begin><end>{t1}</end></TimeSpan>
      <Point>
        <altitudeMode>relativeToGround</altitudeMode>
        <coordinates>{flon:.6f},{flat:.6f},0</coordinates>
      </Point>
    </Placemark>""")
                        pms.append(_bm_polygon(
                            flon, flat, lethal_km,
                            style_id=_CIRCLE_STYLES[ci],
                            name=circle_name,
                            t_begin=t0,
                            t_end=t1,
                            extrude_height_m=IRAN_BM_LETHAL_M * 2,
                        ))

                # Persistent final state (red) after flashing ends
                t_settle = ts_offset(dead_s, _FLASH_REPS * 3 * _FLASH_S)
                pms.append(f"""    <Placemark>
      <name>{impact_label}</name>
      <styleUrl>#bm_hit</styleUrl>
      <TimeSpan><begin>{t_settle}</begin></TimeSpan>
      <Point>
        <altitudeMode>relativeToGround</altitudeMode>
        <coordinates>{flon:.6f},{flat:.6f},0</coordinates>
      </Point>
    </Placemark>""")
                pms.append(_bm_polygon(
                    flon, flat, lethal_km,
                    style_id="bm_kill_radius",
                    name=circle_name,
                    t_begin=t_settle,
                    t_end=None,   # persists
                    extrude_height_m=IRAN_BM_LETHAL_M * 2,
                ))

    return pms


def _agent_label(agent_id, unit_name,
                  is_marine, is_stinger, is_drone, is_osprey,
                  is_ship, is_dboat, is_shahed, is_island_shahed,
                  phase_hp, max_hp, dead=False, is_air=False):
    """Build a verbose placemark <name> for an agent.

    Format (alive):  "{type} {id}  {hp_bar}"
    Format (dead):   "{type} {id}  {empty_bar}  KIA / SHOT DOWN / SUNK"
    Ships use unit_name (e.g. "USS Tripoli (LHA-7)") in place of the raw agent_id.
    """
    if unit_name:
        # Ships: full display name replaces both type prefix and raw id
        base = unit_name
    elif is_marine:
        base = f"USMC Fireteam {agent_id}"
    elif is_stinger:
        base = f"IRGC MANPADS {agent_id}"
    elif is_osprey:
        base = f"MV-22B Osprey {agent_id}"
    elif is_drone:
        base = f"MQ-9 Reaper {agent_id}"
    elif is_dboat:
        base = f"IRGCN FIAC {agent_id}"
    elif is_shahed:
        base = f"Shahed-136 {agent_id}"
    elif is_island_shahed:
        base = f"Shahed-136 Island Strike {agent_id}"
    else:
        # IRGC ground squad
        base = f"IRGC Squad {agent_id}"

    if max_hp:
        if dead:
            bar = "\u2591" * max_hp   # all empty
        else:
            bar = "\u2588" * phase_hp + "\u2591" * (max_hp - phase_hp)
        hp_str = f"  {bar}  [{phase_hp}/{max_hp} HP]"
    else:
        hp_str = ""

    if dead:
        if is_ship:
            status = "  ⚠ SUNK"
        elif is_air:
            status = "  ✕ SHOT DOWN"
        else:
            status = "  ✕ KIA"
        return f"{base}{hp_str}{status}"

    return f"{base}{hp_str}"


def agent_to_placemarks(agent, is_marine, n_steps,
                         desc_html=None, desc_fn=None,
                         is_stinger=False, is_drone=False, is_osprey=False,
                         is_ship=False, is_dboat=False, is_shahed=False,
                         is_island_shahed=False,
                         altitude_m=0, max_hp=None,
                         unit_name=None):
    """altitude_m > 0 → track rendered at that height relativeToGround.
    Dead markers always clamp to ground regardless of altitude_m.
    unit_name overrides the agent_id in the label (used for named ships)."""
    if not agent.track:
        return []

    alt_mode   = "relativeToGround" if altitude_m > 0 else "clampToGround"
    alt_str    = str(int(altitude_m))
    is_air     = is_osprey or is_drone or is_shahed or is_island_shahed

    placemarks = []

    # Build HP phases — SKIP hp=0 phase (dead agents stop their track)
    phases  = []
    cur_hp  = agent.track[0][3]
    cur_pts = [(agent.track[0][0], agent.track[0][1], agent.track[0][2])]

    for step, lon, lat, hp in agent.track[1:]:
        if hp == cur_hp:
            cur_pts.append((step, lon, lat))
        else:
            if cur_hp > 0:
                phases.append((cur_hp, cur_pts))
            cur_hp  = hp
            cur_pts = [(step, lon, lat)]
    if cur_hp > 0:
        phases.append((cur_hp, cur_pts))

    first_phase = True
    for phase_hp, pts in phases:
        style   = _hp_style(phase_hp, is_marine, alive=True,
                             is_stinger=is_stinger, is_drone=is_drone,
                             is_osprey=is_osprey, is_ship=is_ship,
                             is_dboat=is_dboat, is_shahed=is_shahed,
                             is_island_shahed=is_island_shahed)
        t_begin = ts(pts[0][0])
        t_end   = ts(pts[-1][0])
        when_lines  = "\n          ".join(f"<when>{ts(s)}</when>" for s, _, _ in pts)
        coord_lines = "\n          ".join(
            f"<gx:coord>{lon:.6f} {lat:.6f} {alt_str}</gx:coord>" for _, lon, lat in pts
        )
        if desc_fn is not None:
            desc_tag = f"\n      <description>{desc_fn(phase_hp)}</description>"
        elif first_phase and desc_html:
            desc_tag = f"\n      <description>{desc_html}</description>"
        else:
            desc_tag = ""
        label = _agent_label(
            agent.agent_id, unit_name,
            is_marine, is_stinger, is_drone, is_osprey,
            is_ship, is_dboat, is_shahed, is_island_shahed,
            phase_hp, max_hp, dead=False, is_air=is_air,
        )
        placemarks.append(f"""    <Placemark>
      <name>{label}</name>{desc_tag}
      <styleUrl>{style}</styleUrl>
      <TimeSpan><begin>{t_begin}</begin><end>{t_end}</end></TimeSpan>
      <gx:Track>
        <altitudeMode>{alt_mode}</altitudeMode>
        {when_lines}
        {coord_lines}
      </gx:Track>
    </Placemark>""")
        first_phase = False

    # Animated dead marker — icon rises from ground ("soul rising" effect)
    if agent.dead_step is not None:
        idx = agent.dead_step
        death_lon = agent.track[idx][1] if idx < len(agent.track) else agent.lon
        death_lat = agent.track[idx][2] if idx < len(agent.track) else agent.lat
        style     = _hp_style(0, is_marine, alive=False,
                               is_stinger=is_stinger, is_drone=is_drone,
                               is_osprey=is_osprey, is_ship=is_ship,
                               is_dboat=is_dboat, is_shahed=is_shahed,
                               is_island_shahed=is_island_shahed)
        if desc_fn is not None:
            desc_tag = f"\n      <description>{desc_fn(0)}</description>"
        elif desc_html:
            desc_tag = f"\n      <description>{desc_html}</description>"
        else:
            desc_tag = ""
        anim_whens = "\n          ".join(
            f"<when>{ts(agent.dead_step + i)}</when>"
            for i in range(DEATH_RISE_STEPS + 1)
        )
        if is_air:
            # Fall: altitude_m → 0
            anim_coords = "\n          ".join(
                f"<gx:coord>{death_lon:.6f} {death_lat:.6f} "
                f"{int(altitude_m * (DEATH_RISE_STEPS - i) / DEATH_RISE_STEPS)}</gx:coord>"
                for i in range(DEATH_RISE_STEPS + 1)
            )
        else:
            # Rise: 0 → DEATH_RISE_ALT_M
            anim_coords = "\n          ".join(
                f"<gx:coord>{death_lon:.6f} {death_lat:.6f} "
                f"{int(DEATH_RISE_ALT_M * i / DEATH_RISE_STEPS)}</gx:coord>"
                for i in range(DEATH_RISE_STEPS + 1)
            )
        dead_label = _agent_label(
            agent.agent_id, unit_name,
            is_marine, is_stinger, is_drone, is_osprey,
            is_ship, is_dboat, is_shahed, is_island_shahed,
            0, max_hp, dead=True, is_air=is_air,
        )
        placemarks.append(f"""    <Placemark>
      <name>{dead_label}</name>{desc_tag}
      <styleUrl>{style}</styleUrl>
      <TimeSpan><begin>{ts(agent.dead_step)}</begin></TimeSpan>
      <gx:Track>
        <altitudeMode>relativeToGround</altitudeMode>
        {anim_whens}
        {anim_coords}
      </gx:Track>
    </Placemark>""")

    return placemarks
