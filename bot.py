import os
import sqlite3
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from dotenv import load_dotenv  # Импортируем загрузчик переменных

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем переменные из файла .env (если он есть в папке)
# Или из системных переменных окружения хостинга (если ты задал их через export)
load_dotenv()

# ==================== ИМПОРТ ПЕРЕМЕННЫХ ИЗ ОКРУЖЕНИЯ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
GROUP_ID_RAW = os.getenv("GROUP_ID")
ROBLOX_COOKIE = os.getenv("ROBLOX_COOKIE")

# Проверка, что всё успешно импортировалось
if not all([BOT_TOKEN, ADMIN_ID_RAW, GROUP_ID_RAW, ROBLOX_COOKIE]):
    critical_error = "❌ Ошибка: Не все переменные окружения заданы на хостинге! Проверьте файл .env."
    logging.critical(critical_error)
    raise ValueError(critical_error)

# Преобразуем ID в числа, так как из окружения всё приходит в виде строк
ADMIN_ID = int(ADMIN_ID_RAW)
GROUP_ID = int(GROUP_ID_RAW)
# =========================================================================


# 1. Инициализация Базы Данных SQLite
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            roblox_username TEXT UNIQUE,
            roblox_user_id INTEGER UNIQUE,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()

# Получение данных пользователя из БД
def get_user(tg_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT roblox_username, roblox_user_id, status FROM users WHERE tg_id = ?", (tg_id,))
    row = cursor.fetchone()
    conn.close()
    return row

# Регистрация нового пользователя в БД
def register_user(tg_id, username, roblox_id):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (tg_id, roblox_username, roblox_user_id) VALUES (?, ?, ?)", (tg_id, username, roblox_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

# Обновление статуса заявки
def update_status(tg_id, status):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE tg_id = ?", (status, tg_id))
    conn.commit()
    conn.close()


# 2. Функции взаимодействия с Roblox API
async def get_roblox_user_id(username: str):
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {
        "usernames": [username],
        "excludeBannedUsers": True
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("data"):
                    return data["data"][0]["id"], data["data"][0]["name"]
            return None, None

async def roblox_request(method: str, url: str, csrf_token: str = None):
    headers = {
        "Cookie": f".ROBLOSECURITY={ROBLOX_COOKIE}",
        "Content-Type": "application/json"
    }
    if csrf_token:
        headers["X-CSRF-TOKEN"] = csrf_token
        
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers) as response:
            if response.status == 403 and "x-csrf-token" in response.headers:
                new_csrf = response.headers["x-csrf-token"]
                return await roblox_request(method, url, csrf_token=new_csrf)
            try:
                res_json = await response.json()
            except Exception:
                res_json = {}
            return response.status, res_json

async def accept_join_request(group_id: int, roblox_user_id: int):
    url = f"https://groups.roblox.com/v1/groups/{group_id}/join-requests/users/{roblox_user_id}"
    status, data = await roblox_request("POST", url)
    if status == 200:
        return True, "Успешно одобрено"
    else:
        error_msg = data.get("errors", [{}])[0].get("message", "Неизвестная ошибка")
        return False, error_msg


# 3. Настройка Telegram-бота
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    
    if user_data:
        roblox_username, _, status = user_data
        status_ru = {
            'pending': '⏳ на рассмотрении админов',
            'approved': '✅ одобрена (вы приняты в группу)',
            'rejected': '❌ отклонена'
        }.get(status, status)
        
        await message.answer(
            f"Вы уже отправили заявку для аккаунта Roblox: <b>{roblox_username}</b>.\n"
            f"Текущий статус: {status_ru}.\n\n"
            f"⚠️ Изменение никнейма или отправка новой заявки невозможна."
        )
    else:
        await message.answer(
            "Привет! Чтобы вступить в нашу группу в Roblox, отправь мне свой <b>точный никнейм</b> в Roblox.\n\n"
            "⚠️ <b>Внимание:</b> ты можешь указать только один никнейм. Изменить его позже будет нельзя!"
        )

@dp.message()
async def process_nickname(message: Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)
    if user_data:
        await message.answer("Вы уже привязали никнейм. Изменить его нельзя.")
        return
        
    username = message.text.strip()
    roblox_id, real_username = await get_roblox_user_id(username)
    if not roblox_id:
        await message.answer("❌ Игрок с таким ником не найден в Roblox. Проверь буквы и попробуй снова.")
        return
        
    success = register_user(user_id, real_username, roblox_id)
    if not success:
        await message.answer("❌ Этот никнейм Roblox или ваш Telegram уже используются для другой заявки!")
        return
        
    admin_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
        ]
    ])
    
    tg_user = f"@{message.from_user.username}" if message.from_user.username else f"ID: {user_id}"
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🔔 <b>Новая заявка на вступление!</b>\n\n"
                f"👤 Пользователь Telegram: {tg_user}\n"
                f"🎮 Roblox ник: <b>{real_username}</b>\n"
                f"🆔 Roblox ID: <code>{roblox_id}</code>\n"
                f"🔗 Профиль: <a href='https://www.roblox.com/users/{roblox_id}/profile'>Перейти в профиль</a>\n\n"
                f"<i>Перед нажатием 'Одобрить' убедитесь, что игрок подал заявку (Join Group) непосредственно в саму группу Roblox!</i>"
            ),
            reply_markup=admin_markup,
            disable_web_page_preview=True
        )
        await message.answer(
            f"✅ Никнейм <b>{real_username}</b> успешно сохранен и отправлен админам!\n\n"
            f"⚠️ <b>Важный шаг:</b> Теперь перейдите в нашу группу в Roblox и нажмите кнопку <b>'Join Group'</b>. "
            f"Когда админ нажмет кнопку в Telegram, бот автоматически одобрит твою заявку в Roblox!"
        )
    except Exception as e:
        logging.error(f"Ошибка отправки админу: {e}")
        await message.answer("⚠️ Произошла ошибка при отправке заявки администратору. Пожалуйста, сообщите нам.")


# Обработчик кнопки "Одобрить"
@dp.callback_query(F.data.startswith('approve_'))
async def handle_approve(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return
        
    user_id = int(callback.data.split('_')[1])
    user_data = get_user(user_id)
    
    if not user_data:
        await callback.answer("Пользователь не найден в базе.", show_alert=True)
        return
        
    roblox_username, roblox_id, status = user_data
    
    if status == 'approved':
        await callback.answer("Эта заявка уже была одобрена ранее!", show_alert=True)
        return
        
    success, message = await accept_join_request(GROUP_ID, roblox_id)
    
    if success:
        update_status(user_id, 'approved')
        await callback.message.edit_text(
            f"✅ Заявка пользователя {roblox_username} (TG ID: {user_id}) успешно одобрена!\n"
            f"Бот успешно принял его в группу Roblox."
        )
        try:
            await bot.send_message(user_id, f"🎉 Твоя заявка одобрена! Бот автоматически принял тебя в группу Roblox под ником <b>{roblox_username}</b>!")
        except Exception:
            pass
    else:
        await callback.answer(
            f"Ошибка Roblox API: {message}\n\nВозможно, игрок еще не отправил запрос в группу Roblox.", 
            show_alert=True
        )


# Обработчик кнопки "Отклонить"
@dp.callback_query(F.data.startswith('reject_'))
async def handle_reject(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return
        
    user_id = int(callback.data.split('_')[1])
    user_data = get_user(user_id)
    
    if not user_data:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
        
    roblox_username, _, status = user_data
    
    if status == 'rejected':
        await callback.answer("Эта заявка уже отклонена!", show_alert=True)
        return
        
    update_status(user_id, 'rejected')
    await callback.message.edit_text(
        f"❌ Заявка пользователя {roblox_username} (TG ID: {user_id}) отклонена."
    )
    
    try:
        await bot.send_message(user_id, f"❌ Извини, твоя заявка для аккаунта <b>{roblox_username}</b> была отклонена администратором.")
    except Exception:
        pass


# Запуск бота
async def main():
    init_db()
    print("Бот успешно запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
