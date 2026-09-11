import datetime
import json
import os
import random
import re
 
from dotenv import load_dotenv
load_dotenv()
 
from .. import contract
from . import platform
 
 
def _display_name(persona, link, handle, rng):
    first = persona["identity"]["first_name"]
    last = persona["identity"]["last_name"]
    if link == "careless":
        return rng.choice([first, f"{first} {last[0]}.", f"{first} {last}"])
    if link == "moderate":
        return rng.choice([first, f"{first.lower()}", handle.rstrip("0123456789")])
    return handle.rstrip("0123456789")
 
 
def _location_field(persona, link, rng):
    city_full = persona["attributes"]["city_country"]
    city = city_full.split(",")[0].strip()
    state = persona["geo"].get("home_state", "")
    if link == "careless":
        return rng.choice([city_full.replace(", USA", ""), f"{city}", f"{city}, {state}"])
    if link == "moderate":
        return rng.choice([state, f"{state}, USA", ""])
    if link == "disciplined":
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
 
 
def _system(persona, n, link, n_filler):
    b = persona.get("bible", {})
    voice = b.get("voice_descriptor", "casual and conversational")
    topics = b.get("topics", persona.get("interests", []))
    tells = b.get("signature_tells", [])
    backstory = b.get("backstory", "")
    tell_line = (
        f"Weave these exact verbal tics in naturally, verbatim, across some posts: {tells}.\n"
        if tells else ""
    )
    filler_line = (
        f"Of the {n} posts, about {n_filler} should be pure mundane FILLER that reveals nothing "
        "identifying — weather, food, being tired, a show, a generic reaction. The rest reflect who you are.\n"
        if n_filler else ""
    )
    return (
        "You roleplay a fictional social-media user and write their Chirp content.\n\n"
        f"WHO YOU ARE (private, do not restate):\n{backstory}\n\n"
        f"YOUR VOICE: {voice}\n"
        f"YOU POST ABOUT: {', '.join(topics)}\n"
        f"{tell_line}\n"
        f"{platform.FORMAT_HINT}\n\n"
        f"BIO INSTRUCTION: {platform.BIO_LEAKAGE.get(link, platform.BIO_LEAKAGE['moderate'])}\n\n"
        f"POST LEAKAGE: {platform.POST_LEAKAGE.get(link, platform.POST_LEAKAGE['moderate'])}\n"
        f"{filler_line}"
        "POST RULES: When a post does reveal something, do it INDIRECTLY through concrete lived "
        "detail, never stating your age, job, or city word-for-word. Each post distinct.\n\n"
        f'Return ONLY JSON: {{"bio": "<one-line bio>", "posts": ["post 1", ... {n} posts]}}. '
        "No prose outside the JSON, no code fences."
    )
 
 
def _anthropic_bio_posts(persona, n, link, n_filler):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=platform.MODEL, max_tokens=1500, system=_system(persona, n, link, n_filler),
        messages=[{"role": "user", "content": f"Write my bio and {n} chirp posts now."}],
    )
    raw = "".join(bl.text for bl in msg.content if bl.type == "text").strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    data = json.loads(raw)
    posts = [str(p) for p in data.get("posts", [])][:n]
    if not posts:
        raise ValueError("model returned no posts")
    return str(data.get("bio", "")), posts
 
 
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
 
 
def _offline_bio_posts(persona, n, link, n_filler, rng):
    a = persona["attributes"]
    tells = persona.get("bible", {}).get("signature_tells", [])
    topics = persona.get("bible", {}).get("topics", persona.get("interests", []))
    base = _OFFLINE_POSTS.get(a["occupation"], ["another day, another to-do list that won't quit"])
    n_topical = max(0, n - n_filler)
    posts = []
    for i in range(n_topical):
        t = base[i % len(base)]
        if tells and i % 2 == 0:
            t = f"{t} {tells[i % len(tells)]}"
        posts.append(t)
    for i in range(n_filler):
        posts.append(_FILLER[i % len(_FILLER)])
    rng.shuffle(posts)
    bio = "" if link in ("disciplined", "meticulous") else f"just here posting about {', '.join(topics[:2])} [offline stub]"
    return bio, posts
 
 
def _bio_posts(persona, n, link, n_filler, rng):
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _anthropic_bio_posts(persona, n, link, n_filler)
        except Exception as e:
            print(f"  [chirp] LLM call failed for {persona['persona_id']} ({e}); offline fallback")
    return _offline_bio_posts(persona, n, link, n_filler, rng)
 
 
def emit(personas, footprint, out_dir, seed, today):
    rng = random.Random(seed)
    profiles, posts = [], []
    key = contract.new_module_key(platform.ID)
    pc = 0
 
    for persona_id, handles in footprint.get(platform.ID, {}).items():
        persona = personas[persona_id]
        link = persona.get("linkability", "moderate")
        schedule = persona.get("schedule", {})
        for handle in handles:
            key["account_to_persona"][handle] = persona_id
            n = rng.randint(platform.POST_MIN, platform.POST_MAX)
            n_filler = round(n * platform.FILLER_RATIO.get(link, 0.3))
            bio, texts = _bio_posts(persona, n, link, n_filler, rng)
            texts = texts[:n]
 
            pc += 1
            prof_id = f"chirp_prof_{pc:05d}"
            profiles.append(contract.make_record(
                prof_id, platform.ID, handle, channel=platform.CHANNEL, record_type="profile",
                handle=f"@{handle}",
                display_name=_display_name(persona, link, handle, rng),
                bio=bio,
                location=_location_field(persona, link, rng),
                join_date=f"{rng.randint(2015, 2024)}-{rng.randint(1, 12):02d}",
                post_count=rng.randint(len(texts), 4000),
                follower_count=rng.randint(20, 3000),
                following_count=rng.randint(30, 1500),
            ))
            key["obs_to_persona"][prof_id] = persona_id
 
            stamps = _timestamps(schedule, len(texts), today, rng)
            geo_chance = platform.GEOTAG_CHANCE.get(link, 0.0)
            for text, ts in zip(texts, stamps):
                pc += 1
                post_id = f"chirp_post_{pc:05d}"
                geotag = None
                if rng.random() < geo_chance:
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
 
    prof_path = contract.write_observation_file(out_dir, "chirp_profiles.jsonl", profiles)
    post_path = contract.write_observation_file(out_dir, "chirp_posts.jsonl", posts)
    contract.write_module_key(out_dir, platform.ID, key)
    print(f"  [chirp] {len(profiles)} profiles, {len(posts)} posts")
    return {"observations": len(profiles) + len(posts),
            "profiles": len(profiles), "posts": len(posts),
            "prof_path": prof_path, "post_path": post_path}