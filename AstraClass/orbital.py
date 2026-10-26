import json, random, math

with open("Star_Data.json", "r") as f:
    Star_Data = json.load(f)
with open("Model_Data.json", "r") as f:
    Model = json.load(f)["system"]

def PoissonSample(key, lamb):
    random.seed(key)
    if lamb <= 0:
        return 0
    L = math.exp(-lamb)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1

def Sigmoid(z):
    return 1.0 / (1.0 + math.exp(-z))

def BodyCountLambda(Star_Class, Star_Metallicity):
    BaseRate = Star_Data[Star_Class][0]['lambda']
    params = Model["body_count"]
    clamp = params["metallicity_clamp"]
    FeH_Multiplier = 1.0 + params["metallicity_multiplier"] * max(min(Star_Metallicity, clamp), -clamp)
    return BaseRate * FeH_Multiplier

def BodyGiantProbability(Star_Metallicity, Star_Mo):
    params = Model["giant_probability"]
    k = params["k"]
    x0 = params["x0"]
    z = k * (Star_Metallicity - x0)
    p = Sigmoid(z)
    if Star_Mo is not None:
        p *= (1.0 + params["star_mass_boost"] * (max(Star_Mo - 1.0, 0.0)))
    return max(0.0, min(params["max"], p))

def BodyZoneDistribution(key, Star_Class, Star_Metallicity, Star_Mo, N):
    Star_Info = Star_Data[Star_Class][0]
    random.seed(key + "zones")
    weights = Star_Info["zone_weights"]
    boost = Model["zone_distribution"]["metallicity_boost"]
    rocky = weights["rocky"] * (1 + boost * Star_Metallicity)
    giant = weights["giant"] * (1 + boost * Star_Metallicity)
    Body_GiantProbability = BodyGiantProbability(Star_Metallicity, Star_Mo)
    giant *= Body_GiantProbability
    total = rocky + giant
    rocky /= total
    giant /= total
    zones = random.choices(["rocky", "giant"], weights=[rocky, giant], k=N)
    zones.sort(key=lambda z: 0 if z == "rocky" else 1)
    Body_RockyCount = zones.count("rocky")
    Body_GiantCount = zones.count("giant")
    return zones, Body_RockyCount, Body_GiantCount

def GenerateBeltPopulation(key, belt_tag, Star_Metallicity, Star_Mo, belt_zone, has_giant, suffix="belt"):
    """Generates dwarf body count and SMAs for a belt region.
    belt_tag: 'inner' or 'outer'
    belt_zone: [min_AU, max_AU]
    has_giant: bool — whether the system has any giant bodies
    Returns (count, [sma_list])"""
    random.seed(key + suffix + belt_tag)
    params = Model["belts"]
    # Base lambda by belt type
    base_lambda = params["inner_lambda"] if belt_tag == "inner" else params["outer_lambda"]
    # Metallicity boost: more metals = more debris
    feh_factor = 1.0 + params["metallicity_boost"] * max(min(Star_Metallicity, 1.0), -1.0)
    # Giant shepherding: giants increase belt population (captured/corralled debris)
    giant_factor = params["giant_shepherding"] if has_giant else 1.0
    lamb = base_lambda * feh_factor * giant_factor
    lamb = max(params["lambda_range"][0], min(lamb, params["lambda_range"][1]))
    # Poisson sample for count
    if lamb <= 0:
        return 0, []
    L = math.exp(-lamb)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            count = max(0, k - 1)
            break
    if count == 0:
        return 0, []
    # Generate SMAs within belt bounds with minimum spacing (Model_Data system.belts)
    spacing = params["min_spacing_au"]
    belt_min, belt_max = belt_zone
    if belt_max - belt_min < spacing * count:
        count = max(1, int((belt_max - belt_min) / spacing))
    smas = []
    current_min = belt_min
    for _ in range(count):
        sma = round(random.uniform(current_min, belt_max), 3)
        smas.append(sma)
        current_min = sma + spacing
        if current_min >= belt_max:
            break
    smas.sort()
    return len(smas), smas

def MutualHillRadius(sma_AU, m1_Me, m2_Me, star_Mo):
    """Calculates the mutual Hill radius for two bodies at a given SMA.
    Used to derive physically grounded minimum orbital separations."""
    Earth_Mass_kg = 5.972e24
    Sol_Mass_kg   = 1.989e30
    m1_kg  = m1_Me * Earth_Mass_kg
    m2_kg  = m2_Me * Earth_Mass_kg
    M_star = star_Mo * Sol_Mass_kg
    return sma_AU * ((m1_kg + m2_kg) / (3 * M_star)) ** (1.0 / 3.0)

def GladmanMinSeparation(sma_AU, m1_Me, m2_Me, star_Mo, k):
    """Minimum stable orbital separation using the Gladman (1993) criterion:
    delta > k * R_mH  where R_mH is the mutual Hill radius.
    k per body type is in Model_Data system.placement (giants use a larger k
    to account for the representative mass underestimating actual giant masses).
    Returns minimum separation in AU."""
    return k * MutualHillRadius(sma_AU, m1_Me, m2_Me, star_Mo)

def BodySMAPlacement(key, N, zone_min, zone_max, star_Mo, rep_mass_Me, body_type_tag, k):
    """Places N bodies within [zone_min, zone_max] using Hill-radius-derived
    minimum separations (Gladman 1993).

    Uses a representative mass (rep_mass_Me) to estimate spacing before
    individual body masses are known. Spacing is recalculated at each step
    using the current SMA, so it correctly tightens near the star and widens
    further out.

    If N bodies cannot fit in the zone even at minimum spacing, count is
    reduced to the maximum that physically fits. Returns the final SMA list.

    rep_mass_Me and k per body type: Model_Data system.placement.
    """
    if N <= 0:
        return []

    random.seed(key + body_type_tag)

    # Step 1 — verify N bodies can fit; reduce if not
    # Estimate total space needed by summing minimum separations from zone_min outward
    test_sma  = zone_min
    max_fit   = 0
    for _ in range(N):
        min_sep = GladmanMinSeparation(test_sma, rep_mass_Me, rep_mass_Me, star_Mo, k=k)
        if test_sma + min_sep > zone_max and max_fit == 0:
            break
        max_fit += 1
        test_sma += min_sep

    # Always place at least 1 body if the zone exists
    N_actual = max(1, min(N, max_fit)) if zone_max > zone_min else 0
    if N_actual == 0:
        return []

    # Step 2 — place bodies iteratively
    # Each body is drawn randomly from [current_min, zone_max], then the next
    # minimum is derived from that body's actual SMA.
    smas        = []
    current_min = zone_min

    for i in range(N_actual):
        if current_min >= zone_max:
            break

        # Draw SMA randomly within remaining zone
        sma = round(random.uniform(current_min, zone_max), 3)
        smas.append(sma)

        # Derive next minimum from this body's actual SMA
        min_sep     = GladmanMinSeparation(sma, rep_mass_Me, rep_mass_Me, star_Mo, k=k)
        current_min = round(sma + min_sep, 4)

    return smas

def RandomNumberSet(key, N, min, max, S):
    """Legacy fixed-spacing SMA placement. Retained for belt population
    (belt bodies are tiny and fixed spacing is appropriate there).
    Main body placement now uses BodySMAPlacement() instead."""
    if N <= 0:
        return []
    random.seed(key)
    numbers_list = []
    random_numbers = [random.uniform(min, max) for n in range(N)]
    random_numbers = [round(n, 3) for n in random_numbers]
    random_numbers = sorted(random_numbers, key=float)
    smallest_value = random_numbers[0] + S
    numbers_list.append(smallest_value)
    for i in range(N - 1):
        random_numbers = [random.uniform(smallest_value, max) for n in range(N)]
        random_numbers = [round(n, 3) for n in random_numbers]
        random_numbers = sorted(random_numbers, key=float)
        smallest_value = round(random_numbers[0] + S, 3)
        numbers_list.append(smallest_value)
    return numbers_list
