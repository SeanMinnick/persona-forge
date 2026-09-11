import argparse
import json
import os
import random
import vocab
 
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POP_PATH = os.path.join(HERE, "personas", "population.json")
 
MODEL_DEFAULT = "claude-haiku-4-5"
TELLS_BY_LINKABILITY = {"careless": 4, "moderate": 2, "disciplined": 1, "meticulous": 0}
 
 
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
 
 
def _system(p, n_tells):
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
        f'  "signature_tells": exactly {n_tells} short recurring verbal habits (phrases, emoji, sign-offs) '
        "that would show up across their posts. Use an empty list if the count is 0.\n"
        '  "topics": 4-6 concrete recurring things they post about, grounded in their interests and life.\n'
        '  "timeline": 3-5 objects like {"month": "2026-03", "event": "..."} for the past year.\n'
        "No prose outside the JSON, no code fences."
    )
 
 
def _anthropic_bible(p, model, n_tells):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model, max_tokens=1500, system=_system(p, n_tells),
        messages=[{"role": "user", "content": "Write the bible now as JSON."}],
    )
    raw = "".join(b.text for b in msg.content if b.type == "text").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    bible = json.loads(raw)
    bible["signature_tells"] = list(bible.get("signature_tells", []))[:n_tells]
    bible["_source"] = "llm"
    bible["_model"] = model
    return bible
 
 
_TELL_BANK = ["ngl", "lowkey", "imo", "🙃", "...anyway", "just me?", "to be fair", "tbh", "at the end of the day", "ok but", "just saying", "it is what it is", "godspeed", "right?", "am i wrong?", "thoughts?", "prolly", "def", "y'all", "folks", "mate", "buddy", "cheers", "LOVE this"]
 
 
def _offline_bible(p, rng, n_tells):
    a = p["attributes"]
    return {
        "backstory": (
            f"{p['identity']['first_name']} is a {a['age']}-year-old {a['occupation']} "
            f"in {a['city_country']}, originally from {a['birth_city_country']}. "
            f"Currently {a['relationship_status']}. [offline stub backstory]"
        ),
        "voice_descriptor": f"Casual, {p['linkability']} about privacy. [offline stub voice]",
        "signature_tells": rng.sample(_TELL_BANK, k=min(n_tells, len(_TELL_BANK))),
        "topics": list(p["interests"]),
        "timeline": [{"month": "2026-03", "event": "[offline stub event]"}],
        "_source": "offline",
        "_model": None,
    }
 
 
def generate_bible(p, model, rng, use_llm):
    n_tells = TELLS_BY_LINKABILITY[p["linkability"]]
    if use_llm:
        try:
            return _anthropic_bible(p, model, n_tells)
        except Exception as e:
            print(f"  [bible] LLM failed for {p['persona_id']} ({e}); offline fallback")
    return _offline_bible(p, rng, n_tells)
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--path", default=POP_PATH)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
 
    use_llm = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not use_llm:
        print("no ANTHROPIC_API_KEY set -> offline stub bibles")
 
    with open(args.path) as f:
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
        with open(args.path, "w") as f:
            json.dump(pop, f, indent=2)
        done += 1
        print(f"  bible for {pid} ({p['linkability']}, {p['bible']['_source']})")
 
    print(f"generated {done} bibles -> {args.path}")
 
 
if __name__ == "__main__":
    main()