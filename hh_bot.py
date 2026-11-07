"""
hh.uz yangi vakansiyalarni Telegram'ga yuboruvchi bot.
Ishga tushirish:  pip install requests   ->   python hh_bot.py
"""
import json
import os
import time
from pathlib import Path

import requests

# ====== SOZLAMALAR ======
BOT_TOKEN = os.getenv("BOT_TOKEN", "BU_YERGA_BOT_TOKEN")   # @BotFather bergan token
MY_ID = 7944365548                                          # sening Telegram ID'ing
HH_TOKEN = os.getenv("HH_TOKEN", "")                        # dev.hh.ru dan olingan token (bo'sh bo'lishi ham mumkin, avval sinab ko'r)
CONTACT = os.getenv("CONTACT", "email@example.com")         # User-Agent uchun o'z emailing
CHECK_EVERY = 300                                           # soniya (300 = 5 daqiqa)
AREA = 97                                                   # 97 = butun O'zbekiston

# Yo'nalishlar va kalit so'zlar (lavozim nomi bo'yicha qidiriladi). O'zing tahrirla.
DIRECTIONS = {
    "marketing": "SMM OR маркетолог OR marketing OR таргетолог OR SEO OR контент OR копирайтер",
    "bank": "банк OR кассир OR кредит OR операционист OR бухгалтер OR финансист",
    "it": "программист OR developer OR разработчик OR QA OR тестировщик OR дизайнер OR аналитик",
}
# ========================

SEEN_FILE = Path("seen.json")
HEADERS = {"User-Agent": f"VakansiyaBot/1.0 ({CONTACT})"}
if HH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {HH_TOKEN}"


def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return None  # None = birinchi ishga tushish


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(sorted(seen)))


def fetch(query):
    r = requests.get(
        "https://api.hh.ru/vacancies",
        params={
            "area": AREA,
            "text": query,
            "search_field": "name",
            "order_by": "publication_time",
            "period": 1,
            "per_page": 50,
        },
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("items", [])


def salary_text(s):
    if not s:
        return "Maosh ko'rsatilmagan"
    a, b, cur = s.get("from"), s.get("to"), s.get("currency", "")
    parts = []
    if a:
        parts.append(f"{a:,}".replace(",", " "))
    if b:
        parts.append(f"{b:,}".replace(",", " "))
    return " - ".join(parts) + f" {cur}"


def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": MY_ID, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )
    if not r.ok:
        print("Telegram xato:", r.text)


def run_once(seen, first_run):
    new_count = 0
    for name, query in DIRECTIONS.items():
        try:
            items = fetch(query)
        except Exception as e:
            print(f"[{name}] hh xato:", e)
            send(f"[{name}] hh xato: {e}")
            continue
        for v in items:
            vid = v["id"]
            if vid in seen:
                continue
            seen.add(vid)
            if first_run:
                continue  # birinchi marta eskilarni yubormaymiz
            new_count += 1
            text = (
                f"#{name}\n"
                f"{v['name']}\n"
                f"Kompaniya: {v.get('employer', {}).get('name', '-')}\n"
                f"Shahar: {v.get('area', {}).get('name', '-')}\n"
                f"Maosh: {salary_text(v.get('salary'))}\n"
                f"{v['alternate_url']}"
            )
            send(text)
            time.sleep(1)
    save_seen(seen)
    return new_count


def main():
    seen = load_seen()
    first_run = seen is None
    if first_run:
        seen = set()
        print("Birinchi ishga tushish: mavjud vakansiyalar eslab qolinadi, yuborilmaydi.")
    if os.getenv("RUN_ONCE"):  # GitHub Actions rejimi: bir marta tekshirib chiqadi
        n = run_once(seen, first_run)
        print(f"Tekshirildi. Yangi: {n}")
        return
    while True:
        n = run_once(seen, first_run)
        first_run = False
        print(f"Tekshirildi. Yangi: {n}")
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
