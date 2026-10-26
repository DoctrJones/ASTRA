import json, random, math

with open("Star_Data.json", "r") as f:
    Star_Data = json.load(f)
with open("Model_Data.json", "r") as f:
    Model = json.load(f)["stellar"]

def StellarClass(key):
    random.seed(key)
    Star_Classes = ["O", "B", "A", "F", "G", "K", "M"]
    Class_Probabilities = [Star_Data[c][0]["percent"] for c in Star_Classes]
    total = sum(Class_Probabilities)
    weights = [p / total for p in Class_Probabilities]
    Star_Class = random.choices(Star_Classes, weights=weights, k=1)[0]
    return Star_Class

def GalaxyPosition(key):
    random.seed(key + "position")
    lo, hi = Model["galaxy_position_range"]
    Star_Position_X = random.randint(lo, hi)
    Star_Position_Y = random.randint(lo, hi)
    Star_Position_Z = random.randint(lo, hi)
    return Star_Position_X, Star_Position_Y, Star_Position_Z

def StellarSphereOfInfluence(Star_Mo):
    Star_SOI = round(Model["soi_au_per_solar_mass"] * Star_Mo, 3)
    return Star_SOI

def StellarSpectralType(Star_Temperature, Star_Class):
    Star_Class = Star_Data[Star_Class][0]['class']
    Temperature_Max = Star_Data[Star_Class][0]['temperature_max']
    Temperature_Min = Star_Data[Star_Class][0]['temperature_min']
    Spectral_Index = Temperature_Min
    Spectral_Type = 10
    Temperature_Step = (Temperature_Max - Temperature_Min) / 10
    while Spectral_Index < Star_Temperature:
        Spectral_Index += Temperature_Step
        Spectral_Type -= 1
    return Spectral_Type

def StellarMetallicity(Star_Class, key):
    Star_Info = Star_Data[Star_Class][0]
    random.seed(key + "metallicity")
    FeH_Min = Star_Info['feh_min']
    FeH_Max = Star_Info['feh_max']
    FeH_Mean = Star_Info['feh_mean']
    FeH_Sigma = Star_Info['feh_sigma']
    Star_FeH = round(random.gauss(FeH_Mean, FeH_Sigma), 3)
    Star_FeH = max(min(Star_FeH, FeH_Max), FeH_Min)
    return Star_FeH

def StellarAbsoluteMagnitude(Lo):
    Mbol_SUN = 4.74
    Mv_SUN = 4.83
    if Lo is None or Lo <= 0:
        return 0, 0
    Star_Mbol = round(Mbol_SUN - 2.5 * math.log10(Lo), 3)
    Star_Mv = round(Mv_SUN - 2.5 * math.log10(Lo), 3)
    return Star_Mbol, Star_Mv

def StellarGoldilocksBoundary(Radius_Star, Temperature_Star, Irradiance_Max, Irradiance_Min):
    AU = 149598023  # km
    SBSigma = 5.67e-8
    Goldilocks_Min = round((math.sqrt((Radius_Star**2 * SBSigma * Temperature_Star**4) / Irradiance_Max)) / AU, 3)
    Goldilocks_Max = round((math.sqrt((Radius_Star**2 * SBSigma * Temperature_Star**4) / Irradiance_Min)) / AU, 3)
    return [Goldilocks_Min, Goldilocks_Max]

def StellarIceLine(Star_Lo):
    return round(Model["ice_line_coefficient"] * math.sqrt(Star_Lo), 3)

def StellarIceLineZone(Star_Lo, zone):
    """Zone [min, max] in AU as multiples of the ice line (Model_Data stellar.zones)."""
    Star_IceLine = StellarIceLine(Star_Lo)
    lo, hi = Model["zones"][zone]
    return [round(lo * Star_IceLine, 3), round(hi * Star_IceLine, 3)]

def StellarRockyZone(Star_Lo):
    return StellarIceLineZone(Star_Lo, "rocky")

def StellarInnerBelt(Star_Lo):
    return StellarIceLineZone(Star_Lo, "inner_belt")

def StellarGiantZone(Star_Lo):
    return StellarIceLineZone(Star_Lo, "giant")

def StellarOuterBelt(Star_Lo):
    return StellarIceLineZone(Star_Lo, "outer_belt")
