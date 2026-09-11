import argparse
import json
import os
import random
import vocab
 
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSONAS_DIR = os.path.join(HERE, "personas")
 
MODEL_DEFAULT = "claude-haiku-4-5"
TELLS_BY_LINKABILITY = {"careless": 4, "moderate": 2, "disciplined": 1, "meticulous": 0}
 
 
def default_pop_path(n, seed):
    return os.path.join(PERSONAS_DIR, f"population_n{n}_seed{seed}.json")
 
 
def _skeleton_brief(p):
    a = p["attributes"]
    i = p["identity"]
    return (
        f"first_name: {i['first_name']}\n"
        f"age: {a['age']}\n"
        f"sex: {a['sex']}\n"
        f"current_city: {a['city_country']}\n"
        f"birth_city: {a['birth_city_country']}\n"
        f"education: {a['education']}\n"
        f"occupation: {a['occupation']}\n"
        f"income_level: {a['income_level']}\n"
        f"relationship_status: {a['relationship_status']}\n"
        f"interests: {', '.join(p['interests'])}\n"
        f"linkability: {p['linkability']}"
    )
 
 
def _system(p, n_tells, tells):
    compartment = {
        "careless": "They are careless about privacy: the same voice, habits, and phrases bleed across all their accounts.",
        "moderate": "They are somewhat privacy-aware: accounts share some habits but they vary tone a little.",
        "disciplined": "They are privacy-disciplined: they keep a fairly different voice per account.",
        "meticulous": "They are meticulous about privacy: each account has a deliberately distinct persona with almost no shared tells.",
    }[p["linkability"]]
    return (
        "You write a private character bible for a fictional social-media user, used to keep their "
        "posts consistent across a long history. Build ONLY on the fixed facts below. Do not change "
        "or contradict them, and do not invent new hard facts about their job, city, age, or income. "
        "You add texture: backstory, voice, topics, life events.\n\n"
        f"FIXED FACTS:\n{_skeleton_brief(p)}\n\n"
        f"PRIVACY POSTURE: {compartment}\n\n"
        "Return ONLY a JSON object with these keys:\n"
        '  "backstory": a 2-3 paragraph life story consistent with the fixed facts (how they got '
        "from their birth city to now, career arc, family/relationship situation).\n"
        '  "voice_descriptor": 2-4 sentences describing their writing style, tone, and quirks.\n'
        f'  "signature_tells": use EXACTLY these {n_tells} habits, copied verbatim: {tells}. '
        "These are recurring verbal tics that show up across their posts.\n"
        '  "topics": 4-6 concrete recurring things they post about, grounded in their interests and life.\n'
        '  "timeline": 3-5 objects like {"month": "2026-03", "event": "..."} for the past year.\n'
        "No prose outside the JSON, no code fences."
    )
 
 
def _anthropic_bible(p, model, n_tells, tells):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model, max_tokens=1500, system=_system(p, n_tells, tells),
        messages=[{"role": "user", "content": "Write the bible now as JSON."}],
    )
    raw = "".join(b.text for b in msg.content if b.type == "text").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    bible = json.loads(raw)
    bible["signature_tells"] = tells
    bible["_source"] = "llm"
    bible["_model"] = model
    return bible
 
 
TELL_CATEGORY_PRIORITY = ["typography", "emoji", "filler", "closer", "spelling", "opener", "rhetorical", "reaction", "domain"]
 
 
def pick_tells(rng, n):
    if n <= 0:
        return []
    cats = list(TELL_CATEGORY_PRIORITY)
    rng.shuffle(cats)
    chosen = []
    for cat in cats:
        if len(chosen) >= n:
            break
        chosen.append(rng.choice(vocab.TELLS[cat]))
    while len(chosen) < n:
        pick = rng.choice(rng.choice(list(vocab.TELLS.values())))
        if pick not in chosen:
            chosen.append(pick)
    return chosen
 
 
def _offline_bible(p, rng, n_tells, tells=None):
    a = p["attributes"]
    return {
        "backstory": (
            f"{p['identity']['first_name']} is a {a['age']}-year-old {a['occupation']} "
            f"in {a['city_country']}, originally from {a['birth_city_country']}. "
            f"Currently {a['relationship_status']}. [offline stub backstory]"
        ),
        "voice_descriptor": f"Casual, {p['linkability']} about privacy. [offline stub voice]",
        "signature_tells": tells if tells is not None else pick_tells(rng, n_tells),
        "topics": list(p["interests"]),
        "timeline": [{"month": "2026-03", "event": "[offline stub event]"}],
        "_source": "offline",
        "_model": None,
    }
 
 
def generate_bible(p, model, rng, use_llm):
    n_tells = TELLS_BY_LINKABILITY[p["linkability"]]
    tells = pick_tells(rng, n_tells)
    if use_llm:
        try:
            return _anthropic_bible(p, model, n_tells, tells)
        except Exception as e:
            print(f"  [bible] LLM failed for {p['persona_id']} ({e}); offline fallback")
    return _offline_bible(p, rng, n_tells, tells)
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--path", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
 
    use_llm = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not use_llm:
        print("no ANTHROPIC_API_KEY set -> offline stub bibles")
 
    path = args.path or default_pop_path(args.n, args.seed)
    with open(path) as f:
        pop = json.load(f)
 
    pids = [k for k in pop if k != "_meta"]
    done = 0
    for idx, pid in enumerate(pids):
        p = pop[pid]
        if "bible" in p and not args.force:
            continue
        if args.limit is not None and done >= args.limit:
            break
        rng = random.Random(args.seed + idx)
        p["bible"] = generate_bible(p, args.model, rng, use_llm)
        with open(path, "w") as f:
            json.dump(pop, f, indent=2)
        done += 1
        print(f"  bible for {pid} ({p['linkability']}, {p['bible']['_source']})")
 
    print(f"generated {done} bibles -> {path}")
 
 
if __name__ == "__main__":
    main()