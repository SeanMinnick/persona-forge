ID = "chirp"
CHANNEL = "social_text"
DISPLAY_NAME = "Chirp (Twitter-like microblog)"
MIN_WORDS = 5
MAX_WORDS = 30
POSTS_PER_ACCOUNT = 4
MODEL = "claude-haiku-4-5"
 
FORMAT_HINT = (
    "This is Chirp, a Twitter-like microblog. Each post is a SHORT standalone "
    "thought — no replies, no threading. Punchy and casual; lowercase is fine, "
    "an occasional hashtag is fine. Do not @mention real people or brands."
)