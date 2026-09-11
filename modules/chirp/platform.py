ID = "chirp"
CHANNEL = "social_text"
DISPLAY_NAME = "Chirp (Twitter-like microblog)"
MODEL = "claude-haiku-4-5"
 
MIN_WORDS = 5
MAX_WORDS = 30
POST_MIN = 8
POST_MAX = 25
WINDOW_DAYS = 90
 
CLIENTS = ["Chirp for iPhone", "Chirp for Android", "Chirp Web", "Chirp for iPad"]
 
GEOTAG_CHANCE = {"careless": 0.15, "moderate": 0.03, "disciplined": 0.0, "meticulous": 0.0}
 
FORMAT_HINT = (
    "This is Chirp, a Twitter-like microblog. Each post is a SHORT standalone thought "
    "(5-30 words), no replies or threading. Punchy and casual; lowercase is fine, an "
    "occasional hashtag is fine. Do not @mention real people or brands."
)
 
BIO_LEAKAGE = {
    "careless": "Write a lively bio that openly signals your job and city and a hobby or two. You are not privacy-conscious.",
    "moderate": "Write a bio that hints at your interests and maybe vaguely at what you do, but not your city.",
    "disciplined": "Write a short, guarded bio that reveals no job, city, or identifying detail.",
    "meticulous": "Write a generic, near-empty bio that reveals nothing personal at all.",
}