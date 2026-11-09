import json, random, math
from .config import project_path
from .tectonics import TectonicVolcanicActivity

with open(project_path("Model_Data.json"), "r", encoding="utf-8") as f:
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

GAS_BY_NAME = {g["name"]: g for g in GAS_TABLE}
FORMULA = {g["name"]: g["formula"] for g in GAS_TABLE}

def _sig(x, digits=4):
    """Round to significant figures (trace gases need ppm/ppb precision)."""
    return float(f"{x:.{digits}g}")

# ---------------------------------------------------------------------------
# Which gases a body can hold (escape)
# ---------------------------------------------------------------------------

def BodyGasRetention(key, Body_Type, Body_Mass, Body_Radius, Dynamo_Factor, Bare_Temperature, Body_Irradiance, Body_SMA, index, Subclass_Data=None, seed_suffix=""):
    """Names of the gases the body can keep: allowed for its body type (zones), slow enough
    to survive thermal (Jeans) escape, and not stripped by the star.

    Escape is judged at the exosphere temperature, which starlight heats far above the surface
    (Earth ~1000 K). It scales with irradiance, so Earth loses H2 and He while cold Titan keeps N2."""
    random.seed(key + str(index) + "atmo" + seed_suffix)
    esc = Model["escape"]
    exo_K = max(Bare_Temperature + 273.15,
                esc["exosphere_K_at_earth"] * (max(Body_Irradiance, 0.0) / esc["earth_irradiance"]) ** esc["exosphere_irradiance_exponent"],
                10.0)
    V_escape = BodyEscapeVelocity(Body_Mass, Body_Radius)
    strip = Model["stellar_stripping"]
    retained = []
    for gas in GAS_TABLE:
        if Body_Type not in gas["zones"]:
            continue
        if V_escape < Model["jeans_factor"] * BodyThermalVelocity(gas["mol_mass"], exo_K):
            continue
        if Body_SMA < strip["sma_au"] and gas["mol_mass"] < strip["light_gas_mol_mass"]:
            strip_chance = strip["max_chance"] * (1.0 - Body_SMA / strip["sma_au"])
            strip_chance *= max(strip["min_exposure"], 1.0 - Dynamo_Factor * strip["dynamo_shielding"])
            # Sub-Earths (< 0.1 Me terrestrial) are more vulnerable to stripping
            if Body_Type == "rocky" and Subclass_Data is not None and Body_Mass < Subclass_Data.get("sub_earth_threshold", 0.1):
                strip_chance = min(1.0, strip_chance + Subclass_Data.get("sub_earth_strip_bonus", 0.3))
            if random.random() < strip_chance:
                continue
        retained.append(gas["name"])
    return retained

# ---------------------------------------------------------------------------
# Planet-level volatile geochemistry (drawn once per body)
# ---------------------------------------------------------------------------

def BodyGeochemistry(key, index, Body_Type, Body_Mass, Body_SMA, Star_Metallicity, Star_IceLine, Star_T,
                     Dynamo_Factor, Tidal_Heat_Flux, Bare_Temperature, seed_suffix="", Atmo_Class="Thick"):
    """Volatile traits that decide what a rocky world, dwarf or moon outgasses.

    - C/O ratio rises with stellar metallicity (Nissen 2014); above carbon_rich_above the world is
      carbon-rich, with a more reduced mantle and more carbon.
    - Mantle redox (delta-IW) decides oxidised (CO2, H2O, SO2) vs reduced (H2, CO, CH4, H2S)
      outgassing (Ortenzi et al. 2020).
    - C, N, S inventories scale with metallicity; water depends on forming beyond the ice line.
    - Outgassing strength follows the volcanism tier and peaks at 2-4 Earth masses (Ortenzi et al.
      2020); tidal heating drives sulfur volcanism (Io).
    - Massive super-Earths may keep a primordial H2/He envelope; ocean worlds of M dwarfs may build
      abiotic O2 from water loss (Luger & Barnes 2015, debated).
    Every random draw happens unconditionally, in a fixed order, so the stream is stable."""
    random.seed(key + str(index) + "geochem" + seed_suffix)
    gc = Model["geochemistry"]
    feh = max(-1.0, min(1.0, Star_Metallicity or 0.0))

    co = gc["c_to_o"]
    c_to_o = random.gauss(co["solar"] + co["metallicity_slope"] * feh, co["scatter"])
    carbon_rich = c_to_o >= co["carbon_rich_above"]

    rd = gc["redox"]
    redox = random.gauss(rd["mean_dIW"], rd["sigma_dIW"]) + (rd["carbon_rich_shift"] if carbon_rich else 0.0)
    redox = max(rd["range"][0], min(rd["range"][1], redox))

    metal = 10 ** (gc["metallicity_exponent"] * feh)
    inventory = {el: metal * 10 ** random.gauss(0.0, gc["inventory_scatter_dex"]) for el in ("C", "N", "S")}
    inventory["C"] *= (max(c_to_o, 0.05) / co["solar"]) ** co["carbon_exponent"]

    wt = gc["water"]
    beyond_ice_line = Star_IceLine is not None and Body_SMA >= Star_IceLine
    oceans = (wt["beyond_ice_line_oceans"] if beyond_ice_line else wt["inside_ice_line_oceans"]) * 10 ** random.gauss(0.0, wt["scatter_dex"])
    if beyond_ice_line:
        inventory["N"] *= gc["beyond_ice_line_nitrogen"]   # accreted as ammonia ice (Titan's N2)

    og = gc["outgassing"]
    volcanism = TectonicVolcanicActivity(Dynamo_Factor, Body_Mass, Body_SMA) if Body_Type == "rocky" else "None"
    peak = math.log(og["mass_peak_me"])
    mass_factor = math.exp(-(math.log(max(Body_Mass, 1e-4)) - peak) ** 2 / (2 * og["mass_width_ln"] ** 2)) / \
                  math.exp(-peak ** 2 / (2 * og["mass_width_ln"] ** 2))
    outgassing = og["by_volcanism"][volcanism] * mass_factor
    # Strong tidal heating drives sulfur volcanism and boils off carbon, nitrogen and water (Io)
    tidal = max(Tidal_Heat_Flux, 0.0)
    tidal_sulfur = 1.0 + tidal / og["tidal_sulfur_flux"]
    depletion = 1.0 / (1.0 + tidal / og["tidal_depletion_flux"])
    inventory["C"] *= depletion
    inventory["N"] *= depletion
    oceans *= depletion

    env = gc["primordial_envelope"]
    roll_envelope = random.random()
    p_envelope = 1.0 / (1.0 + math.exp(-(math.log10(max(Body_Mass, 1e-4)) - math.log10(env["half_mass_me"])) / env["width_dex"]))
    envelope = Body_Type == "rocky" and roll_envelope < p_envelope

    ao = gc["abiotic_oxygen"]
    roll_o2 = random.random()
    o2_size = 10 ** random.uniform(*ao["log_weight_range"])
    abiotic_o2 = (Star_T < ao["star_below_K"] and oceans >= ao["min_oceans"]
                  and Bare_Temperature + 273.15 >= ao["min_bare_K"] and roll_o2 < ao["chance"])

    # Share of the outgassed atmosphere still held today: worlds with a weak dynamo ("Thin") have
    # lost most of theirs to the stellar wind (Mars ~1%); others keep it, with scatter.
    rt = gc["retention"]
    roll_thick = random.gauss(0.0, rt["thick_sigma_dex"])
    roll_thin = random.uniform(*rt["thin_log_range"])
    retention = 10 ** (roll_thin if Atmo_Class == "Thin" else roll_thick)

    return {
        "c_to_o": c_to_o, "carbon_rich": carbon_rich, "redox": redox,
        "inventory": inventory, "oceans": oceans, "beyond_ice_line": beyond_ice_line,
        "volcanism": volcanism, "outgassing": outgassing, "tidal_sulfur": tidal_sulfur,
        "envelope": envelope, "abiotic_o2": o2_size if abiotic_o2 else 0.0,
        "retention": retention,
    }

def BodyGiantMix(key, index, Subclass_Data, Star_Metallicity, seed_suffix=""):
    """Giant atmosphere weights: the subclass's observed mix (Planet_Data gas_table_weights,
    Jupiter / Neptune), heavy species scaled by stellar metallicity, with scatter."""
    random.seed(key + str(index) + "atmo_mix" + seed_suffix)
    comp = Model["composition"]
    feh = max(-1.0, min(1.0, Star_Metallicity or 0.0))
    weights = {}
    for name, w in (Subclass_Data or {}).get("gas_table_weights", {}).items():
        if name in ("H2", "He"):
            weights[name] = w * random.uniform(*comp["giant_weight_jitter"])
        else:
            weights[name] = w * 10 ** (comp["giant_metallicity_exponent"] * feh + random.gauss(0.0, comp["giant_heavy_scatter_dex"]))
    return weights

# ---------------------------------------------------------------------------
# Composition at a given surface temperature (called inside the climate loop)
# ---------------------------------------------------------------------------

def _saturation_atm(gas, T_K):
    """Clausius-Clapeyron saturation pressure (atm) from the gas's 1-atm boiling/frost point."""
    cond = gas.get("condense")
    if not cond:
        return float("inf")
    return math.exp(cond["latent_kJ"] * 1000 / 8.314 * (1 / cond["boil_K"] - 1 / max(T_K, 1.0)))

def _water_saturation_atm(T_K):
    """Saturation vapour pressure of water (atm): over ice below 273 K, over liquid above."""
    if T_K >= 647.0:
        return float("inf")           # above the critical point there is no liquid
    if T_K < 273.15:
        return 6.112e-3 / 1.01325 * math.exp(22.46 * (T_K - 273.15) / (T_K - 0.53))
    if T_K < 373.15:
        return 6.112e-3 / 1.01325 * math.exp(17.67 * (T_K - 273.15) / (T_K - 29.65))
    return math.exp(40700 / 8.314 * (1 / 373.15 - 1 / T_K))

def _ocean_vapour_atm(oceans, Body_Mass, Body_Radius, Body_SurfaceGravity):
    """Surface pressure (atm) the body's whole water inventory would make as vapour."""
    mass_kg = oceans * Model["geochemistry"]["water"]["earth_ocean_kg"] * Body_Mass
    area = 4 * math.pi * (Body_Radius * 6.371e6) ** 2
    return mass_kg * Body_SurfaceGravity / area / 101325

def BodyGasComposition(Body_Type, retained, traits, Surface_Temperature_K, Surface_Pressure,
                       Body_Mass, Body_Radius, Body_SurfaceGravity, Haze_Index, Absorbed_Flux=0.0, Pressure_Scale=1.0):
    """Mole fractions {name: x} for the current surface temperature, plus climate flags.

    Rocky worlds: outgassed sources (geochemistry) -> sinks (photochemistry, weathering, rainout)
    -> partial pressures (Pressure_Scale atm per source unit) -> condensation caps -> water vapour
    from humidity. Surface_Pressure is the previous estimate (liquid water and sulfur speciation);
    the new total is flags["pressure_atm"]. An ocean world absorbing more than the runaway limit
    cannot keep liquid water: its whole ocean becomes steam. Giants: their fixed mix."""
    flags = {"liquid_ocean": False, "weathering": False, "frozen_out": False, "steam": False,
             "runaway": False, "vapour_atm": 0.0, "pressure_atm": Surface_Pressure}
    if Body_Type == "giant":
        w = {n: v for n, v in traits.items() if n in retained}
        total = sum(w.values()) or 1.0
        return {n: v / total for n, v in w.items() if v > 0}, flags

    gc = Model["geochemistry"]; src = gc["sources"]; wt = gc["water"]
    T = Surface_Temperature_K
    P = max(Surface_Pressure, 1e-9)
    inv = traits["inventory"]
    ox = 1.0 / (1.0 + math.exp(-(traits["redox"] - src["oxidised_mid_dIW"]) / src["oxidised_width_dIW"]))
    red = 1.0 - ox
    out = gc["outgassing"]["background"] + traits["outgassing"]

    has_ocean = traits["oceans"] >= wt["ocean_min_oceans"]
    runaway = has_ocean and "H2O" in retained and Absorbed_Flux >= wt["runaway_flux"]
    liquid = has_ocean and not runaway and 273.15 <= T < 647.0 and _water_saturation_atm(T) < P
    flags["liquid_ocean"] = liquid
    flags["runaway"] = runaway

    # Carbonate-silicate thermostat: weathering on liquid-water worlds draws CO2 down, harder when warm
    # Fades continuously to nothing at freezing, so CO2 builds up as a world cools instead of jumping.
    weathering = 1.0
    if has_ocean and not runaway:
        wc = gc["weathering"]
        weathering = wc["at_reference"] ** ((T - wc["frozen_K"]) / (wc["reference_K"] - wc["frozen_K"]))
        if traits["oceans"] >= wt["waterworld_oceans"]:
            weathering *= wc["waterworld_factor"]      # no exposed land: weak regulation
        weathering = min(1.0, weathering)
        flags["weathering"] = weathering < 1.0
    # Soluble gases: rained out in days on wet worlds, deposited on ice on frozen ocean worlds,
    # long-lived on dry worlds (Venus)
    rain = src["rainout"] if liquid else (src["icy_deposition"] if has_ocean else 1.0)
    methane_share = 1.0 / (1.0 + math.exp((T - src["methane_below_K"]) / src["methane_width_K"]))
    ammonia_share = src["ammonia_max_share"] * red ** 2 / (1.0 + math.exp((T - src["ammonia_below_K"]) / src["ammonia_width_K"]))
    shielded = Haze_Index >= Model["greenhouse"]["shortwave"]["haze"]["present_threshold"]
    ammonia_survival = 1.0 if shielded else src["ammonia_photolysis"]
    so2_share = ox / (1.0 + P / src["sulfur_pressure_atm"])

    # Reduced gases (CH4, CO, H2, H2S, NH3) last decades in an oxidising atmosphere but geological
    # times in a reducing one: survival = 10^(-reduced_gas_lifetime_dex x ox). What is destroyed is
    # oxidised: carbon to CO2 (then weathered), H2S to SO2 (then rained out).
    survive = 10 ** (-src["reduced_gas_lifetime_dex"] * ox)
    C = inv["C"] * src["carbon"] * out
    N = inv["N"] * src["nitrogen"]
    S = inv["S"] * src["sulfur"] * traits["outgassing"] * traits["tidal_sulfur"]
    w = {
        "N2":  N * (1.0 - ammonia_share * survive),
        "NH3": N * ammonia_share * survive * ammonia_survival * (src["rainout"] if liquid else 1.0),   # freezes out instead (cap)
        "CO2": C * (ox + red * (1.0 - survive)) * weathering,
        "CO":  C * red * (1.0 - methane_share) * survive,
        "CH4": C * red * methane_share * survive,
        "H2":  traits["oceans"] * src["hydrogen"] * out * red * survive,
        "SO2": S * (so2_share + (1.0 - so2_share) * (1.0 - survive)) * rain,
        "H2S": S * (1.0 - so2_share) * survive * rain,
        "O2":  src["oxygen_trace"] * ox + traits["abiotic_o2"],
        "H2O": 0.0,
        "He":  0.0,
    }
    if traits["envelope"]:
        w["H2"] += src["envelope_h2"]
        w["He"] += src["envelope_he"]
    if not has_ocean:
        w["H2O"] = traits["oceans"] * src["water_outgassed"] * out * ox
    w = {n: v for n, v in w.items() if n in retained and v > 0}

    # Partial pressures (atm): source weights x Pressure_Scale (Earth-like N2 weight 1 -> ~0.78 atm,
    # scaled by planet mass and gravity, times how much atmosphere the world has kept).
    p = {n: v * Pressure_Scale for n, v in w.items()}
    source_total = sum(p.values())
    crh = wt["column_factor"] * wt["relative_humidity"]

    # Condensation: a gas cannot exceed its saturation pressure. Trace condensables thin out with
    # height like water vapour (column humidity crh); a gas that makes up most of the air is
    # buffered at its full saturation pressure (Mars' CO2 against its polar caps).
    for n in list(p):
        sat = _water_saturation_atm(T) if n == "H2O" else _saturation_atm(GAS_BY_NAME[n], T)
        share = p[n] / source_total if source_total > 0 else 0.0
        p[n] = min(p[n], sat * max(crh, share))
    dry_total = sum(p.values())
    flags["frozen_out"] = source_total > 0 and dry_total < wt["frozen_out_fraction"] * source_total

    # Water vapour on ocean worlds: humidity at the surface temperature (column average, Earth 0.4%),
    # rising to full saturation once vapour outweighs the other gases, limited by the ocean.
    # A runaway puts the whole ocean in the air (Venus-like steam atmosphere).
    if has_ocean and "H2O" in retained:
        vapour = _ocean_vapour_atm(traits["oceans"], Body_Mass, Body_Radius, Body_SurfaceGravity)
        if runaway:
            p_water = vapour
            flags["vapour_atm"] = vapour
        else:
            e_sat = _water_saturation_atm(T)
            if e_sat == float("inf"):
                p_water = vapour
            else:
                p_water = min(vapour, e_sat * max(crh, e_sat / (e_sat + dry_total)))
        p["H2O"] = p.get("H2O", 0.0) + p_water

    total = sum(p.values())
    flags["pressure_atm"] = total
    if total <= 0:
        return {}, flags
    fractions = {n: v / total for n, v in p.items() if v > 0}
    flags["steam"] = fractions.get("H2O", 0.0) >= wt["steam_fraction"]
    return fractions, flags

def _composition_output(fractions):
    """{formula: {"value", "unit"}} sorted by abundance, dropping sub-ppb traces; and the type label."""
    floor = Model["composition"]["trace_floor"]
    items = sorted(((n, v) for n, v in fractions.items() if v >= floor), key=lambda kv: kv[1], reverse=True)
    if not items:
        return None, "None"
    if len(items) >= 2 and items[1][1] > Model["composition"]["secondary_gas_label_min"]:
        label = FORMULA[items[0][0]] + "/" + FORMULA[items[1][0]]
    else:
        label = FORMULA[items[0][0]] + "-dominant"
    return {FORMULA[n]: {"value": _sig(v), "unit": "fraction"} for n, v in items}, label

def BodyAtmosphereTraits(Body_Type, traits, fractions, flags, Haze_Index, Surface_Temperature_K):
    """Short descriptive tags for unusual or notable atmospheres."""
    if Body_Type == "giant" or traits is None:
        return []
    t = Model["geochemistry"]["trait_thresholds"]
    tags = []
    if traits["carbon_rich"]:                                       tags.append("Carbon-rich")
    if traits["redox"] <= t["reduced_dIW"]:                         tags.append("Reduced mantle")
    if traits["envelope"] and fractions.get("H2", 0) >= t["gas"]:   tags.append("Primordial hydrogen envelope")
    if flags["runaway"]:                                            tags.append("Runaway greenhouse")
    if flags["steam"]:                                              tags.append("Steam atmosphere")
    if traits["oceans"] >= Model["geochemistry"]["water"]["waterworld_oceans"] and not flags["runaway"]:
        tags.append("Water world")
    if flags["liquid_ocean"]:                                       tags.append("Liquid surface water")
    if flags["weathering"] and Surface_Temperature_K < 373.15:      tags.append("Carbonate-silicate regulated")
    if traits["oceans"] >= Model["geochemistry"]["water"]["ocean_min_oceans"] and Surface_Temperature_K < t["snowball_K"]:
        tags.append("Ice-covered")
    if fractions.get("O2", 0) >= t["gas"]:                          tags.append("Abiotic oxygen")
    if fractions.get("SO2", 0) + fractions.get("H2S", 0) >= t["sulfur"]: tags.append("Sulfur volcanism")
    if fractions.get("NH3", 0) >= t["gas"]:                         tags.append("Ammonia-rich")
    if fractions.get("CH4", 0) >= t["gas"]:                         tags.append("Methane-rich")
    if Haze_Index >= Model["greenhouse"]["shortwave"]["haze"]["present_threshold"]: tags.append("Organic haze")
    if flags["frozen_out"]:                                         tags.append("Frost-buffered atmosphere")
    return tags

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

def BodyAlbedo(fractions, Body_Type, Surface_Pressure=0.0, Surface_Temperature_K=288.0, Haze_Index=0.0, Has_Ocean=False):
    """Bond albedo from its main physical sources rather than per-gas weights:
    surface (rock, or ice on a frozen ocean world), Rayleigh scattering (grows with pressure),
    water clouds (temperate worlds with vapour), sulfate clouds (SO2 with water, as on Venus)
    and organic haze. Giants use a fixed value (Jupiter-Neptune range)."""
    params = Model["albedo"]
    if Body_Type == "giant":
        return params["giant"]
    if not fractions:
        return params["surface"]
    T = Surface_Temperature_K
    albedo = params["ice_surface"] if (Has_Ocean and T < params["ice_below_K"]) else params["surface"]
    albedo += params["rayleigh_max"] * (1 - math.exp(-max(Surface_Pressure, 0.0) / params["rayleigh_scale_atm"]))
    water = fractions.get("H2O", 0.0)
    lo, hi = params["water_cloud_K"]
    if water > 0 and lo <= T <= hi:
        albedo += params["water_clouds"] * min(1.0, water / params["water_cloud_ref_fraction"])
    if T >= params["sulfate_min_K"]:
        # Sulfuric acid clouds need columns of both SO2 and water (Venus: 150 ppm SO2, 30 ppm H2O at 92 bar)
        P = max(Surface_Pressure, 0.0)
        albedo += params["sulfate_clouds"] * min(1.0, fractions.get("SO2", 0.0) * P / params["sulfate_ref_atm"]) \
                                           * min(1.0, water * P / params["sulfate_water_ref_atm"])
    albedo = min(albedo, params["range"][1])
    # An organic haze layer hides what lies beneath it (Titan: Bond albedo ~0.27)
    albedo = (1 - Haze_Index) * albedo + Haze_Index * params["haze"]
    return round(max(params["range"][0], min(albedo, params["range"][1])), 4)

# ---------------------------------------------------------------------------
# Greenhouse effect: Robinson & Catling (2012) gray radiative-convective model
# (their "simplest" case, Section 2.6: no shortwave absorption, no internal heat).
# Settings and calibration notes: Model_Data atmosphere.greenhouse.
# ---------------------------------------------------------------------------

def _scaled_upper_gamma(s, x):
    """e^x * upper incomplete gamma(s, x). Scaled so it stays finite for large x."""
    if x <= 0:
        return math.gamma(s)
    if x < s + 1:
        # Series for the lower incomplete gamma, then Gamma(s) - lower
        term = total = 1.0 / s
        a = s
        for _ in range(500):
            a += 1
            term *= x / a
            total += term
            if term < total * 1e-15:
                break
        return math.exp(x) * math.gamma(s) - x ** s * total
    # Continued fraction (modified Lentz) for the upper incomplete gamma
    tiny = 1e-300
    b = x + 1 - s
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - s)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return x ** s * h

def _planck_fraction_above(x):
    """Fraction of blackbody flux at wavenumbers above x = c2 * nu / T (Widger & Woodall series)."""
    if x <= 0:
        return 1.0
    total = 0.0
    for n in range(1, 400):
        term = math.exp(-n * x) / n * (x**3 + 3 * x**2 / n + 6 * x / n**2 + 6 / n**3)
        total += term
        if term < 1e-12 * total:
            break
    return min(1.0, 15 / math.pi**4 * total)

def PlanckBandFraction(T, bands_cm):
    """Fraction of a T-kelvin blackbody's flux inside the given wavenumber bands [[lo, hi], ...] (cm^-1)."""
    if T <= 0:
        return 0.0
    c2 = 1.4388  # second radiation constant, cm K
    return sum(_planck_fraction_above(c2 * lo / T) - _planck_fraction_above(c2 * hi / T) for lo, hi in bands_cm)

def _gas_fractions(Atmo_Composition):
    """{gas name: mole fraction} from a {formula: {"value": x}} composition."""
    name_of = {g["formula"]: g["name"] for g in GAS_TABLE}
    return {name_of[f]: d["value"] for f, d in Atmo_Composition.items()}

def _column_atm(Surface_Pressure, Body_SurfaceGravity):
    """Atmospheric column in Earth-gravity atm (same pressure on a low-g world = more gas)."""
    return Surface_Pressure * Model["greenhouse"]["earth_gravity"] / max(Body_SurfaceGravity, 0.01)

def GreenhouseOpticalDepth(Atmo_Composition, Surface_Pressure, Body_SurfaceGravity, Emission_Temperature):
    """Gray infrared optical depth at the surface (tau0): line absorption + collision-induced absorption.

    Lines: each gas adds ir_strength x ln(1 + sqrt(u_eff / ir_saturation_atm)). u_eff is the
    gas's column in Earth-gravity atm, weighted by (P / 1 atm)^pressure_scaling for line
    broadening. Square root at small amounts, logarithmic at large ones.

    Collisions (CIA): each pair adds strength x x_a x x_b x P x column x (share of the
    planet's thermal emission inside the pair's bands at Emission_Temperature). Grows with
    pressure squared; the band share makes far-infrared pairs (N2-N2) matter on cold worlds."""
    if Atmo_Composition is None or Surface_Pressure <= 0:
        return 0.0
    params = Model["greenhouse"]
    x = _gas_fractions(Atmo_Composition)
    column = _column_atm(Surface_Pressure, Body_SurfaceGravity)
    broadening = Surface_Pressure ** params["pressure_scaling"]
    tau0 = 0.0
    for g in GAS_TABLE:
        frac = x.get(g["name"], 0.0)
        if g["ir_strength"] > 0 and frac > 0:
            tau0 += g["ir_strength"] * math.log(1 + math.sqrt(frac * column * broadening / g["ir_saturation_atm"]))
    for pair in params["cia"]["pairs"]:
        xa, xb = x.get(pair["a"], 0.0), x.get(pair["b"], 0.0)
        if pair["strength"] > 0 and xa > 0 and xb > 0:
            tau0 += pair["strength"] * xa * xb * Surface_Pressure * column * PlanckBandFraction(Emission_Temperature, pair["bands_cm"])
    return tau0

def GreenhouseShortwaveAloft(Atmo_Composition, Surface_Pressure, Body_SurfaceGravity, Star_T):
    """Fraction of absorbed starlight taken up high in the atmosphere (anti-greenhouse), and haze index.

    Methane absorbs near-infrared starlight in its bands; the share of the star's light there
    is larger for cool stars, which is why methane cools planets of K and M stars.
    Organic haze forms when CH4/CO2 exceeds the onset ratio (and enough CH4 is present) and
    absorbs starlight aloft, as on Titan. Returns (fraction, haze_index 0-1)."""
    if Atmo_Composition is None or Surface_Pressure <= 0:
        return 0.0, 0.0
    sw = Model["greenhouse"]["shortwave"]
    x = _gas_fractions(Atmo_Composition)
    ch4, co2 = x.get("CH4", 0.0), x.get("CO2", 0.0)
    if ch4 <= 0:
        return 0.0, 0.0
    u_ch4 = ch4 * _column_atm(Surface_Pressure, Body_SurfaceGravity)
    band = [[1e4 / sw["methane_band_um"][1], 1e4 / sw["methane_band_um"][0]]]
    f_methane = sw["methane_strength"] * PlanckBandFraction(Star_T, band) * u_ch4 / (u_ch4 + sw["methane_half_atm"])

    hz = sw["haze"]
    ratio = ch4 / co2 if co2 > 0 else float("inf")
    haze = 0.0
    if ratio > hz["onset_ratio"]:
        haze = (1 - math.exp(-(ratio - hz["onset_ratio"]) / hz["ratio_scale"])) * (1 - math.exp(-u_ch4 / hz["methane_scale_atm"]))
    f_haze = hz["max_fraction"] * haze
    fraction = 1 - (1 - f_methane) * (1 - f_haze)
    return min(fraction, sw["max_fraction"]), haze

def GreenhouseLapseExponent(Atmo_Composition):
    """beta = alpha (gamma - 1) / gamma, the convective T-p exponent (T ~ p^beta).
    gamma from the mixture's degrees of freedom; alpha falls from dry to moist with water."""
    params = Model["greenhouse"]["lapse_rate"]
    gas_by_formula = {g["formula"]: g for g in GAS_TABLE}
    total = sum(d["value"] for d in Atmo_Composition.values()) or 1.0
    dof = sum(d["value"] * gas_by_formula[f]["dof"] for f, d in Atmo_Composition.items()) / total
    gamma = 1 + 2 / dof
    water_formula = next(g["formula"] for g in GAS_TABLE if g["name"] == "H2O")
    water = Atmo_Composition.get(water_formula, {}).get("value", 0.0) / total
    alpha = params["dry"] - (params["dry"] - params["moist"]) * min(1.0, water / params["moist_water_fraction"])
    return alpha * (gamma - 1) / gamma

def GreenhouseSurfaceRatio(tau0, beta, f_aloft=0.0):
    """Surface temperature / equilibrium temperature for gray optical depth tau0.

    Solves Robinson & Catling (2012) Eq. 30 for the radiative-convective boundary
    tau_rc, then returns T0/Teq from Eq. 27. Radiative layer above tau_rc, convective
    layer below (T ~ tau^(beta/n)).

    f_aloft is the fraction of absorbed starlight taken up at the top of the atmosphere
    (their stellar channel with k -> infinity). Below that layer the net infrared flux is
    only (1 - f)F, so sigma T^4 = F/2 (1 + (1 - f) D tau) and the upwelling flux is
    F/2 (2 - f + (1 - f) D tau). f = 0 is their Eq. 24-25; f = 1 gives the classic
    anti-greenhouse limit T0 = Teq / 2^(1/4)."""
    if tau0 <= 0 and f_aloft <= 0:
        return 1.0
    params = Model["greenhouse"]
    if tau0 <= 0:
        # No infrared opacity: only the starlight reaching the ground heats it
        return (1 - f_aloft) ** 0.25
    D = params["diffusivity"]
    p = 4 * beta / params["n"]
    s = 1 + p
    G0 = _scaled_upper_gamma(s, D * tau0)
    q = 1 - f_aloft

    def mismatch(tau_rc):
        # Upwelling flux continuity at tau_rc, with T0 eliminated via temperature continuity
        decay = math.exp(-D * (tau0 - tau_rc))
        lhs = decay + (D * tau0) ** (-p) * (_scaled_upper_gamma(s, D * tau_rc) - decay * G0)
        rhs = (2 - f_aloft + q * D * tau_rc) / (1 + q * D * tau_rc) * (tau_rc / tau0) ** p
        return lhs - rhs

    # Bisection in log(tau_rc): positive near 0, negative at tau0
    lo, hi = math.log(tau0) - 28.0, math.log(tau0)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if mismatch(math.exp(mid)) > 0:
            lo = mid
        else:
            hi = mid
    tau_rc = math.exp(0.5 * (lo + hi))
    return ((1 + q * D * tau_rc) / 2 * (tau0 / tau_rc) ** p) ** 0.25

def BodyGreenhouseFactor(Atmo_Composition, Surface_Pressure, Body_SurfaceGravity, Equilibrium_Temperature, Star_T):
    """Returns (surface / equilibrium temperature ratio, surface optical depth,
    fraction of starlight absorbed aloft, haze index)."""
    if Atmo_Composition is None or Surface_Pressure <= 0:
        return 1.0, 0.0, 0.0, 0.0
    tau0 = GreenhouseOpticalDepth(Atmo_Composition, Surface_Pressure, Body_SurfaceGravity, Equilibrium_Temperature)
    f_aloft, haze = GreenhouseShortwaveAloft(Atmo_Composition, Surface_Pressure, Body_SurfaceGravity, Star_T)
    ratio = GreenhouseSurfaceRatio(tau0, GreenhouseLapseExponent(Atmo_Composition), f_aloft)
    return round(ratio, 4), round(tau0, 4), round(f_aloft, 4), round(haze, 4)

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

def BodyAtmospherics(key, Dynamo_Factor, Body_SurfaceGravity, Body_Radius, Star_R, Star_T, Body_SMA, Star_Lo, Body_Type, Body_Mass, index, Body_Subclass=None, Subclass_Data=None, Tidal_Heat_Flux=0.0, seed_suffix="", Star_Metallicity=0.0, Star_IceLine=None):
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

    retained, traits = [], None
    if Body_Atmosphere:
        retained = BodyGasRetention(key, Body_Type, Body_Mass, Body_Radius, Dynamo_Factor, Bare_Temperature,
                                    Body_Irradiance, Body_SMA, index, Subclass_Data, seed_suffix)
        if not retained:
            Body_Atmosphere, Atmo_Class = False, "None"
    if Body_Atmosphere:
        if Body_Type == "giant":
            traits = BodyGiantMix(key, index, Subclass_Data, Star_Metallicity, seed_suffix)
        else:
            traits = BodyGeochemistry(key, index, Body_Type, Body_Mass, Body_SMA, Star_Metallicity, Star_IceLine, Star_T,
                                      Dynamo_Factor, Tidal_Heat_Flux, Bare_Temperature, seed_suffix, Atmo_Class)
        if Body_Type == "giant":
            AMF = BodyAtmosphereMassFraction(key, Body_Type, Atmo_Class, Dynamo_Factor, Body_Mass, Body_SurfaceGravity, index, seed_suffix)
            Surface_Pressure = BodySurfacePressureCalculation(Body_Mass, Body_Radius, Body_SurfaceGravity, AMF)
        else:
            # Pressure follows the gas budget: each source unit is pressure_per_unit_atm on Earth,
            # scaled by mass x gravity / radius^2 (same inventory per kg of planet), times retention.
            Pressure_Scale = (Model["geochemistry"]["pressure_per_unit_atm"] * Body_Mass * (Body_SurfaceGravity / 9.81)
                              / max(Body_Radius, 1e-3) ** 2 * traits["retention"])
            Surface_Pressure = Pressure_Scale * traits["inventory"]["N"] * Model["geochemistry"]["sources"]["nitrogen"]
    else:
        AMF = Surface_Pressure = Atmo_Mass_kg = 0

    # Giants have no surface: evaluate at the reference pressure level (1 bar convention)
    Greenhouse_Pressure = Model["greenhouse"]["giant_reference_pressure_atm"] if (Body_Type == "giant" and Body_Atmosphere) else Surface_Pressure
    has_ocean = traits is not None and Body_Type != "giant" and traits["oceans"] >= Model["geochemistry"]["water"]["ocean_min_oceans"]

    # Climate loop: composition (water vapour, weathering, condensation) depends on the surface
    # temperature, which depends on the composition. Iterate to a self-consistent state.
    # Start from the equilibrium temperature at a typical albedo; damping halves whenever the
    # iteration overshoots, so steep feedbacks (weathering, water vapour) settle instead of oscillating.
    loop = Model["geochemistry"]["climate_iterations"]
    fractions, flags = {}, {"liquid_ocean": False, "weathering": False, "frozen_out": False, "steam": False,
                            "runaway": False, "vapour_atm": 0.0, "pressure_atm": Surface_Pressure}
    Haze_Index = Optical_Depth = Shortwave_Aloft = 0.0
    Greenhouse_Multiplier = 1.0
    Equilibrium_K = BodyCorrectedTemperature(Star_Lo, Body_SMA, loop["start_albedo"], 1.0, Tidal_Heat_Flux) + 273.15
    # Worlds that formed inside the ice line start hot (magma-ocean aftermath), so bistable ones
    # (ice-albedo) settle on the warm branch when it exists; icy bodies accreted cold.
    hot_start = traits is not None and Body_Type != "giant" and not traits["beyond_ice_line"]
    Surface_K = max(Equilibrium_K, loop["start_K"]) if hot_start else Equilibrium_K
    Total_Pressure = Surface_Pressure
    runaway_locked = False
    damping, last_step = loop["damping"], 0.0
    for _ in range(loop["max"] if Body_Atmosphere else 1):
        if Body_Atmosphere:
            # A runaway greenhouse cannot reverse while the water remains, so it stays locked in
            absorbed = float("inf") if runaway_locked else 5.67e-8 * Equilibrium_K ** 4
            fractions, flags = BodyGasComposition(Body_Type, retained, traits, Surface_K, Total_Pressure,
                                                  Body_Mass, Body_Radius, Body_SurfaceGravity, Haze_Index, absorbed,
                                                  Pressure_Scale if Body_Type != "giant" else 1.0)
            runaway_locked = flags["runaway"]
        Total_Pressure = flags["pressure_atm"] if Body_Type != "giant" else Surface_Pressure
        if Body_Type != "giant":
            Greenhouse_Pressure = Total_Pressure
        Body_Albedo = BodyAlbedo(fractions, Body_Type, Total_Pressure, Surface_K, Haze_Index, has_ocean)
        Equilibrium_K = BodyCorrectedTemperature(Star_Lo, Body_SMA, Body_Albedo, 1.0, Tidal_Heat_Flux) + 273.15
        gh_comp = {FORMULA[n]: {"value": v} for n, v in fractions.items()} or None
        Greenhouse_Multiplier, Optical_Depth, Shortwave_Aloft, Haze_Index = BodyGreenhouseFactor(
            gh_comp, Greenhouse_Pressure, Body_SurfaceGravity, Equilibrium_K, Star_T)
        new_K = Equilibrium_K * Greenhouse_Multiplier
        step = new_K - Surface_K
        if abs(step) < loop["tolerance_K"] or Body_Type == "giant":
            Surface_K = new_K
            break
        if step * last_step < 0:
            damping *= 0.5
        last_step = step
        Surface_K += damping * step
    Corrected_Temperature = BodyCorrectedTemperature(Star_Lo, Body_SMA, Body_Albedo, Greenhouse_Multiplier, Tidal_Heat_Flux)
    if Body_Type != "giant" and Body_Atmosphere:
        Surface_Pressure = Total_Pressure          # sum of partial pressures, including any steam
        # Atmosphere mass and mass fraction follow from the pressure (P = M_atm g / 4 pi R^2)
        AMF = Surface_Pressure * 101325 * 4 * math.pi * (Body_Radius * 6.371e6) ** 2 / Body_SurfaceGravity / (Body_Mass * 5.972e24)
    if Body_Atmosphere:
        Atmo_Mass_kg = AMF * Body_Mass * 5.972e24

    Atmo_Composition, Atmosphere_Type = _composition_output(fractions) if Body_Atmosphere else (None, "None")
    Mean_Mol_Weight = BodyMeanMolecularWeight(Atmo_Composition) if Atmo_Composition else 0
    Traits = BodyAtmosphereTraits(Body_Type, traits, fractions, flags, Haze_Index, Corrected_Temperature + 273.15) if Body_Atmosphere else []
    Surface_Water = {"Inventory_Oceans": 0.0, "State": "none"}
    if traits is not None and Body_Type != "giant" and has_ocean:
        state = "vapour" if flags["runaway"] else ("liquid" if flags["liquid_ocean"] else
                ("ice" if Corrected_Temperature < 0 else "vapour"))
        Surface_Water = {"Inventory_Oceans": _sig(traits["oceans"], 3), "State": state}
    Geochemistry = None
    if traits is not None and Body_Type != "giant":
        Geochemistry = {
            "Mantle_Redox_dIW": round(traits["redox"], 2),
            "C_to_O": round(traits["c_to_o"], 3),
            "Volatile_Inventory": {el: round(v, 3) for el, v in traits["inventory"].items()},
            "Water_Oceans": _sig(traits["oceans"], 3),
            "Volcanism": traits["volcanism"],
            "Outgassing": round(traits["outgassing"], 3),
            "note": "Redox vs iron-wustite buffer (Earth's mantle ~ +3.5); inventories relative to Earth; water in Earth oceans (scaled by mass)",
        }

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
        "Traits": Traits,
        "Geochemistry": Geochemistry,
        "Surface_Water": Surface_Water,
        "Mean_Molecular_Weight": {"value": Mean_Mol_Weight if Body_Atmosphere else "NONE", "unit": "u"},
        "Atmosphere_Mass_Fraction": {"value": _sig(AMF, 4) if Body_Atmosphere else "NONE", "unit": "fraction"},
        "Atmosphere_Mass": {"value": f"{Atmo_Mass_kg:.4e}" if Body_Atmosphere else "NONE", "unit": "kg"},
        "Surface_Pressure": {"value": "N/A", "unit": "atm"} if Body_Type == "giant" else {"value": _sig(Surface_Pressure, 4) if Body_Atmosphere else 0, "unit": "atm"},
        "Albedo": {"value": Body_Albedo},
        "Greenhouse_Multiplier": {"value": Greenhouse_Multiplier},
        "Optical_Depth": {"value": Optical_Depth, "note": "Gray infrared optical depth at the surface (1 bar level for giants)"},
        "Shortwave_Absorbed_Aloft": {"value": Shortwave_Aloft, "note": "Fraction of absorbed starlight taken up high in the atmosphere by methane and haze (anti-greenhouse)"},
        "Haze": {"value": Haze_Index, "present": Haze_Index >= Model["greenhouse"]["shortwave"]["haze"]["present_threshold"], "note": "Organic (Titan-like) haze index, 0-1"},
        "Scale_Height": {"value": round(Scale_Height_km, 2) if Body_Atmosphere else "NONE", "unit": "km"},
        "Surface_Density": {"value": round(Surface_Density, 4) if Body_Atmosphere else "NONE", "unit": "kg/m^3"},
        "Exosphere_Radius": {"value": round(Body_ExosphereRadius, 3) if Body_Atmosphere else "NONE", "unit": "Re"},
        "Exosphere_Height": {"value": round(Body_ExosphereAltitude, 3) if Body_Atmosphere else "NONE", "unit": "Re"},
        "Atmosphere_Volume": {"value": Body_AtmosphereVolume if Body_Atmosphere else "NONE", "unit": "km^3"},
        "Irradiance": {"value": Body_Irradiance, "unit": "W/m^2"},
        "Bare_Temperature": {"value": Bare_Temperature, "unit": "C"},
        "Surface_Temperature": {"value": Corrected_Temperature, "unit": "C"}
    }
