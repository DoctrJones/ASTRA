import json, random, math

with open("Model_Data.json", "r", encoding="utf-8") as f:
    Model = json.load(f)["atmosphere"]

# Gas properties (Model_Data atmosphere.gases). Order matters: draws happen in this order.
GAS_TABLE = Model["gases"]

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
    JEANS_FACTOR = Model["jeans_factor"]
    strip = Model["stellar_stripping"]
    comp = Model["composition"]
    retained_gases = []
    for gas in GAS_TABLE:
        if Body_Type not in gas["zones"]:
            continue
        V_thermal = BodyThermalVelocity(gas["mol_mass"], temperature_K)
        if V_escape < JEANS_FACTOR * V_thermal:
            continue
        if Body_SMA < strip["sma_au"] and gas["mol_mass"] < strip["light_gas_mol_mass"]:
            strip_chance = strip["max_chance"] * (1.0 - Body_SMA / strip["sma_au"])
            strip_chance *= max(strip["min_exposure"], 1.0 - Dynamo_Factor * strip["dynamo_shielding"])
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
        weight = gas["abundance"] * random.uniform(*comp["abundance_jitter"])

        if Body_Type == "giant":
            if subclass_weights is not None:
                # Apply subclass-specific weight from Planet_Data.json.
                # This replaces the old hardcoded 3x H2/He multiplier and
                # fixes the He/H2 dominance inversion bug.
                gas_override = subclass_weights.get(gas["name"], None)
                if gas_override is not None:
                    weight = gas_override * random.uniform(*comp["giant_weight_jitter"])
            else:
                # Legacy fallback if no subclass data — retain old behaviour
                if gas["name"] in ["H2", "He"]:
                    weight *= comp["legacy_giant_h2_he_boost"]
        elif Body_Type == "rocky" and gas["name"] in ["N2", "CO2"]:
            weight *= comp["rocky_n2_co2_base"] + comp["rocky_n2_co2_dynamo"] * max(0.0, Dynamo_Factor)

        if gas["name"] in ["CH4", "NH3"] and temperature_K < comp["cold_below_k"]:
            weight *= comp["cold_ch4_nh3_factor"]
        elif gas["name"] in ["CH4", "NH3"] and temperature_K > comp["hot_above_k"]:
            weight *= comp["hot_ch4_nh3_factor"]

        fractions[gas["name"]] = weight

    total = sum(fractions.values())
    for gas_name in fractions:
        fractions[gas_name] = round(fractions[gas_name] / total, 4)

    dominant = max(fractions, key=fractions.get)
    sorted_gases = sorted(fractions.items(), key=lambda x: x[1], reverse=True)
    gas_lookup = {g["name"]: g["formula"] for g in GAS_TABLE}

    if len(sorted_gases) >= 2 and sorted_gases[1][1] > comp["secondary_gas_label_min"]:
        Atmosphere_Type = gas_lookup[sorted_gases[0][0]] + "/" + gas_lookup[sorted_gases[1][0]]
    else:
        Atmosphere_Type = gas_lookup[dominant] + "-dominant"

    Composition = {}
    for gas_name, frac in sorted_gases:
        Composition[gas_lookup[gas_name]] = {"value": frac, "unit": "fraction"}

    return Composition, Atmosphere_Type

def BodyAtmosphereMassFraction(key, Body_Type, Atmo_Class, Dynamo_Factor, Body_Mass, Body_SurfaceGravity, index, seed_suffix=""):
    random.seed(key + str(index) + "amf" + seed_suffix)
    amf = Model["mass_fraction"]
    if Body_Type == "giant":
        base = random.uniform(*amf["giant_range"])
        mass_boost = amf["giant_mass_boost"] * math.log10(max(Body_Mass, amf["giant_mass_floor"]))
        return min(base + mass_boost, amf["giant_max"])
    g_ratio = Body_SurfaceGravity / 9.81
    if Atmo_Class == "Thick":
        base_log_min, base_log_max = amf["thick_log_range"]
    else:
        base_log_min, base_log_max = amf["thin_log_range"]
    g_shift = amf["gravity_shift"] * math.log10(max(g_ratio, amf["gravity_ratio_floor"]))
    log_min = base_log_min + g_shift
    log_max = base_log_max + g_shift
    range_center = (log_min + log_max) / 2.0
    range_half = (log_max - log_min) / 2.0
    narrowing = amf["narrowing"]
    log_min = range_center - range_half * narrowing
    log_max = range_center + range_half * narrowing
    if g_ratio < amf["low_gravity_ratio"]:
        range_width = log_max - log_min
        log_max = log_min + range_width * amf["low_gravity_range_keep"]
    log_AMF = random.uniform(log_min, log_max)
    AMF = 10 ** log_AMF
    AMF *= (1.0 + amf["dynamo_boost"] * max(0.0, Dynamo_Factor - amf["dynamo_offset"]))
    AMF *= (1.0 + amf["mass_boost"] * math.log10(max(Body_Mass / 1.0, amf["mass_floor"])))
    AMF = min(AMF, amf["max"])
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
    params = Model["albedo"]
    if Atmo_Composition is None:
        return params["no_atmosphere"]
    gas_albedo = {g["formula"]: g["albedo"] for g in GAS_TABLE}
    albedo = sum(data["value"] * gas_albedo[formula] for formula, data in Atmo_Composition.items())
    if Atmo_Class == "Thick":
        albedo *= params["thick_multiplier"]
    elif Atmo_Class == "Thin":
        albedo *= params["thin_multiplier"]
    return round(max(params["range"][0], min(albedo, params["range"][1])), 4)

def BodyGreenhouseFactor(Atmo_Composition, Surface_Pressure):
    if Atmo_Composition is None or Surface_Pressure <= 0:
        return 1.0
    params = Model["greenhouse"]
    gas_greenhouse = {g["formula"]: g["greenhouse"] for g in GAS_TABLE}
    greenhouse_opacity = sum(data["value"] * gas_greenhouse[formula] for formula, data in Atmo_Composition.items())
    pressure_factor = max(0.0, 1.0 + math.log10(max(Surface_Pressure, params["pressure_floor"])))
    greenhouse_multiplier = min(1.0 + params["coefficient"] * greenhouse_opacity * pressure_factor, params["max"])
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

    classes = Model["classes"]
    if Dynamo_Factor >= classes["thick_min_dynamo"]:
        Body_Atmosphere = True
        Atmo_Class = "Thick"
        k = classes["thick_exosphere_k"]
    elif Dynamo_Factor >= classes["thin_min_dynamo"]:
        Body_Atmosphere = True
        Atmo_Class = "Thin"
        k = classes["thin_exosphere_k"]
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
            AMF = min(AMF, Model["mass_fraction"]["max"])
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
