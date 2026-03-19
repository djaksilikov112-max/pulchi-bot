import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import database as db
import keyboards as kb
from config import config

logger = logging.getLogger(__name__)
router = Router()

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

class AdminStates(StatesGroup):
    broadcast_text = State()

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz.")
        return
    stats = db.get_stats()
    text = (
        "👑 <b>Admin Panel</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"💎 Faol obunalar: <b>{stats['active_subs']}</b>\n"
        f"💰 Daromad: <b>{stats['total_revenue']:,} so'm</b>\n"
        f"🧮 Kalkulyator: <b>{stats['calc_count']}</b>\n"
        f"🤖 AI: <b>{stats['ai_count']}</b>\n"
        f"📊 Bugun: <b>{stats['today_users']}</b>"
    )
    await message.answer(text, reply_markup=kb.admin_kb())

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    stats = db.get_stats()
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami: {stats['total_users']}\n"
        f"💎 Obunalar: {stats['active_subs']}\n"
        f"💰 Daromad: {stats['total_revenue']:,} so'm\n"
        f"🧮 Kalkulyator: {stats['calc_count']}\n"
        f"🤖 AI: {stats['ai_count']}\n"
        f"📅 Bugun: {stats['today_users']}"
    )
    await message.answer(text)

@router.message(Command("broadcast"))
async def cmd_broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.broadcast_text)
    await message.answer("📢 Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:\n<i>(/cancel bekor qilish)</i>")

@router.message(AdminStates.broadcast_text)
async def do_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    with db.get_connection() as conn:
        users = conn.execute("SELECT user_id FROM users").fetchall()
    sent = 0
    failed = 0
    for (user_id,) in users:
        try:
            await message.bot.send_message(user_id, message.text)
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"✅ Yuborildi: {sent}\n❌ Yuborilmadi: {failed}")
    db.log_event("broadcast", message.from_user.id)

@router.message(Command("update_rates"))
async def cmd_update_rates(message: Message):
    if not is_admin(message.from_user.id):
        return
    banks = db.get_all_banks()
    lines = ["🏦 <b>Banklar:</b>\n"]
    for b in banks:
        lines.append(f"ID={b['id']} | {b['name']}: {b['min_rate']}%–{b['max_rate']}%")
    lines.append("\n<i>/set_rate {id} {min} {max}</i>")
    await message.answer("\n".join(lines))

@router.message(Command("set_rate"))
async def cmd_set_rate(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("❌ Format: /set_rate {bank_id} {min} {max}")
        return
    try:
        bank_id = int(parts[1])
        min_rate = float(parts[2])
        max_rate = float(parts[3])
    except ValueError:
        await message.answer("❌ Noto'g'ri qiymatlar.")
        return
    db.update_bank_rate(bank_id, min_rate, max_rate)
    bank = db.get_bank(bank_id)
    await message.answer(f"✅ <b>{bank['name']}</b> yangilandi: {min_rate}%–{max_rate}%")

@router.message(Command("confirm_pay"))
async def cmd_confirm_pay(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❌ Format: /confirm_pay {payment_id} {transaction_id}")
        return
    payment_id = int(parts[1])
    transaction_id = parts[2]
    with db.get_connection() as conn:
        pay = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
        if not pay:
            await message.answer("❌ To'lov topilmadi.")
            return
    db.confirm_payment(payment_id, transaction_id)
    try:
        await message.bot.send_message(pay["user_id"], "🎉 <b>Obuna faollashtirildi!</b>\n\nTo'lovingiz tasdiqlandi!")
    except Exception:
        pass
    await message.answer(f"✅ To'lov #{payment_id} tasdiqlandi.")

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("✅ Bekor qilindi.")

@router.callback_query(F.data == "adm_stats")
async def cb_adm_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    stats = db.get_stats()
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami: {stats['total_users']}\n"
        f"💎 Obunalar: {stats['active_subs']}\n"
        f"💰 Daromad: {stats['total_revenue']:,} so'm\n"
        f"🧮 Kalkulyator: {stats['calc_count']}\n"
        f"🤖 AI: {stats['ai_count']}\n"
        f"📅 Bugun: {stats['today_users']}"
    )
    await call.message.edit_text(text, reply_markup=kb.admin_kb())

@router.callback_query(F.data == "adm_banks")
async def cb_adm_banks(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    banks = db.get_all_banks()
    lines = ["🏦 <b>Banklar:</b>\n"]
    for b in banks:
        lines.append(f"✅ ID={b['id']} {b['name']}: {b['min_rate']}–{b['max_rate']}%")
    await call.message.edit_text("\n".join(lines), reply_markup=kb.admin_kb())

@router.callback_query(F.data == "adm_users")
async def cb_adm_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    with db.get_connection() as conn:
        recent = conn.execute("SELECT user_id, full_name, is_subscribed, last_active FROM users ORDER BY last_active DESC LIMIT 10").fetchall()
    lines = ["👥 <b>So'nggi 10 foydalanuvchi:</b>\n"]
    for r in recent:
        sub_icon = "💎" if r["is_subscribed"] else "👤"
        lines.append(f"{sub_icon} {r['full_name'] or '—'} (ID: {r['user_id']})")
    await call.message.edit_text("\n".join(lines), reply_markup=kb.admin_kb())

@router.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AdminStates.broadcast_text)
    await call.message.edit_text("📢 Xabar matnini kiriting:")
