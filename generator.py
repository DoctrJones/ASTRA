import json, random, math
from AstraClass import AstraFunctions
from AstraClass.moons import GenerateMoons

def generate_star(key, Star_Data, Habitability_Data, Model_Data):
    """Generates all star properties for a given key. Returns a star data dict."""
    Star_Class = AstraFunctions.StellarClass(key)
    Star_Info = Star_Data[Star_Class][0]

    # Own seed stream — seeding with the bare key reused the StellarClass draw,
    # pinning each star's mass to the slice of its range that selected the class.
    random.seed(key + "starprops")
    # On the main sequence mass, radius and temperature rise together, so one
    # position within the class sets all three. A small per-property jitter keeps
    # same-position stars from being identical; reflecting at 0/1 instead of
    # clamping avoids pile-ups at the class bounds and keeps each property
    # uniformly distributed over its range, as the independent draws were.
    Class_Position = random.random()
    Jitter = Model_Data["stellar"]["class_position_jitter"]
    def class_value(lo, hi):
        u = Class_Position + random.uniform(-Jitter, Jitter)
        u = -u if u < 0 else (2 - u if u > 1 else u)
        return lo + u * (hi - lo)
    Star_Mo = round(class_value(Star_Info['Mo_min'], Star_Info['Mo_max']), 4)
    Star_Ro = round(class_value(Star_Info['Ro_min'], Star_Info['Ro_max']), 4)
    Star_T  = round(class_value(Star_Info['temperature_min'], Star_Info['temperature_max']), 4)
    # Luminosity follows from radius and temperature (Stefan-Boltzmann, solar T = 5772 K).
    # Drawing it independently left zones/temperatures (from Lo) disagreeing with
    # irradiance/Goldilocks (from R and T) by up to 100x.
    Star_Lo = round(Star_Ro**2 * (Star_T / 5772) ** 4, 6)
    Star_R  = round(Star_Ro * 695700, 4)

    Star_SOI          = AstraFunctions.StellarSphereOfInfluence(Star_Mo)
    Star_Pos          = AstraFunctions.GalaxyPosition(key)
    Star_Spectral     = AstraFunctions.StellarSpectralType(Star_T, Star_Class)
    Star_Metallicity  = AstraFunctions.StellarMetallicity(Star_Class, key)
    Star_Mbol, Star_Mv = AstraFunctions.StellarAbsoluteMagnitude(Star_Lo)
    Goldilocks_Irradiance = Model_Data["stellar"]["goldilocks_irradiance"]
    Star_GoldilocksZone = AstraFunctions.StellarGoldilocksBoundary(Star_R, Star_T, Goldilocks_Irradiance["max"], Goldilocks_Irradiance["min"])
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
            "corrected": AstraFunctions.PoissonSample(key + "bodycount", AstraFunctions.BodyCountLambda(Star_Class, Star_Metallicity)),
        }
    }

def assign_giant_subclass(key, index, Body_Mass, Body_SMA, Star_IceLine, Planet_Data, Model_Data):
    """Determines whether a giant body is a gas_giant or ice_giant.

    Classification is mass-primary with a zone/temperature probabilistic bias:
    - Bodies >= ice_giant M_E_max (95 Me) are always gas_giant (above Saturn mass, unambiguous).
    - Bodies < gas_giant M_E_min (30 Me) are always ice_giant.
    - 30-95 Me overlap: ice_giant by default, with a sigmoid probability of being
      gas_giant that rises with mass and proximity to the ice line.

    Both boundaries come from Planet_Data so the classifier can never hand a body
    to a subclass whose mass bounds would clamp it (the old hardcoded 95 Me check
    let 10-95 Me gas giants through, which then piled up at the 95 Me floor).

    Returns (subclass_string, subclass_data_dict).
    """
    random.seed(key + str(index) + "subclass")

    gas_data  = next(e for e in Planet_Data["giant"] if e["class"] == "gas_giant")
    ice_data  = next(e for e in Planet_Data["giant"] if e["class"] == "ice_giant")

    # Hard upper boundary: above Saturn mass, unambiguously gas giant
    if Body_Mass >= ice_data["M_E_max"]:
        return "gas_giant", gas_data
    # Hard lower boundary: too light to be a gas giant
    if Body_Mass < gas_data["M_E_min"]:
        return "ice_giant", ice_data

    # Probabilistic zone in the 30-95 Me overlap range (Model_Data planetary.giant_classifier).
    # Sigmoid centred at the midpoint — above it leans gas giant, below leans ice giant.
    # Zone modifier: bodies closer to the ice line are warmer and more gas-giant-like.
    clf = Model_Data["planetary"]["giant_classifier"]
    mass_z = (Body_Mass - clf["midpoint"]) / clf["width"]
    mass_p = 1.0 / (1.0 + math.exp(-mass_z))

    # Zone bias: within zone_reach x ice line = warmer = nudge toward gas giant
    bias_max = clf["zone_bias_max"]
    zone_bias = max(0.0, min(bias_max, bias_max * (clf["zone_reach"] - Body_SMA / max(Star_IceLine, clf["ice_line_floor_au"]))))
    p_gas = max(0.0, min(clf["max"], mass_p + zone_bias))

    if random.random() < p_gas:
        return "gas_giant", gas_data
    else:
        return "ice_giant", ice_data

def assign_rocky_subclass(Body_Mass, Planet_Data):
    """Determines whether a rocky body is terrestrial or super_earth.

    Classification is purely mass-based:
    - >= super_earth M_E_min (2 Me) → super_earth
    - below it                       → terrestrial (includes sub-Earth low end, < 0.1 Me)

    No RNG needed — the mass itself is the discriminator.
    Returns (subclass_string, subclass_data_dict).
    """
    terrestrial_data = next(e for e in Planet_Data["rocky"] if e["class"] == "terrestrial")
    super_earth_data = next(e for e in Planet_Data["rocky"] if e["class"] == "super_earth")

    if Body_Mass >= super_earth_data["M_E_min"]:
        return "super_earth", super_earth_data
    else:
        return "terrestrial", terrestrial_data

def generate_body(key, index, Body_Type, Body_SMA, star, Habitability_Data, Planet_Data, Model_Data, Rocky_Count=1, Giant_Count=1):
    """Generates all properties for a single orbital body. Returns a body data dict.
    Rocky_Count and Giant_Count are the actual placed body counts post-Gladman reduction,
    used by BodyMassGeneration to correctly apply the competitive disk mass factor (f_Comp).
    """

    # Assign subclass before any downstream calls.
    # Giants: provisional mass draw first (same seed = same result), then classify.
    # Rocky: classify after mass generation — no bounds clamping needed.
    Body_Subclass = None
    Subclass_Data = None
    # Before the subclass is known, mass is drawn across every subclass of this type
    Type_Mass_Range = (min(e["M_E_min"] for e in Planet_Data[Body_Type]),
                       max(e["M_E_max"] for e in Planet_Data[Body_Type]))
    if Body_Type == "giant":
        Body_Subclass, Subclass_Data = assign_giant_subclass(
            key, index,
            AstraFunctions.BodyMassGeneration(key, star["body_mass_scale"], star["Star_Mo"], star["Star_Metallicity"], Body_Type, Giant_Count, index, Mass_Range=Type_Mass_Range),
            Body_SMA,
            star["zones"]["Star_IceLine"],
            Planet_Data, Model_Data
        )

    # Pass the correct placed body count so f_Comp applies disk mass competition properly
    Body_Count = Rocky_Count if Body_Type == "rocky" else Giant_Count
    Body_Mass = AstraFunctions.BodyMassGeneration(key, star["body_mass_scale"], star["Star_Mo"], star["Star_Metallicity"], Body_Type, Body_Count, index, Body_Subclass, Subclass_Data, Mass_Range=Type_Mass_Range)

    if Body_Type == "rocky":
        Body_Subclass, Subclass_Data = assign_rocky_subclass(Body_Mass, Planet_Data)
    Body_Radius        = AstraFunctions.BodyRadiusGeneration(key, Body_Mass, Body_Type, index, Body_Subclass, Subclass_Data)
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

def generate_dwarf(key, index, dwarf_type, dwarf_SMA, star, Habitability_Data, Planet_Data, belt_tag):
    """Generates a single dwarf body. Simplified pipeline — no full tectonics."""
    # Belt-specific seed key — with the bare key, dwarf N shared every seed with planet N.
    dwarf_key = key + belt_tag + "belt"
    Dwarf_Data = next(e for e in Planet_Data["dwarf"] if e["class"] == dwarf_type)
    Body_Mass          = AstraFunctions.BodyMassGeneration(dwarf_key, star["body_mass_scale"], star["Star_Mo"], star["Star_Metallicity"], dwarf_type, 1, index, Subclass_Data=Dwarf_Data)
    Body_Radius        = AstraFunctions.BodyRadiusGeneration(dwarf_key, Body_Mass, dwarf_type, index, Subclass_Data=Dwarf_Data)
    Body_Volume        = AstraFunctions.BodyVolumeCalculation(Body_Radius)
    Body_Density       = AstraFunctions.BodyDensityCalculation(Body_Mass, Body_Volume)
    Body_CoreMass, Body_CoreData = AstraFunctions.BodyCoreCaluclation(dwarf_key, star["Star_Metallicity"], dwarf_type, Body_Mass, index)
    Body_OrbitalData   = AstraFunctions.BodyOrbitalMechanicsCaluclation(star["Star_Mo"], dwarf_SMA, Body_Mass, Body_Radius, star["zones"])
    Body_SurfaceGravity = AstraFunctions.BodySurfaceGravity(Body_Mass, Body_Radius)
    Body_AtmosphericData = AstraFunctions.BodyAtmospherics(dwarf_key, Body_CoreData["Dynamo_Factor"]["value"], Body_SurfaceGravity, Body_Radius, star["Star_km"], star["Star_T"], dwarf_SMA, star["Star_Lo"], dwarf_type, Body_Mass, index)
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

def generate_belt(key, belt_tag, dwarf_type, star, Habitability_Data, Planet_Data):
    """Generates all dwarf bodies for a single belt. Returns list of dwarf dicts."""
    belt_zone = star["zones"]["Star_InnerBelt"] if belt_tag == "inner" else star["zones"]["Star_OuterBelt"]
    has_giant = star.get("has_giant", False)

    count, smas = AstraFunctions.GenerateBeltPopulation(
        key, belt_tag, star["Star_Metallicity"], star["Star_Mo"], belt_zone, has_giant
    )

    dwarfs = []
    for i, sma in enumerate(smas):
        dwarf = generate_dwarf(key, i, dwarf_type, sma, star, Habitability_Data, Planet_Data, belt_tag)
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
    with open("Model_Data.json", "r") as f:
        Model_Data = json.load(f)

    star = generate_star(key, Star_Data, Habitability_Data, Model_Data)

    Star_LambdaCorrected = star["lambda"]["corrected"]
    Star_OrbitalZones, Body_RockyCount, Body_GiantCount = AstraFunctions.BodyZoneDistribution(
        key, star["class"], star["Star_Metallicity"], star["Star_Mo"], Star_LambdaCorrected
    )
    # Hill-radius-derived placement (Gladman 1993) — replaces fixed spacing.
    # Representative masses and k per body type: Model_Data system.placement.
    Placement = Model_Data["system"]["placement"]
    Body_RockySMA = AstraFunctions.BodySMAPlacement(
        key, Body_RockyCount,
        star["zones"]["Star_RockyZone"][0], star["zones"]["Star_RockyZone"][1],
        star["Star_Mo"], rep_mass_Me=Placement["rocky"]["representative_mass"], body_type_tag="rocky",
        k=Placement["rocky"]["k"]
    )
    Body_GiantSMA = AstraFunctions.BodySMAPlacement(
        key, Body_GiantCount,
        star["zones"]["Star_GiantZone"][0], star["zones"]["Star_GiantZone"][1],
        star["Star_Mo"], rep_mass_Me=Placement["giant"]["representative_mass"], body_type_tag="giant",
        k=Placement["giant"]["k"]
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
        body = generate_body(key, i, Body_Type, Body_SMA, star, Habitability_Data, Planet_Data, Model_Data,
                             Rocky_Count=Body_RockyCount, Giant_Count=Body_GiantCount)
        bodies.append(body)

    # Pass 2: belt populations
    inner_belt = generate_belt(key, "inner", "rocky_dwarf", star, Habitability_Data, Planet_Data)
    outer_belt = generate_belt(key, "outer", "icy_dwarf",   star, Habitability_Data, Planet_Data)

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
