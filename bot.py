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

# ---------------- DATA ----------------
links = {}
video_requests = {}
pending_video_send = {}

# ---------------- STATES ----------------
class LinkState(StatesGroup):
    waiting = State()

# ---------------- KEYBOARDS ----------------
def user_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Отправить ссылку", callback_data="send_link")],
        [InlineKeyboardButton(text="🎬 Запросить видео", callback_data="ask_video")]
    ])


def admin_link_kb(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟡 В работе", callback_data=f"link_work:{uid}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"link_reject:{uid}")
        ],
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"link_approve:{uid}")
        ]
    ])


def admin_video_kb(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟡 В работе", callback_data=f"video_work:{uid}"),
            InlineKeyboardButton(text="❌ Отказ", callback_data=f"video_reject:{uid}")
        ],
        [
            InlineKeyboardButton(text="📤 Отправить видео", callback_data=f"video_send:{uid}")
        ]
    ])


# ---------------- START ----------------
@dp.message(Command("start"))
async def start(m: Message):
    await m.answer("Меню:", reply_markup=user_menu())


# ---------------- USER: MENU ----------------
@dp.callback_query()
async def user_actions(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    data = call.data

    # ---------- LINK ----------
    if data == "send_link":
        await state.set_state(LinkState.waiting)
        await call.message.answer("📎 Отправьте ссылку:")

    # ---------- VIDEO REQUEST ----------
    elif data == "ask_video":
        video_requests[uid] = {"status": "new"}

        await call.message.answer("🎬 Запрос отправлен")

        await bot.send_message(
            ADMIN_ID,
            f"🎬 ЗАПРОС ВИДЕО\n👤 {call.from_user.username}\n🆔 {uid}",
            reply_markup=admin_video_kb(uid)
        )

    await call.answer()


# ---------------- LINK INPUT ----------------
@dp.message(LinkState.waiting)
async def link_input(m: Message, state: FSMContext):
    uid = m.from_user.id
    link = m.text

    links[uid] = {"link": link, "status": "moderation"}

    await m.answer("⏳ Отправлено на модерацию")

    await bot.send_message(
        ADMIN_ID,
        f"📎 ССЫЛКА НА МОДЕРАЦИЮ\n👤 {m.from_user.username}\n🆔 {uid}\n🔗 {link}",
        reply_markup=admin_link_kb(uid)
    )

    await state.clear()


# ======================================================
# =================== ADMIN LOGIC ======================
# ======================================================

@dp.callback_query()
async def admin_handler(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    data = call.data

    # ---------------- LINK ----------------
    if data.startswith("link_work:"):
        uid = int(data.split(":")[1])
        await bot.send_message(uid, "🟡 Ваша заявка в работе")
        await call.message.answer("ОК")

    elif data.startswith("link_reject:"):
        uid = int(data.split(":")[1])
        await bot.send_message(uid, "❌ Ваша заявка отклонена")
        await call.message.answer("Отклонено")

    elif data.startswith("link_approve:"):
        uid = int(data.split(":")[1])
        await bot.send_message(uid, "✅ Ваша заявка одобрена и будет обработана")
        await call.message.answer("Одобрено")

    # ---------------- VIDEO ----------------
    elif data.startswith("video_work:"):
        uid = int(data.split(":")[1])
        await bot.send_message(uid, "🟡 Видео в работе")
        await call.message.answer("ОК")

    elif data.startswith("video_reject:"):
        uid = int(data.split(":")[1])
        await bot.send_message(uid, "❌ Видео-запрос отклонён")
        await call.message.answer("Отказ")

    elif data.startswith("video_send:"):
        uid = int(data.split(":")[1])
        pending_video_send["uid"] = uid
        await call.message.answer("📤 Отправьте видео следующим сообщением:")

    await call.answer()


# ---------------- ADMIN SEND VIDEO ----------------
@dp.message(F.video | F.document)
async def send_video(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    uid = pending_video_send.get("uid")
    if not uid:
        return

    if m.video:
        await bot.send_video(uid, m.video.file_id)
    else:
        await bot.send_document(uid, m.document.file_id)

    await bot.send_message(uid, "📤 Видео отправлено")

    pending_video_send.clear()


# ---------------- RUN ----------------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
