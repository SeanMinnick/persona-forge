"""
verify.py - this verifies the composed dataset does not leak data directly to the profiler

    python verify.py
 
"""

import argparse
import json
import os
 
from modules import contract
 
BANNED_SUBSTRINGS = ["persona_id", "pers_"]
STUB_MARKERS = ["[offline stub]"]
 
 
def verify(out_dir, freeze=False):
    obs_dir = os.path.join(out_dir, "observations")
    key_dir = os.path.join(out_dir, "answer_key")
    problems = []
    total = 0
 
    persona_ids = set()
    for fn in os.listdir(key_dir):
        if fn == "footprint.json":
            fp = json.load(open(os.path.join(key_dir, fn)))
            for accounts in fp.values():
                persona_ids.update(accounts.keys())
 
    for fn in os.listdir(obs_dir):
        for line in open(os.path.join(obs_dir, fn)):
            total += 1
            obs = json.loads(line)
            for field in obs:
                if field not in contract.ALLOWED_OBS_FIELDS:
                    problems.append(f"{fn}:{obs.get('obs_id')} unexpected field '{field}'")
            for attr in contract.ATTRIBUTES:
                if attr in obs:
                    problems.append(f"{fn}:{obs.get('obs_id')} leaked attribute '{attr}'")
            blob = json.dumps(obs)
            for pid in persona_ids:
                if pid in blob:
                    problems.append(f"{fn}:{obs.get('obs_id')} persona_id '{pid}' in record")
            for banned in BANNED_SUBSTRINGS:
                if banned in blob:
                    problems.append(f"{fn}:{obs.get('obs_id')} banned substring '{banned}' in record")
            if freeze:
                for marker in STUB_MARKERS:
                    if marker in blob:
                        problems.append(f"{fn}:{obs.get('obs_id')} stub marker '{marker}' in record")
 
    if freeze:
        for fn in os.listdir(key_dir):
            if fn == "footprint.json":
                continue
            k = json.load(open(os.path.join(key_dir, fn)))
            meta = k.get("account_meta", {})
            if not meta:
                problems.append(f"{fn} has no account_meta; regenerate with the current emitter")
            for handle, am in meta.items():
                gen = am.get("generation", {})
                if gen.get("source") != "llm":
                    problems.append(f"{fn}:{handle} not LLM-generated (source={gen.get('source')})")
                if any(gen.get("short", {}).values()):
                    problems.append(f"{fn}:{handle} short on posts {gen.get('short')}")

    if problems:
        print(f"FAIL — {len(problems)} boundary violation(s) across {total} observations:")
        for p in problems[:20]:
            print("  -", p)
        raise SystemExit(1)
    print(f"PASS — checked {total} observations across all modules, no identity leaked.")
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()
    verify(args.out_dir, args.freeze)
 
 
if __name__ == "__main__":
    main()