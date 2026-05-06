import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------------- STATES ----------------
class LinkState(StatesGroup):
    waiting = State()

pending_video = {}

# ---------------- UI ----------------
def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Отправить ссылку", callback_data="link")],
        [InlineKeyboardButton(text="🎬 Запросить видео", callback_data="video")]
    ])

def admin_kb(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟡 В работе", callback_data=f"work:{uid}"),
            InlineKeyboardButton(text="❌ Отказ", callback_data=f"reject:{uid}")
        ],
        [
            InlineKeyboardButton(text="📤 Отправить видео", callback_data=f"send:{uid}")
        ]
    ])

# ---------------- START ----------------
@dp.message(F.text == "/start")
async def start(m: Message):
    await m.answer("Меню:", reply_markup=menu())

# ---------------- USER ----------------
@dp.callback_query()
async def cb(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    data = call.data

    if data == "link":
        await state.set_state(LinkState.waiting)
        await call.message.answer("📎 Введите ссылку:")

    elif data == "video":
        await bot.send_message(
            ADMIN_ID,
            f"🎬 ЗАПРОС ВИДЕО\n👤 {call.from_user.username}\n🆔 {uid}",
            reply_markup=admin_kb(uid)
        )
        await call.message.answer("🎬 Запрос отправлен")

# ---------------- LINK INPUT ----------------
@dp.message(LinkState.waiting)
async def link(m: Message, state: FSMContext):
    uid = m.from_user.id

    await bot.send_message(
        ADMIN_ID,
        f"📎 ССЫЛКА\n👤 {m.from_user.username}\n🆔 {uid}\n🔗 {m.text}",
        reply_markup=admin_kb(uid)
    )

    await m.answer("⏳ Отправлено на модерацию")
    await state.clear()

# ---------------- ADMIN ACTIONS ----------------
@dp.callback_query()
async def admin(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    data = call.data

    if data.startswith("work:"):
        uid = int(data.split(":")[1])
        await bot.send_message(uid, "🟡 В работе")

    elif data.startswith("reject:"):
        uid = int(data.split(":")[1])
        await bot.send_message(uid, "❌ Отклонено")

    elif data.startswith("send:"):
        uid = int(data.split(":")[1])
        pending_video["uid"] = uid
        await call.message.answer("📤 Отправьте видео")

# ---------------- VIDEO FROM ADMIN ----------------
@dp.message(F.video | F.document)
async def video(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    uid = pending_video.get("uid")
    if not uid:
        return

    if m.video:
        await bot.send_video(uid, m.video.file_id)
    else:
        await bot.send_document(uid, m.document.file_id)

    await bot.send_message(uid, "📤 Видео отправлено")
    pending_video.clear()

# ---------------- WEBHOOK SETUP ----------------
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

def main():
    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

if __name__ == "__main__":
    main()
