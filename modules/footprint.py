import random
 
HANDLE_WORDS = [
    "quiet", "harbor", "night", "shift", "maple", "mortar", "byte", "wrangler",
    "coastal", "ember", "pixel", "drifter", "north", "wander", "static", "willow",
    "cobalt", "raven", "hollow", "ridge", "amber", "signal", "tidal", "verdant",
]
 
PRESENCE_BY_LINKABILITY = {
    "careless": 0.85,
    "moderate": 0.65,
    "disciplined": 0.5,
    "meticulous": 0.4,
}
 
MULTI_ACCOUNT_CHANCE = {
    "careless": 0.4,
    "moderate": 0.15,
    "disciplined": 0.05,
    "meticulous": 0.0,
}
 
 
def _handle(rng):
    return "".join(w.capitalize() for w in rng.sample(HANDLE_WORDS, 2)) + str(rng.randint(1, 999))
 
 
def plan(personas, module_ids, seed):
    rng = random.Random(seed)
    footprint = {m: {} for m in module_ids}
 
    for persona_id, p in personas.items():
        link = p.get("linkability", "moderate")
        presence = PRESENCE_BY_LINKABILITY.get(link, 0.6)
        multi = MULTI_ACCOUNT_CHANCE.get(link, 0.1)
        for m in module_ids:
            if rng.random() > presence:
                continue
            n_accounts = 2 if rng.random() < multi else 1
            handles = [_handle(rng) for _ in range(n_accounts)]
            footprint[m][persona_id] = handles
 
    return footprint