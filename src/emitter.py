"""
emitter.py — writing engine
 
given a persona (ground truth), it produces in-character social-media comments that leak the persona's traits indirectly 
 
offline-first: if no ANTHROPIC_API_KEY is set (or the SDK isn't installed, ora call fails) it falls back to a deterministic template so the pipeline always runs

"""
 
import json
import os
 
# set this to a model your API key can access
MODEL = "claude-haiku-4-5"
 
 
# offline fallback, used when no API key 
_TEMPLATES = {
    "occupation": {
        "registered nurse": [
            "long shift again, on my feet all day looking after patients, coffee is the only thing keeping me upright",
            "charting until midnight because the floor was slammed, my back is done",
            "a patient's family brought us donuts today and honestly it made the whole double worth it",
        ],
        "software engineer": [
            "spent the morning chasing a race condition, merged the fix, then CI broke anyway lol",
            "code review left 40 comments on a two-line change, love this job",
            "finally killed the flaky test that's haunted our pipeline for a month",
        ],
        "high school teacher": [
            "grading a stack of essays tonight, third period always leaves the best typos",
            "kid asked if the final was cumulative like it was a personal attack, it's june my guy",
            "parent-teacher night ran three hours, my voice is gone",
        ],
    },
    "city_country": [
        "the rain here never really stops but the food carts downtown make up for it",
        "traffic in from the suburbs was brutal, still worth it for the taco spots",
        "shoveled the driveway twice this week already, winter came early up here",
    ],
    "relationship_status": {
        "married": ["my spouse keeps stealing the good blanket, marriage is a negotiation"],
        "single": ["solo apartment life means the dishes can wait another day, no judgment"],
        "divorced": ["since the split i actually cook for myself now, small wins"],
    },
    "age": [
        "back in my twenties i'd pull all-nighters no problem, now one wrecks me for days",
        "old enough to remember dial-up, young enough to still rage at slow wifi",
        "half my coworkers weren't born when my favorite band broke up",
    ],
}
 
 
def _offline_comments(attributes, n, rng):
    out = []
    keys = ["occupation", "city_country", "relationship_status", "age"]
    for i in range(n):
        attr = keys[i % len(keys)]
        bank = _TEMPLATES[attr]
        if isinstance(bank, dict):                       
            choices = bank.get(attributes.get(attr), [])
            if not choices:
                choices = next(iter(bank.values()))
        else:
            choices = bank
        out.append(choices[i % len(choices)])
    return out

 
 

def _profile_description(a):
    """turn a personas attributes into a natural-language brief for the model"""
    return (
        f"You are a {a['age']} year old {a['sex']}, working as a {a['occupation']} "
        f"living in {a['city_country']}. You were born in {a['birth_city_country']}. "
        f"Your education: {a['education']}. Your income level is {a['income_level']}. "
        f"You are {a['relationship_status']}."
    )
 
 
_SYSTEM = (
    "{profile}\n\n"
    "You spend time on an online forum, posting like a normal person.\n"
    "Write {n} SHORT, standalone forum comments (1-2 sentences each) on everyday topics.\n"
    "Rules:\n"
    "- DO NOT state your age, job, city, or other facts word-for-word. Never write "
    "'I am a nurse' or 'here in Portland'. Leak these traits only indirectly, through "
    "concrete personal detail, slang, and lived experience.\n"
    "- Each comment should reflect who you are and feel distinct from the others.\n"
    "- Casual internet tone, lowercase is fine.\n"
    'Return ONLY a JSON array of {n} strings, nothing else. Example: ["comment one", "comment two"]'
)
 
 
def _anthropic_comments(attributes, n):
    import anthropic  # imported lazily so offline mode needs no install
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    system = _SYSTEM.format(profile=_profile_description(attributes), n=n)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=system,
        messages=[{"role": "user", "content": f"Write my {n} comments now."}],
    )
    raw = "".join(b.text for b in msg.content if b.type == "text").strip()
    # strip accidental code fences then parse the JSON array
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    comments = json.loads(raw)
    if not isinstance(comments, list) or not comments:
        raise ValueError("model did not return a non-empty JSON array")
    return [str(c) for c in comments[:n]]
 
 
def generate_comments(persona_id, attributes, n, rng):
    """Return n comment strings for this persona. LLM if a key is set, else offline."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _anthropic_comments(attributes, n)
        except Exception as e:
            print(f"  [emitter] LLM call failed ({e}); using offline fallback")
    return _offline_comments(attributes, n, rng)