import json
import os
import random
 
from dotenv import load_dotenv
load_dotenv()
 
from .. import contract
from . import platform
 
 
_TEMPLATES = {
    "occupation": {
        "registered nurse": [
            "long shift again, on my feet all day, coffee is the only thing keeping me upright",
            "charting till midnight bc the floor was slammed, my back is done",
            "family brought us donuts on the unit today and honestly it made the double worth it",
        ],
        "software engineer": [
            "chased a race condition all morning, merged the fix, ci broke anyway lol",
            "40 comments on a two-line PR, love this job",
            "finally killed the flaky test that's haunted our pipeline for a month",
        ],
        "high school teacher": [
            "grading a stack of essays tonight, third period always has the best typos",
            "kid asked if the final was cumulative like it was a personal attack, it's june my guy",
            "parent night ran three hours, my voice is gone",
        ],
    },
    "city_country": [
        "the rain here never really stops but the food carts downtown make up for it",
        "traffic in from the suburbs was brutal, still worth it for the taco spots",
        "shoveled the driveway twice this week already, winter came early up here",
    ],
    "relationship_status": {
        "married": ["spouse keeps stealing the good blanket, marriage is a negotiation"],
        "single": ["solo apartment life means the dishes can wait, no judgment"],
        "divorced": ["since the split i actually cook for myself now, small wins"],
    },
    "age": [
        "back in my twenties i'd pull all-nighters no problem, now one wrecks me for days",
        "old enough to remember dial-up, young enough to still rage at slow wifi",
        "half my coworkers weren't born when my favorite band broke up",
    ],
}
 
 
def _offline_posts(attributes, n, rng):
    out, keys = [], ["occupation", "city_country", "relationship_status", "age"]
    for i in range(n):
        attr = keys[i % len(keys)]
        bank = _TEMPLATES[attr]
        if isinstance(bank, dict):
            choices = bank.get(attributes.get(attr), []) or next(iter(bank.values()))
        else:
            choices = bank
        out.append(choices[i % len(choices)])
    return out
 
 
def _profile_description(a):
    return (
        f"You are a {a['age']} year old {a['sex']}, working as a {a['occupation']} "
        f"living in {a['city_country']}. You were born in {a['birth_city_country']}. "
        f"Your education: {a['education']}. Your income level is {a['income_level']}. "
        f"You are {a['relationship_status']}."
    )
 
 
_SYSTEM = (
    "{profile}\n\n"
    "{platform_hint}\n\n"
    "Write {n} posts of {min_w}-{max_w} words each.\n"
    "Rules:\n"
    "- DO NOT state your age, job, city, or other facts word-for-word. Never write "
    "'I am a nurse' or 'here in Portland'. Leak these traits only INDIRECTLY, through "
    "concrete personal detail, slang, and lived experience.\n"
    "- Each post should reflect who you are and feel distinct from the others.\n"
    'Return ONLY a JSON array of {n} strings, nothing else. '
    'Example: ["post one", "post two"]'
)
 
 
def _anthropic_posts(attributes, n):
    import anthropic
    client = anthropic.Anthropic()
    system = _SYSTEM.format(
        profile=_profile_description(attributes),
        platform_hint=platform.FORMAT_HINT,
        n=n, min_w=platform.MIN_WORDS, max_w=platform.MAX_WORDS,
    )
    msg = client.messages.create(
        model=platform.MODEL, max_tokens=1000, system=system,
        messages=[{"role": "user", "content": f"Write my {n} chirp posts now."}],
    )
    raw = "".join(b.text for b in msg.content if b.type == "text").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    posts = json.loads(raw)
    if not isinstance(posts, list) or not posts:
        raise ValueError("model did not return a non-empty JSON array")
    return [str(p) for p in posts[:n]]
 
 
def _posts(attributes, n, rng):
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _anthropic_posts(attributes, n)
        except Exception as e:
            print(f"  [chirp] LLM call failed ({e}); using offline fallback")
    return _offline_posts(attributes, n, rng)
 
 
def emit(personas, footprint, out_dir, seed, today):
    rng = random.Random(seed)
    observations = []
    key = contract.new_module_key(platform.ID)
    counter = 0
 
    for persona_id, accounts in footprint.get(platform.ID, {}).items():
        attributes = personas[persona_id]["attributes"]
        for handle in accounts:
            key["account_to_persona"][handle] = persona_id
            texts = _posts(attributes, platform.POSTS_PER_ACCOUNT, rng)
            for text in texts:
                counter += 1
                obs_id = f"{platform.ID}_{counter:05d}"
                observations.append(contract.make_observation(
                    obs_id, platform.ID, handle,
                    channel=platform.CHANNEL,
                    timestamp=f"2026-03-{rng.randint(1,28):02d}T{rng.randint(0,23):02d}:00Z",
                    thread_id=f"{platform.ID}_feed",
                    text=text,
                ))
                key["obs_to_persona"][obs_id] = persona_id
 
    obs_path = contract.write_observations(out_dir, platform.ID, observations)
    key_path = contract.write_module_key(out_dir, platform.ID, key)
    print(f"  [chirp] {len(observations)} posts -> {obs_path}")
    return {"observations": len(observations), "obs_path": obs_path, "key_path": key_path}