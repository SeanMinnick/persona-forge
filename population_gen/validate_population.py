import argparse
import datetime
import json
import os
import vocab
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import opsec as opsec_mod
 
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "populations")
 
ATTR_KEYS = ["age", "sex", "city_country", "birth_city_country", "education", "occupation", "income_level", "relationship_status"]
 
CITY_SET = {c["city_country"] for c in vocab.CITIES}
CITY_BY_CC = {c["city_country"]: c for c in vocab.CITIES}
OCC_SET = {o["occupation"] for o in vocab.OCCUPATIONS}
EDU_BY_OCC = {o["occupation"]: o["edu"] for o in vocab.OCCUPATIONS}
INC_BY_OCC = {o["occupation"]: o["income_level"] for o in vocab.OCCUPATIONS}
INTEREST_SET = set(vocab.INTEREST_TAGS)
ALL_TELLS = {t for cat in vocab.TELLS.values() for t in cat}
 
 
def default_pop_path(n, seed):
    return os.path.join(DATA_DIR, f"population_n{n}_seed{seed}.json")
 
 
def check_persona(pid, p, today, errors, warnings):
    def err(msg):
        errors.append(f"{pid}: {msg}")
 
    def warn(msg):
        warnings.append(f"{pid}: {msg}")
 
    a = p.get("attributes", {})
    ident = p.get("identity", {})
    geo = p.get("geo", {})
 
    for k in ATTR_KEYS:
        if k not in a:
            err(f"missing attribute '{k}'")
 
    if a.get("sex") not in vocab.SEX:
        err(f"sex '{a.get('sex')}' not in vocab.SEX")
    if a.get("relationship_status") not in vocab.RELATIONSHIP_STATUS:
        err(f"relationship_status '{a.get('relationship_status')}' not in vocab")
    o = p.get("opsec")
    if not isinstance(o, int) or not (opsec_mod.OPSEC_MIN <= o <= opsec_mod.OPSEC_MAX):
        err(f"opsec '{o}' not an int in [{opsec_mod.OPSEC_MIN},{opsec_mod.OPSEC_MAX}]")
    if p.get("tier") not in vocab.TIER:
        err(f"tier '{p.get('tier')}' not in vocab")
 
    occ = a.get("occupation")
    if occ not in OCC_SET:
        err(f"occupation '{occ}' not in vocab")
    else:
        if a.get("education") != EDU_BY_OCC[occ]:
            err(f"education '{a.get('education')}' does not match occupation '{occ}' (expected '{EDU_BY_OCC[occ]}')")
        if a.get("income_level") != INC_BY_OCC[occ]:
            err(f"income_level '{a.get('income_level')}' does not match occupation '{occ}' (expected '{INC_BY_OCC[occ]}')")
 
    for field in ("city_country", "birth_city_country"):
        if a.get(field) not in CITY_SET:
            err(f"{field} '{a.get(field)}' not in vocab.CITIES")
 
    home_cc = a.get("city_country")
    if home_cc in CITY_BY_CC:
        c = CITY_BY_CC[home_cc]
        if abs(geo.get("home_lat", 0) - c["lat"]) > 0.01 or abs(geo.get("home_lon", 0) - c["lon"]) > 0.01:
            err(f"geo coords {geo.get('home_lat')},{geo.get('home_lon')} do not match {home_cc} {c['lat']},{c['lon']}")
        if geo.get("timezone") != c["tz"]:
            err(f"timezone '{geo.get('timezone')}' does not match {home_cc} ('{c['tz']}')")
        if geo.get("home_city") != home_cc:
            warn(f"geo.home_city '{geo.get('home_city')}' != attributes.city_country '{home_cc}'")
 
    if ident.get("age") != a.get("age"):
        err(f"identity.age {ident.get('age')} != attributes.age {a.get('age')}")
    if ident.get("sex") != a.get("sex"):
        err(f"identity.sex '{ident.get('sex')}' != attributes.sex '{a.get('sex')}'")
 
    age = a.get("age")
    if isinstance(age, int) and not (16 <= age <= 100):
        err(f"age {age} out of plausible range")
 
    for tag in p.get("interests", []):
        if tag not in INTEREST_SET:
            err(f"interest '{tag}' not in vocab.INTEREST_TAGS")
 
    sched = p.get("schedule", {})
    for k in ("wake_hour", "sleep_hour", "work_start_hour"):
        v = sched.get(k)
        if v is None or not (0 <= v <= 23):
            err(f"schedule.{k} '{v}' out of range 0-23")
 
    bible = p.get("bible")
    if bible is None:
        warn("no bible yet")
        return
 
    n_expected = opsec_mod.tells_count(o) if isinstance(o, int) else None
    tells = bible.get("signature_tells", [])
    if n_expected is not None and len(tells) != n_expected:
        err(f"bible has {len(tells)} tells, expected {n_expected} for opsec {o}")
    for t in tells:
        if t not in ALL_TELLS:
            err(f"bible tell '{t}' not in vocab.TELLS (invented?)")
    if len(tells) != len(set(tells)):
        err("bible has duplicate signature_tells")
 
    born_year = today.year - age if isinstance(age, int) else None
    for entry in bible.get("timeline", []):
        month = entry.get("month", "")
        try:
            y, m = int(month[:4]), int(month[5:7])
            d = datetime.date(y, m, 1)
        except (ValueError, IndexError):
            err(f"timeline month '{month}' not YYYY-MM")
            continue
        if d > today.replace(day=1):
            err(f"timeline event dated {month} is in the future (today {today.isoformat()})")
        if born_year and y < born_year:
            err(f"timeline event {month} predates birth year {born_year}")
 
    for field in ("backstory", "voice_descriptor", "topics"):
        if not bible.get(field):
            err(f"bible missing '{field}'")
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--path", default=None)
    ap.add_argument("--today", default=None)
    args = ap.parse_args()
 
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    path = args.path or default_pop_path(args.n, args.seed)
    with open(path) as f:
        pop = json.load(f)
 
    errors, warnings = [], []
    pids = [k for k in pop if k != "_meta"]
    for pid in pids:
        check_persona(pid, pop[pid], today, errors, warnings)
 
    names = {}
    for pid in pids:
        i = pop[pid].get("identity", {})
        key = (i.get("first_name"), i.get("last_name"))
        names.setdefault(key, []).append(pid)
    collisions = {f"{a} {b}": v for (a, b), v in names.items() if len(v) > 1}
 
    print(f"validated {len(pids)} personas in {os.path.basename(path)} (today={today.isoformat()})")
    print(f"  errors:   {len(errors)}")
    print(f"  warnings: {len(warnings)}")
    for e in errors:
        print("  ERROR  ", e)
    for w in warnings:
        print("  warn   ", w)
    if collisions:
        print(f"  name collisions ({len(collisions)}): {collisions}")
    else:
        print("  name collisions: none")
 
    raise SystemExit(1 if errors else 0)
 
 
if __name__ == "__main__":
    main()