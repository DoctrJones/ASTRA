import random, math

def TectonicActivity(Dynamo_Factor, Body_Mass, Body_Type):
    if Body_Type == "giant":
        return "None"
    activity_score = Dynamo_Factor * 0.6 + min(Body_Mass, 3.0) * 0.4
    if activity_score >= 0.4:
        return "Active"
    elif activity_score >= 0.2:
        return "Dormant"
    else:
        return "Dead"

def TectonicPlateCount(key, Dynamo_Factor, Body_Mass, Rotational_Period, index):
    random.seed(key + str(index) + "plates")
    base = 4 + int(6 * min(Dynamo_Factor, 1.5))
    spin_factor = 24.0 / max(Rotational_Period, 1.0)
    spin_bonus = int(min(spin_factor, 6.0) * 0.5)
    mass_bonus = int(2.0 * min(Body_Mass, 5.0))
    count = base + spin_bonus + mass_bonus + random.randint(-1, 2)
    return max(3, min(count, 25))

def TectonicMaxElevation(Body_SurfaceGravity):
    earth_g = 9.81
    earth_max = 10.0  # km
    return round(earth_max * (earth_g / Body_SurfaceGravity), 2)

def TectonicMaxDepth(Max_Elevation):
    return round(-Max_Elevation * 0.55, 2)

def TectonicOceanCoverage(key, Atmo_Composition, Surface_Temperature, Surface_Pressure, Body_Type, index):
    random.seed(key + str(index) + "ocean")
    if Body_Type == "giant" or Atmo_Composition is None:
        return 0.0
    h2o_frac = 0.0
    for formula, data in Atmo_Composition.items():
        if formula == "H₂O":
            h2o_frac = data["value"]
            break
    if h2o_frac < 0.01:
        return 0.0
    if Surface_Pressure > 0.006:
        boiling_point = 100 + 28 * math.log10(max(Surface_Pressure, 0.01))
        if 0 < Surface_Temperature < boiling_point:
            temp_factor = 1.0 - (Surface_Temperature / boiling_point) * 0.5
            base_coverage = h2o_frac * temp_factor * 3.0
            coverage = base_coverage * random.uniform(0.6, 1.4)
            return round(max(0.05, min(coverage, 0.95)), 3)
    ch4_frac = 0.0
    for formula, data in Atmo_Composition.items():
        if formula == "CH₄":
            ch4_frac = data["value"]
            break
    if ch4_frac > 0.05 and Surface_Temperature < -140:
        coverage = ch4_frac * random.uniform(0.3, 1.0)
        return round(max(0.01, min(coverage, 0.4)), 3)
    return 0.0

def TectonicVolcanicActivity(Dynamo_Factor, Body_Mass, Body_SMA):
    tidal_factor = 0.0
    if Body_SMA < 0.2:
        tidal_factor = 0.3 * (1.0 - Body_SMA / 0.2)
    volcanic_score = Dynamo_Factor * 0.5 + min(Body_Mass, 2.0) * 0.2 + tidal_factor
    if volcanic_score >= 0.5:
        return "High"
    elif volcanic_score >= 0.3:
        return "Moderate"
    elif volcanic_score >= 0.15:
        return "Low"
    else:
        return "None"

def TectonicErosionRate(Has_Atmosphere, Surface_Pressure, Surface_Temperature, Ocean_Coverage):
    if not Has_Atmosphere:
        return "None"
    score = min(Surface_Pressure, 10.0) * 0.05
    if Surface_Temperature > 200 or Surface_Temperature < -100:
        score += 0.3
    elif abs(Surface_Temperature) > 50:
        score += 0.15
    if Ocean_Coverage > 0:
        score += Ocean_Coverage * 0.8
    if score >= 0.5:
        return "High"
    elif score >= 0.25:
        return "Moderate"
    elif score >= 0.1:
        return "Low"
    else:
        return "None"

def TectonicGeneratePlates(key, Plate_Count, Body_Radius, Ocean_Coverage, Max_Elevation, Max_Depth, Body_SurfaceGravity, index):
    random.seed(key + str(index) + "plategen")
    Re = 6371  # km
    plates = []
    oceanic_ratio = max(0.2, min(Ocean_Coverage + 0.3, 0.7))
    golden_ratio = (1 + math.sqrt(5)) / 2
    for p in range(Plate_Count):
        theta = math.acos(1 - 2 * (p + 0.5) / Plate_Count)
        phi = 2 * math.pi * p / golden_ratio
        lat = math.degrees(theta) - 90.0 + random.uniform(-10, 10)
        lon = math.degrees(phi) % 360 - 180 + random.uniform(-10, 10)
        lat = max(-89.0, min(89.0, lat))
        lon = ((lon + 180) % 360) - 180
        if random.random() < oceanic_ratio:
            plate_type = "oceanic"
            thickness = random.uniform(5.0, 15.0)
            mean_elev = random.uniform(Max_Depth * 0.6, Max_Depth * 0.1)
        else:
            plate_type = "continental"
            thickness = random.uniform(25.0, 70.0)
            mean_elev = random.uniform(0.2, Max_Elevation * 0.3)
        base_area = 1.0 / Plate_Count
        area = base_area * random.uniform(0.5, 1.5)
        azimuth = random.uniform(0, 360)
        speed = random.uniform(1.0, 12.0) * (9.81 / Body_SurfaceGravity) * 0.7
        speed = max(0.5, min(speed, 20.0))
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
    if delta > 2.09:
        return "convergent"
    elif delta < 1.05:
        return "divergent"
    else:
        return "transform"

def TectonicGenerateBoundaries(key, plates, Max_Elevation, Max_Depth, index):
    random.seed(key + str(index) + "boundaries")
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
        neighbor_count = min(random.randint(2, 4), len(distances))
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
                    boundary["peak_elevation"] = {"value": round(Max_Elevation * random.uniform(0.5, 0.95), 2), "unit": "km"}
                elif pa_type == "oceanic" and pb_type == "oceanic":
                    boundary["feature"] = "trench"
                    boundary["depth"] = {"value": round(Max_Depth * random.uniform(0.6, 1.0), 2), "unit": "km"}
                else:
                    boundary["feature"] = "subduction_zone"
                    boundary["volcanic_arc_elevation"] = {"value": round(Max_Elevation * random.uniform(0.3, 0.7), 2), "unit": "km"}
                    boundary["trench_depth"] = {"value": round(Max_Depth * random.uniform(0.4, 0.8), 2), "unit": "km"}
            elif boundary_type == "divergent":
                if pa_type == "oceanic" or pb_type == "oceanic":
                    boundary["feature"] = "mid_ocean_ridge"
                    boundary["ridge_elevation"] = {"value": round(abs(Max_Depth) * random.uniform(0.1, 0.4), 2), "unit": "km"}
                else:
                    boundary["feature"] = "rift_valley"
                    boundary["depth"] = {"value": round(Max_Depth * random.uniform(0.2, 0.5), 2), "unit": "km"}
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
    if Activity == "Dead":
        Max_Elev = TectonicMaxElevation(Body_SurfaceGravity)
        Max_Dep = TectonicMaxDepth(Max_Elev)
        Ocean = TectonicOceanCoverage(key, Atmo_Composition, Surface_Temperature, Surface_Pressure, Body_Type, index)
        return {
            "Tectonic_Activity": {"value": Activity},
            "Plate_Count": {"value": 1},
            "Max_Elevation": {"value": round(Max_Elev * 0.4, 2), "unit": "km"},
            "Max_Depth": {"value": round(Max_Dep * 0.3, 2), "unit": "km"},
            "Ocean_Coverage": {"value": Ocean, "unit": "fraction"},
            "Sea_Level": {"value": 0.0 if Ocean == 0 else round(Max_Dep * 0.15, 2), "unit": "km"},
            "Volcanic_Activity": {"value": "None"},
            "Erosion_Rate": {"value": TectonicErosionRate(Has_Atmosphere, Surface_Pressure, Surface_Temperature, Ocean)},
            "Plates": [],
            "Boundaries": [],
            "Heightmap": {"status": "not_generated", "description": "Regenerable from seed + params"}
        }
    Plate_Count = TectonicPlateCount(key, Dynamo_Factor, Body_Mass, Rotational_Period, index)
    if Activity == "Dormant":
        Plate_Count = max(3, Plate_Count // 2)
    Max_Elev = TectonicMaxElevation(Body_SurfaceGravity)
    Max_Dep = TectonicMaxDepth(Max_Elev)
    Ocean = TectonicOceanCoverage(key, Atmo_Composition, Surface_Temperature, Surface_Pressure, Body_Type, index)
    Volcanic = TectonicVolcanicActivity(Dynamo_Factor, Body_Mass, Body_SMA)
    if Activity == "Dormant":
        downgrade = {"High": "Moderate", "Moderate": "Low", "Low": "None", "None": "None"}
        Volcanic = downgrade[Volcanic]
    Erosion = TectonicErosionRate(Has_Atmosphere, Surface_Pressure, Surface_Temperature, Ocean)
    Sea_Level = 0.0 if Ocean == 0 else round(Max_Dep * 0.15, 2)
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
