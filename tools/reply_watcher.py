"""
Watcher continu de replies Presto.

Tourne toutes les 30 min via GitHub Actions.
Cherche les tweets d'actu québécoise récents les plus engagés,
répond avec des faits. Max 2 replies par run, ~30/jour.

State persisté dans data/reply_state.json pour éviter les doublons.
"""

import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import tweepy
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
STATE_FILE   = PROJECT_ROOT / "data" / "reply_state.json"

MAX_PER_RUN  = int(os.getenv("REPLY_MAX_PER_RUN", "2"))
MAX_PER_DAY  = int(os.getenv("REPLY_MAX_PER_DAY", "30"))
MIN_LIKES    = int(os.getenv("REPLY_MIN_LIKES", "3"))

# Topics de base — enrichis chaque matin par le briefing du jour
BASE_TOPICS = [
    "Québec politique",
    "Legault CAQ",
    "Canada Carney",
    "Alberta séparation",
    "CRTC médias",
    "économie Québec",
    "RadioCanada",
    "santé Québec",
    "logement Québec",
    "tarifs douaniers Canada",
    "intelligence artificielle Québec",
    "environnement Québec",
    "immigration Québec",
]

REPLY_PROMPT = """\
Tu es @PrestoPodcast, un briefing d'actualité québécoise factuel généré par IA.
Ton style : neutre, précis, jamais opiniatif. Tu apportes de la valeur factuelle.

Tweet auquel tu réponds :
\"\"\"{tweet_text}\"\"\"

Contexte récent de Presto sur ce type de sujet :
{context}

Rédige UNE réponse en français québécois (max 220 chars) qui :
- Ajoute 1-2 faits concrets ou chiffres que le tweet ne mentionne pas
- Est directe — commence par le fait, pas par "Selon Presto" ou "Saviez-vous"
- Termine par : -> prestopodcast.online
- Ton neutre, factuel, jamais condescendant

Réponds avec le texte du reply UNIQUEMENT.
"""


# ── State ──────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"replied": [], "daily": {}, "topics_used": []}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def daily_count(state: dict) -> int:
    return state["daily"].get(today(), 0)


def increment_daily(state: dict):
    state["daily"][today()] = daily_count(state) + 1
    # Purge les entrées > 3 jours
    cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state["daily"] = {k: v for k, v in state["daily"].items() if k >= cutoff[:7]}


# ── Topics dynamiques ───────────────────────────────────────────────────────

def load_dynamic_topics() -> list[str]:
    """Charge les topics du dernier briefing généré."""
    scripts = sorted((PROJECT_ROOT / "output" / "scripts").glob("*.xml"))
    if not scripts:
        return []
    import re
    script = scripts[-1].read_text(encoding="utf-8")
    titres = re.findall(r'<chapitre titre="([^"]+)">', script)
    return [t for t in titres if len(t) > 5]


def load_recent_context() -> str:
    """Charge le contexte résumé des derniers briefings."""
    ctx_file = PROJECT_ROOT / "data" / "context.json"
    if not ctx_file.exists():
        return ""
    entries = json.loads(ctx_file.read_text(encoding="utf-8"))
    if not entries:
        return ""
    last = entries[-1]
    return last.get("summary", "")[:800]


# ── X helpers ────────────────────────────────────────────────────────────────

def search_tweets(query: str, tw: tweepy.Client, replied_ids: set) -> list[dict]:
    """Cherche des tweets récents sur un sujet, retourne les plus engagés."""
    try:
        resp = tw.search_recent_tweets(
            query=f"{query} lang:fr -is:retweet -is:reply",
            max_results=20,
            tweet_fields=["public_metrics", "author_id", "created_at"],
            expansions=["author_id"],
            user_fields=["public_metrics", "username"],
            sort_order="relevancy",
        )
    except Exception as e:
        log.warning("Search error (%s): %s", query, e)
        return []

    if not resp.data:
        return []

    users = {u.id: u for u in (resp.includes.get("users") or [])}
    results = []

    for tweet in resp.data:
        if str(tweet.id) in replied_ids:
            continue
        m = tweet.public_metrics
        score = m["like_count"] + m["retweet_count"] * 2 + m["reply_count"]
        author = users.get(tweet.author_id)
        followers = author.public_metrics["followers_count"] if author else 0
        # Bonus audience
        if followers > 5000:
            score += 15
        elif followers > 1000:
            score += 5
        if score < MIN_LIKES:
            continue
        results.append({
            "id": str(tweet.id),
            "text": tweet.text,
            "score": score,
            "followers": followers,
            "username": author.username if author else "?",
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:3]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    dry_run = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")

    state       = load_state()
    replied_ids = set(state.get("replied", []))

    if daily_count(state) >= MAX_PER_DAY:
        log.info("Max daily replies atteint (%d). Rien à faire.", MAX_PER_DAY)
        return

    # Topics : dynamiques (briefing du jour) + base, shufflés
    dynamic = load_dynamic_topics()
    all_topics = dynamic + [t for t in BASE_TOPICS if t not in dynamic]
    # Évite de répéter les mêmes topics que le dernier run
    used = set(state.get("topics_used", []))
    fresh = [t for t in all_topics if t not in used]
    if not fresh:
        fresh = all_topics  # reset si tout a été utilisé
        state["topics_used"] = []

    random.shuffle(fresh)
    context = load_recent_context()

    claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    tw = tweepy.Client(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
        wait_on_rate_limit=True,
    )

    posted = 0

    for topic in fresh:
        if posted >= MAX_PER_RUN:
            break
        if daily_count(state) >= MAX_PER_DAY:
            break

        log.info("── Topic : %s", topic)
        state.setdefault("topics_used", []).append(topic)

        tweets = search_tweets(topic, tw, replied_ids)
        if not tweets:
            log.info("   Aucun tweet pertinent.")
            continue

        best = tweets[0]
        log.info("   @%s (score=%d, %d followers) : %s",
                 best["username"], best["score"], best["followers"],
                 best["text"][:80])

        # Génère la réponse
        try:
            msg = claude.messages.create(
                model=os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001"),
                max_tokens=130,
                messages=[{"role": "user", "content": REPLY_PROMPT.format(
                    tweet_text=best["text"], context=context or "Aucun contexte disponible."
                )}],
            )
            reply_text = msg.content[0].text.strip()
        except Exception as e:
            log.error("   Erreur Claude : %s", e)
            continue

        log.info("   Reply (%d chars) : %s", len(reply_text), reply_text)

        if dry_run:
            log.info("   [DRY_RUN] Non posté.")
        else:
            try:
                resp = tw.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=int(best["id"]),
                )
                tweet_url = f"https://x.com/prestopodcast/status/{resp.data['id']}"
                log.info("   Posté : %s", tweet_url)
                replied_ids.add(best["id"])
                state["replied"] = list(replied_ids)[-500:]  # garde max 500
                increment_daily(state)
                save_state(state)
                posted += 1
                time.sleep(8)
            except Exception as e:
                log.error("   Erreur posting : %s", e)

    log.info("── Run terminé : %d reply(ies) postés, %d aujourd'hui au total.",
             posted, daily_count(state))
    save_state(state)


if __name__ == "__main__":
    main()
