import json, random, math

with open("Model_Data.json", "r") as f:
    Model = json.load(f)["planetary"]

def BodyMassGeneration(key, Star_BodyMassScale, Star_Mo, Star_Metallicity, Body_OrbitalZone, Body_Count, index, Body_Subclass=None, Subclass_Data=None, Mass_Range=None):
    """Mass draw bounds come from Planet_Data: the subclass's M_E_min/M_E_max when
    Subclass_Data is given, otherwise Mass_Range (min, max) — the span of the
    subclasses the body could still become (rocky mass is drawn before its subclass
    is known; giants draw a provisional mass to choose theirs)."""
    random.seed(key + str(index) + "mass")
    if Subclass_Data is not None:
        m_min = Subclass_Data["M_E_min"]
        m_max = Subclass_Data["M_E_max"]
    else:
        m_min, m_max = Mass_Range
    if Body_OrbitalZone == "rocky":
        mu = math.log(Model["rocky_mass"]["median"])
        sigma = Model["rocky_mass"]["sigma"]
        mass = math.exp(random.gauss(mu, sigma))
        mass = max(m_min, min(mass, m_max))
    elif Body_OrbitalZone == "giant":
        core = random.uniform(*Model["giant_mass"]["core_range"])
        env_base = random.uniform(*Model["giant_mass"]["envelope_ratio_range"])
        envelope = core * env_base
        mass = core + envelope
        # Clamp to subclass range
        mass = max(m_min, min(mass, m_max))
    elif Body_OrbitalZone in ("rocky_dwarf", "icy_dwarf"):
        log_min = math.log10(m_min)
        log_max = math.log10(m_max)
        mass = 10 ** random.uniform(log_min, log_max)
    else:
        mass = 0.001  # fallback

    mods = Model["mass_modifiers"]
    beta_feh = mods["metallicity_beta"]
    f_FeH = max(mods["metallicity_floor"], 1.0 + beta_feh * Star_Metallicity)
    f_StarMass = 1.0 + mods["star_mass_boost"] * max(0.0, Star_Mo - 1.0)
    if Body_OrbitalZone in mods["competition"]:
        comp = mods["competition"][Body_OrbitalZone]
        f_Comp = 1.0 / (1.0 + comp["strength"] * max(0, Body_Count - comp["free_bodies"]))
    else:
        f_Comp = 1.0  # dwarfs don't compete for disk mass

    mass *= f_FeH * f_StarMass * f_Comp

    # Re-clamp after modifiers to keep within subclass bounds
    if Body_OrbitalZone == "giant" and Subclass_Data is not None:
        mass = max(Subclass_Data["M_E_min"], min(mass, Subclass_Data["M_E_max"]))
    else:
        mass = max(mods["sanity_range"][0], min(mass, mods["sanity_range"][1]))

    return round(mass, 6)

def BodyRadiusGeneration(key, Body_Mass, Body_Type, index, Body_Subclass=None, Subclass_Data=None):
    """Radius from mass using the class's radius model in Planet_Data (see
    _comment_radius_model there). Subclass_Data is the Planet_Data entry for the
    body's class: rocky subclass, giant subclass, or dwarf type."""
    random.seed(key + str(index) + "radius")
    model = Subclass_Data
    if "inflated_mass_min" in model and Body_Mass >= model["inflated_mass_min"]:
        # Inflated regime (gas giants >= 200 Me): radius no longer tracks mass
        Body_Radius = random.uniform(*model["inflated_radius_range"])
    else:
        scalar = random.uniform(*model["radius_exponent_range"])
        ref = model.get("radius_reference")
        if ref is None:
            Body_Radius = Body_Mass ** scalar  # Earth-anchored: 1 Me -> 1 Re
        else:
            # Anchored to a reference body (Saturn, Neptune) — the bare M^s form
            # gave giants radii far below their class and clamped them all to the floor.
            Body_Radius = ref["radius"] * (Body_Mass / ref["mass"]) ** scalar
        if "radius_scatter" in model:
            Body_Radius *= random.uniform(*model["radius_scatter"])
    Body_Radius = max(model["R_E_min"], min(Body_Radius, model["R_E_max"]))
    return round(Body_Radius, 6)

def BodyVolumeCalculation(Body_Radius):
    Re = 6371  # km
    Body_Radius_km = Body_Radius * Re
    Body_Volume = (4/3) * math.pi * (Body_Radius_km**3)
    return Body_Volume

def BodyDensityCalculation(Body_Mass, Body_Volume):
    Me = 5.972e24  # kg
    Body_Mass_kg = Body_Mass * Me
    return round(Body_Mass_kg / Body_Volume, 4)

def BodySurfaceGravity(Body_Mass, Body_Radius):
    if Body_Mass <= 0 or Body_Radius <= 0:
        return "=ERROR="
    Earth_Mass = 5.972e24
    Earth_Radius = 6371000
    G = 6.6743e-11
    Body_Mass_kg = Body_Mass * Earth_Mass
    Body_Radius_m = Body_Radius * Earth_Radius
    return round((G * Body_Mass_kg) / (Body_Radius_m**2), 4)

def BodyCoreCaluclation(key, Star_Metallicity, Body_Type, Body_Mass, index, Body_Subclass=None, Subclass_Data=None):
    random.seed(key + str(index) + "core")
    core = Model["core"]
    base_mu = math.log(core["cmf_median"])
    base_sigma = core["cmf_sigma"]
    CMF = math.exp(random.gauss(base_mu, base_sigma))
    clamp = core["metallicity_clamp"]
    FeH_Clamped = max(-clamp, min(clamp, Star_Metallicity))
    FeH_Factor = 1.0 + core["cmf_metallicity_factor"] * FeH_Clamped
    Zone_Factor = core["rocky_zone_factor"] if Body_Type == "rocky" else 1.0
    Mass_Factor = 1.0 + core["cmf_mass_factor"] * max(0.0, math.log10(max(Body_Mass, 1.0)))
    CMF *= FeH_Factor * Zone_Factor * Mass_Factor
    CMF = max(core["cmf_range"][0], min(CMF, core["cmf_range"][1]))

    iron = core["iron"]
    Fe_mean = iron["mean"] + iron["metallicity_shift"] * FeH_Clamped
    Fe_frac = random.gauss(Fe_mean, iron["sigma"])
    Fe_frac = max(iron["range"][0], min(Fe_frac, iron["range"][1]))
    Ni_frac = random.uniform(*core["nickel_range"])
    Light_frac = max(core["light_element_min"], 1.0 - Fe_frac - Ni_frac)
    Sum = Fe_frac + Ni_frac + Light_frac
    Fe_frac /= Sum; Ni_frac /= Sum; Light_frac /= Sum

    Body_CoreMass = CMF * Body_Mass
    Rho_Fe = core["density_kg_m3"]["Fe"]
    Rho_Ni = core["density_kg_m3"]["Ni"]
    Rho_Light = core["density_kg_m3"]["Light"]
    Rho_core = (Fe_frac * Rho_Fe) + (Ni_frac * Rho_Ni) + (Light_frac * Rho_Light)
    Body_CoreMass_KG = Body_CoreMass * 5.972e24
    Body_CoreVolume = (Body_CoreMass_KG / Rho_core) / 1e9
    Body_CoreRadius_KM = ((3 * Body_CoreVolume) / (4 * math.pi)) ** (1/3)
    Body_CoreRadius = Body_CoreRadius_KM / 6.371e3

    liquid = core["liquid"]
    clip_lo, clip_hi = liquid["proxy_clip"]
    Core_Proxy = Body_CoreMass / liquid["reference_core_mass"]
    proxy_clip = max(clip_lo, min(Core_Proxy, clip_hi))
    a = liquid["alpha_base"] + liquid["alpha_rise"] * (proxy_clip - clip_lo) / (clip_hi - clip_lo)
    b = liquid["beta_base"] - liquid["beta_drop"] * (proxy_clip - clip_lo) / (clip_hi - clip_lo)
    a *= random.uniform(*liquid["jitter"])
    b *= random.uniform(*liquid["jitter"])
    Liquid_frac = random.betavariate(a, b)
    Liquid_frac = max(0.0, min(Liquid_frac, 1.0))

    if Body_Type == "rocky":
        dyn = core["rocky_dynamo"]
        Mass_Factor_Dynamo = dyn["base"] + dyn["slope"] * min(dyn["cap"], math.log10(max(Body_CoreMass, dyn["core_mass_floor"])) + dyn["offset"])
        Spin_Factor = random.uniform(*dyn["spin_range"])
        Dynamo_Factor = Mass_Factor_Dynamo * Spin_Factor
    elif Body_Type == "giant":
        # Dynamo range per giant subclass (Planet_Data dynamo_range)
        d_min, d_max = Subclass_Data["dynamo_range"]
        Dynamo_Factor = random.uniform(d_min, d_max)
    else:
        # Dwarfs: geologically dead, negligible dynamo
        Dynamo_Factor = random.uniform(*core["dwarf_dynamo_range"])

    Body_CoreData = {
        "CMF": {"value": round(CMF, 4), "unit": "fraction"},
        "Mass": {"value": round(Body_CoreMass, 4), "unit": "Me"},
        "Radius": {"value": round(Body_CoreRadius, 4), "unit": "Re"},
        "Volume": {"value": round(Body_CoreVolume, 4), "unit": "km^3"},
        "Density": {"value": round(Rho_core, 1), "unit": "kg/m^3"},
        "Composition": {
            "Fe": {"value": round(Fe_frac, 4), "unit": "%"},
            "Ni": {"value": round(Ni_frac, 4), "unit": "%"},
            "Light Elements": {"value": round(Light_frac, 4), "unit": "%"},
        },
        "Liquid_Core_Fraction": {"value": round(Liquid_frac, 4), "unit": "fraction"},
        "Dynamo_Factor": {"value": round(Dynamo_Factor, 4), "unit": "unitless"}
    }
    return Body_CoreMass, Body_CoreData

def BodyOrbitalMechanicsCaluclation(Star_Mass, Body_SMA, Body_Mass, Body_Radius, Star_Zones):
    Sol_Mass = 1.989e30
    Earth_Mass = 5.972e24
    AU = 1.496e11
    G = 6.6743e-11
    Earth_Radius_km = 6371
    Star_Mass_kg = Star_Mass * Sol_Mass
    Body_Mass_kg = Body_Mass * Earth_Mass
    Body_SMA_m = AU * Body_SMA
    Body_OrbitalSpeed = math.sqrt((G * Star_Mass_kg) / Body_SMA_m) / 1000
    Body_OrbitalPeriod = (math.sqrt((4 * (math.pi**2)) / (G * (Star_Mass_kg + Body_Mass_kg)) * (Body_SMA_m**3))) / 86400
    Body_HillRadius = (Body_SMA_m * ((Body_Mass_kg / (3 * Star_Mass_kg))**(1/3))) / AU
    Tangential_Velocity = random.uniform(*Model["equatorial_speed_range_kms"])
    Rotational_Period = ((2 * math.pi * (Body_Radius * Earth_Radius_km)) / round(Tangential_Velocity, 4) / 3600)
    Zone_Lookup = [
        ("Rocky Zone",  Star_Zones["Star_RockyZone"]),
        ("Inner Belt",  Star_Zones["Star_InnerBelt"]),
        ("Giant Zone",  Star_Zones["Star_GiantZone"]),
        ("Outer Belt",  Star_Zones["Star_OuterBelt"]),
    ]
    Orbital_Zone = "Undefined"
    for zone_name, zone_range in Zone_Lookup:
        if zone_range[0] <= Body_SMA <= zone_range[1]:
            Orbital_Zone = zone_name
            break
    Goldilocks = Star_Zones["Star_GoldilocksZone"]
    In_Goldilocks = Goldilocks[0] <= Body_SMA <= Goldilocks[1]
    return {
        "Semi-Major-Axis": {"value": Body_SMA, "unit": "AU"},
        "Orbital_Speed": {"value": round(Body_OrbitalSpeed, 4), "unit": "km/s"},
        "Orbital_Period": {"value": round(Body_OrbitalPeriod, 4), "unit": "days"},
        "Rotational_Speed": {"value": round(Tangential_Velocity, 4), "unit": "km/s"},
        "Rotational_Period": {"value": round(Rotational_Period, 4), "unit": "hours"},
        "Hill_Radius": {"value": round(Body_HillRadius, 4), "unit": "AU"},
        "Orbital_Zone": {"value": Orbital_Zone},
        "In_Goldilocks": {"value": In_Goldilocks}
    }
