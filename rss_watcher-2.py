"""
Surveille les flux RSS des médias francophones du monde entier et envoie une
notification Telegram dès qu'un article sur la Roumanie est publié.
"""

import feedparser
import requests
import json
import os
import hashlib
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

FEEDS = {
    # France
    "Le Monde":         "https://www.lemonde.fr/rss/une.xml",
    "Le Figaro":        "https://www.lefigaro.fr/rss/figaro_actualites.xml",
    "Libération":       "https://www.liberation.fr/arc/outboundfeeds/rss/",
    "France Info":      "https://www.francetvinfo.fr/titres.rss",
    "France 24":        "https://www.france24.com/fr/rss",
    "RFI":              "https://www.rfi.fr/fr/rss",
    # Belgique
    "RTBF":             "https://www.rtbf.be/rss/info/une",
    "Le Soir":          "https://www.lesoir.be/rss",
    "La Libre":         "https://www.lalibre.be/arc/outboundfeeds/rss/",
    # Suisse
    "RTS":              "https://www.rts.ch/rss/info",
    "Le Temps":         "https://www.letemps.ch/rss",
    "24 Heures":        "https://www.24heures.ch/rss",
    # Canada
    "Radio-Canada":     "https://ici.radio-canada.ca/rss/4159",
    "Le Devoir":        "https://www.ledevoir.com/rss/manchettes.xml",
    "La Presse":        "https://www.lapresse.ca/rss/nouvelles.xml",
    # Afrique francophone
    "Jeune Afrique":    "https://www.jeuneafrique.com/feed/",
    "TV5 Monde":        "https://information.tv5monde.com/rss",
    # Luxembourg
    "RTL Luxembourg":   "https://www.rtl.lu/rss/infos.xml",
}

KEYWORDS = [
    "roumanie", "roumain", "roumains", "roumaine", "roumaines",
    "bucarest", "cluj", "transylvanie", "moldavie",
    "ceausescu", "danube", "carpates", "iasi", "timisoara",
]

SEEN_FILE = "seen_articles.json"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def article_id(entry) -> str:
    raw = getattr(entry, "link", "") or getattr(entry, "title", "")
    return hashlib.md5(raw.encode()).hexdigest()


def matches_romania(entry) -> bool:
    text = " ".join([
        getattr(entry, "title",   "") or "",
        getattr(entry, "summary", "") or "",
    ]).lower()
    return any(kw in text for kw in KEYWORDS)


def send_telegram(source: str, title: str, link: str, pub_date: str):
    msg = (
        f"🇷🇴 *Nouvel article sur la Roumanie*\n\n"
        f"📰 *{source}*\n"
        f"📌 {title}\n"
        f"🕐 {pub_date}\n"
        f"🔗 [Lire l'article]({link})"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }, timeout=10)
    resp.raise_for_status()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    seen = load_seen()
    new_seen = set()
    found = 0

    for source, url in FEEDS.items():
        print(f"[{source}] Lecture du flux…")
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"  ⚠️  Erreur lecture flux : {e}")
            continue

        for entry in feed.entries:
            aid = article_id(entry)
            new_seen.add(aid)

            if aid in seen:
                continue

            if not matches_romania(entry):
                continue

            title    = getattr(entry, "title",   "Sans titre")
            link     = getattr(entry, "link",    url)
            pub_date = getattr(entry, "published", datetime.now().strftime("%d/%m/%Y %H:%M"))

            print(f"  🇷🇴 Correspondance : {title[:80]}")
            try:
                send_telegram(source, title, link, pub_date)
                found += 1
            except Exception as e:
                print(f"  ❌ Erreur Telegram : {e}")

    save_seen(seen | new_seen)
    print(f"\nTerminé — {found} notification(s) envoyée(s).")


if __name__ == "__main__":
    main()
