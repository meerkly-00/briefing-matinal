"""
Génère et publie le tweet quotidien Presto à partir du script XML du jour.
Usage : python tools/tweet.py output/scripts/2026-05-29.xml
"""

import os
import re
import sys
from pathlib import Path

import anthropic
import tweepy
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

TWEET_PROMPT = """Tu es chargé de rédiger UN tweet en français québécois pour le compte @prestopodcast.

À partir du script XML du briefing ci-dessous, extrais le fait le plus fort, le plus concret, le plus surprenant ou le plus important de la journée.

Règles strictes :
- Maximum 240 caractères en tout (URL incluse)
- Commence directement par le fait, pas par "Aujourd'hui" ou "Dans le briefing"
- Chiffres bruts si possible (ex: "4 morts", "86e jour", "10x la vitesse du son")
- Pas de hashtags
- Termine par : ▶ prestopodcast.online
- Ton neutre, factuel, percutant

Réponds avec le tweet uniquement, rien d'autre.

Script XML :
{script}"""


def extract_tweet(script_xml: str) -> str:
    # Tronquer si trop long pour l'API (garder intro + 3 premiers chapitres)
    truncated = script_xml[:6000] if len(script_xml) > 6000 else script_xml

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=256,
        messages=[{"role": "user", "content": TWEET_PROMPT.format(script=truncated)}],
    )
    return message.content[0].text.strip()


def post_tweet(text: str) -> str:
    client = tweepy.Client(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    response = client.create_tweet(text=text)
    return response.data["id"]


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/tweet.py <script.xml>", file=sys.stderr)
        sys.exit(1)

    script_path = Path(sys.argv[1])
    if not script_path.exists():
        print(f"Fichier introuvable : {script_path}", file=sys.stderr)
        sys.exit(1)

    script_xml = script_path.read_text(encoding="utf-8")
    print("Génération du tweet...")
    tweet_text = extract_tweet(script_xml)

    print(f"\nTweet ({len(tweet_text)} chars):\n{tweet_text}\n")

    if os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes"):
        print("[DRY_RUN] Tweet non publié.")
        return

    tweet_id = post_tweet(tweet_text)
    print(f"Tweet publié : https://x.com/prestopodcast/status/{tweet_id}")


if __name__ == "__main__":
    main()
