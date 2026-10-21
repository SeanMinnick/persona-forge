import datetime
import json
import os
import random
import re

from dotenv import load_dotenv
load_dotenv()

from .. import contract
from . import platform
import opsec as opsec_mod
import vocab


def _display_name(persona, mode, handle, rng):
    first = persona["identity"]["first_name"]
    last = persona["identity"]["last_name"]
    if mode == "identity":
        return rng.choice([first, f"{first} {last[0]}.", f"{first} {last}"])
    if mode == "hint":
        return rng.choice([first, f"{first.lower()}", handle.rstrip("0123456789")])
    return handle.rstrip("0123456789")


def _location_field(persona, mode, rng):
    city_full = persona["attributes"]["city_country"]
    city = city_full.split(",")[0].strip()
    state = persona["geo"].get("home_state", "")
    if mode == "identity":
        return rng.choice([city_full.replace(", USA", ""), f"{city}", f"{city}, {state}"])
    if mode == "hint":
        return rng.choice([state, f"{state}, USA", ""])
    if mode == "generic_hint":
        return rng.choice(["", "USA", "somewhere"])
    return rng.choice(["", "the internet", "here and there"])


def _timestamps(schedule, count, today, rng):
    out = []
    jitter = schedule.get("post_hour_jitter", 1.0)
    for _ in range(count):
        day = today - datetime.timedelta(days=rng.randint(0, platform.WINDOW_DAYS))
        weekend = day.weekday() >= 5
        windows = schedule.get("weekend_online_windows" if weekend else "weekday_online_windows", [[9, 22]])
        w = rng.choice(windows) if windows else [9, 22]
        base = rng.uniform(w[0], max(w[0] + 0.5, w[1]))
        hour = int(min(23, max(0, base + rng.gauss(0, jitter))))
        dt = datetime.datetime(day.year, day.month, day.day, hour, rng.randint(0, 59), rng.randint(0, 59))
        out.append(dt)
    out.sort()
    return [dt.strftime("%Y-%m-%dT%H:%M:%S") for dt in out]


def _extract_hashtags(text):
    return re.findall(r"#\w+", text)


def _tell_line(persona):
    tells = persona.get("bible", {}).get("signature_tells", [])
    if not tells:
        return ""
    return f"Weave these exact verbal tics in naturally, verbatim, across some posts: {tells}.\n"


def _facts(persona):
    a = persona["attributes"]
    g = persona.get("geo", {})
    interests = ", ".join(persona.get("interests", [])) or "none in particular"
    return (
        f"- you are {a['age']} years old\n"
        f"- your job: {a['occupation']}\n"
        f"- you live in {a['city_country']} (state: {g.get('home_state', '')})\n"
        f"- you are originally from {a['birth_city_country']}\n"
        f"- relationship status: {a['relationship_status']}\n"
        f"- your real hobbies/interests: {interests}\n"
    )


def _system_signal(persona, n):
    b = persona.get("bible", {})
    voice = b.get("voice_descriptor", "casual and conversational")
    topics = b.get("topics", persona.get("interests", []))
    backstory = b.get("backstory", "")
    return (
        "You roleplay a fictional social-media user and write their Chirp content.\n\n"
        "GROUND TRUTH ABOUT YOU (fixed and true — never contradict, replace, or invent around these):\n"
        f"{_facts(persona)}\n"
        f"WHO YOU ARE (private backstory, do not restate):\n{backstory}\n\n"
        f"YOUR VOICE: {voice}\n"
        f"YOU POST ABOUT: {', '.join(topics)}\n"
        f"{_tell_line(persona)}"
        f"{platform.FORMAT_HINT}\n\n"
        f"Write {n} posts that each let something real from the GROUND TRUTH above slip INDIRECTLY, "
        "through concrete lived detail of your actual job, city, commute, household, hobbies, or "
        "relationships. Do NOT invent a different job, city, or lifestyle than the ground truth. "
        "Never state your age, job, or city word-for-word. Each post distinct.\n\n"
        'Return ONLY JSON: {"bio": "<one-line bio>", "posts": ["post 1", ...]}. '
        "No prose outside the JSON, no code fences."
    )


def _system_cover(persona, n_decoy, n_filler, decoys):
    voice = persona.get("bible", {}).get("voice_descriptor", "casual and conversational")
    sections, keys = [], []
    if n_decoy:
        sections.append(
            f'  "decoy" ({n_decoy} posts): substantive, opinionated posts strictly about these safe '
            f"topics: {', '.join(decoys)}. Have real takes and preferences about them, but say NOTHING "
            "about your job, city, household, routine, age, or relationships."
        )
        keys.append('"decoy": ["..."]')
    if n_filler:
        sections.append(
            f'  "filler" ({n_filler} posts): pure mundane noise with no substance at all — weather, being '
            "tired, food, a show, a passing reaction. Nothing anyone could learn from, and NOT about the "
            "decoy topics."
        )
        keys.append('"filler": ["..."]')
    distinct = (
        "Keep the two sets unmistakably different in register: decoy posts have a point of view, "
        "filler posts have none.\n"
        if n_decoy and n_filler else ""
    )
    return (
        "You roleplay a fictional social-media user and write their Chirp content.\n\n"
        f"YOUR VOICE: {voice}\n"
        f"{_tell_line(persona)}"
        f"{platform.FORMAT_HINT}\n\n"
        "Write the following sets of posts:\n"
        + "\n".join(sections) + "\n\n"
        + distinct
        + "Every post distinct.\n\n"
        f'Return ONLY JSON: {{{", ".join(keys)}}}, with exactly the counts above. '
        "No prose outside the JSON, no code fences."
    )


def _call(system, user):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=platform.MODEL, max_tokens=2000, system=system,
        messages=[{"role": "user", "content": user}],
    )
    raw = "".join(bl.text for bl in msg.content if bl.type == "text").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)


def _texts(data, n):
    out = [str(p).strip() for p in data.get("posts", []) if str(p).strip()]
    return out[:n]


_OFFLINE_POSTS = {
    "registered nurse": ["long shift again, on my feet all day, coffee is the only thing keeping me upright"],
    "software engineer": ["chased a race condition all morning, merged the fix, ci broke anyway lol"],
    "high school teacher": ["grading a stack of essays tonight, third period always has the best typos"],
}

_FILLER = [
    "the weather cannot make up its mind today",
    "why is every good show eight seasons long",
    "coffee number three and counting",
    "traffic was a nightmare but we made it",
    "sunday scaries hitting early this week",
    "ordered the same takeout for the third time, no regrets",
    "the group chat has been unhinged today",
    "finally folded the laundry that's been sitting for a week",
]

_DECOY_TEMPLATES = [
    "got back into {t} this month and honestly it's the only thing clearing my head",
    "unpopular opinion but {t} is way more interesting than people give it credit for",
    "spent the whole evening on {t} again, no regrets",
    "anyone else find {t} weirdly relaxing or is that just me",
]


def _decoys(persona, k, rng):
    real = set(persona.get("interests", []))
    pool = [t for t in vocab.INTEREST_TAGS if t not in real]
    if not pool:
        pool = list(vocab.INTEREST_TAGS)
    return rng.sample(pool, min(k, len(pool)))


def _offline_signal(persona, n):
    a = persona["attributes"]
    tells = persona.get("bible", {}).get("signature_tells", [])
    topics = persona.get("bible", {}).get("topics", persona.get("interests", []))
    base = _OFFLINE_POSTS.get(a["occupation"], ["another day, another to-do list that won't quit"])
    posts = []
    for i in range(n):
        t = base[i % len(base)]
        if tells and i % 2 == 0:
            t = f"{t} {tells[i % len(tells)]}"
        posts.append(t)
    bio = f"just here posting about {', '.join(topics[:2])} [offline stub]"
    return bio, posts


def _offline_decoy(persona, n, decoys):
    out = []
    for i in range(n):
        topic = decoys[i % len(decoys)] if decoys else "coffee"
        out.append(_DECOY_TEMPLATES[i % len(_DECOY_TEMPLATES)].format(t=topic))
    return out


def _offline_filler(persona, n):
    return [_FILLER[i % len(_FILLER)] for i in range(n)]


def _gen_cover(persona, n_decoy, n_filler, decoys):
    data = _call(_system_cover(persona, n_decoy, n_filler, decoys), "Write the posts now.")
    dec = [str(p).strip() for p in data.get("decoy", []) if str(p).strip()][:n_decoy]
    fil = [str(p).strip() for p in data.get("filler", []) if str(p).strip()][:n_filler]
    return dec, fil


def _generate(persona, counts, decoys, use_llm):
    n_signal, n_decoy, n_filler = counts
    bio, sig, dec, fil = "", [], [], []
    if use_llm:
        try:
            if n_signal:
                data = _call(_system_signal(persona, n_signal), f"Write my bio and {n_signal} chirp posts now.")
                bio, sig = str(data.get("bio", "")), _texts(data, n_signal)
            if n_decoy or n_filler:
                dec, fil = _gen_cover(persona, n_decoy, n_filler, decoys)
            return bio, {"signal": sig, "decoy": dec, "filler": fil}
        except Exception as e:
            print(f"  [chirp] LLM failed for {persona['persona_id']} ({e}); offline fallback")
    bio, sig = _offline_signal(persona, n_signal)
    dec = _offline_decoy(persona, n_decoy, decoys)
    fil = _offline_filler(persona, n_filler)
    return bio, {"signal": sig, "decoy": dec, "filler": fil}


def emit(personas, footprint, out_dir, seed, today):
    rng = random.Random(seed)
    use_llm = bool(os.environ.get("ANTHROPIC_API_KEY"))
    profiles, posts = [], []
    key = contract.new_module_key(platform.ID)
    pc = 0

    for persona_id, handles in footprint.get(platform.ID, {}).items():
        persona = personas[persona_id]
        o = persona["opsec"]
        mode = opsec_mod.handle_mode(o)
        schedule = persona.get("schedule", {})

        for handle in handles:
            key["account_to_persona"][handle] = persona_id
            n = rng.randint(platform.POST_MIN, platform.POST_MAX)

            draws = []
            for _ in range(n):
                s = opsec_mod.sample_signal(rng, o)
                sub = opsec_mod.sample_substance(rng)
                draws.append((s, sub, opsec_mod.route_post(s, sub)))

            counts = (
                sum(1 for d in draws if d[2] == "signal"),
                sum(1 for d in draws if d[2] == "decoy"),
                sum(1 for d in draws if d[2] == "filler"),
            )
            decoys = _decoys(persona, 3, rng) if counts[1] else []

            bio, by_kind = _generate(persona, counts, decoys, use_llm)
            if not bio and mode in ("identity", "hint"):
                bio = "just here [offline stub]"

            paired = []
            for s, sub, kind in draws:
                bucket = by_kind.get(kind, [])
                if not bucket:
                    continue
                paired.append((bucket.pop(0), s, sub, kind))

            pc += 1
            prof_id = f"chirp_prof_{pc:05d}"
            profiles.append(contract.make_record(
                prof_id, platform.ID, handle, channel=platform.CHANNEL, record_type="profile",
                handle=f"@{handle}",
                display_name=_display_name(persona, mode, handle, rng),
                bio=bio,
                location=_location_field(persona, mode, rng),
                join_date=f"{rng.randint(2015, 2024)}-{rng.randint(1, 12):02d}",
                post_count=rng.randint(max(1, len(paired)), 4000),
                follower_count=rng.randint(20, 3000),
                following_count=rng.randint(30, 1500),
            ))
            key["obs_to_persona"][prof_id] = persona_id

            stamps = _timestamps(schedule, len(paired), today, rng)
            geo_chance = opsec_mod.geotag_chance(o)
            for (text, s, sub, kind), ts in zip(paired, stamps):
                pc += 1
                post_id = f"chirp_post_{pc:05d}"
                geotag = None
                if kind == "signal" and rng.random() < geo_chance:
                    lat = persona["geo"]["home_lat"] + rng.gauss(0, 0.03)
                    lon = persona["geo"]["home_lon"] + rng.gauss(0, 0.03)
                    geotag = f"{lat:.4f},{lon:.4f}"
                posts.append(contract.make_record(
                    post_id, platform.ID, handle, channel=platform.CHANNEL, record_type="post",
                    text=text, timestamp=ts, post_type="original",
                    hashtags=_extract_hashtags(text), mentions=[],
                    like_count=rng.randint(0, 200), repost_count=rng.randint(0, 40),
                    client=rng.choice(platform.CLIENTS), geotag=geotag,
                    thread_id=None, parent_id=None,
                ))
                key["obs_to_persona"][post_id] = persona_id
                key["obs_signal"][post_id] = {"signal": s, "substance": sub, "kind": kind}

    prof_path = contract.write_observation_file(out_dir, "chirp_profiles.jsonl", profiles)
    post_path = contract.write_observation_file(out_dir, "chirp_posts.jsonl", posts)
    contract.write_module_key(out_dir, platform.ID, key)
    print(f"  [chirp] {len(profiles)} profiles, {len(posts)} posts")
    return {"observations": len(profiles) + len(posts),
            "profiles": len(profiles), "posts": len(posts),
            "prof_path": prof_path, "post_path": post_path}
