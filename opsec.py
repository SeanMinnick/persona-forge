"""
opsec.py - central OPSEC model for persona-forge.
 
OPSEC score is an int in [0, 100]; higher = stronger tradecraft = harder to
profile. Scores are drawn from tier-specific Beta distributions whose shapes
are calibrated to protective-behavior prevalences in Pew Research Center's
"How Americans View Data Privacy" (2023); all per-persona knobs are pure
functions f(opsec) so they can be cited, plotted, and tuned in one place.
"""
 
OPSEC_MIN = 0
OPSEC_MAX = 100
 
# Beta distribution parameters for OPSEC score sampling, by tier. These are calibrated to Pew Research Center's "How Americans View Data Privacy" (2023) survey data.
BACKGROUND_BETA = (2.3, 3.4)
PROTECTED_BETA = (4.2, 2.6)
 
#forces any input to a valid int in [0,100]
def clamp(o):
    return max(OPSEC_MIN, min(OPSEC_MAX, int(round(o))))
 
# converts 0-100 int into 0-1 fraction for use in probability calculations
def norm(opsec):
    return clamp(opsec) / 100.0
 
# function to return beta parameters based on tier
def _beta_for(tier):
    return PROTECTED_BETA if tier == "protected" else BACKGROUND_BETA
 
# real draw, intakes rng and tier, returns clamped OPSEC value 0-100
def sample_opsec(rng, tier):
    a, b = _beta_for(tier)
    return clamp(100 * rng.betavariate(a, b))


def leakage_profile(opsec):
    o = norm(opsec)
    return {
        "self_disclosure": round((1 - o) ** 1.2, 3),
        "location_leak": round(max(0.0, 0.9 - o), 3),
        "handle_identifiability": round((1 - o) ** 1.5, 3),
        "voice_consistency": round(1 - o, 3),
    }
 
 
_FREQ_LADDER = [
    (0.05, "almost never"),
    (0.15, "very rarely"),
    (0.30, "rarely"),
    (0.45, "occasionally"),
    (0.60, "sometimes"),
    (0.75, "often"),
    (0.90, "very often"),
    (1.01, "almost always"),
]
 
 
def freq_phrase(p):
    for hi, word in _FREQ_LADDER:
        if p < hi:
            return word
    return "almost always"
 
 
 
def tells_count(opsec):
    return int(round(4 * (1 - norm(opsec))))
 
 
def filler_ratio(opsec):
    return 0.3 + 0.6 * norm(opsec)
 
 
def geotag_chance(opsec):
    return max(0.0, 0.18 * (1 - norm(opsec)) - 0.03)
 
 
def presence(opsec):
    return 0.9 - 0.55 * norm(opsec)
 
 
def multi_account_chance(opsec):
    return max(0.0, 0.45 * (1 - norm(opsec)) - 0.05)
 
 
def handle_mode(opsec):
    o = norm(opsec)
    if o < 0.30:
        return "identity"
    if o < 0.55:
        return "hint"
    if o < 0.75:
        return "generic_hint"
    return "random"
 
 
def broker_coverage(opsec):
    return max(0.05, 0.95 - 0.7 * norm(opsec))
 
 
def field_completeness(opsec):
    return max(0.2, 0.95 - 0.6 * norm(opsec))
 
 
def record_staleness(opsec):
    return 0.1 + 0.7 * norm(opsec)
 
 
def join_key_overlap(opsec):
    return max(0.05, 0.9 - 0.8 * norm(opsec))
 
 
def identity_fragmentation(opsec):
    return 0.05 + 0.5 * norm(opsec)
 
 
def field_accuracy(opsec):
    return max(0.4, 0.9 - 0.4 * norm(opsec))