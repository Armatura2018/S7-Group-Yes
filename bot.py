import os
import asyncio
import logging
import aiohttp
import aiosqlite
from pathlib import Path
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.enums import ParseMode
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CREATOR_ID = int(os.getenv("CREATOR_ID", 0))
GROUP_ID = int(os.getenv("GROUP_ID", 0))
ROBLOX_COOKIE = os.getenv("ROBLOX_COOKIE")

BLACKLIST_GROUPS_RAW = os.getenv("BLACKLIST_GROUPS", "")
BLACKLIST_GROUPS = [int(g.strip()) for g in BLACKLIST_GROUPS_RAW.split(",") if g.strip().isdigit()]

# Путь к базе данных (по умолчанию data/bot_database.db)
DB_PATH = os.getenv("DATABASE_PATH", "data/bot_database.db")
# ===================================================

# 1. АСИНХРОННАЯ БАЗА ДАННЫХ (aiosqlite)
async def init_db():
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                roblox_username TEXT UNIQUE,
                roblox_user_id INTEGER UNIQUE,
                status TEXT DEFAULT 'pending'
            )
        ''')
        # НОВАЯ: Таблица логов авторизации (сохраняем также юзернейм в ТГ для таблицы логов)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                tg_username TEXT,
                roblox_username TEXT,
                timestamp TEXT
            )
        ''')
        await db.commit()
    print(f"База данных инициализирована по пути: {DB_PATH}")

async def register_user(tg_id, username, roblox_id):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO users (tg_id, roblox_username, roblox_user_id) VALUES (?, ?, ?)", (tg_id, username, roblox_id))
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        return False

async def update_status(tg_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET status = ? WHERE tg_id = ?", (status, tg_id))
        await db.commit()

async def delete_user_by_username(username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM users WHERE roblox_username COLLATE NOCASE = ?", (username,))
        deleted = cursor.rowcount > 0
        await db.commit()
        return deleted

async def log_authorization(tg_id: int, tg_username: str, roblox_username: str):
    # Время по МСК (или просто текущее системное)
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO logs (tg_id, tg_username, roblox_username, timestamp) VALUES (?, ?, ?, ?)",
            (tg_id, tg_username, roblox_username, now_str)
        )
        await db.commit()

# Получение всех логов
async def get_all_logs():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT tg_id, tg_username, roblox_username, timestamp FROM logs ORDER BY id DESC") as cursor:
            return await cursor.fetchall()


# 2. ФУНКЦИИ ROBLOX API
async def get_roblox_user_id(username: str):
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": True}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("data"):
                    return data["data"][0]["id"], data["data"][0]["name"]
            return None, None

async def get_user_creation_date(roblox_id: int):
    url = f"https://users.roblox.com/v1/users/{roblox_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("created")
    return None

async def get_user_groups(roblox_id: int):
    url = f"https://groups.roblox.com/v2/users/{roblox_id}/groups/roles"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return [g["group"]["id"] for g in data.get("data", [])]
    return []

async def analyze_account(roblox_id: int):
    reasons = []
    
    created_str = await get_user_creation_date(roblox_id)
    if created_str:
        try:
            created_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_days = (now - created_date).days
            
            if age_days < 14:
                reasons.append(f"Новый аккаунт (возраст: {age_days} дн.)")
        except Exception:
            reasons.append("Ошибка определения возраста")
            
    user_groups = await get_user_groups(roblox_id)
    forbidden = set(user_groups).intersection(set(BLACKLIST_GROUPS))
    if forbidden:
        reasons.append(f"Состоит в запрещенных группах: {', '.join(map(str, forbidden))}")

    if reasons:
        return True, " | ".join(reasons)
    return False, "Чистый аккаунт"

async def roblox_request(method: str, url: str, csrf_token: str = None):
    headers = {"Cookie": f".ROBLOSECURITY={ROBLOX_COOKIE}", "Content-Type": "application/json"}
    if csrf_token: headers["X-CSRF-TOKEN"] = csrf_token
        
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers) as response:
            if response.status == 403 and "x-csrf-token" in response.headers:
                return await roblox_request(method, url, csrf_token=response.headers["x-csrf-token"])
            try:
                res_json = await response.json()
            except:
                res_json = {}
            return response.status, res_json

async def accept_join_request(group_id: int, roblox_user_id: int):
    url = f"https://groups.roblox.com/v1/groups/{group_id}/join-requests/users/{roblox_user_id}"
    status, data = await roblox_request("POST", url)
    if status == 200:
        return True, "Успешно одобрено"
    else:
        return False, data.get("errors", [{}])[0].get("message", "Неизвестная ошибка")


# 3. БОТ (ХЭНДЛЕРЫ)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Команда /reset Никнейм (только для админа)
@dp.message(Command("reset"))
async def cmd_reset_user(message: Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID:
        return 
        
    if not command.args:
        await message.answer(
            "⚠️ <b>Ошибка:</b> Не указан никнейм.\n"
            "Использование: <code>/reset НикИгрока</code>\n"
            "Пример: <code>/reset Builderman</code>"
        )
        return
        
    username_to_reset = command.args.strip()
    is_deleted = await delete_user_by_username(username_to_reset)
    
    if is_deleted:
        await message.answer(
            f"✅ Привязка для аккаунта <b>{username_to_reset}</b> успешно удалена из базы!\n\n"
            f"Теперь пользователь сможет отправить новую заявку и привязать новый никнейм."
        )
    else:
        await message.answer(f"❌ Аккаунт <b>{username_to_reset}</b> не найден в базе данных.")

from aiogram import html

# Команда /admin ID (доступна только Создателю из переменной окружения)
@dp.message(Command("admin"))
async def cmd_change_admin(message: Message, command: CommandObject):
    global ADMIN_ID
    if message.from_user.id != CREATOR_ID: # Убедись, что CREATOR_ID задан в коде
        return

    if not command.args or not command.args.strip().isdigit():
        await message.answer("⚠️ Использование: <code>/admin ID_ПОЛЬЗОВАТЕЛЯ</code>")
        return

    new_admin_id = int(command.args.strip())
    ADMIN_ID = new_admin_id
    await message.answer(f"👑 Новый администратор успешно назначен! ID: <code>{new_admin_id}</code>. Теперь все заявки на проверку будут дублироваться ему.")

# Команда /logs (доступна Создателю и текущему Админу)
@dp.message(Command("logs"))
async def cmd_view_logs(message: Message):
    if message.from_user.id not in (CREATOR_ID, ADMIN_ID):
        return

    logs = await get_all_logs()
    if not logs:
        await message.answer("🗄 Список логов авторизации пока пуст.")
        return

    text = "📋 <b>Логи авторизаций в Roblox:</b>\n\n"
    
    for tg_id, tg_username, roblox_username, timestamp in logs:
        display_name = f"@{tg_username}" if tg_username else "Пользователь"
        safe_name = html.quote(display_name)
        
        # Строка таблицы с кликабельным TG ником, ID в скобках и ником Roblox
        line = f"🕒 [{timestamp}] 👤 <a href='tg://user?id={tg_id}'>{safe_name}</a> (<code>{tg_id}</code>) ➔ 🎮 <b>{roblox_username}</b>\n"
        
        # Лимит одного сообщения в ТГ — 4096 символов. Разбиваем, если логов слишком много
        if len(text) + len(line) > 4000:
            await message.answer(text, disable_web_page_preview=True)
            text = ""
        text += line

    if text:
        await message.answer(text, disable_web_page_preview=True)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_data = await get_user(message.from_user.id)
    if user_data:
        await message.answer(f"Ты уже привязал аккаунт <b>{user_data[0]}</b>. Статус: {user_data[2]}")
    else:
        await message.answer("Пришли мне свой никнейм в Roblox (только точный ник!):")

@dp.message()
async def process_nickname(message: Message):
    user_id = message.from_user.id
    if await get_user(user_id):
        await message.answer("Никнейм уже привязан.")
        return
        
    username = message.text.strip()
    roblox_id, real_username = await get_roblox_user_id(username)
    if not roblox_id:
        await message.answer("❌ Игрок не найден. Проверь ник.")
        return
        
    if not await register_user(user_id, real_username, roblox_id):
        await message.answer("❌ Этот аккаунт уже используется.")
        return
        
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я нажал(а) Join Group", callback_data=f"check_{user_id}")]
    ])
    
    await message.answer(
        f"✅ Никнейм <b>{real_username}</b> найден!\n\n"
        f"⚠️ <b>Остался последний шаг:</b>\n"
        f"1. Открой нашу группу в Roblox\n"
        f"2. Нажми кнопку <b>'Join Group'</b> (отправь заявку)\n"
        f"3. ТОЛЬКО ПОСЛЕ ЭТОГО нажми кнопку ниже, чтобы бот проверил твой аккаунт.",
        reply_markup=markup
    )

@dp.callback_query(F.data.startswith('check_'))
async def process_check_join(callback: CallbackQuery):
    user_id = int(callback.data.split('_')[1])
    if callback.from_user.id != user_id:
        await callback.answer("Это не твоя кнопка!", show_alert=True)
        return

    user_data = await get_user(user_id)
    roblox_username, roblox_id, status = user_data
    
    if status != 'pending':
        await callback.answer("Ваша заявка уже была обработана.", show_alert=True)
        return

    await callback.message.edit_text("⏳ Анализирую аккаунт (дата регистрации, группы)...")
    
    needs_review, reason = await analyze_account(roblox_id)

    if needs_review:
        admin_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{user_id}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")]
        ])
        tg_user = f"@{callback.from_user.username}" if callback.from_user.username else f"ID: {user_id}"
        
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=(f"🔔 <b>Ручная проверка!</b>\n"
                  f"👤 Telegram: {tg_user}\n🎮 Ник: <b>{roblox_username}</b>\n"
                  f"⚠️ <b>Сработало правило:</b> {reason}\n"
                  f"🔗 <a href='https://www.roblox.com/users/{roblox_id}/profile'>Профиль игрока</a>"),
            reply_markup=admin_markup, disable_web_page_preview=True
        )
        await callback.message.edit_text(
            f"⚠️ Твой аккаунт не прошел автоматическую проверку.\n"
            f"Заявка отправлена администраторам на ручное рассмотрение. Ожидай!"
        )
    else:
        success, message_text = await accept_join_request(GROUP_ID, roblox_id)
        if success:
            await update_status(user_id, 'approved')
            await log_authorization(user_id, callback.from_user.username, roblox_username)
            
            await callback.message.edit_text(
                f"🎉 Авто-проверка пройдена успешно!\n"
                f"Бот автоматически принял тебя в группу Roblox под ником <b>{roblox_username}</b>!"
            )
        else:
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить снова", callback_data=f"check_{user_id}")]
            ])
            await callback.message.edit_text(
                f"❌ Ошибка Roblox: {message_text}\n\n"
                f"Ты точно нажал(а) кнопку 'Join Group'? Попробуй отправить заявку и нажми проверить снова.",
                reply_markup=markup
            )

@dp.callback_query(F.data.startswith('approve_'))
async def handle_approve(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    user_id = int(callback.data.split('_')[1])
    user_data = await get_user(user_id)
    if not user_data or user_data[2] == 'approved': return
        
    success, msg = await accept_join_request(GROUP_ID, user_data[1])
    if success:
        await update_status(user_id, 'approved')
        await log_authorization(user_id, callback.from_user.username, user_data[0])
        await callback.message.edit_text(f"✅ Заявка {user_data[0]} (TG: {user_id}) одобрена вручную!")
        try: await bot.send_message(user_id, f"🎉 Твоя заявка была одобрена администратором!") 
        except: pass
    else:
        await callback.answer(f"Ошибка API: {msg}", show_alert=True)

@dp.callback_query(F.data.startswith('reject_'))
async def handle_reject(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    user_id = int(callback.data.split('_')[1])
    user_data = await get_user(user_id)
    if not user_data or user_data[2] == 'rejected': return
        
    await update_status(user_id, 'rejected')
    await callback.message.edit_text(f"❌ Заявка {user_data[0]} отклонена.")
    try: await bot.send_message(user_id, f"❌ Извини, твоя заявка для <b>{user_data[0]}</b> отклонена администратором.")
    except: pass


async def main():
    await init_db()  # Обязательно добавляем await сюда!
    print("Бот с фильтром запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
