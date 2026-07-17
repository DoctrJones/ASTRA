import json

def print_system(system):
    """Prints a human-readable summary of a generated system to the console."""
    star = system["star"]
    divider     = "= " * 64
    divider_sm  = "= " * 25

    print("=Base Star Properties=")
    print(f"Star Class:              {star['class']}")
    print(f"Name:                    {star['name']}")
    print(f"Star Mass (Mo):          {star['Star_Mo']}")
    print(f"Star Radius (Ro):        {star['Star_Ro']}")
    print(f"Star Luminosity (Lo):    {star['Star_Lo']}")
    print(f"Star Temperature (K):    {star['Star_T']}")
    print(f"Star Color:              {star['color']}")
    print(f"Metallicity (FeH):       {star['Star_Metallicity']}")
    print(f"Mbol | Mv:               {star['Star_Mbol']} | {star['Star_Mv']}")
    print(f"SOI (AU):                {star['Star_SOI']}")
    print(divider_sm)
    pos = star["Star_Position"]
    print(f"Galaxy Position:         X:{pos['x']} Y:{pos['y']} Z:{pos['z']}")
    zones = star["zones"]
    print(f"Goldilocks Zone (AU):    {zones['Star_GoldilocksZone']}")
    print(f"Ice Line (AU):           {zones['Star_IceLine']}")
    print(f"Rocky Zone (AU):         {zones['Star_RockyZone']}")
    print(f"Inner Belt (AU):         {zones['Star_InnerBelt']}")
    print(f"Giant Zone (AU):         {zones['Star_GiantZone']}")
    print(f"Outer Belt (AU):         {zones['Star_OuterBelt']}")
    print(divider_sm)
    print(f"Body Count (Lambda):     {star['lambda']['raw']:.3f} → {star['lambda']['corrected']} bodies")
    print(f"Rocky: {system['rocky_count']}  Giant: {system['giant_count']}")
    print(f"Zones:                   {system['orbital_zones']}")
    print(f"Rocky SMA's:             {system['rocky_sma']}")
    print(f"Giant SMA's:             {system['giant_sma']}")

    # Habitability census — scan all bodies and their moons
    # Mirrors LIFE_TIERS in search.py: prebiotic and lifeless are not considered life-bearing
    LIFE_TIERS = {"microbial", "simple_multicellular", "complex_multicellular", "advanced"}
    hab_entries = []
    for body in system["bodies"]:
        bio_score = body["habitability"].get("Biosphere_Score", {}).get("value")
        tier      = body["habitability"].get("Biosphere_Tier", {}).get("value", "lifeless")
        biochem   = body["habitability"].get("Biochemistry_Type", {}).get("value", "None")
        if bio_score and bio_score > 0 and tier in LIFE_TIERS:
            hab_entries.append((body["name"], tier, bio_score, biochem, "planet"))
        for moon in body.get("moons", []):
            m_score   = moon["habitability"].get("Biosphere_Score", {}).get("value")
            m_tier    = moon["habitability"].get("Biosphere_Tier", {}).get("value", "lifeless")
            m_biochem = moon["habitability"].get("Biochemistry_Type", {}).get("value", "None")
            if m_score and m_score > 0 and m_tier in LIFE_TIERS:
                hab_entries.append((moon["name"], m_tier, m_score, m_biochem, "moon"))

    print(divider_sm)
    if hab_entries:
        print(f"Habitable Bodies:        {len(hab_entries)}")
        for name, tier, score, biochem, btype in sorted(hab_entries, key=lambda x: x[2], reverse=True):
            tag = f"[{btype}]"
            print(f"  {name:<28} {tag:<8} {tier:<22} score={score:.4f}  ({biochem})")
    else:
        print(f"Habitable Bodies:        0  — no life-bearing bodies in this system")

    for body in system["bodies"]:
        print(divider)
        subclass_str = f" ({body['subclass']})" if body.get("subclass") else ""
        print(f"{body['name']} | Type: {body['type']}{subclass_str}")
        print(f"  Mass (Me): {body['mass']}  Radius (Re): {body['radius']}  SMA (AU): {body['SMA']}")
        print(f"  Surface Gravity (m/s^2): {body['surface_gravity']}")
        print(f"  Volume (km^3): {body['volume']:.3e}  Density (kg/km^3): {body['density']:.3e}")
        print(f"  Core:        {body['core']}")
        print(f"  Orbit:       {body['orbit']}")
        print(f"  Atmosphere:  {body['atmosphere']}")
        print(f"  Tectonics:   {body['tectonics']}")
        print(f"  Habitability:{body['habitability']}")
        rings = body.get("rings", {})
        if rings.get("present"):
            roche_f  = rings.get('roche_failures', 0)
            tidal_d  = rings.get('tidal_disruptions', 0)
            parts = []
            if roche_f:  parts.append(f"{roche_f} Roche failure(s)")
            if tidal_d:  parts.append(f"{tidal_d} tidal disruption(s)")
            print(f"  Rings:       PRESENT  ({', '.join(parts)})")
        moons = body.get("moons", [])
        if moons:
            print(f"  Moons ({len(moons)}):")
            for moon in moons:
                tidal  = moon["tidal"]["tidal_flux"]["value"]
                temp   = moon["atmosphere"]["Surface_Temperature"]["value"]
                hab    = moon["habitability"]["Biosphere_Tier"]["value"]
                sub_oc = moon["tectonics"]["Subsurface_Ocean"]["value"]
                ecc    = moon["orbit"]["eccentricity"]["value"]
                sma_km = moon["orbit"]["SMA_parent_km"]["value"]
                print(f"    {moon['name']} | {moon['type']} | mass={moon['mass']['value']} Me | SMA={sma_km} km | ecc={ecc}")
                print(f"      Tidal flux={tidal} W/m²  Temp={temp}°C  Biosphere={hab}  Subsurface ocean={sub_oc}")

    for belt_tag, belt_bodies in [("Inner Belt", system["inner_belt"]), ("Outer Belt", system["outer_belt"])]:
        print(divider)
        print(f"{belt_tag}: {len(belt_bodies)} bodies")
        for dwarf in belt_bodies:
            print(f"  {dwarf['name']} | Type: {dwarf['type']} | Mass (Me): {dwarf['mass']} | Radius (Re): {dwarf['radius']} | SMA (AU): {dwarf['SMA']}")
            print(f"    Gravity: {dwarf['surface_gravity']} m/s²  |  Temp: {dwarf['atmosphere']['Surface_Temperature']['value']}°C  |  Atmo: {dwarf['atmosphere']['Atmosphere_Type']['value']}")

    print(divider)

def save_system(system, formatted):
    """Writes the formatted system dict to a JSON file in the Generated Systems folder."""
    import os
    output_dir = "Generated Systems"
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, system["star"]["name"] + ".json")
    with open(filename, "w") as f:
        json.dump(formatted, f, indent=4)
    print(f"Saved: {filename}")
