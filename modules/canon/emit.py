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

# for image generation
import base64
from pathlib import Path
IMAGE_GENERATION_DISABLED = (os.environ.get("CANON_IMAGES", "1") != "1"
                             or os.environ.get("LLM_OFFLINE") == "1")

"""
Instagram Posts:
- username
- picture/post
- caption
- optional: location
- date
"""
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

# Photo/Post
"""
What to have/analyze in photo
- subject (person, dog, etc,)
- background (work place, lab, gym, etc)
- any props or things the person is holding 
"""
def _post_field(persona, mode, rng):
    if mode == "identity":
        return rng.choice(["a photo reflecting the persona's everyday life", 
                           "a candid photo consistent with person's lifestyle", 
                           "a realistic photo of something the persona would plausibly post",
                           ])
    if mode == "hint":
        return rng.choice(["a photo with hints of the persona's lifestyle", "an everyday phone snapshot"])
    return rng.choice(["", "a candid, everyday photo", "a realistic social media post"])

def generate_photo(prompt, post_id, out_dir):
    global IMAGE_GENERATION_DISABLED

    if IMAGE_GENERATION_DISABLED:
        return None
    try:
        from openai import OpenAI

        client = OpenAI()

        result = client.images.generate(
            model=platform.IMAGE_MODEL,
            prompt=(
                "Create a fictional, synthetic social-media photograph. "
                "Use natural smartphone photography, realistic lighting, "
                "and everyday composition. Do not imitate an actual person's "
                "identity or reproduce a real person's photograph. "
                + prompt
            ),
            # Higher size == more tokens;Smallest Square --> 816 x 816 (~280 tokens per image)
            size="816x816",
            # gpt image generation models support quality input
            quality="medium"
        )

        image_bytes = base64.b64decode(result.data[0].b64_json)

        image_dir = Path(out_dir) / "images"
        image_dir.mkdir(parents=True, exist_ok=True)

        image_path = image_dir / f"{post_id}.png"
        image_path.write_bytes(image_bytes)

        return str(image_path.relative_to(Path(out_dir)))

    except Exception as e:
        print(f"  [canon] Image generation failed for {post_id}: {e}")
        if "429" in str(e) or "insufficient_quota" in str(e):
            IMAGE_GENERATION_DISABLED = True
            print("  [canon] Image generation disabled for remaining posts. Continuing with captions.")
        return None

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


def _system_signal(persona, n):
    b = persona.get("bible", {})
    voice = b.get("voice_descriptor", "casual and conversational")
    topics = b.get("topics", persona.get("interests", []))
    backstory = b.get("backstory", "")
    # visual post section:
    # visual_identity = b.get("backstory", "")

    return (
        "You roleplay a fictional social-media user and write their Canon content.\n\n"
        f"WHO YOU ARE (private, do not restate):\n{backstory}\n\n"
        f"YOUR VOICE: {voice}\n"
        f"YOU POST ABOUT: {', '.join(topics)}\n"
        f"{_tell_line(persona)}"
        f"{platform.FORMAT_HINT}\n\n"
        f"Write {n} posts that each reveal something real about your job, city, routine, "
        "household, or relationships, always INDIRECTLY through concrete lived detail, never "
        "stating your age, job, or city word-for-word. Each post distinct.\n"
        "Each post MUST contain:\n"
        "1. A natural caption between 5 and 30 words.\n"
        "2. A detailed image_prompt describing a realistic photograph "
        "that visually corresponds to that caption.\n\n"

        "The photographs should reflect the fictional user's everyday "
        "life, hobbies, environment, food, activities, and surroundings.\n\n"

        "Use realistic smartphone photography, natural lighting, "
        "authentic everyday settings, and varied compositions.\n\n"

        "Do not make every image look like a professional advertisement. "
        "Avoid repetitive compositions.\n\n"

        "Do not include identifiable real people or real private information.\n\n"
        'Return ONLY JSON: {"bio": "<one-line bio>", "posts": [{"caption": "caption here", "image_prompt": "photo description here"}]}\n\n'
        "No prose outside the JSON, no code fences."
    )

# Update _system_cover() to include image_prompt for 3 types of posts: signal, decoy, and filler
def _system_cover(persona, n_decoy, n_filler, decoys):
    voice = persona.get("bible", {}).get("voice_descriptor", "casual and conversational")
    sections, keys = [], []
    if n_decoy:
        sections.append(
            f'  "decoy" ({n_decoy} posts): substantive, opinionated posts strictly about these safe '
            f"topics: {', '.join(decoys)}. Have real takes and preferences about them, but say NOTHING "
            "about your job, city, household, routine, age, or relationships."
        )
        keys.append('"decoy": [{"caption": "...", "image_prompt": "..."}]')
    if n_filler:
        sections.append(
            f'  "filler" ({n_filler} posts): pure mundane noise with no substance at all — weather, being '
            "tired, food, a show, a passing reaction. Nothing anyone could learn from, and NOT about the "
            "decoy topics."
        )
        keys.append('"filler": [{"caption": "...", "image_prompt": "..."}]')
    distinct = (
        "Keep the two sets unmistakably different in register: decoy posts have a point of view, "
        "filler posts have none.\n"
        if n_decoy and n_filler else ""
    )
    image_instruction = (
        "Every decoy and filler post must also contain an image_prompt "
        "describing a realistic photograph that matches the post.\n"
    )   
    return (
        "You roleplay a fictional social-media user and write and post their Canon content.\n\n"
        f"YOUR VOICE: {voice}\n"
        f"{_tell_line(persona)}"
        f"{platform.FORMAT_HINT}\n\n"
        "Write the following sets of posts:\n"
        + "\n".join(sections) + "\n\n"
        + distinct
        + image_instruction
        + "Every post distinct.\n\n"
        f'Return ONLY JSON: {{{", ".join(keys)}}}, with exactly the counts above. '
        "No prose outside the JSON, no code fences."
    )


def _call(system, user):
    from openai import OpenAI
    client = OpenAI()
    response = client.response.create(
        model=platform.MODEL,
        input=[{"role": "system", "content": system},{"role": "user", "content": user}],
    )
    # A more OPENAI-style usage rather than Anthropic:
    raw = response.output_text.strip()

    if raw.startswith("```"):
        raw = raw.split("```", 1)[1].rsplit("```", 1)[0]
        raw = raw.removeprefix("json").strip()

    return json.loads(raw)
    # raw = "".join(bl.text for bl in msg.content if bl.type == "text").strip()
    # if raw.startswith("```"):
    #     raw = raw.split("```")[1].lstrip("json").strip()
    # return json.loads(raw)

# Changed _texts() to also assume posts are NOT ONLY strings but images as well
def _texts(data, n):
    out = []

    for post in data.get("posts", []):
        if not isinstance(post, dict):
            continue

        caption = str(post.get("caption", "")).strip()
        image_prompt = str(post.get("image_prompt", "")).strip()

        if caption and image_prompt:
            out.append({
                "caption": caption,
                "image_prompt": image_prompt
            })

    return out[:n]


_OFFLINE_POSTS = {
    "registered nurse": ["long shift again, on my feet all day, coffee is the only thing keeping me upright"],
    "software engineer": ["chased a race condition all morning, merged the fix, cl broke anyway lol"],
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
        posts.append({
            "caption": t,
            "image_prompt": (
                "A realistic everyday smartphone photograph "
                "visually related to this caption: " + t)
        })
    bio = f"just here posting about {', '.join(topics[:2])} [offline stub]"
    return bio, posts


def _offline_decoy(persona, n, decoys):
    out = []
    for i in range(n):
        topic = decoys[i % len(decoys)] if decoys else "coffee"
        caption = (_DECOY_TEMPLATES[i % len(_DECOY_TEMPLATES)].format(t=topic))
        out.append({
            "caption": caption,
            "image_prompt": (
                f"A realistic casual smartphone photograph "
                f"showing an everyday scene related to {topic}."
            )
        })
    return out


def _offline_filler(persona, n):
    out = []
    for i in range(n):
        caption = _FILLER[i % len(_FILLER)]
        out.append({
            "caption": caption,
            "image_prompt": (
                "A realistic casual smartphone photograph "
                "of an everyday mundane scene matching this caption: "
                + caption
            )
        })
    return out



def _gen_cover(persona, n_decoy, n_filler, decoys):
    data = _call(_system_cover(persona, n_decoy, n_filler, decoys), "Write the posts now and include an image-matching prompt that correspond with the text.")
    # dec = [str(p).strip() for p in data.get("decoy", []) if str(p).strip()][:n_decoy]
    # fil = [str(p).strip() for p in data.get("filler", []) if str(p).strip()][:n_filler]
    dec = [{"caption": str(p.get("caption", "")).strip(), "image_prompt": str(p.get("image_prompt", "")).strip()} for p in data.get("decoy", []) if isinstance(p, dict) and str(p.get("caption", "")).strip() and str(p.get("image_prompt", "")).strip()][:n_decoy]
    fil = [{"caption": str(p.get("caption", "")).strip(), "image_prompt": str(p.get("image_prompt", "")).strip()} for p in data.get("filler", []) if isinstance(p, dict) and str(p.get("caption", "")).strip() and str(p.get("image_prompt", "")).strip()][:n_filler]
    return dec, fil


def _generate(persona, counts, decoys, use_llm, strict):
    n_signal, n_decoy, n_filler = counts
    meta = {"source": "llm", "short": {"signal": 0, "decoy": 0, "filler": 0}}
    bio, sig, dec, fil = "", [], [], []
    if use_llm:
        try:
            if n_signal:
                data = _call(_system_signal(persona, n_signal), f"Write my bio and {n_signal} canon posts now.")
                bio, sig = str(data.get("bio", "")), _texts(data, n_signal)
            if n_decoy or n_filler:
                dec, fil = _gen_cover(persona, n_decoy, n_filler, decoys)
            meta["short"] = {"signal": n_signal - len(sig),
                             "decoy": n_decoy - len(dec),
                             "filler": n_filler - len(fil)}
            return bio, {"signal": sig, "decoy": dec, "filler": fil}, meta
        except Exception as e:
            if strict:
                raise RuntimeError(
                    f"canon generation failed for {persona['persona_id']}: {e}") from e
            print(f"  [canon] LLM failed for {persona['persona_id']} ({e}); offline fallback")
            meta["source"] = "offline"
            meta["error"] = str(e)
    else:
        meta["source"] = "offline"
    bio, sig = _offline_signal(persona, n_signal)
    dec = _offline_decoy(persona, n_decoy, decoys)
    fil = _offline_filler(persona, n_filler)
    return bio, {"signal": sig, "decoy": dec, "filler": fil}, meta


def emit(personas, footprint, out_dir, seed, today, strict=False, model=None):
    rng = random.Random(seed)
    use_llm = (bool(os.environ.get("OPENAI_API_KEY"))
               and os.environ.get("LLM_OFFLINE") != "1")
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

            bio, by_kind, gen_meta = _generate(persona, counts, decoys, use_llm, strict)
            if not bio and mode in ("identity", "hint"):
                bio = "just here [offline stub]"

            key["account_meta"][handle] = {
                "opsec": o,
                "decoy_topics": decoys,
                "counts": {"signal": counts[0], "decoy": counts[1], "filler": counts[2]},
                "generation": gen_meta,
            }

            paired = []
            for s, sub, kind in draws:
                bucket = by_kind.get(kind, [])
                if not bucket:
                    post_data = {
                        "caption": "The camera couldn't keep up with the beauty.",
                        "image_prompt": "A placeholder image indicating that image generation failed."
                    }
                else:
                    post_data = bucket.pop(0)
                paired.append((post_data, s, sub, kind))

            pc += 1
            prof_id = f"canon_prof_{pc:05d}"
            profiles.append(contract.make_record(
                prof_id, platform.ID, handle, channel=platform.CHANNEL, record_type="profile",
                handle=f"@{handle}",
                display_name=_display_name(persona, mode, handle, rng),
                bio=bio,
                location=_location_field(persona, mode, rng),
                # post=_post_field(persona, mode, rng),
                join_date=f"{rng.randint(2015, 2024)}-{rng.randint(1, 12):02d}",
                post_count=rng.randint(max(1, len(paired)), 4000),
                follower_count=rng.randint(20, 3000),
                following_count=rng.randint(30, 1500),
            ))
            key["obs_to_persona"][prof_id] = persona_id

            stamps = _timestamps(schedule, len(paired), today, rng)
            geo_chance = opsec_mod.geotag_chance(o)
            for (post_data, s, sub, kind), ts in zip(paired, stamps):
                # for post_data, s, sub, kind in paired:
                pc += 1
                post_id = f"canon_post_{pc:05d}"
                geotag = None
                text = post_data["caption"]
                image_prompt = post_data["image_prompt"]
                image_path = None
                has_image = False
                
                image_path = generate_photo(image_prompt, post_id, out_dir)
                if image_path is None:
                    text += " (the photo was simply too beautiful to be captured.)"
                
                if kind == "signal" and rng.random() < geo_chance:
                    lat = persona["geo"]["home_lat"] + rng.gauss(0, 0.03)
                    lon = persona["geo"]["home_lon"] + rng.gauss(0, 0.03)
                    geotag = f"{lat:.4f},{lon:.4f}"
                posts.append(contract.make_record(
                    post_id, platform.ID, handle, channel=platform.CHANNEL, record_type="post",
                    text=text, timestamp=ts, post_type="original",
                    image_prompt=image_prompt, image_path=image_path, has_image=image_path is not None,
                    hashtags=_extract_hashtags(text), mentions=[],
                    like_count=rng.randint(0, 200), repost_count=rng.randint(0, 40),
                    client=rng.choice(platform.CLIENTS), geotag=geotag,
                    thread_id=None, parent_id=None,
                ))
                key["obs_to_persona"][post_id] = persona_id
                key["obs_signal"][post_id] = {"signal": s, "substance": sub, "kind": kind}

    prof_path = contract.write_observation_file(out_dir, "canon_profiles.jsonl", profiles)
    post_path = contract.write_observation_file(out_dir, "canon_posts.jsonl", posts)
    contract.write_module_key(out_dir, platform.ID, key)
    print(f"  [canon] {len(profiles)} profiles, {len(posts)} posts")
    return {"observations": len(profiles) + len(posts),
            "profiles": len(profiles), "posts": len(posts),
            "prof_path": prof_path, "post_path": post_path}
