from .stellar import (
    StellarClass, GalaxyPosition, StellarSphereOfInfluence, StellarSpectralType,
    StellarMetallicity, StellarAbsoluteMagnitude, StellarGoldilocksBoundary,
    StellarIceLine, StellarRockyZone, StellarInnerBelt, StellarGiantZone, StellarOuterBelt
)
from .orbital import (
    PoissonSample, Sigmoid, BodyCountLambda, BodyGiantProbability,
    BodyZoneDistribution, RandomNumberSet, GenerateBeltPopulation,
    MutualHillRadius, GladmanMinSeparation, BodySMAPlacement
)
from .planetary import (
    BodyMassGeneration, BodyRadiusGeneration, BodyVolumeCalculation,
    BodyDensityCalculation, BodySurfaceGravity, BodyCoreCaluclation,
    BodyOrbitalMechanicsCaluclation
)
from .atmosphere import (
    BodyEscapeVelocity, BodyThermalVelocity, BodyAtmosphereComposition,
    BodyAtmosphereMassFraction, BodyMeanMolecularWeight, BodySurfacePressureCalculation,
    BodyBareTemperature, BodyAlbedo, BodyGreenhouseFactor, BodyCorrectedTemperature,
    BodyAtmospherics, GAS_TABLE
)
from .tectonics import (
    TectonicActivity, TectonicPlateCount, TectonicMaxElevation, TectonicMaxDepth,
    TectonicOceanCoverage, TectonicVolcanicActivity, TectonicErosionRate,
    TectonicGeneratePlates, TectonicBoundaryType, TectonicGenerateBoundaries,
    TectonicGenerateHeightmap, BodyTectonics
)
from .moons import (
    MoonRocheLimit, MoonStableZone, MoonMassGeneration,
    MoonDensityGeneration, MoonRadiusFromDensity,
    MoonSurfaceGravity, MoonDynamoFactor, MoonTidalAtmosphereGate,
    MoonOrbitalEccentricity, MoonOrbitalPeriod, MoonOrbitalSpeed,
    MoonTidalHeating, MoonTidalVolcanicFactor,
    MoonType, MoonTectonicsStub, GenerateMoon, GenerateMoons
)
from .habitability import (
    HabitabilityRangeScore, HabitabilityCheckOverrides, HabitabilityAtmosphereScore,
    HabitabilityBiochemistryScore, HabitabilityDetermineTier, BodyHabitability,
    HabitabilityTidalEnergyScore, HabitabilityEnergyScore,
    GAS_NAME_MAP
)

class AstraFunctions:
    # Stellar
    StellarClass = staticmethod(StellarClass)
    GalaxyPosition = staticmethod(GalaxyPosition)
    StellarSphereOfInfluence = staticmethod(StellarSphereOfInfluence)
    StellarSpectralType = staticmethod(StellarSpectralType)
    StellarMetallicity = staticmethod(StellarMetallicity)
    StellarAbsoluteMagnitude = staticmethod(StellarAbsoluteMagnitude)
    StellarGoldilocksBoundary = staticmethod(StellarGoldilocksBoundary)
    StellarIceLine = staticmethod(StellarIceLine)
    StellarRockyZone = staticmethod(StellarRockyZone)
    StellarInnerBelt = staticmethod(StellarInnerBelt)
    StellarGiantZone = staticmethod(StellarGiantZone)
    StellarOuterBelt = staticmethod(StellarOuterBelt)
    # Orbital
    PoissonSample = staticmethod(PoissonSample)
    Sigmoid = staticmethod(Sigmoid)
    BodyCountLambda = staticmethod(BodyCountLambda)
    BodyGiantProbability = staticmethod(BodyGiantProbability)
    BodyZoneDistribution = staticmethod(BodyZoneDistribution)
    RandomNumberSet = staticmethod(RandomNumberSet)
    GenerateBeltPopulation = staticmethod(GenerateBeltPopulation)
    MutualHillRadius = staticmethod(MutualHillRadius)
    GladmanMinSeparation = staticmethod(GladmanMinSeparation)
    BodySMAPlacement = staticmethod(BodySMAPlacement)
    # Planetary
    BodyMassGeneration = staticmethod(BodyMassGeneration)
    BodyRadiusGeneration = staticmethod(BodyRadiusGeneration)
    BodyVolumeCalculation = staticmethod(BodyVolumeCalculation)
    BodyDensityCalculation = staticmethod(BodyDensityCalculation)
    BodySurfaceGravity = staticmethod(BodySurfaceGravity)
    BodyCoreCaluclation = staticmethod(BodyCoreCaluclation)
    BodyOrbitalMechanicsCaluclation = staticmethod(BodyOrbitalMechanicsCaluclation)
    # Atmosphere
    GAS_TABLE = GAS_TABLE
    BodyEscapeVelocity = staticmethod(BodyEscapeVelocity)
    BodyThermalVelocity = staticmethod(BodyThermalVelocity)
    BodyAtmosphereComposition = staticmethod(BodyAtmosphereComposition)
    BodyAtmosphereMassFraction = staticmethod(BodyAtmosphereMassFraction)
    BodyMeanMolecularWeight = staticmethod(BodyMeanMolecularWeight)
    BodySurfacePressureCalculation = staticmethod(BodySurfacePressureCalculation)
    BodyBareTemperature = staticmethod(BodyBareTemperature)
    BodyAlbedo = staticmethod(BodyAlbedo)
    BodyGreenhouseFactor = staticmethod(BodyGreenhouseFactor)
    BodyCorrectedTemperature = staticmethod(BodyCorrectedTemperature)
    BodyAtmospherics = staticmethod(BodyAtmospherics)
    # Tectonics
    TectonicActivity = staticmethod(TectonicActivity)
    TectonicPlateCount = staticmethod(TectonicPlateCount)
    TectonicMaxElevation = staticmethod(TectonicMaxElevation)
    TectonicMaxDepth = staticmethod(TectonicMaxDepth)
    TectonicOceanCoverage = staticmethod(TectonicOceanCoverage)
    TectonicVolcanicActivity = staticmethod(TectonicVolcanicActivity)
    TectonicErosionRate = staticmethod(TectonicErosionRate)
    TectonicGeneratePlates = staticmethod(TectonicGeneratePlates)
    TectonicBoundaryType = staticmethod(TectonicBoundaryType)
    TectonicGenerateBoundaries = staticmethod(TectonicGenerateBoundaries)
    TectonicGenerateHeightmap = staticmethod(TectonicGenerateHeightmap)
    BodyTectonics = staticmethod(BodyTectonics)
    # Moons
    MoonRocheLimit = staticmethod(MoonRocheLimit)
    MoonStableZone = staticmethod(MoonStableZone)
    MoonMassGeneration = staticmethod(MoonMassGeneration)
    MoonDensityGeneration = staticmethod(MoonDensityGeneration)
    MoonRadiusFromDensity = staticmethod(MoonRadiusFromDensity)
    MoonSurfaceGravity = staticmethod(MoonSurfaceGravity)
    MoonDynamoFactor = staticmethod(MoonDynamoFactor)
    MoonTidalAtmosphereGate = staticmethod(MoonTidalAtmosphereGate)
    MoonOrbitalEccentricity = staticmethod(MoonOrbitalEccentricity)
    MoonOrbitalPeriod = staticmethod(MoonOrbitalPeriod)
    MoonOrbitalSpeed = staticmethod(MoonOrbitalSpeed)
    MoonTidalHeating = staticmethod(MoonTidalHeating)
    MoonTidalVolcanicFactor = staticmethod(MoonTidalVolcanicFactor)
    MoonType = staticmethod(MoonType)
    MoonTectonicsStub = staticmethod(MoonTectonicsStub)
    GenerateMoon = staticmethod(GenerateMoon)
    GenerateMoons = staticmethod(GenerateMoons)
    # Habitability
    GAS_NAME_MAP = GAS_NAME_MAP
    HabitabilityRangeScore = staticmethod(HabitabilityRangeScore)
    HabitabilityCheckOverrides = staticmethod(HabitabilityCheckOverrides)
    HabitabilityAtmosphereScore = staticmethod(HabitabilityAtmosphereScore)
    HabitabilityBiochemistryScore = staticmethod(HabitabilityBiochemistryScore)
    HabitabilityDetermineTier = staticmethod(HabitabilityDetermineTier)
    BodyHabitability = staticmethod(BodyHabitability)
    HabitabilityTidalEnergyScore = staticmethod(HabitabilityTidalEnergyScore)
    HabitabilityEnergyScore = staticmethod(HabitabilityEnergyScore)
