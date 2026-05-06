import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

requests = {}
waiting_reply = {}


# ---------- STATES ----------
class ReplyState(StatesGroup):
    waiting_text = State()


# ---------- KEYBOARDS ----------
def user_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📹 Запросить видео", callback_data="request_video")],
        [InlineKeyboardButton(text="❌ Отменить запрос", callback_data="cancel")]
    ])


def admin_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"approve:{user_id}")],
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply:{user_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")]
    ])


# ---------- START ----------
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Отправь ссылку или запрос:", reply_markup=user_keyboard())


# ---------- USER ----------
@dp.message(F.text)
async def handle_text(message: Message):
    uid = message.from_user.id
    text = message.text

    requests[uid] = {"text": text, "status": "pending"}

    await message.answer("⏳ Отправлено на проверку")

    await bot.send_message(
        ADMIN_ID,
        f"📩 Новый запрос\n\n"
        f"👤 @{message.from_user.username}\n"
        f"🆔 {uid}\n"
        f"📎 {text}",
        reply_markup=admin_keyboard(uid)
    )


# ---------- CALLBACK ----------
@dp.callback_query()
async def callback(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    data = call.data

    if data == "request_video":
        requests[uid] = {"type": "video", "status": "pending"}

        await call.message.answer("📹 Запрос отправлен")

        await bot.send_message(
            ADMIN_ID,
            f"📹 VIDEO REQUEST\n👤 {call.from_user.username}\n🆔 {uid}",
            reply_markup=admin_keyboard(uid)
        )

    elif data == "cancel":
        requests[uid] = {"status": "canceled"}

        await call.message.answer("❌ Отменено")

        await bot.send_message(ADMIN_ID, f"⚠️ User {uid} отменил запрос")

    elif data.startswith("approve:"):
        target = int(data.split(":")[1])
        await bot.send_message(target, "✅ Принято")
        await call.message.answer("OK")

    elif data.startswith("reject:"):
        target = int(data.split(":")[1])
        await bot.send_message(target, "❌ Отклонено")
        await call.message.answer("OK")

    elif data.startswith("reply:"):
        target = int(data.split(":")[1])
        waiting_reply[uid] = target

        await state.set_state(ReplyState.waiting_text)
        await call.message.answer("Введите ответ:")


# ---------- ADMIN REPLY ----------
@dp.message(ReplyState.waiting_text)
async def reply(message: Message, state: FSMContext):
    admin = message.from_user.id

    if admin != ADMIN_ID:
        return

    user_id = waiting_reply.get(admin)

    await bot.send_message(user_id, f"💬 Ответ:\n{message.text}")

    await message.answer("Отправлено")
    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())