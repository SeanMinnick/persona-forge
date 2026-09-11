import json
import os
 
ATTRIBUTES = [
    "age", "sex", "city_country", "birth_city_country",
    "education", "occupation", "income_level", "relationship_status",
]
 
ALLOWED_OBS_FIELDS = {
    "obs_id", "module", "channel", "record_type", "account_id",
    "timestamp", "thread_id", "parent_id", "geotag", "text", "body",
    "handle", "display_name", "bio", "location", "join_date",
    "post_count", "follower_count", "following_count",
    "post_type", "hashtags", "mentions", "like_count", "repost_count", "client",
}
 
 
def make_record(obs_id, module, account_id, channel, record_type, **fields):
    rec = {
        "obs_id": obs_id,
        "module": module,
        "channel": channel,
        "record_type": record_type,
        "account_id": account_id,
    }
    for k, v in fields.items():
        if k not in ALLOWED_OBS_FIELDS:
            raise ValueError(f"field '{k}' not allowed in an observation record")
        rec[k] = v
    return rec
 
 
def new_module_key(module):
    return {
        "module": module,
        "account_to_persona": {},
        "obs_to_persona": {},
    }
 
 
def write_observation_file(out_dir, filename, records):
    obs_dir = os.path.join(out_dir, "observations")
    os.makedirs(obs_dir, exist_ok=True)
    path = os.path.join(obs_dir, filename)
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path
 
 
def write_module_key(out_dir, module, key):
    key_dir = os.path.join(out_dir, "answer_key")
    os.makedirs(key_dir, exist_ok=True)
    path = os.path.join(key_dir, f"{module}.json")
    with open(path, "w") as f:
        json.dump(key, f, indent=2)
    return path