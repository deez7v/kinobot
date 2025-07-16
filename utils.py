import json
from config import DB_PATH

def load_db():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_movie(title, genre, link, description, year, poster=""):
    db = load_db()
    db["movies"].append({
        "title": title,
        "genre": genre,
        "year": year,
        "link": link,
        "description": description,
        "poster": poster,
        "views": 0
    })
    save_db(db)

def add_genre(genre):
    db = load_db()
    if genre not in db["genres"]:
        db["genres"].append(genre)
        save_db(db)

def delete_movie(title, year):
    db = load_db()
    db["movies"] = [m for m in db["movies"] if not (m["title"] == title and m["year"] == year)]
    save_db(db)

def search_movies(query):
    db = load_db()
    return [
        m for m in db["movies"]
        if query.lower() in m["title"].lower()
    ]

def increment_views(movie):
    db = load_db()
    for m in db["movies"]:
        if m["title"] == movie["title"] and m["year"] == movie["year"]:
            m["views"] += 1
            break
    save_db(db)

async def check_user_subscriptions(user_id, bot):
    from config import CHANNELS
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ['member', 'creator', 'administrator']:
                return False
        except Exception as e:
            print(f"Ошибка при проверке подписки на {ch}: {e}")
            return False
    return True
