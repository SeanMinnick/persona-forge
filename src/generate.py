"""
generate.py - Reads ground-truth personas and writes afrozen dataset: 
an observation store (what the profiler sees)
an answer key (hidden truth for the scorer)
 
    python src/generate.py
 
"""
 
import json
import os
import random
from schema import to_observation, new_answer_key
from emitter import generate_posts
from platforms import get_platform
 
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSONAS_PATH = os.path.join(HERE, "personas", "personas.json")
OUT_DIR = os.path.join(HERE, "output", "baseline")
 
SEED = 42
POSTS_PER_ACCOUNT = 4
 
 
def account_key(platform_id, handle):
    return f"{platform_id}:{handle}"
 
 
def generate():
    rng = random.Random(SEED)
    with open(PERSONAS_PATH) as f:
        personas = json.load(f)
 
    observations = []
    key = new_answer_key()
    key["persona_meta"] = {}
    counter = 0
 
    for persona_id, persona in personas.items():
        key["persona_attributes"][persona_id] = persona["attributes"]
        key["persona_meta"][persona_id] = {
            "linkability": persona.get("linkability", "unspecified"),
            "accounts": [account_key(a["platform"], a["handle"]) for a in persona["accounts"]],
        }
        for account in persona["accounts"]:
            platform = get_platform(account["platform"])
            handle = account["handle"]
            key["account_to_persona"][account_key(platform.id, handle)] = persona_id
            print(f"generating {POSTS_PER_ACCOUNT} {platform.id} posts for {handle} ...")
            texts = generate_posts(persona["attributes"], platform, POSTS_PER_ACCOUNT, rng)
            for text in texts:
                counter += 1
                obs_id = f"obs_{counter:04d}"
                obs = to_observation(
                    obs_id=obs_id, account_id=handle, text=text,
                    channel=platform.channel, platform=platform.id,
                    timestamp=f"2026-03-{rng.randint(1, 28):02d}T"
                              f"{rng.randint(0, 23):02d}:00Z",
                    thread_id=f"{platform.id}_feed",
                )
                observations.append(obs)
                key["obs_to_persona"][obs_id] = persona_id
 
    os.makedirs(OUT_DIR, exist_ok=True)
    obs_path = os.path.join(OUT_DIR, "observations.jsonl")
    key_path = os.path.join(OUT_DIR, "answer_key.json")
    with open(obs_path, "w") as f:
        for obs in observations:
            f.write(json.dumps(obs) + "\n")
    with open(key_path, "w") as f:
        json.dump(key, f, indent=2)
 
    print(f"\nwrote {len(observations)} observations -> {obs_path}")
    print(f"wrote answer key ({len(key['obs_to_persona'])} obs, "
          f"{len(key['account_to_persona'])} accounts) -> {key_path}")
 
 
if __name__ == "__main__":
    generate()