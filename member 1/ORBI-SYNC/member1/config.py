
# ==========================================
# ORBI-SYNC - MEMBER 1 CONFIGURATION
# ==========================================

# Satellite data sources from CelesTrak.
# These are public groups, not a guarantee
# that Indian satellites are included.

TLE_GROUPS = [
    "active",
    "cosmos-2251-debris",
    "iridium-33-debris"
]

# Maximum number of unique objects
MAX_OBJECTS = 200

# Prediction settings
PREDICTION_DAYS = 3
SAMPLE_INTERVAL_SECONDS = 60

# Objects closer than this distance
# are reported as conjunction candidates.
MISS_DISTANCE_THRESHOLD_KM = 10.0

# Uncertainty assumption:
# Increase multiplier by 0.05 per 24 hours
# of the older TLE in a pair.
UNCERTAINTY_GROWTH_PER_DAY = 0.05

# Output folder
OUTPUT_DIRECTORY = "output"
