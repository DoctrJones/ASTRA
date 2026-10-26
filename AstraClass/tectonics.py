import json, random, math

with open("Model_Data.json", "r") as f:
    Model = json.load(f)["tectonics"]

def TectonicActivity(Dynamo_Factor, Body_Mass, Body_Type):
    if Body_Type == "giant":
        return "None"
    act = Model["activity"]
    activity_score = Dynamo_Factor * act["dynamo_weight"] + min(Body_Mass, act["mass_cap"]) * act["mass_weight"]
    if activity_score >= act["active_min"]:
        return "Active"
    elif activity_score >= act["dormant_min"]:
        return "Dormant"
    else:
        return "Dead"

def TectonicPlateCount(key, Dynamo_Factor, Body_Mass, Rotational_Period, index):
    random.seed(key + str(index) + "plates")
    pl = Model["plates"]
    base = pl["base"] + int(pl["dynamo_scale"] * min(Dynamo_Factor, pl["dynamo_cap"]))
    spin_factor = pl["spin_reference_hours"] / max(Rotational_Period, pl["min_period_hours"])
    spin_bonus = int(min(spin_factor, pl["spin_cap"]) * pl["spin_weight"])
    mass_bonus = int(pl["mass_scale"] * min(Body_Mass, pl["mass_cap"]))
    count = base + spin_bonus + mass_bonus + random.randint(*pl["jitter"])
    return max(pl["range"][0], min(count, pl["range"][1]))

def TectonicMaxElevation(Body_SurfaceGravity):
    earth_g = 9.81
    earth_max = Model["relief"]["earth_max_elevation_km"]
    return round(earth_max * (earth_g / Body_SurfaceGravity), 2)

def TectonicMaxDepth(Max_Elevation):
    return round(-Max_Elevation * Model["relief"]["depth_ratio"], 2)

def TectonicOceanCoverage(key, Atmo_Composition, Surface_Temperature, Surface_Pressure, Body_Type, index):
    random.seed(key + str(index) + "ocean")
    oc = Model["ocean"]
    if Body_Type == "giant" or Atmo_Composition is None:
        return 0.0
    h2o_frac = 0.0
    for formula, data in Atmo_Composition.items():
        if formula == "H₂O":
            h2o_frac = data["value"]
            break
    if h2o_frac < oc["min_h2o_fraction"]:
        return 0.0
    if Surface_Pressure > oc["min_pressure"]:
        boiling_point = oc["boiling_base_c"] + oc["boiling_per_decade_c"] * math.log10(max(Surface_Pressure, oc["boiling_pressure_floor"]))
        if 0 < Surface_Temperature < boiling_point:
            temp_factor = 1.0 - (Surface_Temperature / boiling_point) * oc["temperature_factor"]
            base_coverage = h2o_frac * temp_factor * oc["coverage_scale"]
            coverage = base_coverage * random.uniform(*oc["jitter"])
            return round(max(oc["range"][0], min(coverage, oc["range"][1])), 3)
    ch4_frac = 0.0
    for formula, data in Atmo_Composition.items():
        if formula == "CH₄":
            ch4_frac = data["value"]
            break
    meth = oc["methane"]
    if ch4_frac > meth["min_fraction"] and Surface_Temperature < meth["max_temperature_c"]:
        coverage = ch4_frac * random.uniform(*meth["jitter"])
        return round(max(meth["range"][0], min(coverage, meth["range"][1])), 3)
    return 0.0

def TectonicVolcanicActivity(Dynamo_Factor, Body_Mass, Body_SMA):
    vol = Model["volcanic"]
    tidal_factor = 0.0
    if Body_SMA < vol["tidal_sma_au"]:
        tidal_factor = vol["tidal_max"] * (1.0 - Body_SMA / vol["tidal_sma_au"])
    volcanic_score = Dynamo_Factor * vol["dynamo_weight"] + min(Body_Mass, vol["mass_cap"]) * vol["mass_weight"] + tidal_factor
    if volcanic_score >= vol["high_min"]:
        return "High"
    elif volcanic_score >= vol["moderate_min"]:
        return "Moderate"
    elif volcanic_score >= vol["low_min"]:
        return "Low"
    else:
        return "None"

def TectonicErosionRate(Has_Atmosphere, Surface_Pressure, Surface_Temperature, Ocean_Coverage):
    if not Has_Atmosphere:
        return "None"
    ero = Model["erosion"]
    score = min(Surface_Pressure, ero["pressure_cap"]) * ero["pressure_weight"]
    if Surface_Temperature > ero["extreme_hot_c"] or Surface_Temperature < ero["extreme_cold_c"]:
        score += ero["extreme_bonus"]
    elif abs(Surface_Temperature) > ero["mild_abs_c"]:
        score += ero["mild_bonus"]
    if Ocean_Coverage > 0:
        score += Ocean_Coverage * ero["ocean_weight"]
    if score >= ero["high_min"]:
        return "High"
    elif score >= ero["moderate_min"]:
        return "Moderate"
    elif score >= ero["low_min"]:
        return "Low"
    else:
        return "None"

def TectonicGeneratePlates(key, Plate_Count, Body_Radius, Ocean_Coverage, Max_Elevation, Max_Depth, Body_SurfaceGravity, index):
    random.seed(key + str(index) + "plategen")
    Re = 6371  # km
    plates = []
    gen = Model["plate_generation"]
    oceanic_ratio = max(gen["oceanic_range"][0], min(Ocean_Coverage + gen["oceanic_offset"], gen["oceanic_range"][1]))
    jitter = gen["position_jitter_deg"]
    golden_ratio = (1 + math.sqrt(5)) / 2
    for p in range(Plate_Count):
        theta = math.acos(1 - 2 * (p + 0.5) / Plate_Count)
        phi = 2 * math.pi * p / golden_ratio
        lat = math.degrees(theta) - 90.0 + random.uniform(-jitter, jitter)
        lon = math.degrees(phi) % 360 - 180 + random.uniform(-jitter, jitter)
        lat = max(-89.0, min(89.0, lat))
        lon = ((lon + 180) % 360) - 180
        if random.random() < oceanic_ratio:
            plate_type = "oceanic"
            thickness = random.uniform(*gen["oceanic_thickness_km"])
            mean_elev = random.uniform(Max_Depth * gen["oceanic_depth_fraction"][0], Max_Depth * gen["oceanic_depth_fraction"][1])
        else:
            plate_type = "continental"
            thickness = random.uniform(*gen["continental_thickness_km"])
            mean_elev = random.uniform(gen["continental_min_elevation_km"], Max_Elevation * gen["continental_elevation_fraction"])
        base_area = 1.0 / Plate_Count
        area = base_area * random.uniform(*gen["area_jitter"])
        azimuth = random.uniform(0, 360)
        speed = random.uniform(*gen["speed_cm_yr"]) * (9.81 / Body_SurfaceGravity) * gen["speed_scale"]
        speed = max(gen["speed_range"][0], min(speed, gen["speed_range"][1]))
        plates.append({
            "id": p,
            "type": plate_type,
            "center_lat": round(lat, 2),
            "center_lon": round(lon, 2),
            "area_fraction": round(area, 4),
            "drift_vector": {"azimuth": round(azimuth, 1), "speed": round(speed, 2), "unit": "cm/yr"},
            "thickness": {"value": round(thickness, 1), "unit": "km"},
            "mean_elevation": {"value": round(mean_elev, 2), "unit": "km"}
        })
    total_area = sum(p["area_fraction"] for p in plates)
    for p in plates:
        p["area_fraction"] = round(p["area_fraction"] / total_area, 4)
    return plates

def TectonicBoundaryType(plate_a, plate_b):
    az_a = math.radians(plate_a["drift_vector"]["azimuth"])
    az_b = math.radians(plate_b["drift_vector"]["azimuth"])
    delta = abs(az_a - az_b) % (2 * math.pi)
    if delta > math.pi:
        delta = 2 * math.pi - delta
    if delta > Model["boundaries"]["convergent_min_rad"]:
        return "convergent"
    elif delta < Model["boundaries"]["divergent_max_rad"]:
        return "divergent"
    else:
        return "transform"

def TectonicGenerateBoundaries(key, plates, Max_Elevation, Max_Depth, index):
    random.seed(key + str(index) + "boundaries")
    bnd = Model["boundaries"]
    boundaries = []
    processed = set()
    for i in range(len(plates)):
        distances = []
        for j in range(len(plates)):
            if i == j:
                continue
            dlat = plates[i]["center_lat"] - plates[j]["center_lat"]
            dlon = plates[i]["center_lon"] - plates[j]["center_lon"]
            dist = math.sqrt(dlat**2 + dlon**2)
            distances.append((j, dist))
        distances.sort(key=lambda x: x[1])
        neighbor_count = min(random.randint(*bnd["neighbors"]), len(distances))
        for n in range(neighbor_count):
            j = distances[n][0]
            pair = tuple(sorted([i, j]))
            if pair in processed:
                continue
            processed.add(pair)
            boundary_type = TectonicBoundaryType(plates[i], plates[j])
            pa_type = plates[i]["type"]
            pb_type = plates[j]["type"]
            boundary = {"plate_a": i, "plate_b": j, "type": boundary_type}
            if boundary_type == "convergent":
                if pa_type == "continental" and pb_type == "continental":
                    boundary["feature"] = "mountain_range"
                    boundary["peak_elevation"] = {"value": round(Max_Elevation * random.uniform(*bnd["mountain_fraction"]), 2), "unit": "km"}
                elif pa_type == "oceanic" and pb_type == "oceanic":
                    boundary["feature"] = "trench"
                    boundary["depth"] = {"value": round(Max_Depth * random.uniform(*bnd["trench_fraction"]), 2), "unit": "km"}
                else:
                    boundary["feature"] = "subduction_zone"
                    boundary["volcanic_arc_elevation"] = {"value": round(Max_Elevation * random.uniform(*bnd["volcanic_arc_fraction"]), 2), "unit": "km"}
                    boundary["trench_depth"] = {"value": round(Max_Depth * random.uniform(*bnd["subduction_trench_fraction"]), 2), "unit": "km"}
            elif boundary_type == "divergent":
                if pa_type == "oceanic" or pb_type == "oceanic":
                    boundary["feature"] = "mid_ocean_ridge"
                    boundary["ridge_elevation"] = {"value": round(abs(Max_Depth) * random.uniform(*bnd["ridge_fraction"]), 2), "unit": "km"}
                else:
                    boundary["feature"] = "rift_valley"
                    boundary["depth"] = {"value": round(Max_Depth * random.uniform(*bnd["rift_fraction"]), 2), "unit": "km"}
            elif boundary_type == "transform":
                boundary["feature"] = "fault_line"
                boundary["seismic_activity"] = random.choice(["High", "Moderate", "Low"])
            boundaries.append(boundary)
    return boundaries

def TectonicGenerateHeightmap(key, plates, boundaries, Max_Elevation, Max_Depth, Body_Name, index, resolution=(1024, 512)):
    import numpy as np
    random.seed(key + str(index) + "heightmap")
    noise_seed = random.randint(0, 2**31)
    width, height = resolution
    heightmap = np.zeros((height, width), dtype=np.float32)
    lats = np.linspace(90, -90, height)
    lons = np.linspace(-180, 180, width)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    plate_lats = np.array([p["center_lat"] for p in plates])
    plate_lons = np.array([p["center_lon"] for p in plates])
    plate_elevs = np.array([p["mean_elevation"]["value"] for p in plates])
    plate_ids = np.zeros((height, width), dtype=np.int32)
    min_dist = np.full((height, width), 1e9, dtype=np.float32)
    for p_idx in range(len(plates)):
        dlat = lat_grid - plate_lats[p_idx]
        dlon = lon_grid - plate_lons[p_idx]
        dlon = np.where(dlon > 180, dlon - 360, dlon)
        dlon = np.where(dlon < -180, dlon + 360, dlon)
        cos_lat = np.cos(np.radians(lat_grid))
        dist = np.sqrt(dlat**2 + (dlon * cos_lat)**2)
        closer = dist < min_dist
        min_dist = np.where(closer, dist, min_dist)
        plate_ids = np.where(closer, p_idx, plate_ids)
    heightmap = plate_elevs[plate_ids]
    elevation_range = Max_Elevation - Max_Depth
    theta_rad = np.radians(90 - lat_grid)
    phi_rad = np.radians(lon_grid)
    sx = np.sin(theta_rad) * np.cos(phi_rad)
    sy = np.sin(theta_rad) * np.sin(phi_rad)
    sz = np.cos(theta_rad)
    rng = np.random.default_rng(noise_seed)
    TABLE_SIZE = 512
    perm = rng.permutation(TABLE_SIZE).astype(np.int32)
    perm = np.concatenate([perm, perm])
    grad_vectors = rng.standard_normal((TABLE_SIZE, 3)).astype(np.float32)
    grad_norms = np.sqrt((grad_vectors**2).sum(axis=1, keepdims=True))
    grad_vectors = grad_vectors / np.maximum(grad_norms, 1e-10)
    octaves = [
        {"freq": 3.0,  "amp": 0.35},
        {"freq": 6.0,  "amp": 0.25},
        {"freq": 12.0, "amp": 0.15},
        {"freq": 24.0, "amp": 0.10},
        {"freq": 48.0, "amp": 0.05},
    ]
    def hash3d_grad(ix, iy, iz):
        return perm[perm[perm[ix % TABLE_SIZE] + iy % TABLE_SIZE] + iz % TABLE_SIZE] % TABLE_SIZE
    def grad_dot(ix, iy, iz, dx, dy, dz):
        idx = hash3d_grad(ix, iy, iz)
        return grad_vectors[idx, 0] * dx + grad_vectors[idx, 1] * dy + grad_vectors[idx, 2] * dz
    for octave in octaves:
        freq = octave["freq"]
        amp = octave["amp"]
        x = sx * freq; y = sy * freq; z = sz * freq
        xi = np.floor(x).astype(np.int32); yi = np.floor(y).astype(np.int32); zi = np.floor(z).astype(np.int32)
        xf = x - xi; yf = y - yi; zf = z - zi
        u = xf*xf*xf*(xf*(xf*6 - 15) + 10)
        v = yf*yf*yf*(yf*(yf*6 - 15) + 10)
        w = zf*zf*zf*(zf*(zf*6 - 15) + 10)
        n000 = grad_dot(xi,   yi,   zi,   xf,   yf,   zf)
        n100 = grad_dot(xi+1, yi,   zi,   xf-1, yf,   zf)
        n010 = grad_dot(xi,   yi+1, zi,   xf,   yf-1, zf)
        n110 = grad_dot(xi+1, yi+1, zi,   xf-1, yf-1, zf)
        n001 = grad_dot(xi,   yi,   zi+1, xf,   yf,   zf-1)
        n101 = grad_dot(xi+1, yi,   zi+1, xf-1, yf,   zf-1)
        n011 = grad_dot(xi,   yi+1, zi+1, xf,   yf-1, zf-1)
        n111 = grad_dot(xi+1, yi+1, zi+1, xf-1, yf-1, zf-1)
        nx00 = n000 + u * (n100 - n000); nx10 = n010 + u * (n110 - n010)
        nx01 = n001 + u * (n101 - n001); nx11 = n011 + u * (n111 - n011)
        nxy0 = nx00 + v * (nx10 - nx00); nxy1 = nx01 + v * (nx11 - nx01)
        heightmap += (nxy0 + w * (nxy1 - nxy0)) * amp * elevation_range
    heightmap = np.clip(heightmap, Max_Depth, Max_Elevation)
    filepath = str(Body_Name) + "_heightmap.npy"
    np.save(filepath, heightmap)
    return heightmap, filepath

def BodyTectonics(key, Body_Type, Body_Mass, Body_Radius, Body_SurfaceGravity, Dynamo_Factor,
                  Rotational_Period, Surface_Temperature, Surface_Pressure, Has_Atmosphere,
                  Atmo_Composition, Body_SMA, Body_Name, index):
    if Body_Type == "giant":
        return {
            "Tectonic_Activity": {"value": "None"},
            "Note": "Gas giants do not have solid surface tectonics"
        }
    Activity = TectonicActivity(Dynamo_Factor, Body_Mass, Body_Type)
    relief = Model["relief"]
    if Activity == "Dead":
        Max_Elev = TectonicMaxElevation(Body_SurfaceGravity)
        Max_Dep = TectonicMaxDepth(Max_Elev)
        Ocean = TectonicOceanCoverage(key, Atmo_Composition, Surface_Temperature, Surface_Pressure, Body_Type, index)
        return {
            "Tectonic_Activity": {"value": Activity},
            "Plate_Count": {"value": 1},
            "Max_Elevation": {"value": round(Max_Elev * relief["dead_elevation_fraction"], 2), "unit": "km"},
            "Max_Depth": {"value": round(Max_Dep * relief["dead_depth_fraction"], 2), "unit": "km"},
            "Ocean_Coverage": {"value": Ocean, "unit": "fraction"},
            "Sea_Level": {"value": 0.0 if Ocean == 0 else round(Max_Dep * relief["sea_level_depth_fraction"], 2), "unit": "km"},
            "Volcanic_Activity": {"value": "None"},
            "Erosion_Rate": {"value": TectonicErosionRate(Has_Atmosphere, Surface_Pressure, Surface_Temperature, Ocean)},
            "Plates": [],
            "Boundaries": [],
            "Heightmap": {"status": "not_generated", "description": "Regenerable from seed + params"}
        }
    Plate_Count = TectonicPlateCount(key, Dynamo_Factor, Body_Mass, Rotational_Period, index)
    if Activity == "Dormant":
        Plate_Count = max(Model["plates"]["range"][0], Plate_Count // Model["plates"]["dormant_divisor"])
    Max_Elev = TectonicMaxElevation(Body_SurfaceGravity)
    Max_Dep = TectonicMaxDepth(Max_Elev)
    Ocean = TectonicOceanCoverage(key, Atmo_Composition, Surface_Temperature, Surface_Pressure, Body_Type, index)
    Volcanic = TectonicVolcanicActivity(Dynamo_Factor, Body_Mass, Body_SMA)
    if Activity == "Dormant":
        downgrade = {"High": "Moderate", "Moderate": "Low", "Low": "None", "None": "None"}
        Volcanic = downgrade[Volcanic]
    Erosion = TectonicErosionRate(Has_Atmosphere, Surface_Pressure, Surface_Temperature, Ocean)
    Sea_Level = 0.0 if Ocean == 0 else round(Max_Dep * relief["sea_level_depth_fraction"], 2)
    Plates = TectonicGeneratePlates(key, Plate_Count, Body_Radius, Ocean, Max_Elev, Max_Dep, Body_SurfaceGravity, index)
    Boundaries = TectonicGenerateBoundaries(key, Plates, Max_Elev, Max_Dep, index)
    return {
        "Tectonic_Activity": {"value": Activity},
        "Plate_Count": {"value": Plate_Count},
        "Max_Elevation": {"value": Max_Elev, "unit": "km"},
        "Max_Depth": {"value": Max_Dep, "unit": "km"},
        "Ocean_Coverage": {"value": Ocean, "unit": "fraction"},
        "Sea_Level": {"value": Sea_Level, "unit": "km"},
        "Volcanic_Activity": {"value": Volcanic},
        "Erosion_Rate": {"value": Erosion},
        "Plates": Plates,
        "Boundaries": Boundaries,
    }
