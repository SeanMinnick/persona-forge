"""
platforms.py — establishes the platform contract for the profiler. Each platform has a channel, a format hint, and min/max word counts. The profiler uses this to validate observations.

"""

from dataclasses import dataclass
 
 
@dataclass(frozen=True)
class Platform:
    id: str
    display_name: str
    channel: str
    format_hint: str
    min_words: int
    max_words: int
 
 
CHIRP = Platform(
    id="chirp",
    display_name="Chirp (Twitter-like microblog)",
    channel="social_text",
    format_hint=(
        "This is Chirp, a Twitter-like microblog. Each post is a SHORT standalone "
        "thought — no replies, no threading. Punchy and casual; lowercase is fine, "
        "an occasional hashtag is fine. Do not @mention real people or brands."
    ),
    min_words=5,
    max_words=30,
)
 
 
PLATFORMS = {p.id: p for p in [CHIRP]}
 
 
def get_platform(platform_id: str) -> Platform:
    if platform_id not in PLATFORMS:
        raise KeyError(
            f"unknown platform '{platform_id}'. Known: {sorted(PLATFORMS)}"
        )
    return PLATFORMS[platform_id]