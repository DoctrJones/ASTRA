import random, math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
G                = 6.6743e-11
Earth_Mass       = 5.972e24
Earth_Radius     = 6.371e6
Earth_Radius_km  = 6371.0
AU               = 1.496e11
SBSigma          = 5.67e-8

# Mass threshold above which a moon runs the full planetary pipeline
PLANETARY_MASS_THRESHOLD = 0.5   # Me

# Tidal flux ceiling above which a moon is considered tidally disrupted.
# Moons producing tidal flux above this ceiling are treated as tidally
# disrupted — the physics of long-term stability breaks down because
# eccentricity would circularise on very short timescales, shutting off
# the heating before it could reach equilibrium. Disrupted moons are
# removed from the stable moon list and added to the parent body's rings.
# Reference: Io observed surface flux ~2 W/m². Ceiling at 1000 W/m² is
# ~500x Io — hot but not immediately absurd. Tightened from 1e5 in v0.3.2
# following the tidal formula fix (missing mean motion factor); the old
# ceiling was calibrated against fluxes that were ~24,000x-200,000x too high.
TIDAL_DISRUPTION_FLUX = 1e3   # W/m²

# ---------------------------------------------------------------------------
# Orbital boundary calculations
# ---------------------------------------------------------------------------

def MoonRocheLimit(Parent_Radius_Re, Parent_Density_kgkm3, Moon_Density_kgkm3):
    """Roche limit in metres — rigid-body approximation.
    d = R_parent * 2.44 * (rho_parent / rho_moon)^(1/3)"""
    R_parent_m = Parent_Radius_Re * Earth_Radius
    rho_parent = Parent_Density_kgkm3 / 1e9
    rho_moon   = Moon_Density_kgkm3   / 1e9
    if rho_moon <= 0:
        rho_moon = 3500.0
    return 2.44 * R_parent_m * (rho_parent / rho_moon) ** (1.0 / 3.0)

def MoonStableZone(Parent_Radius_Re, Parent_Density_kgkm3, Moon_Density_kgkm3, Hill_Radius_AU):
    """Returns (roche_m, stable_max_m). Stable max = 0.5 * Hill radius."""
    roche_m    = MoonRocheLimit(Parent_Radius_Re, Parent_Density_kgkm3, Moon_Density_kgkm3)
    hill_m     = Hill_Radius_AU * AU
    stable_max = hill_m * 0.5
    return roche_m, stable_max

# ---------------------------------------------------------------------------
# Moon physical generation (simplified pipeline)
# ---------------------------------------------------------------------------

def MoonMassGeneration(key, parent_mass_Me, parent_subclass, index, moon_index):
    """Log-uniform mass scaled to parent. Canup-Ward limit ~0.025 x parent."""
    random.seed(key + str(index) + "moon" + str(moon_index))
    if parent_subclass in ("gas_giant", "ice_giant"):
        log_min = math.log10(parent_mass_Me * 0.000001)
        log_max = math.log10(parent_mass_Me * 0.025)
    else:
        log_min = math.log10(max(parent_mass_Me * 0.0001, 0.0001))
        log_max = math.log10(max(parent_mass_Me * 0.012,  0.001))
    log_min = max(log_min, math.log10(0.0001))
    log_max = max(log_max, log_min + 0.5)
    return round(10 ** random.uniform(log_min, log_max), 6)

def MoonDensityGeneration(key, moon_type, index, moon_index, tidal_params):
    """Draws moon bulk density from Planet_Data density_mean/sigma per moon type.
    Returns density in kg/km^3.

    Density-first approach (v0.3.2). Small moons (< 0.5 Me) don't self-compress
    meaningfully — real solar system moons cluster tightly around their bulk
    material density regardless of mass (Moon 3.34, Io 3.53, Enceladus 1.61,
    Ganymede 1.94, Callisto 1.83 g/cm^3). Drawing density from Planet_Data and
    deriving radius from mass produces physically plausible densities by
    construction, replacing the emergent-density power law that produced
    iron-density moonlets.
    """
    random.seed(key + str(index) + "moondens" + str(moon_index))
    params  = tidal_params.get(moon_type, {})
    if moon_type == "rocky_moon":
        d_mean_default, d_sigma_default = 3.5, 0.5
        d_lo, d_hi = 2.5, 5.5   # bulk rock — no compression regime for small bodies
    else:  # icy_moon
        d_mean_default, d_sigma_default = 1.8, 0.3
        d_lo, d_hi = 1.0, 2.5   # ice/rock mixtures
    d_mean  = params.get("density_mean",  d_mean_default)
    d_sigma = params.get("density_sigma", d_sigma_default)
    density_gcm3 = random.gauss(d_mean, d_sigma)
    density_gcm3 = max(d_lo, min(density_gcm3, d_hi))
    # g/cm^3 -> kg/km^3 :  1 g/cm^3 = 1000 kg/m^3 = 1e12 kg/km^3
    return round(density_gcm3 * 1e12, 2)

def MoonRadiusFromDensity(moon_mass_Me, moon_density_kgkm3):
    """Derives radius and volume from mass and bulk density.
    R = (3M / 4 pi rho)^(1/3).  Returns (radius_Re, volume_km3)."""
    if moon_mass_Me <= 0 or moon_density_kgkm3 <= 0:
        return 0.0, 0.0
    mass_kg      = moon_mass_Me * Earth_Mass
    density_kgm3 = moon_density_kgkm3 / 1e9
    volume_m3    = mass_kg / density_kgm3
    radius_m     = (3.0 * volume_m3 / (4.0 * math.pi)) ** (1.0 / 3.0)
    radius_Re    = radius_m / Earth_Radius
    volume_km3   = volume_m3 / 1e9
    return round(radius_Re, 6), round(volume_km3, 2)

def MoonSurfaceGravity(moon_mass_Me, moon_radius_Re):
    if moon_mass_Me <= 0 or moon_radius_Re <= 0:
        return 0.0
    mass_kg  = moon_mass_Me * Earth_Mass
    radius_m = moon_radius_Re * Earth_Radius
    return round((G * mass_kg) / (radius_m ** 2), 4)

def MoonDynamoFactor(key, moon_mass_Me, moon_type, index, moon_index):
    """Simplified dynamo for small moons only.
    Moons >= PLANETARY_MASS_THRESHOLD use the full planetary core calculation instead."""
    random.seed(key + str(index) + "moondyn" + str(moon_index))
    if moon_type == "rocky_moon":
        base = 0.05 + 0.25 * min(1.0, math.log10(max(moon_mass_Me, 0.001)) + 3) / 3.0
        return round(random.uniform(0.0, base), 4)
    else:
        return round(random.uniform(0.0, 0.05), 4)

# Minimum mass for tidal outgassing to sustain atmosphere against Jeans escape.
# Below this (~Io mass), outgassed material is lost too quickly regardless of flux.
TIDAL_ATMOSPHERE_MASS_GATE = 0.05  # Me

def MoonTidalAtmosphereGate(dynamo_factor, tidal_flux_Wm2, moon_mass_Me):
    """Returns an effective dynamo value for atmosphere gating.
    Tidal outgassing can sustain a thin atmosphere on volcanically active moons
    even when the intrinsic dynamo is below the 0.2 threshold.
    Requires: tidal flux >= 0.5 W/m² AND moon mass >= 0.05 Me.
    Below the mass gate, Jeans escape strips outgassed material regardless of flux.
    Only applies to small moons — large moons use the planetary pipeline directly."""
    if moon_mass_Me >= PLANETARY_MASS_THRESHOLD:
        return dynamo_factor  # planetary pipeline handles its own dynamo
    if moon_mass_Me < TIDAL_ATMOSPHERE_MASS_GATE:
        return dynamo_factor  # too small — Jeans escape wins
    if tidal_flux_Wm2 >= 0.5 and dynamo_factor < 0.2:
        return 0.21
    return dynamo_factor

# ---------------------------------------------------------------------------
# Moon orbital mechanics (around parent body)
# ---------------------------------------------------------------------------

def MoonOrbitalEccentricity(key, index, moon_index, moon_sma_m, roche_m):
    """Beta distribution biased low. Close-in moons skew higher (resonance pumping)."""
    random.seed(key + str(index) + "moonex" + str(moon_index))
    proximity = max(0.0, 1.0 - (moon_sma_m / (roche_m * 10.0)))
    alpha = max(0.5, 2.0 - proximity * 1.5)
    beta  = max(2.0, 8.0 - proximity * 3.0)
    e = random.betavariate(alpha, beta) * 0.35
    return round(e, 4)

def MoonOrbitalPeriod(moon_sma_m, parent_mass_Me):
    """Kepler period around parent. Hours."""
    parent_mass_kg = parent_mass_Me * Earth_Mass
    period_s = 2 * math.pi * math.sqrt(moon_sma_m ** 3 / (G * parent_mass_kg))
    return round(period_s / 3600.0, 4)

def MoonOrbitalSpeed(moon_sma_m, parent_mass_Me):
    """Circular orbital speed. km/s."""
    parent_mass_kg = parent_mass_Me * Earth_Mass
    return round(math.sqrt(G * parent_mass_kg / moon_sma_m) / 1000.0, 4)

# ---------------------------------------------------------------------------
# Tidal heating — Peale-Cassen-Reynolds
# ---------------------------------------------------------------------------

def MoonTidalHeating(moon_mass_Me, moon_radius_Re, moon_sma_m, eccentricity,
                     parent_mass_Me, k2, Q):
    """Peale-Cassen-Reynolds tidal dissipation power.
    Q_tidal = (21/2) * (k2/Q) * G * M_parent^2 * R_moon^5 * e^2 * n / a^6
    where n = sqrt(G * M_parent / a^3) is the mean motion.

    The mean motion factor was missing prior to v0.3.2 — the previous formula
    was off by 1/n and produced units of energy rather than power (dimensional
    mismatch). Corrected fluxes are ~24,000x (Io-orbit) to ~200,000x (outer
    giant moon orbit) lower than the pre-fix values.

    Returns (total_watts, flux_W/m^2)."""
    if eccentricity == 0.0 or Q <= 0 or moon_sma_m <= 0:
        return 0.0, 0.0
    M_parent      = parent_mass_Me * Earth_Mass
    R_moon        = moon_radius_Re * Earth_Radius
    k2_over_Q     = k2 / Q
    # Mean motion (orbital angular frequency)
    n_motion      = math.sqrt(G * M_parent / (moon_sma_m ** 3))
    numerator     = (21.0 / 2.0) * k2_over_Q * G * (M_parent**2) * (R_moon**5) * (eccentricity**2) * n_motion
    denominator   = moon_sma_m ** 6
    if denominator == 0:
        return 0.0, 0.0
    tidal_power_W   = numerator / denominator
    surface_area_m2 = 4 * math.pi * R_moon ** 2
    tidal_flux_Wm2  = tidal_power_W / surface_area_m2 if surface_area_m2 > 0 else 0.0
    return round(tidal_power_W, 4), round(tidal_flux_Wm2, 6)

def MoonTidalVolcanicFactor(tidal_flux_Wm2):
    """Converts tidal flux to volcanic factor 0.0–1.5.
    Io ~2 W/m² → ~1.0. Earth internal ~0.09 W/m² → ~0.3."""
    if tidal_flux_Wm2 <= 0:
        return 0.0
    score = 0.3 * math.log10(max(tidal_flux_Wm2, 1e-6) + 1e-6) + 0.8
    return round(max(0.0, min(score, 1.5)), 4)

def MoonTidalFluxEstimate(moon_mass_Me, moon_sma_m, parent_mass_Me, k2=0.3, Q=100):
    """Quick tidal flux estimate used as a pre-generation disruption check.
    Uses representative k2/Q values for a rocky moon and the corrected PCR
    formula with mean motion factor (v0.3.2 fix).
    Full calculation runs inside GenerateMoon after this check passes."""
    if moon_sma_m <= 0:
        return 0.0
    R_moon_approx = (moon_mass_Me ** 0.32) * Earth_Radius  # rough radius estimate
    M_parent      = parent_mass_Me * Earth_Mass
    e_typical     = 0.15   # representative eccentricity for early check.
                           # Higher than the median draw (~0.03-0.05) to catch
                           # cases where the actual ecc lands in the upper tail;
                           # a post-generation flux check backstops leaks.
    k2_over_Q     = k2 / Q
    n_motion      = math.sqrt(G * M_parent / (moon_sma_m ** 3))
    numerator     = (21.0 / 2.0) * k2_over_Q * G * (M_parent**2) * (R_moon_approx**5) * (e_typical**2) * n_motion
    denominator   = moon_sma_m ** 6
    if denominator == 0:
        return 0.0
    tidal_power_W   = numerator / denominator
    surface_area_m2 = 4 * math.pi * R_moon_approx ** 2
    return tidal_power_W / surface_area_m2 if surface_area_m2 > 0 else 0.0

# ---------------------------------------------------------------------------
# Moon type
# ---------------------------------------------------------------------------

def MoonType(moon_sma_m, parent_sma_AU, moon_ice_line_fraction):
    """Rocky inside ice line proxy, icy beyond."""
    if moon_ice_line_fraction is None:
        return "rocky_moon"
    ice_line_m = parent_sma_AU * AU * moon_ice_line_fraction
    return "rocky_moon" if moon_sma_m <= ice_line_m else "icy_moon"

# ---------------------------------------------------------------------------
# Simplified tectonics stub (small moons only)
# ---------------------------------------------------------------------------

def MoonTectonicsStub(dynamo_factor, tidal_factor, moon_mass_Me, moon_type):
    """Activity assessment without plate generation. Used for small moons only."""
    if moon_type == "icy_moon":
        activity_score = dynamo_factor * 0.3 + tidal_factor * 0.7
    else:
        activity_score = dynamo_factor * 0.6 + tidal_factor * 0.4 + min(moon_mass_Me, 0.5) * 0.2

    if activity_score >= 0.5:
        activity = "Active"
    elif activity_score >= 0.25:
        activity = "Dormant"
    else:
        activity = "Dead"

    volcanic_score = dynamo_factor * 0.4 + tidal_factor * 0.6
    if volcanic_score >= 0.6:
        volcanic = "High"
    elif volcanic_score >= 0.35:
        volcanic = "Moderate"
    elif volcanic_score >= 0.15:
        volcanic = "Low"
    else:
        volcanic = "None"

    subsurface_ocean = moon_type == "icy_moon" and tidal_factor >= 0.2

    return {
        "Tectonic_Activity": {"value": activity},
        "Volcanic_Activity":  {"value": volcanic},
        "Subsurface_Ocean":   {"value": subsurface_ocean},
        "Tidal_Factor":       {"value": tidal_factor, "unit": "unitless"},
        "Note": "Moon — simplified tectonic stub, no plate generation"
    }

# ---------------------------------------------------------------------------
# GenerateMoon — branching entry point
# ---------------------------------------------------------------------------

def GenerateMoon(key, index, moon_index, moon_sma_m, moon_type, parent_mass_Me,
                 parent_subclass, parent_sma_AU, parent_radius_Re,
                 star_lo, star_r, star_t, star_metallicity, eccentricity,
                 tidal_params, Habitability_Data, star_zones, parent_name,
                 Planet_Data):
    """Generates a single moon. Branches into full planetary pipeline for
    moons >= PLANETARY_MASS_THRESHOLD, simplified pipeline for smaller moons."""

    from .planetary import (BodyMassGeneration, BodyRadiusGeneration,
                             BodyVolumeCalculation, BodyDensityCalculation,
                             BodySurfaceGravity, BodyCoreCaluclation,
                             BodyOrbitalMechanicsCaluclation)
    from .atmosphere import BodyAtmospherics
    from .habitability import BodyHabitability
    from .tectonics import BodyTectonics

    moon_name = parent_name + "-M" + str(moon_index + 1)

    # --- Shared: mass, tidal params, orbital mechanics ---
    moon_mass   = MoonMassGeneration(key, parent_mass_Me, parent_subclass, index, moon_index)
    moon_sma_AU_parent = moon_sma_m / AU
    orbital_period_hrs = MoonOrbitalPeriod(moon_sma_m, parent_mass_Me)
    orbital_speed_kms  = MoonOrbitalSpeed(moon_sma_m, parent_mass_Me)
    moon_star_sma_AU   = parent_sma_AU  # approximation: moon << parent orbit

    params  = tidal_params.get(moon_type, tidal_params.get("rocky_moon", {"k2": 0.3, "Q_min": 10, "Q_max": 500}))
    random.seed(key + str(index) + "moonQ" + str(moon_index))
    Q_val   = random.uniform(params["Q_min"], params["Q_max"])
    k2_val  = params["k2"]

    orbit_block = {
        "SMA_parent":     {"value": round(moon_sma_AU_parent, 6), "unit": "AU"},
        "SMA_parent_km":  {"value": round(moon_sma_m / 1000, 1), "unit": "km"},
        "eccentricity":   {"value": eccentricity},
        "orbital_period": {"value": orbital_period_hrs, "unit": "hours"},
        "orbital_speed":  {"value": orbital_speed_kms,  "unit": "km/s"},
    }

    # -----------------------------------------------------------------------
    # BRANCH A: Full planetary pipeline (>= 0.5 Me)
    # -----------------------------------------------------------------------
    if moon_mass >= PLANETARY_MASS_THRESHOLD:

        # Determine rocky subclass
        from .moons import _assign_rocky_subclass_inline
        moon_subclass, moon_subclass_data = _assign_rocky_subclass_inline(moon_mass, Planet_Data)

        # Full planetary physical properties
        moon_radius   = BodyRadiusGeneration(key, moon_mass, "rocky", index, moon_subclass)
        moon_volume   = BodyVolumeCalculation(moon_radius)
        moon_density  = BodyDensityCalculation(moon_mass, moon_volume)
        moon_gravity  = BodySurfaceGravity(moon_mass, moon_radius)
        _, moon_core  = BodyCoreCaluclation(key, star_metallicity, "rocky", moon_mass, index)
        moon_dynamo   = moon_core["Dynamo_Factor"]["value"]

        # Tidal heating using full radius
        tidal_power_W, tidal_flux_Wm2 = MoonTidalHeating(
            moon_mass, moon_radius, moon_sma_m, eccentricity,
            parent_mass_Me, k2_val, Q_val
        )
        tidal_factor = MoonTidalVolcanicFactor(tidal_flux_Wm2)

        # Full atmosphere with tidal flux — moon-specific seed to avoid AMF collision with parent
        moon_atmo = BodyAtmospherics(
            key, moon_dynamo, moon_gravity, moon_radius,
            star_r, star_t, moon_star_sma_AU, star_lo,
            "rocky", moon_mass, index,
            Body_Subclass=moon_subclass, Subclass_Data=moon_subclass_data,
            Tidal_Heat_Flux=tidal_flux_Wm2,
            seed_suffix="M" + str(moon_index)
        )

        sp = moon_atmo["Surface_Pressure"]["value"]
        sp_numeric = sp if isinstance(sp, (int, float)) else 0

        # Full tectonics
        moon_tectonics = BodyTectonics(
            key, "rocky", moon_mass, moon_radius, moon_gravity,
            moon_dynamo,
            # Rotational period — draw from orbital mechanics stub
            orbital_period_hrs,
            moon_atmo["Surface_Temperature"]["value"],
            sp_numeric,
            moon_atmo["Has_Atmosphere"],
            moon_atmo["Composition"],
            moon_star_sma_AU, moon_name, index
        )

        # Inject tidal volcanic boost into full tectonics output
        if tidal_factor > 0:
            upgrade = {"None": "Low", "Low": "Moderate", "Moderate": "High", "High": "High"}
            current = moon_tectonics.get("Volcanic_Activity", {}).get("value", "None")
            if current in upgrade and tidal_factor >= 0.3:
                moon_tectonics["Volcanic_Activity"]["value"] = upgrade[current]

        # Add subsurface ocean flag (not generated by BodyTectonics)
        moon_tectonics["Subsurface_Ocean"] = {"value": False}
        moon_tectonics["Tidal_Factor"]     = {"value": tidal_factor, "unit": "unitless"}
        moon_tectonics["Pipeline"]         = {"value": "full_planetary"}

        ocean_coverage = moon_tectonics.get("Ocean_Coverage", {}).get("value", 0.0)

        # Full habitability — tidal flux passed in for energy scoring
        moon_hab = BodyHabitability(
            Habitability_Data, "rocky", moon_mass, moon_gravity,
            moon_dynamo,
            moon_atmo["Has_Atmosphere"],
            moon_atmo["Surface_Temperature"]["value"],
            sp_numeric,
            moon_atmo["Composition"],
            ocean_coverage,
            moon_atmo["Irradiance"]["value"],
            Tidal_Flux_Wm2=tidal_flux_Wm2
        )

        return {
            "name":            moon_name,
            "type":            moon_type,
            "subclass":        moon_subclass,
            "pipeline":        "full_planetary",
            "mass":            {"value": moon_mass,    "unit": "Me"},
            "radius":          {"value": moon_radius,  "unit": "Re"},
            "volume":          {"value": moon_volume,  "unit": "km^3"},
            "density":         {"value": moon_density, "unit": "kg/km^3"},
            "surface_gravity": {"value": moon_gravity, "unit": "m/s^2"},
            "orbit":           orbit_block,
            "tidal": {
                "tidal_power":  {"value": tidal_power_W,  "unit": "W"},
                "tidal_flux":   {"value": tidal_flux_Wm2, "unit": "W/m^2"},
                "tidal_factor": {"value": tidal_factor,   "unit": "unitless"},
                "eccentricity": {"value": eccentricity},
                "k2":           {"value": k2_val},
                "Q":            {"value": round(Q_val, 1)},
            },
            "dynamo_factor":   {"value": moon_dynamo, "unit": "unitless"},
            "core":            moon_core,
            "atmosphere":      moon_atmo,
            "tectonics":       moon_tectonics,
            "habitability":    moon_hab,
        }

    # -----------------------------------------------------------------------
    # BRANCH B: Simplified pipeline (< 0.5 Me)
    # -----------------------------------------------------------------------
    # Density-first (v0.3.2): draw bulk density from Planet_Data, derive radius
    # from mass + density. Small moons don't self-compress, so this produces
    # physically realistic densities where the old power-law radius did not.
    moon_density = MoonDensityGeneration(key, moon_type, index, moon_index, tidal_params)
    moon_radius, moon_volume = MoonRadiusFromDensity(moon_mass, moon_density)
    moon_gravity = MoonSurfaceGravity(moon_mass, moon_radius)
    moon_dynamo  = MoonDynamoFactor(key, moon_mass, moon_type, index, moon_index)

    tidal_power_W, tidal_flux_Wm2 = MoonTidalHeating(
        moon_mass, moon_radius, moon_sma_m, eccentricity,
        parent_mass_Me, k2_val, Q_val
    )
    tidal_factor = MoonTidalVolcanicFactor(tidal_flux_Wm2)

    # Tidal atmosphere gate — may elevate effective dynamo for outgassing
    effective_dynamo = MoonTidalAtmosphereGate(moon_dynamo, tidal_flux_Wm2, moon_mass)

    moon_atmo = BodyAtmospherics(
        key, effective_dynamo, moon_gravity, moon_radius,
        star_r, star_t, moon_star_sma_AU, star_lo,
        "rocky", moon_mass, index,
        Body_Subclass=None, Subclass_Data=None,
        Tidal_Heat_Flux=tidal_flux_Wm2,
        seed_suffix="M" + str(moon_index)
    )

    moon_tectonics = MoonTectonicsStub(moon_dynamo, tidal_factor, moon_mass, moon_type)

    ocean_coverage = 0.0
    if moon_atmo.get("Composition") and moon_tectonics["Subsurface_Ocean"]["value"]:
        ocean_coverage = 0.05

    sp = moon_atmo["Surface_Pressure"]["value"]
    sp_numeric = sp if isinstance(sp, (int, float)) else 0

    moon_hab = BodyHabitability(
        Habitability_Data, "rocky", moon_mass, moon_gravity,
        moon_dynamo,
        moon_atmo["Has_Atmosphere"],
        moon_atmo["Surface_Temperature"]["value"],
        sp_numeric,
        moon_atmo["Composition"],
        ocean_coverage,
        moon_atmo["Irradiance"]["value"],
        Tidal_Flux_Wm2=tidal_flux_Wm2
    )

    return {
        "name":            moon_name,
        "type":            moon_type,
        "subclass":        None,
        "pipeline":        "simplified",
        "mass":            {"value": moon_mass,    "unit": "Me"},
        "radius":          {"value": moon_radius,  "unit": "Re"},
        "volume":          {"value": moon_volume,  "unit": "km^3"},
        "density":         {"value": moon_density, "unit": "kg/km^3"},
        "surface_gravity": {"value": moon_gravity, "unit": "m/s^2"},
        "orbit":           orbit_block,
        "tidal": {
            "tidal_power":  {"value": tidal_power_W,  "unit": "W"},
            "tidal_flux":   {"value": tidal_flux_Wm2, "unit": "W/m^2"},
            "tidal_factor": {"value": tidal_factor,   "unit": "unitless"},
            "eccentricity": {"value": eccentricity},
            "k2":           {"value": k2_val},
            "Q":            {"value": round(Q_val, 1)},
        },
        "dynamo_factor":   {"value": moon_dynamo, "unit": "unitless"},
        "atmosphere":      moon_atmo,
        "tectonics":       moon_tectonics,
        "habitability":    moon_hab,
    }

# ---------------------------------------------------------------------------
# Internal helper — rocky subclass lookup without circular import
# ---------------------------------------------------------------------------

def _assign_rocky_subclass_inline(moon_mass, Planet_Data):
    """Inline version of assign_rocky_subclass for use inside moons.py.
    Avoids circular import with generator.py."""
    terrestrial_data = next(e for e in Planet_Data["rocky"] if e["class"] == "terrestrial")
    super_earth_data = next(e for e in Planet_Data["rocky"] if e["class"] == "super_earth")
    if moon_mass >= super_earth_data["M_E_min"]:
        return "super_earth", super_earth_data
    return "terrestrial", terrestrial_data

# ---------------------------------------------------------------------------
# GenerateMoons — master placement function
# ---------------------------------------------------------------------------

def GenerateMoons(key, index, body_type, body_subclass, subclass_data,
                  body_mass_Me, body_radius_Re, body_density_kgkm3,
                  body_sma_AU, body_hill_radius_AU, body_name,
                  star_lo, star_r, star_t, star_metallicity, star_zones,
                  Habitability_Data, Planet_Data):
    """Places all moon candidates. Returns (moons[], rings{}, roche_m)."""

    if body_type not in ("giant", "rocky") or subclass_data is None:
        return [], {"present": False, "roche_failures": 0}, 0.0

    moon_count_range = subclass_data.get("moon_count_range", [0, 0])
    if moon_count_range[1] == 0:
        return [], {"present": False, "roche_failures": 0}, 0.0

    tidal_params  = subclass_data.get("tidal_params", {})
    ice_line_frac = subclass_data.get("moon_ice_line_fraction", None)

    random.seed(key + str(index) + "mooncount")
    n_candidates = random.randint(moon_count_range[0], moon_count_range[1])
    if n_candidates == 0:
        return [], {"present": False, "roche_failures": 0}, 0.0

    rocky_params      = tidal_params.get("rocky_moon", {"density_mean": 3.5})
    body_density_kgm3 = body_density_kgkm3 / 1e9
    moon_density_kgm3 = rocky_params.get("density_mean", 3.5) * 1000  # g/cm³ → kg/m³

    roche_m, stable_max_m = MoonStableZone(
        body_radius_Re,
        body_density_kgm3 * 1e9,
        moon_density_kgm3 * 1e9,
        body_hill_radius_AU
    )

    if stable_max_m <= roche_m:
        return [], {"present": True, "roche_failures": n_candidates}, roche_m

    random.seed(key + str(index) + "moonsma")
    sma_min_m = roche_m * 0.6
    sma_max_m = stable_max_m
    raw_smas  = sorted([
        10 ** random.uniform(math.log10(sma_min_m), math.log10(sma_max_m))
        for _ in range(n_candidates)
    ])

    moons              = []
    roche_failures     = 0
    tidal_disruptions  = 0

    for moon_index, sma_m in enumerate(raw_smas):
        # --- Roche limit check ---
        if sma_m < roche_m:
            roche_failures += 1
            continue

        # --- Tidal disruption pre-check ---
        # Estimate flux before running the full pipeline. If it exceeds the
        # ceiling the moon would vaporise/disintegrate — add to ring system.
        moon_mass_est = MoonMassGeneration(key, body_mass_Me, body_subclass, index, moon_index)
        flux_est      = MoonTidalFluxEstimate(moon_mass_est, sma_m, body_mass_Me)
        if flux_est > TIDAL_DISRUPTION_FLUX:
            tidal_disruptions += 1
            continue

        m_type = MoonType(sma_m, body_sma_AU, ice_line_frac)
        ecc    = MoonOrbitalEccentricity(key, index, moon_index, sma_m, roche_m)

        moon = GenerateMoon(
            key, index, moon_index, sma_m, m_type,
            body_mass_Me, body_subclass, body_sma_AU, body_radius_Re,
            star_lo, star_r, star_t, star_metallicity, ecc,
            tidal_params, Habitability_Data, star_zones, body_name,
            Planet_Data
        )

        # --- Tidal disruption post-check ---
        # The pre-check uses a representative eccentricity; the actual draw
        # can land in the upper tail (ecc up to ~0.35), pushing flux past
        # the ceiling. Re-verify against the fully-computed flux and convert
        # to a ring if the moon fails post-generation.
        actual_flux = moon.get("tidal", {}).get("tidal_flux", {}).get("value", 0.0)
        if actual_flux > TIDAL_DISRUPTION_FLUX:
            tidal_disruptions += 1
            continue

        moons.append(moon)

    rings = {
        "present":           roche_failures > 0 or tidal_disruptions > 0,
        "roche_failures":    roche_failures,
        "tidal_disruptions": tidal_disruptions,
    }
    return moons, rings, roche_m
