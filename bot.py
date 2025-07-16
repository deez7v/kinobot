from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, ADMIN_ID, ADMIN_USERNAME, CHANNELS
from utils import (
    load_db, search_movies, add_movie, add_genre,
    increment_views, delete_movie, save_db, check_user_subscriptions
)
import logging

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Главное меню
start_kb = ReplyKeyboardMarkup(resize_keyboard=True)
start_kb.add("🎬 Жанры", "🔍 Поиск", "📈 ТОП 5 фильмов")

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    if await check_user_subscriptions(user_id, bot):
        await message.answer("Добро пожаловать! Выбери действие:", reply_markup=start_kb)
    else:
        kb = InlineKeyboardMarkup(row_width=1)
        text = (
    "❗️ Чтобы пользоваться ботом, подпишись на все наши каналы:\n"
    "📩 Если бот не работает — обратись к админу: @kinotuts\n"
)
        for i, ch in enumerate(CHANNELS, start=1):
            ch_clean = ch.strip('@')
            text += f"\n📢 Подписка {i}"
            kb.add(InlineKeyboardButton(text=f"Подписка {i}", url=f"https://t.me/{ch_clean}"))
        kb.add(InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subs"))
        await message.answer(text.strip() + "\n\n⬇️ Кнопки ниже для перехода", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "check_subs")
async def check_subs_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if await check_user_subscriptions(user_id, bot):
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await bot.send_message(chat_id=user_id, text="✅ Подписка подтверждена! Добро пожаловать!", reply_markup=start_kb)
    else:
        await callback_query.answer("❌ Подписка не обнаружена. Подпишись на все каналы и попробуй снова.", show_alert=True)

@dp.message_handler(commands=["addmovie"])
async def addmovie_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Команда только для админа.")
    await message.answer(
        "Формат:\n"
        "Название | Жанр | Год | Ссылка | Описание | Постер (URL)\n"
        "Каждый фильм — с новой строки.\n"
        "Если постера нет — оставь поле пустым."
    )

@dp.message_handler(lambda m: m.text == "🎬 Жанры")
async def show_genres(message: types.Message):
    db = load_db()
    if not db["genres"]:
        return await message.answer("Жанры пока не добавлены.")
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for genre in db["genres"]:
        kb.add(genre)
    kb.add("🔙 Назад")
    await message.answer("Выбери жанр:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "🔙 Назад")
async def go_back(message: types.Message):
    await message.answer("Главное меню:", reply_markup=start_kb)

@dp.message_handler(lambda m: m.text == "🔍 Поиск")
async def ask_query(message: types.Message):
    await message.answer("Введи название фильма:")

@dp.message_handler(lambda m: m.text == "📈 ТОП 5 фильмов")
async def show_top_movies(message: types.Message):
    db = load_db()
    sorted_movies = sorted(db["movies"], key=lambda x: x["views"], reverse=True)[:5]
    if not sorted_movies:
        return await message.answer("Пока нет популярных фильмов.")
    for movie in sorted_movies:
        await send_movie_card(message.chat.id, movie)

@dp.message_handler()
async def handle_input(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    # Добавление фильмов
    if "|" in text and user_id == ADMIN_ID:
        lines = text.strip().splitlines()
        success, fail, duplicate = 0, 0, 0
        for line in lines:
            try:
                parts = list(map(str.strip, line.split("|")))
                if len(parts) == 6:
                    title, genre, year, link, desc, poster = parts
                elif len(parts) == 5:
                    title, genre, year, link, desc = parts
                    poster = ""
                else:
                    fail += 1
                    continue

                db = load_db()
                if any(m for m in db["movies"] if m["title"].lower() == title.lower() and m["year"] == year):
                    duplicate += 1
                    continue

                if genre not in db["genres"]:
                    db["genres"].append(genre)
                    save_db(db)

                add_movie(title, genre, link, desc, year, poster)
                success += 1
            except:
                fail += 1

        return await message.answer(f"✅ Добавлено: {success}, ❌ Ошибок: {fail}, ⚠️ Уже в базе: {duplicate}")

    # Поиск по жанрам
    db = load_db()
    if text in db["genres"]:
        genre_movies = [m for m in db["movies"] if m["genre"] == text]
        if not genre_movies:
            return await message.answer("Фильмы этого жанра пока не добавлены.")
        for movie in genre_movies[:7]:
            await send_movie_card(message.chat.id, movie)
        return

    # Поиск по названию
    results = search_movies(text)
    if not results:
        return await message.answer(f"Фильм не найден. Напиши админу {ADMIN_USERNAME}, чтобы мы его добавили.")
    for movie in results:
        await send_movie_card(message.chat.id, movie)
        increment_views(movie)

# Универсальная отправка карточки фильма
async def send_movie_card(chat_id, movie):
    text = (
        f"🎬 {movie['title']} ({movie['year']})\n"
        f"🎭 Жанр: {movie['genre']}\n\n"
        f"💬 {movie['description']}\n\n"
        f"Смотреть тут 👇👇👇\n"
        f"🔗 {movie['link']}\n\n"
        f"❗️Если фильм недоступен — сообщи: {ADMIN_USERNAME}"
    )
    if movie.get("poster"):
        await bot.send_photo(chat_id, photo=movie["poster"], caption=text)
    else:
        await bot.send_message(chat_id, text)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
