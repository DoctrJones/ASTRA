import json
import os
import sys
import math

# ── Configuration ─────────────────────────────────────────────────────────────
OUTPUT_FOLDER = "Reports"
LINE_WIDTH    = 72
#USAGE: python report.py "Generated Systems/system.json"
# ── Formatting helpers ────────────────────────────────────────────────────────
def divider(char="═", width=LINE_WIDTH):
    return char * width

def section(title, char="─"):
    pad = (LINE_WIDTH - len(title) - 2) // 2
    return f"{char * pad} {title} {char * (LINE_WIDTH - pad - len(title) - 2)}"

def field(label, value, unit="", width=28):
    label_str = f"  {label}:"
    value_str = f"{value} {unit}".strip()
    return f"{label_str:<{width}} {value_str}"

def wrap(text, width=LINE_WIDTH, indent=2):
    """Word-wrap a paragraph to width with indent."""
    words  = text.split()
    lines  = []
    current = " " * indent
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current.rstrip())
            current = " " * indent + word + " "
        else:
            current += word + " "
    if current.strip():
        lines.append(current.rstrip())
    return "\n".join(lines)

# ── Narrative builders ────────────────────────────────────────────────────────

def star_narrative(data):
    star   = data
    name   = star["name"]
    cls    = star["class"]
    color  = star["color"]
    mass   = star["Star_Mo"]
    lum    = star["Star_Lo"]
    temp   = star["Star_T"]
    metal  = star["Star_Metallicity"]
    bodies = data["bodies"]
    nb     = len(bodies)
    giants = [b for b in bodies if b["data"]["type"] == "giant"]
    rocky  = [b for b in bodies if b["data"]["type"] == "rocky"]

    # Star character
    if cls == "O":
        char = "a blazing blue giant — extraordinarily hot and luminous, hostile to most life"
    elif cls == "B":
        char = "a hot blue-white star — brilliant and short-lived by stellar standards"
    elif cls == "A":
        char = "a white star somewhat hotter than our Sun, bathing its system in intense light"
    elif cls == "F":
        char = "a yellowish-white star slightly more massive and luminous than our Sun"
    elif cls == "G":
        char = "a yellow star broadly similar to our own Sun — among the most hospitable stellar types"
    elif cls == "K":
        char = "a stable orange star, cooler and longer-lived than the Sun, considered favourable for life"
    else:
        char = "a dim red dwarf — the most common type of star in the galaxy, cool and long-lived"

    # Metallicity flavour
    if metal > 0.2:
        metal_note = "Its high metallicity suggests a rich supply of heavy elements, favouring rocky planet formation."
    elif metal > 0.0:
        metal_note = "With slightly above-average metallicity, conditions were favourable for planet formation."
    elif metal > -0.3:
        metal_note = "Its near-solar metallicity places it in the typical range for planet-bearing stars."
    elif metal > -0.6:
        metal_note = "Its below-average metallicity hints at an older, more metal-poor origin."
    else:
        metal_note = "Its low metallicity suggests this is an old, metal-poor star — planetary formation here was challenging."

    # System character
    if not bodies:
        sys_note = "Remarkably, no major orbital bodies formed around it — only belt debris remains."
    elif len(giants) == 0:
        sys_note = f"Its system consists entirely of rocky worlds — {nb} terrestrial bod{'y' if nb==1 else 'ies'} with no giant planets."
    elif len(giants) == 1:
        sys_note = f"Its system hosts {nb} orbital bod{'y' if nb==1 else 'ies'}, including one gas giant."
    else:
        sys_note = f"Its system is dominated by {len(giants)} gas giants among {nb} total orbital bodies."

    text = (f"{name} is {char}. "
            f"It shines with {lum} solar luminosities at a surface temperature of {round(temp)} K, "
            f"with a mass of {mass} solar masses. "
            f"{metal_note} {sys_note}")
    return wrap(text)

def body_narrative(body, star_data):
    name    = body["name"]
    btype   = body["data"]["type"]
    subclass = body["data"].get("subclass") or ""
    mass    = body["data"]["mass"]["value"]
    sma     = body["data"]["SMA"]["value"]
    temp    = body["atmosphere"]["Surface_Temperature"]["value"]
    press   = body["atmosphere"]["Surface_Pressure"]["value"]
    has_atmo = body["atmosphere"]["Has_Atmosphere"]
    atmo_type = body["atmosphere"]["Atmosphere_Type"]["value"]
    irrad   = body["atmosphere"]["Irradiance"]["value"]
    dynamo  = body["core"]["Dynamo_Factor"]["value"]
    gold    = body["orbit"]["In_Goldilocks"]["value"]
    tect    = body["tectonics"].get("Tectonic_Activity", {}).get("value", "N/A")
    volc    = body["tectonics"].get("Volcanic_Activity", {}).get("value", "None")
    ocean   = body["tectonics"].get("Ocean_Coverage", {}).get("value", 0)
    hab_tier = body["habitability"]["Biosphere_Tier"]["value"]
    bio_score = body["habitability"].get("Biosphere_Score", {}).get("value", 0)
    biochem = body["habitability"]["Biochemistry_Type"]["value"]
    moons   = body.get("moons", [])
    rings   = body.get("rings", {})
    subscores = body["habitability"].get("Subscores") or {}
    energy_sub = subscores.get("energy", {})
    dominant_energy = energy_sub.get("dominant_source", "stellar")

    sentences = []

    # Opening — what kind of world is it
    if btype == "giant":
        if subclass == "gas_giant":
            sentences.append(f"{name} is a gas giant — a massive world of swirling hydrogen and helium with no solid surface, orbiting at {sma} AU.")
        else:
            sentences.append(f"{name} is an ice giant — a dense world of water, methane, and ammonia beneath a thin hydrogen envelope, orbiting at {sma} AU.")
    elif btype == "rocky":
        if mass < 0.1:
            kind = "a small, barren sub-Earth"
        elif mass < 0.5:
            kind = "a modest rocky world, smaller than Earth"
        elif mass < 1.5:
            kind = "a terrestrial world of roughly Earth-like proportions"
        elif mass < 3.0:
            kind = "a substantial super-Earth, more massive than our own planet"
        else:
            kind = "a massive super-Earth with formidable surface gravity"
        sentences.append(f"{name} is {kind}, orbiting at {sma} AU from its star.")

    # Goldilocks context
    if btype == "rocky":
        if gold:
            sentences.append("It sits within the classical habitable zone of its star.")
        else:
            if irrad < 50:
                sentences.append("It lies far beyond the traditional habitable zone, receiving very little stellar energy.")
            elif irrad < 200:
                sentences.append("Though outside the classical habitable zone, it receives modest stellar irradiance.")
            else:
                sentences.append("It sits just outside the classical habitable zone, but receives meaningful stellar energy.")

    # Atmosphere
    if btype != "giant":
        if not has_atmo:
            sentences.append("The surface is exposed and airless — no atmosphere has formed or survived here.")
        else:
            if isinstance(press, (int, float)):
                if press < 0.01:
                    press_desc = "a trace atmosphere barely above vacuum"
                elif press < 0.1:
                    press_desc = "a thin, tenuous atmosphere"
                elif press < 0.5:
                    press_desc = "a modest but present atmosphere"
                elif press < 2.0:
                    press_desc = "a substantial atmosphere comparable to Earth's"
                elif press < 10.0:
                    press_desc = "a dense, pressurised atmosphere"
                else:
                    press_desc = "a crushing, high-pressure atmosphere"
                sentences.append(f"It holds {press_desc} of {round(press, 2)} atm, dominated by {atmo_type}.")

    # Temperature
    if btype != "giant":
        if isinstance(temp, (int, float)):
            if temp < -150:
                temp_desc = "bitterly frozen"
            elif temp < -60:
                temp_desc = "extremely cold"
            elif temp < 0:
                temp_desc = "sub-zero"
            elif temp < 20:
                temp_desc = "cool"
            elif temp < 45:
                temp_desc = "temperate"
            elif temp < 80:
                temp_desc = "warm"
            elif temp < 150:
                temp_desc = "very hot"
            else:
                temp_desc = "scorching"

            if dominant_energy == "tidal" and btype == "rocky":
                sentences.append(f"Surface temperatures are {temp_desc} at {temp}°C, warmed significantly by tidal heating from its parent body rather than starlight.")
            else:
                sentences.append(f"Surface temperatures are {temp_desc} at {temp}°C.")

    # Tectonics
    if btype == "rocky":
        if tect == "Active":
            if volc in ("High", "Moderate"):
                sentences.append(f"The crust is geologically active with {volc.lower()} volcanism across {body['tectonics'].get('Plate_Count', {}).get('value', '?')} tectonic plates.")
            else:
                sentences.append(f"The crust is geologically active across {body['tectonics'].get('Plate_Count', {}).get('value', '?')} tectonic plates.")
        elif tect == "Dormant":
            sentences.append("Geological activity has largely quieted — the world is tectonically dormant.")
        else:
            sentences.append("The crust is geologically dead, with no meaningful tectonic activity.")

        if ocean and ocean > 0:
            if ocean > 0.7:
                sentences.append(f"The surface is predominantly ocean, with {round(ocean*100)}% water coverage leaving little exposed land.")
            elif ocean > 0.4:
                sentences.append(f"Vast oceans cover {round(ocean*100)}% of the surface.")
            elif ocean > 0.1:
                sentences.append(f"Seas and shallow oceans cover {round(ocean*100)}% of the surface.")
            else:
                sentences.append(f"Small bodies of liquid cover only {round(ocean*100)}% of the surface.")

    # Magnetic field
    if btype == "rocky":
        if dynamo >= 0.5:
            sentences.append("A strong magnetic field shields the surface from stellar radiation.")
        elif dynamo >= 0.3:
            sentences.append("A moderate magnetic field provides reasonable protection from stellar radiation.")
        elif dynamo >= 0.2:
            sentences.append("A weak magnetic field offers limited protection from stellar radiation.")
        else:
            sentences.append("The absence of a meaningful magnetic field leaves the surface exposed to stellar radiation.")

    # Life
    LIFE_TIERS = {"microbial", "simple_multicellular", "complex_multicellular", "advanced"}
    if hab_tier in LIFE_TIERS:
        if hab_tier == "microbial":
            life_desc = "Microbial life has taken hold here"
        elif hab_tier == "simple_multicellular":
            life_desc = "Simple multicellular life thrives here — colonial organisms, primitive algae, and filter-feeders"
        elif hab_tier == "complex_multicellular":
            life_desc = "Complex multicellular life has emerged here, with differentiated organisms, nervous systems, and ecological hierarchies"
        else:
            life_desc = "Advanced life has emerged here, with the potential for tool use, social structures, or sapience"

        if biochem == "Chemolithotrophic":
            sentences.append(f"{life_desc}, driven not by sunlight but by chemical energy from volcanic and hydrothermal activity.")
        elif biochem == "Ammonia/Carbon":
            sentences.append(f"{life_desc}, based on ammonia as a solvent rather than water.")
        elif biochem == "Methane/Carbon":
            sentences.append(f"{life_desc}, using liquid methane as a solvent in the extreme cold.")
        elif biochem == "Thermophilic":
            sentences.append(f"{life_desc}, thriving in superheated water kept liquid by immense pressure.")
        else:
            sentences.append(f"{life_desc}, using water as a solvent in the familiar carbon-based tradition.")

        if not gold and btype == "rocky":
            sentences.append("Its presence outside the classical habitable zone is a reminder that life finds a way beyond the expected boundaries.")

    elif hab_tier == "prebiotic":
        sentences.append("Complex organic chemistry is underway here, though self-replicating life has not yet emerged.")
    else:
        sentences.append("Conditions here are too hostile to support any form of life as we understand it.")

    # Rings
    if rings.get("present"):
        roche_f = rings.get("roche_failures", 0)
        tidal_d = rings.get("tidal_disruptions", 0)
        if tidal_d and roche_f:
            sentences.append(f"A ring system encircles it, formed from bodies torn apart by tidal forces and candidates vaporised by extreme heating.")
        elif tidal_d:
            sentences.append(f"A ring system encircles it, formed from {tidal_d} moon candidate(s) destroyed by extreme tidal heating.")
        else:
            sentences.append(f"A ring system encircles it, formed from {roche_f} moon candidate(s) torn apart within the Roche limit.")

    # Moons summary
    if moons:
        hab_moons = [m for m in moons if m["habitability"]["Biosphere_Tier"]["value"] in LIFE_TIERS]
        if hab_moons:
            sentences.append(f"It is orbited by {len(moons)} moon(s), {len(hab_moons)} of which harbour life.")
        else:
            sentences.append(f"It is orbited by {len(moons)} moon(s).")

    return wrap(" ".join(sentences))

def moon_narrative(moon, parent_name):
    name      = moon["name"]
    mtype     = moon["type"]
    mass      = moon["mass"]["value"]
    sma_km    = moon["orbit"]["SMA_parent_km"]["value"]
    ecc       = moon["orbit"]["eccentricity"]["value"]
    tidal     = moon["tidal"]["tidal_flux"]["value"]
    temp      = moon["atmosphere"]["Surface_Temperature"]["value"]
    has_atmo  = moon["atmosphere"]["Has_Atmosphere"]
    press     = moon["atmosphere"]["Surface_Pressure"]["value"]
    hab_tier  = moon["habitability"]["Biosphere_Tier"]["value"]
    biochem   = moon["habitability"]["Biochemistry_Type"]["value"]
    pipeline  = moon.get("pipeline", "simplified")
    sub_ocean = moon["tectonics"].get("Subsurface_Ocean", {}).get("value", False)
    LIFE_TIERS = {"microbial", "simple_multicellular", "complex_multicellular", "advanced"}

    sentences = []

    # Opening
    if pipeline == "full_planetary":
        sentences.append(f"{name} is a substantial moon — large enough to behave like a planet in its own right, orbiting {parent_name} at {round(sma_km):,} km.")
    else:
        if mass < 0.01:
            sentences.append(f"{name} is a small moonlet orbiting {parent_name} at {round(sma_km):,} km.")
        else:
            sentences.append(f"{name} orbits {parent_name} at {round(sma_km):,} km.")

    # Tidal heating
    if tidal > 1e4:
        sentences.append(f"Extreme tidal heating ({round(tidal):,} W/m²) makes it one of the most volcanically intense bodies in the system.")
    elif tidal > 100:
        sentences.append(f"Significant tidal heating ({round(tidal, 1)} W/m²) drives substantial internal heat.")
    elif tidal > 1:
        sentences.append(f"Moderate tidal heating ({round(tidal, 2)} W/m²) supplements the energy it receives from its distant star.")
    elif tidal > 0.01:
        sentences.append(f"Weak tidal heating ({round(tidal, 4)} W/m²) provides a small but measurable internal heat source.")

    # Atmosphere and temperature
    if not has_atmo:
        sentences.append("It has no atmosphere, leaving its surface bare and exposed.")
    else:
        if isinstance(temp, (int, float)):
            if temp < -150:
                sentences.append(f"Despite the absence of meaningful warmth, it holds a thin atmosphere at a frigid {temp}°C.")
            elif temp < 0:
                sentences.append(f"Its atmosphere keeps surface temperatures at {temp}°C — cold, but not impossible for chemistry.")
            elif temp < 50:
                sentences.append(f"A temperate surface temperature of {temp}°C and a present atmosphere make conditions here intriguing.")
            else:
                sentences.append(f"Surface temperatures reach {temp}°C under its atmosphere.")

    # Subsurface ocean
    if sub_ocean:
        sentences.append("Tidal heating is thought to maintain a liquid water ocean beneath its frozen surface.")

    # Life
    if hab_tier in LIFE_TIERS:
        if biochem == "Chemolithotrophic":
            sentences.append("Chemolithotrophic life has emerged here, sustained by chemical energy from tidal heating rather than sunlight.")
        else:
            sentences.append(f"{hab_tier.replace('_', ' ').title()} life has taken hold, using {biochem.lower()} biochemistry.")
    elif sub_ocean:
        sentences.append("While the surface is lifeless, the subsurface ocean remains a candidate for hidden life.")

    return wrap(" ".join(sentences))

# ── Stats blocks ──────────────────────────────────────────────────────────────

def star_stats(data):
    star  = data
    zones = star["zones"]
    lines = []
    lines.append(field("Spectral Class",    star["class"]))
    lines.append(field("Color",             star["color"]))
    lines.append(field("Mass",              star["Star_Mo"], "Mo"))
    lines.append(field("Radius",            star["Star_Ro"], "Ro"))
    lines.append(field("Luminosity",        star["Star_Lo"], "Lo"))
    lines.append(field("Temperature",       f"{star['Star_T']:.0f}", "K"))
    lines.append(field("Metallicity",       star["Star_Metallicity"], "FeH"))
    lines.append(field("Abs. Magnitude",    f"{star['Star_Mbol']} / {star['Star_Mv']}", "Mbol / Mv"))
    lines.append(field("Sphere of Infl.",   star["Star_SOI"], "AU"))
    pos = star["Star_Position"]
    lines.append(field("Galaxy Position",   f"X:{pos['x']}  Y:{pos['y']}  Z:{pos['z']}"))
    lines.append("")
    lines.append(field("Goldilocks Zone",   f"{zones['Star_GoldilocksZone'][0]} – {zones['Star_GoldilocksZone'][1]}", "AU"))
    lines.append(field("Ice Line",          zones["Star_IceLine"], "AU"))
    lines.append(field("Rocky Zone",        f"{zones['Star_RockyZone'][0]} – {zones['Star_RockyZone'][1]}", "AU"))
    lines.append(field("Giant Zone",        f"{zones['Star_GiantZone'][0]} – {zones['Star_GiantZone'][1]}", "AU"))
    lines.append(field("Inner Belt",        f"{zones['Star_InnerBelt'][0]} – {zones['Star_InnerBelt'][1]}", "AU"))
    lines.append(field("Outer Belt",        f"{zones['Star_OuterBelt'][0]} – {zones['Star_OuterBelt'][1]}", "AU"))
    return lines

def body_stats(body):
    d       = body["data"]
    atmo    = body["atmosphere"]
    core    = body["core"]
    orb     = body["orbit"]
    tect    = body["tectonics"]
    hab     = body["habitability"]
    subscores = hab.get("Subscores") or {}
    biochem_d = hab.get("Biochemistry_Details") or {}
    lines = []

    # Physical
    lines.append("  ── Physical ──────────────────────────────────")
    lines.append(field("Type / Subclass",   f"{d['type']} / {d.get('subclass') or 'N/A'}"))
    lines.append(field("Mass",              d["mass"]["value"], "Me"))
    lines.append(field("Radius",            d["radius"]["value"], "Re"))
    lines.append(field("Surface Gravity",   d["surface_gravity"]["value"], "m/s²"))
    lines.append(field("Density",           f"{d['density']['value']:.3e}", "kg/km³"))
    lines.append(field("Volume",            f"{d['volume']['value']:.3e}", "km³"))

    # Orbit
    lines.append("  ── Orbit ─────────────────────────────────────")
    lines.append(field("Semi-Major Axis",   orb["Semi-Major-Axis"]["value"], "AU"))
    lines.append(field("Orbital Period",    orb["Orbital_Period"]["value"], "days"))
    lines.append(field("Orbital Speed",     orb["Orbital_Speed"]["value"], "km/s"))
    lines.append(field("Rotational Period", orb["Rotational_Period"]["value"], "hours"))
    lines.append(field("Hill Radius",       f"{orb['Hill_Radius']['value']} AU / {orb.get('Hill_Radius_km', {}).get('value', 'N/A')} km"))
    roche = orb.get("Roche_Limit", {})
    roche_val = f"{roche.get('value_AU', 'N/A')} AU / {roche.get('value_km', 'N/A')} km"
    lines.append(field("Roche Limit",       roche_val))
    lines.append(field("In Goldilocks",     orb["In_Goldilocks"]["value"]))
    lines.append(field("Orbital Zone",      orb["Orbital_Zone"]["value"]))

    # Core
    lines.append("  ── Core ──────────────────────────────────────")
    lines.append(field("Core Mass Fraction", core["CMF"]["value"]))
    lines.append(field("Core Mass",          core["Mass"]["value"], "Me"))
    lines.append(field("Core Radius",        core["Radius"]["value"], "Re"))
    lines.append(field("Core Density",       core["Density"]["value"], "kg/m³"))
    comp = core["Composition"]
    lines.append(field("Composition",        f"Fe {comp['Fe']['value']}  Ni {comp['Ni']['value']}  Light {comp['Light Elements']['value']}"))
    lines.append(field("Liquid Core Frac.",  core.get("Liquid_Core_Fraction", {}).get("value", "N/A")))
    lines.append(field("Dynamo Factor",      core["Dynamo_Factor"]["value"]))

    # Atmosphere
    lines.append("  ── Atmosphere ────────────────────────────────")
    lines.append(field("Has Atmosphere",     atmo["Has_Atmosphere"]))
    lines.append(field("Class",              atmo["Atmosphere_Class"]["value"]))
    lines.append(field("Type",               atmo["Atmosphere_Type"]["value"]))
    lines.append(field("Surface Pressure",   atmo["Surface_Pressure"]["value"], "atm"))
    lines.append(field("Surface Temp",       atmo["Surface_Temperature"]["value"], "°C"))
    lines.append(field("Bare Temp",          atmo["Bare_Temperature"]["value"], "°C"))
    lines.append(field("Albedo",             atmo["Albedo"]["value"]))
    lines.append(field("Greenhouse Multi.",  atmo["Greenhouse_Multiplier"]["value"]))
    lines.append(field("Mean Mol. Weight",   atmo["Mean_Molecular_Weight"]["value"], "u"))
    lines.append(field("Scale Height",       atmo["Scale_Height"]["value"], "km"))
    lines.append(field("Irradiance",         atmo["Irradiance"]["value"], "W/m²"))
    lines.append(field("Atmo Mass Fraction", atmo["Atmosphere_Mass_Fraction"]["value"]))
    lines.append(field("Atmo Mass",          atmo["Atmosphere_Mass"]["value"], "kg"))
    if atmo.get("Composition"):
        lines.append("  Composition:")
        for gas, val in atmo["Composition"].items():
            lines.append(f"    {gas:<8} {val['value']:.4f}")

    # Tectonics
    if d["type"] != "giant":
        lines.append("  ── Tectonics ─────────────────────────────────")
        lines.append(field("Activity",           tect.get("Tectonic_Activity", {}).get("value", "N/A")))
        lines.append(field("Plate Count",        tect.get("Plate_Count", {}).get("value", "N/A")))
        lines.append(field("Max Elevation",      tect.get("Max_Elevation", {}).get("value", "N/A"), "km"))
        lines.append(field("Max Depth",          tect.get("Max_Depth", {}).get("value", "N/A"), "km"))
        lines.append(field("Ocean Coverage",     tect.get("Ocean_Coverage", {}).get("value", "N/A")))
        lines.append(field("Volcanic Activity",  tect.get("Volcanic_Activity", {}).get("value", "N/A")))
        lines.append(field("Erosion Rate",       tect.get("Erosion_Rate", {}).get("value", "N/A")))
        if tect.get("Boundaries"):
            boundary_types = {}
            for bnd in tect["Boundaries"]:
                bt = bnd["type"]
                boundary_types[bt] = boundary_types.get(bt, 0) + 1
            bnd_str = "  ".join([f"{bt.title()}: {cnt}" for bt, cnt in boundary_types.items()])
            lines.append(field("Boundaries",     bnd_str))

    # Habitability
    lines.append("  ── Habitability ──────────────────────────────")
    lines.append(field("Biosphere Tier",     hab["Biosphere_Tier"]["value"].replace("_", " ").title()))
    lines.append(field("Biosphere Score",    hab.get("Biosphere_Score", {}).get("value", "N/A")))
    lines.append(field("Habitability Index", hab["Habitability_Index"]["value"]))
    lines.append(field("Biochemistry",       hab["Biochemistry_Type"]["value"]))
    if subscores:
        lines.append("  Subscores:")
        for k, v in subscores.items():
            if k == "energy":
                lines.append(f"    {'Energy':<20} {v['value']:.4f}  (stellar {v['stellar_score']:.4f}  tidal {v['tidal_score']:.4f}  dominant: {v['dominant_source']})")
            else:
                lines.append(f"    {k.replace('_',' ').title():<20} {v['value']:.4f}  (weight {v['weight']})")
    if biochem_d:
        lines.append("  Biochemistry Detail:")
        for k, v in biochem_d.items():
            if k not in ("label", "is_chemolithotrophic"):
                lines.append(f"    {k.replace('_',' ').title():<20} {v}")
    bio_pot = hab.get("Biosphere_Potential")
    if bio_pot and bio_pot.get("max_phyla", 0) > 0:
        lines.append(field("Max Phyla",          bio_pot["max_phyla"]))
        lines.append(field("Max Trophic Levels", bio_pot["max_trophic_levels"]))
        niches = bio_pot.get("example_niches", [])
        if niches:
            lines.append(field("Example Niches",     ", ".join(niches)))

    return lines

def moon_stats(moon):
    orb   = moon["orbit"]
    tidal = moon["tidal"]
    atmo  = moon["atmosphere"]
    tect  = moon["tectonics"]
    hab   = moon["habitability"]
    subscores = hab.get("Subscores") or {}
    lines = []

    lines.append("    ── Physical ────────────────────────────────")
    lines.append(field("Type / Pipeline",    f"{moon['type']} / {moon.get('pipeline','simplified')}", width=30))
    lines.append(field("Subclass",           moon.get("subclass") or "N/A", width=30))
    lines.append(field("Mass",               moon["mass"]["value"], "Me", width=30))
    lines.append(field("Radius",             moon["radius"]["value"], "Re", width=30))
    lines.append(field("Surface Gravity",    moon["surface_gravity"]["value"], "m/s²", width=30))
    lines.append(field("Density",            moon["density"]["value"], "kg/km³", width=30))
    lines.append(field("Dynamo Factor",      moon.get("dynamo_factor", {}).get("value", "N/A"), width=30))

    lines.append("    ── Orbit (around parent) ───────────────────")
    lines.append(field("SMA",                f"{orb['SMA_parent']['value']} AU / {orb['SMA_parent_km']['value']} km", width=30))
    lines.append(field("Eccentricity",       orb["eccentricity"]["value"], width=30))
    lines.append(field("Orbital Period",     orb["orbital_period"]["value"], "hours", width=30))
    lines.append(field("Orbital Speed",      orb["orbital_speed"]["value"], "km/s", width=30))

    lines.append("    ── Tidal ────────────────────────────────────")
    lines.append(field("Tidal Power",        f"{tidal['tidal_power']['value']:.4e}", "W", width=30))
    lines.append(field("Tidal Flux",         tidal["tidal_flux"]["value"], "W/m²", width=30))
    lines.append(field("Tidal Factor",       tidal["tidal_factor"]["value"], width=30))
    lines.append(field("k2",                 tidal["k2"]["value"], width=30))
    lines.append(field("Q",                  tidal["Q"]["value"], width=30))

    lines.append("    ── Atmosphere ──────────────────────────────")
    lines.append(field("Has Atmosphere",     atmo["Has_Atmosphere"], width=30))
    lines.append(field("Class",              atmo["Atmosphere_Class"]["value"], width=30))
    lines.append(field("Surface Pressure",   atmo["Surface_Pressure"]["value"], "atm", width=30))
    lines.append(field("Surface Temp",       atmo["Surface_Temperature"]["value"], "°C", width=30))
    lines.append(field("Irradiance",         atmo["Irradiance"]["value"], "W/m²", width=30))
    if atmo.get("Composition"):
        lines.append("    Composition:")
        for gas, val in atmo["Composition"].items():
            lines.append(f"      {gas:<8} {val['value']:.4f}")

    lines.append("    ── Tectonics ────────────────────────────────")
    lines.append(field("Activity",           tect.get("Tectonic_Activity", {}).get("value", "N/A"), width=30))
    lines.append(field("Volcanic",           tect.get("Volcanic_Activity", {}).get("value", "N/A"), width=30))
    lines.append(field("Subsurface Ocean",   tect.get("Subsurface_Ocean", {}).get("value", False), width=30))
    lines.append(field("Tidal Factor",       tect.get("Tidal_Factor", {}).get("value", "N/A"), width=30))

    lines.append("    ── Habitability ─────────────────────────────")
    lines.append(field("Biosphere Tier",     hab["Biosphere_Tier"]["value"].replace("_"," ").title(), width=30))
    lines.append(field("Biosphere Score",    hab.get("Biosphere_Score", {}).get("value", "N/A"), width=30))
    lines.append(field("Biochemistry",       hab["Biochemistry_Type"]["value"], width=30))
    if subscores:
        lines.append("    Subscores:")
        for k, v in subscores.items():
            if k == "energy":
                lines.append(f"      {'Energy':<18} {v['value']:.4f}  (stellar {v['stellar_score']:.4f}  tidal {v['tidal_score']:.4f})")
            else:
                lines.append(f"      {k.replace('_',' ').title():<18} {v['value']:.4f}")
    return lines

# ── Belt summary ──────────────────────────────────────────────────────────────

def belt_summary(belt_bodies, belt_name):
    if not belt_bodies:
        return [f"  No {belt_name} bodies."]
    lines = []
    for b in belt_bodies:
        temp = b["atmosphere"]["Surface_Temperature"]["value"]
        atmo = b["atmosphere"]["Atmosphere_Type"]["value"]
        lines.append(f"  {b['name']:<28} mass={b['data']['mass']['value']:.4f} Me  "
                     f"SMA={b['data']['SMA']['value']} AU  "
                     f"temp={temp}°C  atmo={atmo}")
    return lines

# ── Habitable summary ─────────────────────────────────────────────────────────

def habitable_summary(data):
    LIFE_TIERS = {"microbial", "simple_multicellular", "complex_multicellular", "advanced"}
    entries = []
    for body in data["bodies"]:
        score  = body["habitability"].get("Biosphere_Score", {}).get("value", 0)
        tier   = body["habitability"]["Biosphere_Tier"]["value"]
        biochem = body["habitability"]["Biochemistry_Type"]["value"]
        if score and score > 0 and tier in LIFE_TIERS:
            entries.append((body["name"], "planet", tier, score, biochem))
        for moon in body.get("moons", []):
            m_score  = moon["habitability"].get("Biosphere_Score", {}).get("value", 0)
            m_tier   = moon["habitability"]["Biosphere_Tier"]["value"]
            m_biochem = moon["habitability"]["Biochemistry_Type"]["value"]
            if m_score and m_score > 0 and m_tier in LIFE_TIERS:
                entries.append((moon["name"], "moon", m_tier, m_score, m_biochem))
    return sorted(entries, key=lambda x: x[3], reverse=True)

# ── Main report builder ───────────────────────────────────────────────────────

def build_report(data):
    lines = []
    star_name = data["name"]

    # ── Header ────────────────────────────────────────────────────────────
    lines.append(divider("═"))
    lines.append(f"  ASTRA SYSTEM REPORT")
    lines.append(f"  {star_name}  |  Generated by ASTRA v0.3.0")
    lines.append(f"  System Key: {data.get('key', 'Unknown')}")
    lines.append(divider("═"))
    lines.append("")

    # ── Star ──────────────────────────────────────────────────────────────
    lines.append(section("STAR"))
    lines.append("")
    lines.append(star_narrative(data))
    lines.append("")
    lines.extend(star_stats(data))
    lines.append("")

    # ── Habitable summary ──────────────────────────────────────────────────
    hab_entries = habitable_summary(data)
    lines.append(section("HABITABLE BODIES SUMMARY"))
    lines.append("")
    if hab_entries:
        lines.append(f"  {len(hab_entries)} life-bearing body/bodies in this system:")
        lines.append("")
        for name, btype, tier, score, biochem in hab_entries:
            lines.append(f"  {name:<30} [{btype:<6}]  {tier.replace('_',' ').title():<24}  score={score:.4f}  ({biochem})")
    else:
        lines.append("  No life-bearing bodies detected in this system.")
    lines.append("")

    # ── Bodies ────────────────────────────────────────────────────────────
    for i, body in enumerate(data["bodies"]):
        bname = body["name"]
        btype = body["data"]["type"]
        subclass = body["data"].get("subclass") or ""
        label = f"BODY {i+1} — {bname}  |  {btype.upper()}"
        if subclass:
            label += f" ({subclass})"
        lines.append(section(label))
        lines.append("")
        lines.append(body_narrative(body, data))
        lines.append("")
        lines.extend(body_stats(body))
        lines.append("")

        # Rings
        rings = body.get("rings", {})
        if rings.get("present"):
            lines.append("  ── Rings ─────────────────────────────────────")
            lines.append(field("Roche Failures",    rings.get("roche_failures", 0)))
            lines.append(field("Tidal Disruptions", rings.get("tidal_disruptions", 0)))
            lines.append("")

        # Moons
        moons = body.get("moons", [])
        if moons:
            lines.append(f"  ── Moons ({len(moons)}) ──────────────────────────────────")
            for moon in moons:
                lines.append("")
                lines.append(f"  {moon['name']}")
                lines.append(moon_narrative(moon, bname))
                lines.append("")
                lines.extend(moon_stats(moon))
                lines.append("")

    # ── Belts ──────────────────────────────────────────────────────────────
    if data["inner_belt"]:
        lines.append(section("INNER BELT"))
        lines.append("")
        lines.extend(belt_summary(data["inner_belt"], "inner belt"))
        lines.append("")

    if data["outer_belt"]:
        lines.append(section("OUTER BELT"))
        lines.append("")
        lines.extend(belt_summary(data["outer_belt"], "outer belt"))
        lines.append("")

    # ── Footer ─────────────────────────────────────────────────────────────
    lines.append(divider("═"))
    lines.append(f"  End of report — {star_name}")
    lines.append(divider("═"))

    return "\n".join(lines)

# ── Entry point ───────────────────────────────────────────────────────────────

def report_file(json_path, output_folder=OUTPUT_FOLDER):
    with open(json_path, "r") as f:
        raw = f.read()
    data = json.loads(raw)
    if "stdout" in data:
        data = json.loads(data["stdout"])

    report = build_report(data)

    os.makedirs(output_folder, exist_ok=True)
    out_name = data["name"] + "_report.txt"
    out_path = os.path.join(output_folder, out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report written: {out_path}")
    return out_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python report.py <path_to_system.json> [output_folder]")
        print("       python report.py 'Generated Systems/M3-933245.json'")
        sys.exit(1)

    json_path = sys.argv[1]
    out_folder = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_FOLDER

    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        sys.exit(1)

    report_file(json_path, out_folder)
