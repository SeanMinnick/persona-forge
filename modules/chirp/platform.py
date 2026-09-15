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
 
FORMAT_HINT = (
    "This is Chirp, a Twitter-like microblog. Each post is a SHORT standalone thought "
    "(5-30 words), no replies or threading. Punchy and casual; lowercase is fine, an "
    "occasional hashtag is fine. Do not @mention real people or brands."
)