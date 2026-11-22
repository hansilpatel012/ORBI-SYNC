"""Central configuration for the Member 2 prototype.

Important: the guide's shared JSON schema does not contain physical hard-body
radii or a full covariance matrix. These values therefore must be configured
from trusted object data / operator input. The defaults below are DEMO
ASSUMPTIONS, not measured properties of real satellites.
"""

RISK_THRESHOLDS = {
    "low_max": 1e-6,
    "medium_max": 1e-5,
    "high_max": 1e-3,
    # Pc >= high_max is CRITICAL in this prototype.
}

# The guide supplies uncertainty_scale but not an absolute encounter-plane
# sigma. Set this base value only after agreeing/calibrating it with Member 1.
BASE_SIGMA_KM = 0.1  # illustrative demo assumption; replace with calibrated value

# Combined physical hard-body radius. Must be supplied/calibrated for real use.
DEFAULT_COMBINED_RADIUS_KM = 0.01  # illustrative demo assumption (10 m)

STALE_TLE_HOURS = 72.0
PC_ACCEPTANCE_THRESHOLD = 1e-4

# Candidate search grid. These are simulation candidates, not flight commands.
BURN_LEAD_HOURS = (24, 12, 6)
CANDIDATE_DV_MS = (0.02, 0.05, 0.10, 0.20)
CANDIDATE_DIRECTIONS = ("along_track",)

MAX_ALTERNATIVES = 3
