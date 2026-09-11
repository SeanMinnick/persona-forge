import argparse
import datetime
import json
import os
import random
 
from dotenv import load_dotenv
load_dotenv()
 
import vocab
 
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "populations")
 
MODEL_DEFAULT = "claude-haiku-4-5"
TELLS_BY_LINKABILITY = {"careless": 4, "moderate": 2, "disciplined": 1, "meticulous": 0}
 
 
def default_pop_path(n, seed):
    return os.path.join(DATA_DIR, f"population_n{n}_seed{seed}.json")
 
 
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
 
 
def _system(p, n_tells, tells, today):
    compartment = {
        "careless": "They are careless about privacy: the same voice, habits, and phrases bleed across all their accounts.",
        "moderate": "They are somewhat privacy-aware: accounts share some habits but they vary tone a little.",
        "disciplined": "They are privacy-disciplined: they keep a fairly different voice per account.",
        "meticulous": "They are meticulous about privacy: each account has a deliberately distinct persona with almost no shared tells.",
    }[p["linkability"]]
    born_year = today.year - p["attributes"]["age"]
    return (
        "You write a private character bible for a fictional social-media user, used to keep their "
        "posts consistent across a long history. Build ONLY on the fixed facts below. Do not change "
        "or contradict them, and do not invent new hard facts about their job, city, age, or income. "
        "You add texture: backstory, voice, topics, life events.\n\n"
        f"FIXED FACTS:\n{_skeleton_brief(p)}\n\n"
        f"PRIVACY POSTURE: {compartment}\n\n"
        f"TODAY'S DATE: {today.strftime('%B %d, %Y')}. Anchor every time reference to this date. "
        f"This person is {p['attributes']['age']} now, so they were born around {born_year}. "
        "Any year you state for a life event must be consistent with their current age and with "
        "today's date (e.g. graduating high school around age 18, not later). Prefer absolute years "
        "('in 2019') over relative phrases; if you use a relative phrase like 'X years ago', it must "
        f"be correct relative to {today.year}. Do not place any event in the future.\n\n"
        "Return ONLY a JSON object with these keys:\n"
        '  "backstory": a 2-3 paragraph life story consistent with the fixed facts (how they got '
        "from their birth city to now, career arc, family/relationship situation).\n"
        '  "voice_descriptor": 2-4 sentences describing their writing style, tone, and quirks.\n'
        f'  "signature_tells": use EXACTLY these {n_tells} habits, copied verbatim: {tells}. '
        "These are recurring verbal tics that show up across their posts.\n"
        '  "topics": 4-6 concrete recurring things they post about, grounded in their interests and life.\n'
        f'  "timeline": 3-5 objects like {{"month": "{today.strftime("%Y-%m")}", "event": "..."}} '
        "for the past 12 months, each month at or before today.\n"
        "No prose outside the JSON, no code fences."
    )
 
 
def _anthropic_bible(p, model, n_tells, tells, today):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model, max_tokens=1500, system=_system(p, n_tells, tells, today),
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
        pick = rng.choice(vocab.TELLS[cat])
        if pick not in chosen:
            chosen.append(pick)
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
 
 
def generate_bible(p, model, rng, use_llm, today):
    n_tells = TELLS_BY_LINKABILITY[p["linkability"]]
    tells = pick_tells(rng, n_tells)
    if use_llm:
        try:
            return _anthropic_bible(p, model, n_tells, tells, today)
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
    ap.add_argument("--today", default=None)
    args = ap.parse_args()
 
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
 
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
        p["bible"] = generate_bible(p, args.model, rng, use_llm, today)
        with open(path, "w") as f:
            json.dump(pop, f, indent=2)
        done += 1
        print(f"  bible for {pid} ({p['linkability']}, {p['bible']['_source']})")
 
    print(f"generated {done} bibles -> {path}")
 
 
if __name__ == "__main__":
    main()