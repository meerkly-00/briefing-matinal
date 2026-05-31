"""Usage: py tools/post_replies.py 2026-05-31 <reply_to_id> [start_index]"""
import json, os, sys, time
from pathlib import Path
from dotenv import load_dotenv
import tweepy

load_dotenv(Path(__file__).parent.parent / ".env")

date = sys.argv[1]
reply_to = sys.argv[2]
start = int(sys.argv[3]) if len(sys.argv) > 3 else 1

data = json.loads(Path(f"data/tweets/{date}.json").read_text(encoding="utf-8"))
tweets = data["tweets"][start:]

client = tweepy.Client(
    consumer_key=os.environ["TWITTER_API_KEY"],
    consumer_secret=os.environ["TWITTER_API_SECRET"],
    access_token=os.environ["TWITTER_ACCESS_TOKEN"],
    access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
)

for i, text in enumerate(tweets):
    idx = start + i + 1
    total = len(data["tweets"])
    print(f"Tweet {idx}/{total}: {text[:60]}...")
    try:
        resp = client.create_tweet(text=text, in_reply_to_tweet_id=reply_to)
    except TypeError:
        resp = client.create_tweet(text=text, reply={"in_reply_to_tweet_id": reply_to})
    reply_to = resp.data["id"]
    print(f"  -> {reply_to}")
    if i < len(tweets) - 1:
        time.sleep(2)

print("Done!")
