import random, math

def BodyMassGeneration(key, Star_BodyMassScale, Star_Mo, Star_Metallicity, Body_OrbitalZone, Body_Count, index, Body_Subclass=None, Subclass_Data=None):
    random.seed(key + str(index))
    if Body_OrbitalZone == "rocky":
        mu = math.log(0.9)
        sigma = 0.4
        mass = math.exp(random.gauss(mu, sigma))
        mass = max(0.05, min(mass, 20.0))
    elif Body_OrbitalZone == "giant":
        # Use subclass mass bounds from Planet_Data if available, else fall back to full range
        if Subclass_Data is not None:
            m_min = Subclass_Data["M_E_min"]
            m_max = Subclass_Data["M_E_max"]
        else:
            m_min = 10.0
            m_max = 318.0
        core = random.uniform(5.0, 20.0)
        env_base = random.uniform(5.0, 25.0)
        envelope = core * env_base
        mass = core + envelope
        # Clamp to subclass range
        mass = max(m_min, min(mass, m_max))
    elif Body_OrbitalZone in ("rocky_dwarf", "icy_dwarf"):
        log_min = math.log10(0.0001)
        log_max = math.log10(0.05)
        mass = 10 ** random.uniform(log_min, log_max)
    else:
        mass = 0.001  # fallback

    beta_feh = 0.4
    f_FeH = max(0.5, 1.0 + beta_feh * Star_Metallicity)
    f_StarMass = 1.0 + 0.1 * max(0.0, Star_Mo - 1.0)
    if Body_OrbitalZone == "rocky":
        f_Comp = 1.0 / (1.0 + 0.3 * max(0, Body_Count - 2.0))
    elif Body_OrbitalZone == "giant":
        f_Comp = 1.0 / (1.0 + 0.3 * max(0, Body_Count - 0.5))
    else:
        f_Comp = 1.0  # dwarfs don't compete for disk mass

    mass *= f_FeH * f_StarMass * f_Comp

    # Re-clamp after modifiers to keep within subclass bounds
    if Body_OrbitalZone == "giant" and Subclass_Data is not None:
        mass = max(Subclass_Data["M_E_min"], min(mass, Subclass_Data["M_E_max"]))
    else:
        mass = max(0.0001, min(mass, 5000.0))

    return round(mass, 6)

def BodyRadiusGeneration(key, Body_Mass, Body_Type, index, Body_Subclass=None):
    random.seed(key + str(index))
    if Body_Type == "rocky":
        if Body_Subclass == "super_earth":
            scalar = random.uniform(0.27, 0.30)
        else:
            scalar = random.uniform(0.28, 0.33)
        Body_Radius = Body_Mass ** scalar
        # Clamp to subclass radius bounds from Planet_Data
        if Body_Subclass == "super_earth":
            Body_Radius = max(1.25, min(Body_Radius, 2.0))
        else:
            Body_Radius = max(0.3, min(Body_Radius, 1.25))
    elif Body_Type == "giant":
        if Body_Subclass == "gas_giant":
            # Large, inflated — Jupiter ~11 Re, Saturn ~9.5 Re
            if Body_Mass >= 200:
                Body_Radius = random.uniform(10.0, 15.0)
            else:
                scalar = random.uniform(0.20, 0.26)
                Body_Radius = Body_Mass ** scalar
                Body_Radius = max(8.0, min(Body_Radius, 15.0))
        elif Body_Subclass == "ice_giant":
            # Denser, smaller — Uranus ~4 Re, Neptune ~3.9 Re
            scalar = random.uniform(0.22, 0.28)
            Body_Radius = Body_Mass ** scalar
            Body_Radius = max(3.0, min(Body_Radius, 7.0))
        else:
            # Fallback: original behaviour
            if Body_Mass < 100:
                scalar = random.uniform(0.22, 0.28)
                Body_Radius = Body_Mass ** scalar
            else:
                Body_Radius = random.uniform(8, 12)
    elif Body_Type == "rocky_dwarf":
        scalar = random.uniform(0.30, 0.36)
        Body_Radius = Body_Mass ** scalar
        Body_Radius = max(0.05, min(Body_Radius, 0.5))
    elif Body_Type == "icy_dwarf":
        scalar = random.uniform(0.32, 0.38)
        Body_Radius = Body_Mass ** scalar
        Body_Radius = max(0.05, min(Body_Radius, 0.3))
    else:
        Body_Radius = Body_Mass ** 0.33
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
    random.seed(key + str(index))
    base_mu = math.log(0.32)
    base_sigma = 0.25
    CMF = math.exp(random.gauss(base_mu, base_sigma))
    FeH_Clamped = max(-1.0, min(1.0, Star_Metallicity))
    FeH_Factor = 1.0 + 0.15 * FeH_Clamped
    Zone_Factor = 1.05 if Body_Type == "rocky" else 1.0
    Mass_Factor = 1.0 + 0.03 * max(0.0, math.log10(max(Body_Mass, 1.0)))
    CMF *= FeH_Factor * Zone_Factor * Mass_Factor
    CMF = max(0.01, min(CMF, 0.8))

    Fe_mean = 0.85 + 0.03 * FeH_Clamped
    Fe_frac = random.gauss(Fe_mean, 0.03)
    Fe_frac = max(0.7, min(Fe_frac, 0.95))
    Ni_frac = random.uniform(0.03, 0.08)
    Light_frac = max(0.01, 1.0 - Fe_frac - Ni_frac)
    Sum = Fe_frac + Ni_frac + Light_frac
    Fe_frac /= Sum; Ni_frac /= Sum; Light_frac /= Sum

    Body_CoreMass = CMF * Body_Mass
    Rho_Fe = 7874
    Rho_Ni = 8908
    Rho_Light = 3400
    Rho_core = (Fe_frac * Rho_Fe) + (Ni_frac * Rho_Ni) + (Light_frac * Rho_Light)
    Body_CoreMass_KG = Body_CoreMass * 5.972e24
    Body_CoreVolume = (Body_CoreMass_KG / Rho_core) / 1e9
    Body_CoreRadius_KM = ((3 * Body_CoreVolume) / (4 * math.pi)) ** (1/3)
    Body_CoreRadius = Body_CoreRadius_KM / 6.371e3

    Core_Proxy = Body_CoreMass / 0.32
    proxy_clip = max(0.1, min(Core_Proxy, 5.0))
    a = 1.0 + 1.5 * (proxy_clip - 0.1) / (5.0 - 0.1)
    b = 2.5 - 1.2 * (proxy_clip - 0.1) / (5.0 - 0.1)
    a *= random.uniform(0.9, 1.1)
    b *= random.uniform(0.9, 1.1)
    Liquid_frac = random.betavariate(a, b)
    Liquid_frac = max(0.0, min(Liquid_frac, 1.0))

    if Body_Type == "rocky":
        Mass_Factor_Dynamo = 0.25 + 0.5 * min(1.5, math.log10(max(Body_CoreMass, 0.1)) + 1)
        Spin_Factor = random.uniform(0.5, 1.5)
        Dynamo_Factor = Mass_Factor_Dynamo * Spin_Factor
    elif Body_Type == "giant":
        # Read dynamo range from subclass data if available, else fall back
        if Subclass_Data is not None and "dynamo_range" in Subclass_Data:
            d_min, d_max = Subclass_Data["dynamo_range"]
        else:
            d_min, d_max = 1.5, 3.0
        Dynamo_Factor = random.uniform(d_min, d_max)
    else:
        # Dwarfs: geologically dead, negligible dynamo
        Dynamo_Factor = random.uniform(0.0, 0.05)

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
    Tangential_Velocity = random.uniform(0, 2)
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
