import os
import random
import re
 
from dotenv import load_dotenv
load_dotenv()
 
MODEL = "claude-haiku-4-5"
 
PRESENCE_BY_LINKABILITY = {
    "careless": 0.85, "moderate": 0.65, "disciplined": 0.5, "meticulous": 0.4,
}
MULTI_ACCOUNT_CHANCE = {
    "careless": 0.4, "moderate": 0.15, "disciplined": 0.05, "meticulous": 0.0,
}
 
FALLBACK_WORDS = [
    "quiet", "harbor", "ember", "pixel", "drift", "north", "static", "willow",
    "cobalt", "raven", "hollow", "ridge", "signal", "tidal", "verdant", "amber",
]
 
 
def _sanitize(h):
    h = re.sub(r"[^a-z0-9_.]", "", h.lower())
    return h[:15]
 
 
def _kit_llm(persona, link):
    import anthropic
    client = anthropic.Anthropic()
    ident = persona["identity"]
    interests = ", ".join(persona.get("interests", [])) or "general"
    voice = persona.get("bible", {}).get("voice_descriptor", "casual")
    style = {
        "careless": "Handles should openly reflect their real name and identity (name, city, job, or hobby).",
        "moderate": "Handles should loosely hint at their name or interests, not obviously identifying.",
        "disciplined": "Handles should NOT contain their name. At most a subtle hint like initials or a birth-year number; mostly generic words.",
    }[link]
    system = (
        "Generate social-media handle ideas for a fictional person.\n"
        f"Name: {ident['first_name']} {ident['last_name']}\nInterests: {interests}\nVibe: {voice}\n\n"
        f"OBSCURITY: {style}\n\n"
        'Return ONLY JSON: {"primary": "<main handle>", "variants": ["<3 near-variants of primary>"], '
        '"unrelated": ["<3 generic handles that reveal nothing>"]}. '
        "Handles: lowercase, 3-15 chars, only letters/numbers/underscore/period, no @, no spaces."
    )
    msg = client.messages.create(
        model=MODEL, max_tokens=300, system=system,
        messages=[{"role": "user", "content": "Generate the handles now."}],
    )
    raw = "".join(b.text for b in msg.content if b.type == "text").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    import json
    data = json.loads(raw)
    return {
        "primary": _sanitize(data["primary"]),
        "variants": [_sanitize(v) for v in data.get("variants", []) if _sanitize(v)],
        "unrelated": [_sanitize(u) for u in data.get("unrelated", []) if _sanitize(u)],
    }
 
 
def _random_handle(rng):
    return "".join(rng.sample(FALLBACK_WORDS, 2)) + str(rng.randint(1, 99))
 
 
def _kit_offline(persona, link, rng):
    ident = persona["identity"]
    first = _sanitize(ident["first_name"])
    last = _sanitize(ident["last_name"])
    interests = persona.get("interests", [])
    hobby = _sanitize(interests[0].split()[0]) if interests else "life"
    randoms = [_random_handle(rng) for _ in range(6)]
 
    if link == "careless":
        primary = f"{first}{last[0]}" if last else first
        variants = [f"{first}_{last}", f"{first}.{hobby}", f"{first}{rng.randint(10, 99)}"]
        unrelated = randoms[:3]
    elif link == "moderate":
        primary = f"{first}_{hobby}" if hobby else first
        variants = [f"{first}{rng.randint(10, 99)}", f"{hobby}_{first[0]}", f"{first}.{hobby}"]
        unrelated = randoms[:3]
    elif link == "disciplined":
        yr = str(rng.randint(70, 99))
        inits = (first[0] + (last[0] if last else "")) or first[:2]
        primary = rng.choice([f"{inits}_{randoms[0]}", f"{randoms[0]}{yr}", f"{inits}{yr}"])
        variants = [f"{randoms[1]}{yr}", f"{inits}.{randoms[2]}", f"{randoms[3]}_{inits}"]
        unrelated = randoms[3:6]
    else:
        primary = randoms[0]
        variants = randoms[1:4]
        unrelated = randoms[3:6]
 
    return {
        "primary": _sanitize(primary),
        "variants": [_sanitize(v) for v in variants],
        "unrelated": [_sanitize(u) for u in unrelated],
    }
 
 
def _kit(persona, link, rng, use_llm):
    if link == "meticulous":
        return _kit_offline(persona, link, rng)
    if use_llm:
        try:
            return _kit_llm(persona, link)
        except Exception as e:
            print(f"  [footprint] handle LLM failed for {persona['persona_id']} ({e}); offline")
    return _kit_offline(persona, link, rng)
 
 
def _assign(kit, link, module_counts, claim_unique, claim_core, pid):
    primary = kit["primary"]
    pool = kit["variants"] + kit["unrelated"] or [primary]
    result = {}
    core = claim_core(primary, pid) if link in ("careless", "moderate") else None
    first_module = True
    vi = 0
    for m, cnt in module_counts.items():
        handles = []
        for j in range(cnt):
            if j == 0 and link == "careless":
                handles.append(core)
            elif j == 0 and link == "moderate" and first_module:
                handles.append(core)
            else:
                handles.append(claim_unique(pool[vi % len(pool)], pid))
                vi += 1
        result[m] = handles
        first_module = False
    return result
 
 
def plan(personas, module_ids, seed):
    rng = random.Random(seed)
    use_llm = bool(os.environ.get("ANTHROPIC_API_KEY"))
    footprint = {m: {} for m in module_ids}
    used = {}
 
    def claim_unique(h, pid):
        h = _sanitize(h) or "user"
        cand = h
        while cand in used:
            cand = f"{h}{rng.randint(1, 9999)}"
        used[cand] = pid
        return cand
 
    def claim_core(h, pid):
        h = _sanitize(h) or "user"
        if h in used and used[h] == pid:
            return h
        cand = h
        while cand in used:
            cand = f"{h}{rng.randint(1, 9999)}"
        used[cand] = pid
        return cand
 
    for persona_id, p in personas.items():
        link = p.get("linkability", "moderate")
        presence = PRESENCE_BY_LINKABILITY.get(link, 0.6)
        multi = MULTI_ACCOUNT_CHANCE.get(link, 0.1)
        module_counts = {}
        for m in module_ids:
            if rng.random() > presence:
                continue
            module_counts[m] = 2 if rng.random() < multi else 1
        if not module_counts:
            continue
        kit = _kit(p, link, rng, use_llm)
        assigned = _assign(kit, link, module_counts, claim_unique, claim_core, persona_id)
        for m, handles in assigned.items():
            footprint[m][persona_id] = handles
 
    return footprint