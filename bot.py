import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# хранение заявок
links = {}
video_requests = {}

# ожидания
waiting_link = {}
waiting_admin_video = {}


# ---------------- STATES ----------------
class LinkState(StatesGroup):
    waiting_link = State()


class AdminVideoState(StatesGroup):
    waiting_video = State()


# ---------------- UI ----------------
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Отправить ссылку", callback_data="send_link")],
        [InlineKeyboardButton(text="🎬 Запросить видео", callback_data="ask_video")]
    ])


def admin_video_kb(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟡 В работе", callback_data=f"work:{user_id}"),
            InlineKeyboardButton(text="❌ Отказ", callback_data=f"reject:{user_id}")
        ],
        [
            InlineKeyboardButton(text="📤 Отправить видео", callback_data=f"send_video:{user_id}")
        ]
    ])


# ---------------- START ----------------
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Выберите действие:", reply_markup=main_menu())


# ---------------- CALLBACK USER ----------------
@dp.callback_query()
async def cb(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    data = call.data

    # -------- LINK FLOW --------
    if data == "send_link":
        await state.set_state(LinkState.waiting_link)
        await call.message.answer("📎 Отправьте ссылку:")

    # -------- VIDEO REQUEST --------
    elif data == "ask_video":
        video_requests[user_id] = {"status": "new"}

        await call.message.answer("🎬 Запрос отправлен")

        await bot.send_message(
            ADMIN_ID,
            f"🎬 НОВЫЙ ЗАПРОС ВИДЕО\n👤 {call.from_user.username}\n🆔 {user_id}",
            reply_markup=admin_video_kb(user_id)
        )

    await call.answer()


# ---------------- LINK HANDLER ----------------
@dp.message(LinkState.waiting_link)
async def link_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    link = message.text

    links[user_id] = {"link": link, "status": "moderation"}

    await message.answer("⏳ Видео на модерации")

    await bot.send_message(
        ADMIN_ID,
        f"📎 ССЫЛКА НА МОДЕРАЦИЮ\n👤 {message.from_user.username}\n🆔 {user_id}\n🔗 {link}\n\n"
        f"Статус: модерация"
    )

    await state.clear()
    await message.answer("Выберите действие:", reply_markup=main_menu())


# ---------------- ADMIN ACTIONS ----------------
@dp.callback_query()
async def admin_actions(call: CallbackQuery):
    data = call.data

    if call.from_user.id != ADMIN_ID:
        return

    # в работе
    if data.startswith("work:"):
        uid = int(data.split(":")[1])
        await call.message.answer("🟡 Отмечено как в работе")

    # отказ
    elif data.startswith("reject:"):
        uid = int(data.split(":")[1])
        await bot.send_message(uid, "❌ Ваш запрос отклонён")
        await call.message.answer("Отклонено")

    # отправка видео
    elif data.startswith("send_video:"):
        uid = int(data.split(":")[1])

        waiting_admin_video["uid"] = uid

        await call.message.answer("Отправьте видео следующим сообщением:")


# ---------------- ADMIN SEND VIDEO ----------------
@dp.message(F.video | F.document | F.text)
async def admin_send_video(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    uid = waiting_admin_video.get("uid")
    if not uid:
        return

    if message.video:
        await bot.send_video(uid, message.video.file_id)

    elif message.document:
        await bot.send_document(uid, message.document.file_id)

    else:
        await bot.send_message(uid, f"📤 Видео/сообщение:\n{message.text}")

    await bot.send_message(uid, "📤 Видео отправлено админом")
    waiting_admin_video.clear()


# ---------------- RUN ----------------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())