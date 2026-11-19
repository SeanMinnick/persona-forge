ID = "canon"
CHANNEL = "social_image"
DISPLAY_NAME = "Canon (Instagram-like platform)"
MODEL = "gpt-6-luna"
# Since GPT-6 Luna does not generate images:
IMAGE_MODEL = "gpt-image-2.5-flare"
 
MIN_WORDS = 5
MAX_WORDS = 30
POST_MIN = 8
POST_MAX = 25
WINDOW_DAYS = 90
 
CLIENTS = ["Canon for iPhone", "Canon for Android", "Canon Web", "Canon for iPad"]
 
FORMAT_HINT = (
    "This is Canon, an Instagram-like platform. Each post is a SHORT standalone thought "
    "(5-30 words per caption and minimum 1 photo per caption), no replies or threading. Punchy and casual; lowercase is fine, an "
    "occasional hashtag is fine. Do not @mention real people or brands."
)