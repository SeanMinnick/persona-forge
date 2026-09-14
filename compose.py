"""
compose.py - composes the dataset based on a population file within /populations
    this will kick off any modules that are flagged creating dataset output files for each within /output
 
    python compose.py
 
"""

import argparse
import datetime
import importlib
import json
import os
 
from modules import footprint as footprint_planner
 
HERE = os.path.dirname(os.path.abspath(__file__))
 
AVAILABLE_MODULES = ["chirp"]
 
def load_module(module_id):
    return importlib.import_module(f"modules.{module_id}")
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--today", default=None)
    for m in AVAILABLE_MODULES:
        ap.add_argument(f"--{m}", action="store_true")
    args = ap.parse_args()
 
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    requested = [m for m in AVAILABLE_MODULES if getattr(args, m)]
    if not requested:
        raise SystemExit(f"no modules selected. available: {', '.join('--'+m for m in AVAILABLE_MODULES)}")
 
    with open(args.input) as f:
        pop = json.load(f)
    personas = {k: v for k, v in pop.items() if k != "_meta"}
 
    run_name = args.out or f"run_seed{args.seed}_" + "-".join(requested)
    out_dir = os.path.join(HERE, "output", run_name)
    os.makedirs(out_dir, exist_ok=True)
 
    footprint = footprint_planner.plan(personas, requested, args.seed)
    key_dir = os.path.join(out_dir, "answer_key")
    os.makedirs(key_dir, exist_ok=True)
    with open(os.path.join(key_dir, "footprint.json"), "w") as f:
        json.dump(footprint, f, indent=2)
 
    results = {}
    for module_id in requested:
        mod = load_module(module_id)
        results[module_id] = mod.emit(personas, footprint, out_dir, args.seed, today)
 
    manifest = {
        "input": os.path.basename(args.input),
        "seed": args.seed,
        "today": today.isoformat(),
        "modules": requested,
        "personas": len(personas),
        "results": {k: v["observations"] for k, v in results.items()},
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
 
    print(f"\ncomposed dataset -> {out_dir}")
    print(f"  modules: {', '.join(requested)}")
    print(f"  manifest: {manifest['results']}")
 
 
if __name__ == "__main__":
    main()