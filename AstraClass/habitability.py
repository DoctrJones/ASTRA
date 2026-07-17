import math

GAS_NAME_MAP = {
    "H₂": "H2", "He": "He", "CH₄": "CH4", "NH₃": "NH3",
    "H₂O": "H2O", "N₂": "N2", "O₂": "O2", "CO₂": "CO2", "SO₂": "SO2"
}

def HabitabilityRangeScore(value, viable_min, viable_max, optimal_min, optimal_max):
    if value < viable_min or value > viable_max:
        return 0.0
    center = (optimal_min + optimal_max) / 2.0
    optimal_half_width = (optimal_max - optimal_min) / 2.0
    if optimal_half_width <= 0:
        optimal_half_width = (viable_max - viable_min) * 0.1
    sigma = optimal_half_width / 0.5
    score = math.exp(-((value - center)**2) / (2 * sigma**2))
    if value < optimal_min:
        viable_range = optimal_min - viable_min
        if viable_range > 0:
            score *= (value - viable_min) / viable_range
    elif value > optimal_max:
        viable_range = viable_max - optimal_max
        if viable_range > 0:
            score *= (viable_max - value) / viable_range
    return max(0.0, min(score, 1.0))

def HabitabilityCheckOverrides(Hab_Data, Body_Type, Has_Atmosphere, Surface_Pressure, Surface_Temperature):
    for condition in Hab_Data["no_life_override"]["conditions"]:
        field = condition["field"]
        op    = condition["operator"]
        val   = condition["value"]
        if field == "body_type":
            actual = Body_Type
        elif field == "has_atmosphere":
            actual = Has_Atmosphere
        elif field == "surface_pressure":
            actual = Surface_Pressure
        elif field == "surface_temperature":
            actual = Surface_Temperature
        else:
            continue
        if op == "equals" and actual == val:
            return True, condition["reason"]
        elif op == "less_than" and isinstance(actual, (int, float)) and actual < val:
            return True, condition["reason"]
        elif op == "greater_than" and isinstance(actual, (int, float)) and actual > val:
            return True, condition["reason"]
    return False, None

def HabitabilityAtmosphereScore(Atmo_Composition, required_gases):
    if Atmo_Composition is None:
        return 0.0
    comp_plain = {GAS_NAME_MAP.get(formula, formula): data["value"] for formula, data in Atmo_Composition.items()}
    score = 0.0
    total_weight = 0.0
    for gas_name, gas_req in required_gases.items():
        if gas_name == "_comment":
            continue
        weight    = gas_req["weight"]
        min_frac  = gas_req["min_fraction"]
        total_weight += weight
        actual_frac = comp_plain.get(gas_name, 0.0)
        if min_frac > 0 and actual_frac < min_frac:
            score += 0.0
        elif min_frac == 0 and actual_frac == 0:
            score += weight * 0.3
        else:
            gas_score = min(1.0, actual_frac / (actual_frac + 0.05))
            score += weight * gas_score
    return score / total_weight if total_weight > 0 else 0.0

def HabitabilityTidalEnergyScore(Hab_Data, Tidal_Flux_Wm2):
    """Score tidal flux as an energy source on the same 0-1 scale as stellar radiation.
    Returns 0.0 if tidal flux is below the gate threshold."""
    gate    = Hab_Data["scoring"]["tidal_energy_gate"]["min_flux"]
    params  = Hab_Data["scoring"]["tidal_energy"]
    if Tidal_Flux_Wm2 < gate:
        return 0.0
    return HabitabilityRangeScore(
        Tidal_Flux_Wm2,
        params["viable_min"], params["viable_max"],
        params["optimal_min"], params["optimal_max"]
    )

def HabitabilityEnergyScore(Hab_Data, Irradiance_Wm2, Tidal_Flux_Wm2):
    """Combined energy availability score.
    Takes the maximum of stellar radiation score and tidal energy score.
    This allows tidal flux to substitute for or supplement stellar irradiance.
    A body with both adequate stellar and tidal flux benefits from whichever
    scores higher — they are not mutually exclusive energy sources."""
    rad_params    = Hab_Data["scoring"]["stellar_radiation"]
    stellar_score = HabitabilityRangeScore(
        Irradiance_Wm2,
        rad_params["viable_min"], rad_params["viable_max"],
        rad_params["optimal_min"], rad_params["optimal_max"]
    )
    tidal_score = HabitabilityTidalEnergyScore(Hab_Data, Tidal_Flux_Wm2)
    return max(stellar_score, tidal_score), stellar_score, tidal_score

def HabitabilityBiochemistryScore(Hab_Data, Surface_Temperature, Surface_Pressure,
                                   Atmo_Composition, Tidal_Flux_Wm2=0.0):
    """Tests all biochemistry types and returns the best match.
    Chemolithotrophic type is only eligible when tidal flux >= gate threshold.
    For all other types, energy score uses max(stellar, tidal) — tidal can
    supplement but the biochemistry type itself doesn't require it."""
    best_score   = 0.0
    best_type    = None
    best_details = {}

    tidal_gate = Hab_Data["scoring"]["tidal_energy_gate"]["min_flux"]

    for btype_name, btype_data in Hab_Data["biochemistry_types"].items():
        if btype_name == "_comment":
            continue

        # Chemolithotrophic requires tidal flux above gate — skip if not met
        is_chemolithotrophic = btype_data.get("energy_source") == "tidal"
        if is_chemolithotrophic and Tidal_Flux_Wm2 < tidal_gate:
            continue

        temp_range = btype_data["temperature"]
        temp_score = HabitabilityRangeScore(
            Surface_Temperature,
            temp_range["viable_min"], temp_range["viable_max"],
            temp_range["optimal_min"], temp_range["optimal_max"]
        )
        if temp_score == 0.0:
            continue

        pres_range = btype_data["pressure"]
        pres_score = HabitabilityRangeScore(
            Surface_Pressure,
            pres_range["viable_min"], pres_range["viable_max"],
            pres_range["optimal_min"], pres_range["optimal_max"]
        )
        if pres_score == 0.0:
            continue

        atmo_score = HabitabilityAtmosphereScore(Atmo_Composition, btype_data["required_gases"])
        combined   = temp_score * pres_score * atmo_score

        if combined > best_score:
            best_score = combined
            best_type  = btype_name
            best_details = {
                "temperature_score":    round(temp_score, 4),
                "pressure_score":       round(pres_score, 4),
                "atmosphere_score":     round(atmo_score, 4),
                "complexity_potential": btype_data["complexity_potential"],
                "label":                btype_data["label"],
                "is_chemolithotrophic": is_chemolithotrophic,
            }

    return best_score, best_type, best_details

def HabitabilityDetermineTier(Hab_Data, final_score):
    tiers = Hab_Data["biosphere_tiers"]
    sorted_tiers = sorted(
        [(name, data) for name, data in tiers.items() if name != "_comment"],
        key=lambda x: x[1]["max_score"]
    )
    for tier_name, tier_data in sorted_tiers:
        if final_score <= tier_data["max_score"]:
            return tier_name, tier_data
    return sorted_tiers[-1][0], sorted_tiers[-1][1]

def BodyHabitability(Hab_Data, Body_Type, Body_Mass, Body_SurfaceGravity, Dynamo_Factor,
                     Has_Atmosphere, Surface_Temperature, Surface_Pressure,
                     Atmo_Composition, Ocean_Coverage, Irradiance, Tidal_Flux_Wm2=0.0):
    """Full habitability scoring. Tidal_Flux_Wm2 defaults to 0.0 for planets —
    passes through from moon pipeline for bodies where tidal heating is relevant."""

    overridden, reason = HabitabilityCheckOverrides(
        Hab_Data, Body_Type, Has_Atmosphere, Surface_Pressure, Surface_Temperature
    )
    if overridden:
        return {
            "Habitability_Index":  {"value": 0.0},
            "Biosphere_Tier":      {"value": "lifeless"},
            "Override_Reason":     {"value": reason},
            "Biochemistry_Type":   {"value": "None"},
            "Subscores":           None,
            "Biosphere_Potential": None
        }

    scoring = Hab_Data["scoring"]

    biochem_score, biochem_type, biochem_details = HabitabilityBiochemistryScore(
        Hab_Data, Surface_Temperature, Surface_Pressure, Atmo_Composition, Tidal_Flux_Wm2
    )
    if biochem_score == 0.0:
        return {
            "Habitability_Index":  {"value": 0.0},
            "Biosphere_Tier":      {"value": "lifeless"},
            "Override_Reason":     {"value": "No viable biochemistry match for surface conditions"},
            "Biochemistry_Type":   {"value": "None"},
            "Subscores":           None,
            "Biosphere_Potential": None
        }

    # Individual subscores
    grav_params    = scoring["gravity"]
    gravity_score  = HabitabilityRangeScore(
        Body_SurfaceGravity,
        grav_params["viable_min"], grav_params["viable_max"],
        grav_params["optimal_min"], grav_params["optimal_max"]
    )

    mag_params     = scoring["magnetic_shielding"]
    magnetic_score = HabitabilityRangeScore(
        Dynamo_Factor,
        mag_params["viable_min"], mag_params["viable_max"],
        mag_params["optimal_min"], mag_params["optimal_max"]
    )

    liq_params    = scoring["liquid_surface"]
    liquid_score  = HabitabilityRangeScore(
        Ocean_Coverage,
        liq_params["viable_min"], liq_params["viable_max"],
        liq_params["optimal_min"], liq_params["optimal_max"]
    )

    # Energy score — max(stellar, tidal). Both are always calculated and reported.
    energy_score, stellar_score, tidal_score = HabitabilityEnergyScore(
        Hab_Data, Irradiance, Tidal_Flux_Wm2
    )

    # Determine energy source label for output
    if tidal_score >= stellar_score and tidal_score > 0:
        energy_source = "tidal"
    elif stellar_score > 0:
        energy_source = "stellar"
    else:
        energy_source = "none"

    subscores = {
        "biochemistry": {
            "value":  round(biochem_score, 4),
            "weight": scoring["temperature"]["weight"]
        },
        "gravity": {
            "value":  round(gravity_score, 4),
            "weight": grav_params["weight"]
        },
        "magnetic_shielding": {
            "value":  round(magnetic_score, 4),
            "weight": mag_params["weight"]
        },
        "liquid_surface": {
            "value":  round(liquid_score, 4),
            "weight": liq_params["weight"]
        },
        "energy": {
            "value":          round(energy_score, 4),
            "weight":         scoring["stellar_radiation"]["weight"],
            "stellar_score":  round(stellar_score, 4),
            "tidal_score":    round(tidal_score, 4),
            "dominant_source": energy_source
        }
    }

    # Multiplicative habitability index
    habitability_index = 1.0
    for name, sub in subscores.items():
        s = sub["value"]
        w = sub["weight"]
        if s == 0.0 and w > 0:
            habitability_index = 0.0
            break
        elif s > 0:
            habitability_index *= s ** w
    habitability_index = round(habitability_index, 4)

    complexity      = biochem_details.get("complexity_potential", 1.0)
    biosphere_score = round(habitability_index * complexity, 4)
    tier_name, tier_data = HabitabilityDetermineTier(Hab_Data, biosphere_score)

    return {
        "Habitability_Index":  {"value": habitability_index},
        "Biosphere_Score":     {"value": biosphere_score},
        "Biosphere_Tier":      {"value": tier_name, "description": tier_data["description"]},
        "Biochemistry_Type":   {
            "value": biochem_details.get("label", "None"),
            "key":   biochem_type,
            "chemolithotrophic": biochem_details.get("is_chemolithotrophic", False)
        },
        "Subscores":           subscores,
        "Biochemistry_Details": biochem_details,
        "Biosphere_Potential": {
            "max_phyla":          tier_data.get("max_phyla", 0),
            "max_trophic_levels": tier_data.get("max_trophic_levels", 0),
            "example_niches":     tier_data.get("example_niches", [])
        }
    }
