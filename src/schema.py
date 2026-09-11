"""
schema.py — the contract between this repo (dataset) and the profiler repo.

"""
 
from dataclasses import dataclass, field, asdict
from typing import Optional
 
# the attributes the profiler will try to infer
ATTRIBUTES = [
    "age", "sex", "city_country", "birth_city_country",
    "education", "occupation", "income_level", "relationship_status",
]
 
 
@dataclass
class Observation:
    """What the profiler ingests. Contains NO persona_id and NO attributes."""
    obs_id: str
    channel: str          # e.g. "social_text"
    platform: str         # e.g. "forum"
    account_id: str       # pseudonymous handle, one persona may own several later
    timestamp: str        # ISO 8601
    thread_id: str
    parent_id: Optional[str]
    geotag: Optional[str]
    text: str
 
 
def to_observation(obs_id, account_id, text, *, channel="social_text",
                   platform="forum", timestamp="", thread_id="",
                   parent_id=None, geotag=None) -> dict:
    """Build an observation record from allowed fields only.
 
    Note there is no `persona` or `attributes` parameter. That is deliberate.
    The caller (the emitter) knows which persona this came from, but that
    knowledge is written to the ANSWER KEY, never to the observation.
    """
    return asdict(Observation(
        obs_id=obs_id, channel=channel, platform=platform,
        account_id=account_id, timestamp=timestamp, thread_id=thread_id,
        parent_id=parent_id, geotag=geotag, text=text,
    ))
 
 
def new_answer_key() -> dict:
    """An empty answer key. The scorer (later) reads this to grade guesses."""
    return {
        "account_to_persona": {},   # account_id  -> persona_id
        "obs_to_persona": {},       # obs_id       -> persona_id
        "persona_attributes": {},   # persona_id   -> {attribute: value}
    }