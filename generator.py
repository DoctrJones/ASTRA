import json, random, math
from AstraClass import AstraFunctions
from AstraClass.moons import GenerateMoons

def generate_star(key, Star_Data, Habitability_Data):
    """Generates all star properties for a given key. Returns a star data dict."""
    Star_Class = AstraFunctions.StellarClass(key)
    Star_Info = Star_Data[Star_Class][0]

    random.seed(key)
    Star_Mo = round(random.uniform(Star_Info['Mo_min'], Star_Info['Mo_max']), 4)
    Star_Ro = round(random.uniform(Star_Info['Ro_min'], Star_Info['Ro_max']), 4)
    Star_Lo = round(random.uniform(Star_Info['Lo_min'], Star_Info['Lo_max']), 4)
    Star_T  = round(random.uniform(Star_Info['temperature_min'], Star_Info['temperature_max']), 4)
    Star_R  = round(Star_Ro * 695700, 4)

    Star_SOI          = AstraFunctions.StellarSphereOfInfluence(Star_Mo)
    Star_Pos          = AstraFunctions.GalaxyPosition(key)
    Star_Spectral     = AstraFunctions.StellarSpectralType(Star_T, Star_Class)
    Star_Metallicity  = AstraFunctions.StellarMetallicity(Star_Class, key)
    Star_Mbol, Star_Mv = AstraFunctions.StellarAbsoluteMagnitude(Star_Lo)
    Star_GoldilocksZone = AstraFunctions.StellarGoldilocksBoundary(Star_R, Star_T, 1500, 650)
    Star_IceLine      = AstraFunctions.StellarIceLine(Star_Lo)
    Star_RockyZone    = AstraFunctions.StellarRockyZone(Star_Lo)
    Star_InnerBelt    = AstraFunctions.StellarInnerBelt(Star_Lo)
    Star_GiantZone    = AstraFunctions.StellarGiantZone(Star_Lo)
    Star_OuterBelt    = AstraFunctions.StellarOuterBelt(Star_Lo)

    Star_Name = Star_Class + str(Star_Spectral) + "-" + str(Star_Pos[0]) + str(Star_Pos[1]) + str(Star_Pos[2])

    return {
        "key":             key,
        "name":            Star_Name,
        "class":           Star_Class,
        "color":           Star_Info['color'],
        "body_mass_scale": Star_Info['body_mass_scale'],
        "Star_Mo":         Star_Mo,
        "Star_Ro":         Star_Ro,
        "Star_km":         Star_R,
        "Star_Lo":         Star_Lo,
        "Star_T":          Star_T,
        "Star_Metallicity": Star_Metallicity,
        "Star_Mbol":       Star_Mbol,
        "Star_Mv":         Star_Mv,
        "Star_SOI":        Star_SOI,
        "Star_Position":   {"x": Star_Pos[0], "y": Star_Pos[1], "z": Star_Pos[2]},
        "zones": {
            "Star_GoldilocksZone": Star_GoldilocksZone,
            "Star_IceLine":        Star_IceLine,
            "Star_RockyZone":      Star_RockyZone,
            "Star_InnerBelt":      Star_InnerBelt,
            "Star_GiantZone":      Star_GiantZone,
            "Star_OuterBelt":      Star_OuterBelt,
        },
        "lambda": {
            "raw":       AstraFunctions.BodyCountLambda(Star_Class, Star_Metallicity),
            "corrected": AstraFunctions.PoissonSample(key, AstraFunctions.BodyCountLambda(Star_Class, Star_Metallicity)),
        }
    }

def assign_giant_subclass(key, index, Body_Mass, Body_SMA, Star_IceLine, Planet_Data):
    """Determines whether a giant body is a gas_giant or ice_giant.

    Classification is mass-primary with a zone/temperature probabilistic bias:
    - Bodies >= 95 Me are always gas_giant (above Saturn mass, unambiguous).
    - Bodies < 10 Me fall through to rocky (should not reach this function).
    - 10-95 Me range: ice_giant by default, with a sigmoid probability of being
      gas_giant that rises with mass and proximity to the ice line.

    Returns (subclass_string, subclass_data_dict).
    """
    random.seed(key + str(index) + "subclass")

    gas_data  = next(e for e in Planet_Data["giant"] if e["class"] == "gas_giant")
    ice_data  = next(e for e in Planet_Data["giant"] if e["class"] == "ice_giant")

    # Hard upper boundary: above Saturn mass, unambiguously gas giant
    if Body_Mass >= 95.0:
        return "gas_giant", gas_data

    # Probabilistic zone in the 10-95 Me overlap range.
    # Sigmoid centred at 60 Me — above 60 Me leans gas giant, below leans ice giant.
    # Zone modifier: bodies closer to the ice line are warmer and more gas-giant-like.
    mass_z = (Body_Mass - 60.0) / 15.0
    mass_p = 1.0 / (1.0 + math.exp(-mass_z))

    # Zone bias: within 1.5x ice line = warmer = nudge toward gas giant
    zone_bias = max(0.0, min(0.2, 0.2 * (1.5 - Body_SMA / max(Star_IceLine, 0.01))))
    p_gas = max(0.0, min(0.95, mass_p + zone_bias))

    if random.random() < p_gas:
        return "gas_giant", gas_data
    else:
        return "ice_giant", ice_data

def assign_rocky_subclass(Body_Mass, Planet_Data):
    """Determines whether a rocky body is terrestrial or super_earth.

    Classification is purely mass-based:
    - >= 2 Me → super_earth
    - < 2 Me  → terrestrial (includes sub-Earth low end, < 0.1 Me)

    No RNG needed — the mass itself is the discriminator.
    Returns (subclass_string, subclass_data_dict).
    """
    terrestrial_data = next(e for e in Planet_Data["rocky"] if e["class"] == "terrestrial")
    super_earth_data = next(e for e in Planet_Data["rocky"] if e["class"] == "super_earth")

    if Body_Mass >= super_earth_data["M_E_min"]:
        return "super_earth", super_earth_data
    else:
        return "terrestrial", terrestrial_data

def generate_body(key, index, Body_Type, Body_SMA, star, Habitability_Data, Planet_Data, Rocky_Count=1, Giant_Count=1):
    """Generates all properties for a single orbital body. Returns a body data dict.
    Rocky_Count and Giant_Count are the actual placed body counts post-Gladman reduction,
    used by BodyMassGeneration to correctly apply the competitive disk mass factor (f_Comp).
    """

    # Assign subclass before any downstream calls.
    # Giants: provisional mass draw first (same seed = same result), then classify.
    # Rocky: classify after mass generation — no bounds clamping needed.
    Body_Subclass = None
    Subclass_Data = None
    if Body_Type == "giant":
        Body_Subclass, Subclass_Data = assign_giant_subclass(
            key, index,
            AstraFunctions.BodyMassGeneration(key, star["body_mass_scale"], star["Star_Mo"], star["Star_Metallicity"], Body_Type, Giant_Count, index),
            Body_SMA,
            star["zones"]["Star_IceLine"],
            Planet_Data
        )

    # Pass the correct placed body count so f_Comp applies disk mass competition properly
    Body_Count = Rocky_Count if Body_Type == "rocky" else Giant_Count
    Body_Mass = AstraFunctions.BodyMassGeneration(key, star["body_mass_scale"], star["Star_Mo"], star["Star_Metallicity"], Body_Type, Body_Count, index, Body_Subclass, Subclass_Data)

    if Body_Type == "rocky":
        Body_Subclass, Subclass_Data = assign_rocky_subclass(Body_Mass, Planet_Data)
    Body_Radius        = AstraFunctions.BodyRadiusGeneration(key, Body_Mass, Body_Type, index, Body_Subclass)
    Body_Volume        = AstraFunctions.BodyVolumeCalculation(Body_Radius)
    Body_Density       = AstraFunctions.BodyDensityCalculation(Body_Mass, Body_Volume)
    Body_CoreMass, Body_CoreData = AstraFunctions.BodyCoreCaluclation(key, star["Star_Metallicity"], Body_Type, Body_Mass, index, Body_Subclass, Subclass_Data)
    Body_OrbitalData   = AstraFunctions.BodyOrbitalMechanicsCaluclation(star["Star_Mo"], Body_SMA, Body_Mass, Body_Radius, star["zones"])
    Body_SurfaceGravity = AstraFunctions.BodySurfaceGravity(Body_Mass, Body_Radius)
    Body_AtmosphericData = AstraFunctions.BodyAtmospherics(key, Body_CoreData["Dynamo_Factor"]["value"], Body_SurfaceGravity, Body_Radius, star["Star_km"], star["Star_T"], Body_SMA, star["Star_Lo"], Body_Type, Body_Mass, index, Body_Subclass, Subclass_Data)
    Body_Name          = star["name"] + "-" + str(index + 1)

    Surface_Pressure = Body_AtmosphericData["Surface_Pressure"]["value"]
    Surface_Pressure_Numeric = Surface_Pressure if isinstance(Surface_Pressure, (int, float)) else 0

    Body_TectonicData = AstraFunctions.BodyTectonics(
        key, Body_Type, Body_Mass, Body_Radius, Body_SurfaceGravity,
        Body_CoreData["Dynamo_Factor"]["value"],
        Body_OrbitalData["Rotational_Period"]["value"],
        Body_AtmosphericData["Surface_Temperature"]["value"],
        Surface_Pressure_Numeric,
        Body_AtmosphericData["Has_Atmosphere"],
        Body_AtmosphericData["Composition"],
        Body_SMA, Body_Name, index
    )
    # Super-Earth volcanic boost: nudge volcanic activity up one tier
    if Body_Subclass == "super_earth" and Subclass_Data is not None and Subclass_Data.get("volcanic_boost"):
        upgrade = {"None": "Low", "Low": "Moderate", "Moderate": "High", "High": "High"}
        current = Body_TectonicData.get("Volcanic_Activity", {}).get("value", "None")
        if current in upgrade:
            Body_TectonicData["Volcanic_Activity"]["value"] = upgrade[current]
    Body_HabitabilityData = AstraFunctions.BodyHabitability(
        Habitability_Data, Body_Type, Body_Mass, Body_SurfaceGravity,
        Body_CoreData["Dynamo_Factor"]["value"],
        Body_AtmosphericData["Has_Atmosphere"],
        Body_AtmosphericData["Surface_Temperature"]["value"],
        Surface_Pressure_Numeric,
        Body_AtmosphericData["Composition"],
        Body_TectonicData["Ocean_Coverage"]["value"] if "Ocean_Coverage" in Body_TectonicData else 0,
        Body_AtmosphericData["Irradiance"]["value"]
    )

    # Moon generation — runs for giants and rocky bodies
    Body_Hill_Radius_AU = Body_OrbitalData["Hill_Radius"]["value"]
    Body_Density_kgkm3  = Body_Density
    Body_Moons, Body_Rings, Body_Roche_m = GenerateMoons(
        key, index, Body_Type, Body_Subclass, Subclass_Data,
        Body_Mass, Body_Radius, Body_Density_kgkm3,
        Body_SMA, Body_Hill_Radius_AU, Body_Name,
        star["Star_Lo"], star["Star_km"], star["Star_T"],
        star["Star_Metallicity"], star["zones"],
        Habitability_Data, Planet_Data
    )
    # Inject Roche limit and Hill radius into orbit dict for output
    Body_Roche_AU = round(Body_Roche_m / 1.496e11, 6) if Body_Roche_m > 0 else None
    Body_Roche_km = round(Body_Roche_m / 1000, 1)     if Body_Roche_m > 0 else None
    Body_OrbitalData["Roche_Limit"] = {
        "value_AU": Body_Roche_AU,
        "value_km": Body_Roche_km,
        "note": "Rigid-body approximation using rocky moon density reference (3500 kg/m³)"
    }
    Body_OrbitalData["Hill_Radius_km"] = {
        "value": round(Body_Hill_Radius_AU * 1.496e8, 1),
        "unit": "km"
    }

    return {
        "name":      Body_Name,
        "type":      Body_Type,
        "subclass":  Body_Subclass,
        "mass":      Body_Mass,
        "radius":    Body_Radius,
        "volume":    Body_Volume,
        "density":   Body_Density,
        "SMA":       Body_SMA,
        "surface_gravity": Body_SurfaceGravity,
        "core":        Body_CoreData,
        "orbit":       Body_OrbitalData,
        "atmosphere":  Body_AtmosphericData,
        "tectonics":   Body_TectonicData,
        "habitability":Body_HabitabilityData,
        "moons":       Body_Moons,
        "rings":       Body_Rings,
    }

def generate_dwarf(key, index, dwarf_type, dwarf_SMA, star, Habitability_Data, belt_tag):
    """Generates a single dwarf body. Simplified pipeline — no full tectonics."""
    Body_Mass          = AstraFunctions.BodyMassGeneration(key, star["body_mass_scale"], star["Star_Mo"], star["Star_Metallicity"], dwarf_type, 1, index)
    Body_Radius        = AstraFunctions.BodyRadiusGeneration(key, Body_Mass, dwarf_type, index)
    Body_Volume        = AstraFunctions.BodyVolumeCalculation(Body_Radius)
    Body_Density       = AstraFunctions.BodyDensityCalculation(Body_Mass, Body_Volume)
    Body_CoreMass, Body_CoreData = AstraFunctions.BodyCoreCaluclation(key, star["Star_Metallicity"], dwarf_type, Body_Mass, index)
    Body_OrbitalData   = AstraFunctions.BodyOrbitalMechanicsCaluclation(star["Star_Mo"], dwarf_SMA, Body_Mass, Body_Radius, star["zones"])
    Body_SurfaceGravity = AstraFunctions.BodySurfaceGravity(Body_Mass, Body_Radius)
    Body_AtmosphericData = AstraFunctions.BodyAtmospherics(key, Body_CoreData["Dynamo_Factor"]["value"], Body_SurfaceGravity, Body_Radius, star["Star_km"], star["Star_T"], dwarf_SMA, star["Star_Lo"], dwarf_type, Body_Mass, index)
    Body_Name          = star["name"] + "-" + belt_tag[0].upper() + "B-" + str(index + 1)

    Surface_Pressure = Body_AtmosphericData["Surface_Pressure"]["value"]
    Surface_Pressure_Numeric = Surface_Pressure if isinstance(Surface_Pressure, (int, float)) else 0

    Body_HabitabilityData = AstraFunctions.BodyHabitability(
        Habitability_Data, dwarf_type, Body_Mass, Body_SurfaceGravity,
        Body_CoreData["Dynamo_Factor"]["value"],
        Body_AtmosphericData["Has_Atmosphere"],
        Body_AtmosphericData["Surface_Temperature"]["value"],
        Surface_Pressure_Numeric,
        Body_AtmosphericData["Composition"],
        0,  # no ocean coverage for dwarfs
        Body_AtmosphericData["Irradiance"]["value"]
    )

    return {
        "name":           Body_Name,
        "type":           dwarf_type,
        "subclass":       None,
        "belt":           belt_tag,
        "mass":           Body_Mass,
        "radius":         Body_Radius,
        "volume":         Body_Volume,
        "density":        Body_Density,
        "SMA":            dwarf_SMA,
        "surface_gravity": Body_SurfaceGravity,
        "core":           Body_CoreData,
        "orbit":          Body_OrbitalData,
        "atmosphere":     Body_AtmosphericData,
        "tectonics":      {"Tectonic_Activity": {"value": "Dead"}, "Note": "Dwarf body — geologically inactive"},
        "habitability":   Body_HabitabilityData,
    }

def generate_belt(key, belt_tag, dwarf_type, star, Habitability_Data):
    """Generates all dwarf bodies for a single belt. Returns list of dwarf dicts."""
    belt_zone = star["zones"]["Star_InnerBelt"] if belt_tag == "inner" else star["zones"]["Star_OuterBelt"]
    has_giant = star.get("has_giant", False)

    count, smas = AstraFunctions.GenerateBeltPopulation(
        key, belt_tag, star["Star_Metallicity"], star["Star_Mo"], belt_zone, has_giant
    )

    dwarfs = []
    for i, sma in enumerate(smas):
        dwarf = generate_dwarf(key, i, dwarf_type, sma, star, Habitability_Data, belt_tag)
        dwarfs.append(dwarf)
    return dwarfs

def generate_system(key):
    """Master function: generates a complete star system for a given key.
    Returns a system dict containing star data, main bodies, and belt populations."""
    with open("Star_Data.json", "r") as f:
        Star_Data = json.load(f)
    with open("Habitability_Data.json", "r") as f:
        Habitability_Data = json.load(f)
    with open("Planet_Data.json", "r") as f:
        Planet_Data = json.load(f)

    star = generate_star(key, Star_Data, Habitability_Data)

    Star_LambdaCorrected = star["lambda"]["corrected"]
    Star_OrbitalZones, Body_RockyCount, Body_GiantCount = AstraFunctions.BodyZoneDistribution(
        key, star["class"], star["Star_Metallicity"], star["Star_Mo"], Star_LambdaCorrected
    )
    # Hill-radius-derived placement (Gladman 1993) — replaces fixed spacing.
    # Representative masses: 1.5 Me for rocky (conservative terrestrial),
    # 100 Me for giants (between ice_giant and gas_giant midpoints).
    Body_RockySMA = AstraFunctions.BodySMAPlacement(
        key, Body_RockyCount,
        star["zones"]["Star_RockyZone"][0], star["zones"]["Star_RockyZone"][1],
        star["Star_Mo"], rep_mass_Me=1.5, body_type_tag="rocky"
    )
    Body_GiantSMA = AstraFunctions.BodySMAPlacement(
        key, Body_GiantCount,
        star["zones"]["Star_GiantZone"][0], star["zones"]["Star_GiantZone"][1],
        star["Star_Mo"], rep_mass_Me=175.0, body_type_tag="giant", k=4.0
    )
    # Reconcile counts with what actually fit in the zones
    Body_RockyCount = len(Body_RockySMA)
    Body_GiantCount = len(Body_GiantSMA)
    # Rebuild zone list to match actual placed counts
    rocky_zones = ["rocky"] * Body_RockyCount
    giant_zones = ["giant"] * Body_GiantCount
    Star_OrbitalZones = rocky_zones + giant_zones

    # Pass giant presence into star dict for belt generation
    star["has_giant"] = Body_GiantCount > 0

    # Pass 1: main orbital bodies
    # Pass placed counts (post-Gladman) so disk mass competition is correctly applied
    bodies = []
    for i, Body_Type in enumerate(Star_OrbitalZones):
        Body_SMA = Body_RockySMA[i] if Body_Type == "rocky" else Body_GiantSMA[i - Body_RockyCount]
        body = generate_body(key, i, Body_Type, Body_SMA, star, Habitability_Data, Planet_Data,
                             Rocky_Count=Body_RockyCount, Giant_Count=Body_GiantCount)
        bodies.append(body)

    # Pass 2: belt populations
    inner_belt = generate_belt(key, "inner", "rocky_dwarf", star, Habitability_Data)
    outer_belt = generate_belt(key, "outer", "icy_dwarf",   star, Habitability_Data)

    return {
        "star":          star,
        "orbital_zones": Star_OrbitalZones,
        "rocky_count":   Body_RockyCount,
        "giant_count":   Body_GiantCount,
        "rocky_sma":     Body_RockySMA,
        "giant_sma":     Body_GiantSMA,
        "bodies":        bodies,
        "inner_belt":    inner_belt,
        "outer_belt":    outer_belt,
    }
