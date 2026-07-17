import random, math

GAS_TABLE = [
    {"name": "H2",  "formula": "H₂",  "mol_mass": 2.016,  "abundance": 10.0, "zones": ["giant"]},
    {"name": "He",  "formula": "He",   "mol_mass": 4.003,  "abundance": 8.0,  "zones": ["giant"]},
    {"name": "CH4", "formula": "CH₄",  "mol_mass": 16.04,  "abundance": 1.5,  "zones": ["giant", "rocky", "icy_dwarf"]},
    {"name": "NH3", "formula": "NH₃",  "mol_mass": 17.03,  "abundance": 1.0,  "zones": ["giant", "rocky"]},
    {"name": "H2O", "formula": "H₂O",  "mol_mass": 18.015, "abundance": 2.0,  "zones": ["rocky", "giant"]},
    {"name": "N2",  "formula": "N₂",   "mol_mass": 28.014, "abundance": 4.0,  "zones": ["rocky", "rocky_dwarf", "icy_dwarf"]},
    {"name": "O2",  "formula": "O₂",   "mol_mass": 31.998, "abundance": 0.5,  "zones": ["rocky"]},
    {"name": "CO2", "formula": "CO₂",  "mol_mass": 44.01,  "abundance": 3.0,  "zones": ["rocky", "rocky_dwarf", "icy_dwarf"]},
    {"name": "SO2", "formula": "SO₂",  "mol_mass": 64.07,  "abundance": 0.8,  "zones": ["rocky", "rocky_dwarf"]},
]

def BodyEscapeVelocity(Body_Mass, Body_Radius):
    G = 6.6743e-11
    Earth_Mass = 5.972e24
    Earth_Radius = 6.371e6
    mass_kg = Body_Mass * Earth_Mass
    radius_m = Body_Radius * Earth_Radius
    return math.sqrt((2 * G * mass_kg) / radius_m)

def BodyThermalVelocity(molecular_mass, temperature_K):
    k_B = 1.380649e-23
    amu = 1.66054e-27
    mass_kg = molecular_mass * amu
    return math.sqrt((3 * k_B * temperature_K) / mass_kg)

def BodyAtmosphereComposition(key, Body_Type, Body_Mass, Body_Radius, Body_SurfaceGravity, Dynamo_Factor, Body_SurfaceTemperature, Body_SMA, index, Body_Subclass=None, Subclass_Data=None, seed_suffix=""):
    random.seed(key + str(index) + "atmo" + seed_suffix)
    temperature_K = max(Body_SurfaceTemperature + 273.15, 10.0)
    V_escape = BodyEscapeVelocity(Body_Mass, Body_Radius)
    JEANS_FACTOR = 6.0
    retained_gases = []
    for gas in GAS_TABLE:
        if Body_Type not in gas["zones"]:
            continue
        V_thermal = BodyThermalVelocity(gas["mol_mass"], temperature_K)
        if V_escape < JEANS_FACTOR * V_thermal:
            continue
        if Body_SMA < 0.3 and gas["mol_mass"] < 20.0:
            strip_chance = 0.7 * (1.0 - Body_SMA / 0.3)
            strip_chance *= max(0.1, 1.0 - Dynamo_Factor * 0.5)
            # Sub-Earths (< 0.1 Me terrestrial) are more vulnerable to stripping
            if Body_Type == "rocky" and Subclass_Data is not None and Body_Mass < Subclass_Data.get("sub_earth_threshold", 0.1):
                strip_chance = min(1.0, strip_chance + Subclass_Data.get("sub_earth_strip_bonus", 0.3))
            if random.random() < strip_chance:
                continue
        retained_gases.append(gas)

    if not retained_gases:
        return None, "None"

    # Load subclass gas_table_weights if available (giants only)
    subclass_weights = None
    if Body_Type == "giant" and Subclass_Data is not None and "gas_table_weights" in Subclass_Data:
        subclass_weights = Subclass_Data["gas_table_weights"]

    fractions = {}
    for gas in retained_gases:
        weight = gas["abundance"] * random.uniform(0.5, 1.5)

        if Body_Type == "giant":
            if subclass_weights is not None:
                # Apply subclass-specific weight from Planet_Data.json.
                # This replaces the old hardcoded 3x H2/He multiplier and
                # fixes the He/H2 dominance inversion bug.
                gas_override = subclass_weights.get(gas["name"], None)
                if gas_override is not None:
                    weight = gas_override * random.uniform(0.8, 1.2)
            else:
                # Legacy fallback if no subclass data — retain old behaviour
                if gas["name"] in ["H2", "He"]:
                    weight *= 3.0
        elif Body_Type == "rocky" and gas["name"] in ["N2", "CO2"]:
            weight *= 1.5 + 0.5 * max(0.0, Dynamo_Factor)

        if gas["name"] in ["CH4", "NH3"] and temperature_K < 200:
            weight *= 2.0
        elif gas["name"] in ["CH4", "NH3"] and temperature_K > 500:
            weight *= 0.3

        fractions[gas["name"]] = weight

    total = sum(fractions.values())
    for gas_name in fractions:
        fractions[gas_name] = round(fractions[gas_name] / total, 4)

    dominant = max(fractions, key=fractions.get)
    sorted_gases = sorted(fractions.items(), key=lambda x: x[1], reverse=True)
    gas_lookup = {g["name"]: g["formula"] for g in GAS_TABLE}

    if len(sorted_gases) >= 2 and sorted_gases[1][1] > 0.10:
        Atmosphere_Type = gas_lookup[sorted_gases[0][0]] + "/" + gas_lookup[sorted_gases[1][0]]
    else:
        Atmosphere_Type = gas_lookup[dominant] + "-dominant"

    Composition = {}
    for gas_name, frac in sorted_gases:
        Composition[gas_lookup[gas_name]] = {"value": frac, "unit": "fraction"}

    return Composition, Atmosphere_Type

def BodyAtmosphereMassFraction(key, Body_Type, Atmo_Class, Dynamo_Factor, Body_Mass, Body_SurfaceGravity, index, seed_suffix=""):
    random.seed(key + str(index) + "amf" + seed_suffix)
    if Body_Type == "giant":
        base = random.uniform(0.50, 0.95)
        mass_boost = 0.02 * math.log10(max(Body_Mass, 10.0))
        return min(base + mass_boost, 0.98)
    g_ratio = Body_SurfaceGravity / 9.81
    if Atmo_Class == "Thick":
        base_log_min = -7.0
        base_log_max = -4.0
    else:
        base_log_min = -10.0
        base_log_max = -7.0
    g_shift = 3.0 * math.log10(max(g_ratio, 0.05))
    log_min = base_log_min + g_shift
    log_max = base_log_max + g_shift
    range_center = (log_min + log_max) / 2.0
    range_half = (log_max - log_min) / 2.0
    narrowing = 0.4
    log_min = range_center - range_half * narrowing
    log_max = range_center + range_half * narrowing
    if g_ratio < 0.5:
        range_width = log_max - log_min
        log_max = log_min + range_width * 0.5
    log_AMF = random.uniform(log_min, log_max)
    AMF = 10 ** log_AMF
    AMF *= (1.0 + 0.3 * max(0.0, Dynamo_Factor - 0.2))
    AMF *= (1.0 + 0.3 * math.log10(max(Body_Mass / 1.0, 0.01)))
    AMF = min(AMF, 0.01)
    return AMF

def BodyMeanMolecularWeight(Atmo_Composition):
    formula_to_mol = {g["formula"]: g["mol_mass"] for g in GAS_TABLE}
    mean_mol = 0.0
    for formula, data in Atmo_Composition.items():
        frac = data["value"]
        mol_mass = formula_to_mol.get(formula, 28.0)
        mean_mol += frac * mol_mass
    return round(mean_mol, 3)

def BodySurfacePressureCalculation(Body_Mass, Body_Radius, Body_SurfaceGravity, AMF):
    Earth_Mass = 5.972e24
    Earth_Radius = 6.371e6
    atm = 101325
    M_body_kg = Body_Mass * Earth_Mass
    R_m = Body_Radius * Earth_Radius
    M_atm = AMF * M_body_kg
    A = 4 * math.pi * R_m**2
    P_pa = (M_atm * Body_SurfaceGravity) / A
    return P_pa / atm

def BodyBareTemperature(Star_Lo, Body_SMA):
    Body_SMA_m = Body_SMA * 1.496e11
    Star_Lo_W = Star_Lo * 3.84e26
    SBSigma = 5.67e-8
    top = Star_Lo_W
    bottom = (16 * math.pi * SBSigma) * (Body_SMA_m**2)
    Bare_Temperature_K = (top / bottom) ** (1/4)
    return round(Bare_Temperature_K - 273.15, 2)

def BodyAlbedo(Atmo_Composition, Body_Type, Atmo_Class):
    if Atmo_Composition is None:
        return 0.12
    gas_albedo = {
        "H₂": 0.40, "He": 0.10, "CH₄": 0.45, "NH₃": 0.50,
        "H₂O": 0.65, "N₂": 0.05, "O₂": 0.05, "CO₂": 0.40, "SO₂": 0.55,
    }
    albedo = sum(data["value"] * gas_albedo.get(formula, 0.1) for formula, data in Atmo_Composition.items())
    if Atmo_Class == "Thick":
        albedo *= 1.4
    elif Atmo_Class == "Thin":
        albedo *= 0.6
    return round(max(0.05, min(albedo, 0.85)), 4)

def BodyGreenhouseFactor(Atmo_Composition, Surface_Pressure):
    if Atmo_Composition is None or Surface_Pressure <= 0:
        return 1.0
    gas_greenhouse = {
        "H₂": 0.0, "He": 0.0, "CH₄": 30.0, "NH₃": 8.0,
        "H₂O": 3.5, "N₂": 0.0, "O₂": 0.0, "CO₂": 1.5, "SO₂": 0.5,
    }
    greenhouse_opacity = sum(data["value"] * gas_greenhouse.get(formula, 0.0) for formula, data in Atmo_Composition.items())
    pressure_factor = max(0.0, 1.0 + math.log10(max(Surface_Pressure, 0.001)))
    greenhouse_multiplier = min(1.0 + 0.12 * greenhouse_opacity * pressure_factor, 3.5)
    return round(greenhouse_multiplier, 4)

def BodyCorrectedTemperature(Star_Lo, Body_SMA, Albedo, Greenhouse_Multiplier, Tidal_Heat_Flux=0.0):
    """Equilibrium temperature with albedo, greenhouse, and optional tidal heat flux.
    Tidal_Heat_Flux in W/m² is added to the stellar flux before equilibrium solve."""
    Body_SMA_m = Body_SMA * 1.496e11
    Star_Lo_W = Star_Lo * 3.84e26
    SBSigma = 5.67e-8
    stellar_flux = Star_Lo_W * (1 - Albedo) / ((16 * math.pi * SBSigma) * (Body_SMA_m**2))
    # Tidal flux enters as additional internal heat source, also modulated by albedo
    tidal_contribution = (Tidal_Heat_Flux * (1 - Albedo)) / (4 * SBSigma) if Tidal_Heat_Flux > 0 else 0.0
    Equilibrium_K = (stellar_flux + tidal_contribution) ** (1/4)
    Corrected_K = Equilibrium_K * Greenhouse_Multiplier
    return round(Corrected_K - 273.15, 2)

def BodyAtmospherics(key, Dynamo_Factor, Body_SurfaceGravity, Body_Radius, Star_R, Star_T, Body_SMA, Star_Lo, Body_Type, Body_Mass, index, Body_Subclass=None, Subclass_Data=None, Tidal_Heat_Flux=0.0, seed_suffix=""):
    random.seed(key + str(index))
    SBSigma = 5.67e-8
    Re = 6378  # km
    Body_SMA_km = Body_SMA * 1.496e8
    Body_Irradiance = round(((Star_R**2 * SBSigma * Star_T**4) / (Body_SMA_km**2)), 3)
    Bare_Temperature = BodyBareTemperature(Star_Lo, Body_SMA)

    if Dynamo_Factor >= 0.3:
        Body_Atmosphere = True
        Atmo_Class = "Thick"
        k = 1.5
    elif Dynamo_Factor >= 0.2:
        Body_Atmosphere = True
        Atmo_Class = "Thin"
        k = 0.5
    else:
        Body_Atmosphere = False
        Atmo_Class = "None"
        k = 0

    if Body_Atmosphere:
        Body_ExosphereRadius = Body_Radius * (1 + k * (Dynamo_Factor / Body_SurfaceGravity))
        Body_ExosphereAltitude = Body_ExosphereRadius - Body_Radius
        Body_AtmosphereVolume = f"{((4/3)*math.pi*((Body_ExosphereRadius*Re)**3)) - ((4/3)*math.pi*((Body_Radius*Re)**3)):e}"
    else:
        Body_ExosphereRadius = Body_ExosphereAltitude = Body_AtmosphereVolume = 0

    if Body_Atmosphere:
        Atmo_Composition, Atmosphere_Type = BodyAtmosphereComposition(
            key, Body_Type, Body_Mass, Body_Radius, Body_SurfaceGravity,
            Dynamo_Factor, Bare_Temperature, Body_SMA, index,
            Body_Subclass, Subclass_Data, seed_suffix
        )
    else:
        Atmo_Composition = None
        Atmosphere_Type = "None"

    if Body_Atmosphere and Atmo_Composition is not None:
        AMF = BodyAtmosphereMassFraction(key, Body_Type, Atmo_Class, Dynamo_Factor, Body_Mass, Body_SurfaceGravity, index, seed_suffix)
        # Super-Earths have stronger outgassing — boost AMF from subclass data
        if Body_Subclass == "super_earth" and Subclass_Data is not None:
            AMF *= Subclass_Data.get("amf_multiplier", 1.0)
            AMF = min(AMF, 0.01)
        Mean_Mol_Weight = BodyMeanMolecularWeight(Atmo_Composition)
        Surface_Pressure = BodySurfacePressureCalculation(Body_Mass, Body_Radius, Body_SurfaceGravity, AMF)
        Atmo_Mass_kg = AMF * Body_Mass * 5.972e24
    else:
        AMF = Mean_Mol_Weight = Surface_Pressure = Atmo_Mass_kg = 0

    Body_Albedo = BodyAlbedo(Atmo_Composition, Body_Type, Atmo_Class)
    Greenhouse_Multiplier = BodyGreenhouseFactor(Atmo_Composition, Surface_Pressure)
    Corrected_Temperature = BodyCorrectedTemperature(Star_Lo, Body_SMA, Body_Albedo, Greenhouse_Multiplier, Tidal_Heat_Flux)

    if Body_Atmosphere and Mean_Mol_Weight > 0:
        R = 8.314
        Corrected_T_K = Corrected_Temperature + 273.15
        R_specific = R / (Mean_Mol_Weight / 1000)
        Scale_Height_km = R_specific * max(Corrected_T_K, 10.0) / Body_SurfaceGravity / 1000
        Surface_Density = (Surface_Pressure * 101325) / (R_specific * max(Corrected_T_K, 10.0))
    else:
        Scale_Height_km = Surface_Density = 0

    return {
        "Has_Atmosphere": Body_Atmosphere,
        "Atmosphere_Class": {"value": Atmo_Class},
        "Atmosphere_Type": {"value": Atmosphere_Type},
        "Composition": Atmo_Composition,
        "Mean_Molecular_Weight": {"value": Mean_Mol_Weight if Body_Atmosphere else "NONE", "unit": "u"},
        "Atmosphere_Mass_Fraction": {"value": round(AMF, 8) if Body_Atmosphere else "NONE", "unit": "fraction"},
        "Atmosphere_Mass": {"value": f"{Atmo_Mass_kg:.4e}" if Body_Atmosphere else "NONE", "unit": "kg"},
        "Surface_Pressure": {"value": "N/A", "unit": "atm"} if Body_Type == "giant" else {"value": round(Surface_Pressure, 4) if Body_Atmosphere else 0, "unit": "atm"},
        "Albedo": {"value": Body_Albedo},
        "Greenhouse_Multiplier": {"value": Greenhouse_Multiplier},
        "Scale_Height": {"value": round(Scale_Height_km, 2) if Body_Atmosphere else "NONE", "unit": "km"},
        "Surface_Density": {"value": round(Surface_Density, 4) if Body_Atmosphere else "NONE", "unit": "kg/m^3"},
        "Exosphere_Radius": {"value": round(Body_ExosphereRadius, 3) if Body_Atmosphere else "NONE", "unit": "Re"},
        "Exosphere_Height": {"value": round(Body_ExosphereAltitude, 3) if Body_Atmosphere else "NONE", "unit": "Re"},
        "Atmosphere_Volume": {"value": Body_AtmosphereVolume if Body_Atmosphere else "NONE", "unit": "km^3"},
        "Irradiance": {"value": Body_Irradiance, "unit": "W/m^2"},
        "Bare_Temperature": {"value": Bare_Temperature, "unit": "C"},
        "Surface_Temperature": {"value": Corrected_Temperature, "unit": "C"}
    }
