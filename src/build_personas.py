"""
build_personas.py - creates the ground truth personas based on vocab.py. This is used by the emitter and generator to create the dataset.
 
    python src/build_personas.py
 
"""

import argparse
import json
import os
import random
import vocab
 
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSONAS_DIR = os.path.join(HERE, "personas")

def default_out_path(n, seed):
    return os.path.join(PERSONAS_DIR, f"population_n{n}_seed{seed}.json")

DEFAULT_SEED = 42
DEFAULT_N = 50
PROTECTED_FRACTION = 0.2
LINKABILITY_WEIGHTS = [0.3, 0.35, 0.25, 0.1]
SEX_WEIGHTS = [0.49, 0.49, 0.01]
 
 
def sample_age(rng, occ):
    if occ["edu"].startswith("studying") or occ["occupation"].startswith("part-time"):
        return rng.randint(18, 24)
    if occ["edu"].startswith("Doctorate") or occ["edu"] == "Juris Doctor":
        return rng.randint(30, 62)
    return rng.randint(23, 64)
 
 
def sample_relationship(rng, age):
    if age < 25:
        return rng.choices(vocab.RELATIONSHIP_STATUS, weights=[45, 20, 9, 3, 1, 22])[0]
    if age < 40:
        return rng.choices(vocab.RELATIONSHIP_STATUS, weights=[27, 23, 33, 8, 1, 8])[0]
    return rng.choices(vocab.RELATIONSHIP_STATUS, weights=[14, 14, 43, 21, 8, 0])[0]
 
 
def sample_name(rng, sex):
    if sex == "male":
        first = rng.choice(vocab.FIRST_NAMES_M)
    elif sex == "female":
        first = rng.choice(vocab.FIRST_NAMES_F)
    else:
        first = rng.choice(vocab.FIRST_NAMES_N)
    last = rng.choice(vocab.LAST_NAMES)
    return first, last
 
 
def sample_birth_city(rng, home):
    if rng.random() < 0.45:
        return home
    return rng.choice(vocab.CITIES)
 
def make_schedule(rng, occ):
    early = occ["occupation"] in (
        "registered nurse", "line cook", "warehouse associate", "part-time barista",
        "paramedic", "firefighter", "bus driver", "truck driver", "chef", "construction worker",
    )
    wake = rng.choice([5, 6]) if early else rng.choice([6, 7, 8])
    work_start = wake + rng.choice([1, 2])
    work_hours = rng.choice([8, 9, 10])
    sleep = rng.choice([22, 23, 0])
    evening_start = (work_start + work_hours) % 24
    return {
        "wake_hour": wake,
        "sleep_hour": sleep,
        "work_start_hour": work_start % 24,
        "work_hours": work_hours,
        "weekday_online_windows": [
            [wake, wake + 1],
            [12, 13],
            [evening_start, min(evening_start + 3, 24)],
        ],
        "weekend_online_windows": [[max(wake + 2, 9), 12], [15, 18], [20, 23]],
        "post_hour_jitter": rng.choice([0.5, 1.0, 1.5]),
    }
 
 
def build_population(n, seed):
    rng = random.Random(seed)
    personas = {}
    n_protected = max(1, round(n * PROTECTED_FRACTION))
 
    for i in range(n):
        pid = f"pers_{i + 1:03d}"
        sex = rng.choices(vocab.SEX, weights=SEX_WEIGHTS)[0]
        occ = rng.choice(vocab.OCCUPATIONS)
        age = sample_age(rng, occ)
        first, last = sample_name(rng, sex)
        home = rng.choice(vocab.CITIES)
        born = sample_birth_city(rng, home)
        rel = sample_relationship(rng, age)
        interests = rng.sample(vocab.INTEREST_TAGS, k=rng.randint(2, 4))
        linkability = rng.choices(vocab.LINKABILITY, weights=LINKABILITY_WEIGHTS)[0]
        tier = "protected" if i < n_protected else "background"
 
        personas[pid] = {
            "persona_id": pid,
            "tier": tier,
            "linkability": linkability,
            "identity": {
                "first_name": first,
                "last_name": last,
                "sex": sex,
                "age": age,
            },
            "attributes": {
                "age": age,
                "sex": sex,
                "city_country": home["city_country"],
                "birth_city_country": born["city_country"],
                "education": occ["edu"],
                "occupation": occ["occupation"],
                "income_level": occ["income_level"],
                "relationship_status": rel,
            },
            "geo": {
                "home_city": home["city_country"],
                "home_state": home["state"],
                "home_lat": home["lat"],
                "home_lon": home["lon"],
                "timezone": home["tz"],
            },
            "interests": interests,
            "schedule": make_schedule(rng, occ),
        }
 
    return personas
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=DEFAULT_N)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out_path = args.out or default_out_path(args.n, args.seed)
 
    population = build_population(args.n, args.seed)
    meta = {
        "_meta": {
            "count": len(population),
            "seed": args.seed,
            "protected_fraction": PROTECTED_FRACTION,
            "version": f"n{args.n}_seed{args.seed}",
        }
    }
    out = {**meta, **population}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {len(population)} personas (seed={args.seed}) -> {out_path}")
 
 
if __name__ == "__main__":
    main()