import json, random, math

with open("Star_Data.json", "r") as f:
    Star_Data = json.load(f)

def StellarClass(key):
    random.seed(key)
    Star_Classes = ["O", "B", "A", "F", "G", "K", "M"]
    Class_Probabilities = [0.00003, 0.12, 0.61, 3.0, 7.6, 12.0, 76.0]
    total = sum(Class_Probabilities)
    weights = [p / total for p in Class_Probabilities]
    Star_Class = random.choices(Star_Classes, weights=weights, k=1)[0]
    return Star_Class

def GalaxyPosition(key):
    random.seed(key)
    Star_Position_X = random.randint(1, 100)
    Star_Position_Y = random.randint(1, 100)
    Star_Position_Z = random.randint(1, 100)
    return Star_Position_X, Star_Position_Y, Star_Position_Z

def StellarSphereOfInfluence(Star_Mo):
    Star_SOI = round(40 * Star_Mo, 3)
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
    random.seed(key)
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
    return round(2.7 * math.sqrt(Star_Lo), 3)

def StellarRockyZone(Star_Lo):
    Star_IceLine = StellarIceLine(Star_Lo)
    return [round(0.1 * Star_IceLine, 3), round(0.5 * Star_IceLine, 3)]

def StellarInnerBelt(Star_Lo):
    Star_IceLine = StellarIceLine(Star_Lo)
    return [round(0.5 * Star_IceLine, 3), round(0.9 * Star_IceLine, 3)]

def StellarGiantZone(Star_Lo):
    Star_IceLine = StellarIceLine(Star_Lo)
    return [round(1.1 * Star_IceLine, 3), round(3.5 * Star_IceLine, 3)]

def StellarOuterBelt(Star_Lo):
    Star_IceLine = StellarIceLine(Star_Lo)
    return [round(4 * Star_IceLine, 3), round(10 * Star_IceLine, 3)]
