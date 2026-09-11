"""
verify.py — the guardrail. Run this after generate.py to PROVE the observation
store leaks no identity. This is the check that protects every number you will
ever report: if persona_id or a raw attribute is sitting in the file the
profiler reads, your accuracy scores are fake.
 
    python src/verify.py
"""
 
import json
import os
from schema import ATTRIBUTES
 
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HERE, "output", "baseline")
ALLOWED_FIELDS = {
    "obs_id", "channel", "platform", "account_id",
    "timestamp", "thread_id", "parent_id", "geotag", "text",
}
BANNED_FIELDS = {"persona_id", "persona", "attributes", *ATTRIBUTES}
 
 
def verify():
    obs_path = os.path.join(OUT_DIR, "observations.jsonl")
    key_path = os.path.join(OUT_DIR, "answer_key.json")
    with open(key_path) as f:
        key = json.load(f)
 
    problems = []
    n = 0
    for line in open(obs_path):
        n += 1
        obs = json.loads(line)
        # 1. No banned field names present.
        for bad in BANNED_FIELDS & set(obs.keys()):
            problems.append(f"{obs.get('obs_id')}: leaked field '{bad}'")
        # 2. No unexpected fields at all.
        for extra in set(obs.keys()) - ALLOWED_FIELDS:
            problems.append(f"{obs.get('obs_id')}: unexpected field '{extra}'")
        # 3. The persona_id string itself must not appear anywhere in the record.
        persona_id = key["obs_to_persona"].get(obs["obs_id"], "")
        if persona_id and persona_id in json.dumps(obs):
            problems.append(f"{obs['obs_id']}: persona_id string appears in record")
 
    if problems:
        print(f"FAIL — {len(problems)} boundary violation(s):")
        for p in problems[:20]:
            print("  -", p)
        raise SystemExit(1)
    print(f"PASS — checked {n} observations, no identity leaked into the store.")
 
 
if __name__ == "__main__":
    verify()