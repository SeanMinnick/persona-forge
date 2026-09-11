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
from emitter import generate_comments
 
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSONAS_PATH = os.path.join(HERE, "personas", "personas.json")
OUT_DIR = os.path.join(HERE, "output", "baseline")
 
SEED = 42
COMMENTS_PER_ACCOUNT = 4
 
 
def generate():
    rng = random.Random(SEED)
    with open(PERSONAS_PATH) as f:
        personas = json.load(f)
 
    observations = []
    key = new_answer_key()
    thread_id = "thread_general_1"
    counter = 0
 
    for persona_id, persona in personas.items():
        key["persona_attributes"][persona_id] = persona["attributes"]
        for account_id in persona["accounts"]:
            key["account_to_persona"][account_id] = persona_id
            print(f"generating {COMMENTS_PER_ACCOUNT} comments for {account_id} ...")
            texts = generate_comments(
                persona_id, persona["attributes"], COMMENTS_PER_ACCOUNT, rng
            )
            for text in texts:
                counter += 1
                obs_id = f"obs_{counter:04d}"
                obs = to_observation(
                    obs_id=obs_id, account_id=account_id, text=text,
                    timestamp=f"2026-03-{rng.randint(1, 28):02d}T"
                              f"{rng.randint(0, 23):02d}:00Z",
                    thread_id=thread_id,
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
    print(f"wrote answer key ({len(key['obs_to_persona'])} obs mapped) -> {key_path}")
 
 
if __name__ == "__main__":
    generate()