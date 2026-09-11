import json
import os
 
ATTRIBUTES = [
    "age", "sex", "city_country", "birth_city_country",
    "education", "occupation", "income_level", "relationship_status",
]
 
ALLOWED_OBS_FIELDS = {
    "obs_id", "module", "channel", "account_id", "timestamp",
    "thread_id", "parent_id", "geotag", "text", "body",
}
 
 
def make_observation(obs_id, module, account_id, *, channel, timestamp="",
                     thread_id="", parent_id=None, geotag=None, text=None, body=None):
    obs = {
        "obs_id": obs_id,
        "module": module,
        "channel": channel,
        "account_id": account_id,
        "timestamp": timestamp,
        "thread_id": thread_id,
        "parent_id": parent_id,
        "geotag": geotag,
    }
    if text is not None:
        obs["text"] = text
    if body is not None:
        obs["body"] = body
    return obs
 
 
def new_module_key(module):
    return {
        "module": module,
        "account_to_persona": {},
        "obs_to_persona": {},
    }
 
 
def write_observations(out_dir, module, observations):
    obs_dir = os.path.join(out_dir, "observations")
    os.makedirs(obs_dir, exist_ok=True)
    path = os.path.join(obs_dir, f"{module}.jsonl")
    with open(path, "w") as f:
        for obs in observations:
            f.write(json.dumps(obs) + "\n")
    return path
 
 
def write_module_key(out_dir, module, key):
    key_dir = os.path.join(out_dir, "answer_key")
    os.makedirs(key_dir, exist_ok=True)
    path = os.path.join(key_dir, f"{module}.json")
    with open(path, "w") as f:
        json.dump(key, f, indent=2)
    return path
 
 
class Module:
    id = None
    channel = None
 
    def accounts_per_persona(self, persona, rng):
        raise NotImplementedError
 
    def emit(self, personas, footprint, out_dir, seed, today):
        raise NotImplementedError