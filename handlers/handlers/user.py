import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import database as db
import keyboards as kb
from utils import calculate_all_banks, format_calc_results, format_money, CREDIT_TYPE_INFO, get_required_docs, get_application_script, ai_advise
from config import config

logger = logging.getLogger(__name__)
router = Router()

class CalcStates(StatesGroup):
    waiting_amount = State()
    waiting_months = State()

class ProfileStates(StatesGroup):
    waiting_age = State()

class AIStates(StatesGroup):
    chatting = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    db.upsert_user(user.id, user.username, user.full_name)
    db.log_event("start", user.id)
    text = (
        f"👋 Salom, <b>{user.first_name}</b>!\n\n"
        f"🏦 <b>Pulchi Bot</b>ga xush kelibsiz!\n\n"
        "Men sizga O'zbekistondagi barcha banklarning kredit va omonat "
        "shartlarini solishtirish hamda eng mos kreditni topishda yordam beraman.\n\n"
        "Quyidagi menyudan kerakli bo'limni tanlang 👇"
    )
    await message.answer(text, reply_markup=kb.main_menu_kb())

@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📋 Asosiy menyu:", reply_markup=kb.main_menu_kb())

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "❓ <b>Yordam</b>\n\n"
        "🧮 <b>Kredit Kalkulyator</b> – Summa va muddatni kiriting\n\n"
        "🤖 <b>AI Maslahatchi</b> – Tez orada ishga tushadi\n\n"
        "💳 <b>Kredit Turlari</b> – Barcha kredit turlarini ko'ring\n\n"
        "💰 <b>Omonat Foizlari</b> – Depozit stavkalarini solishtiring\n\n"
        "📋 <b>Ariza Yordamchisi</b> – Obuna a'zolari uchun\n\n"
        "📞 Muammo bo'lsa: @pulchi_support"
    )
    await message.answer(text, reply_markup=kb.back_to_menu_kb())

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("📋 <b>Asosiy Menyu</b>\n\nQuyidagidan tanlang 👇", reply_markup=kb.main_menu_kb())

@router.callback_query(F.data == "calc")
async def cb_calc_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(CalcStates.waiting_amount)
    await call.message.edit_text(
        "🧮 <b>Kredit Kalkulyator</b>\n\nKredit summani kiriting (so'mda):\n\n<i>Masalan: 5000000 yoki 5 mln</i>",
        reply_markup=kb.back_to_menu_kb()
    )

@router.message(CalcStates.waiting_amount)
async def calc_get_amount(message: Message, state: FSMContext):
    text = message.text.strip().lower().replace(" ", "").replace(",", "")
    multiplier = 1
    if "mlrd" in text:
        multiplier = 1_000_000_000
        text = text.replace("mlrd", "")
    elif "mln" in text:
        multiplier = 1_000_000
        text = text.replace("mln", "")
    try:
        amount = float(text) * multiplier
        if amount < 500_000:
            await message.answer("❌ Minimal kredit summasi 500,000 so'm.\nQayta kiriting:")
            return
        if amount > 10_000_000_000:
            await message.answer("❌ Maksimal summa 10 mlrd so'm.\nQayta kiriting:")
            return
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Raqam kiriting:\n<i>Masalan: 5000000</i>")
        return
    await state.update_data(amount=amount)
    await state.set_state(CalcStates.waiting_months)
    await message.answer(f"✅ Summa: <b>{format_money(amount)}</b>\n\n📅 Kredit muddatini kiriting (oyda):\n\n<i>Masalan: 12, 24, 60</i>")

@router.message(CalcStates.waiting_months)
async def calc_get_months(message: Message, state: FSMContext):
    try:
        months = int(message.text.strip())
        if months < 1 or months > 300:
            await message.answer("❌ Muddat 1 dan 300 oygacha bo'lishi kerak.")
            return
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting.")
        return
    data = await state.get_data()
    amount = data["amount"]
    await state.clear()
    results = calculate_all_banks(amount, months)
    result_text = format_calc_results(results, amount, months)
    db.log_event("calc_used", message.from_user.id)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for r in results[:5]:
        builder.row(InlineKeyboardButton(
            text=f"{r['emoji']} {r['bank_name']} – {r['min_payment']:,.0f} so'm/oy",
            callback_data=f"bank_detail_{r['bank_id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Menyu", callback_data="main_menu"))
    await message.answer(result_text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "credit_types")
async def cb_credit_types(call: CallbackQuery):
    await call.message.edit_text("💳 <b>Kredit Turlari</b>\n\nQaysi turdagi kredit qiziqtiradi?", reply_markup=kb.credit_types_kb())

@router.callback_query(F.data.startswith("ct_"))
async def cb_credit_type_detail(call: CallbackQuery):
    code = call.data[3:]
    info = CREDIT_TYPE_INFO.get(code)
    if not info:
        await call.answer("Ma'lumot topilmadi", show_alert=True)
        return
    from database import get_banks_by_credit_type
    banks = get_banks_by_credit_type(code)
    text = f"{info['name']}\n\n{info['desc']}\n\n"
    text += f"🏦 <b>Ushbu kredit beruvchi banklar ({len(banks)} ta):</b>\n"
    for b in banks:
        text += f"• {b['logo_emoji']} {b['name']}: {b['min_rate']}–{b['max_rate']}%\n"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🧮 Bu turdagi kredit hisoblash", callback_data=f"calc_type_{code}"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="credit_types"))
    await call.message.edit_text(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "deposits")
async def cb_deposits(call: CallbackQuery):
    banks = db.get_all_banks()
    text = "💰 <b>Omonat (Depozit) Stavkalari</b>\n\n"
    for b in banks:
        text += (
            f"{b['logo_emoji']} <b>{b['name']}</b>\n"
            f"   UZS: taxminan {b['min_rate']-2:.0f}–{b['min_rate']:.0f}%\n"
            f"   USD: taxminan 5–8%\n\n"
        )
    text += "📞 <i>Aniq stavkalar uchun bankga murojaat qiling.</i>"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Menyu", callback_data="main_menu"))
    await call.message.edit_text(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("bank_detail_"))
async def cb_bank_detail(call: CallbackQuery):
    bank_id = int(call.data.split("_")[-1])
    bank = db.get_bank(bank_id)
    if not bank:
        await call.answer("Bank topilmadi", show_alert=True)
        return
    import json
    ct_list = json.loads(bank.get("credit_types") or "[]")
    ct_names = {"micro": "Mikrokredit", "business": "Biznes", "ipoteka": "Ipoteka", "auto": "Avtokredit", "unemployed": "Ishsizlar"}
    ct_str = ", ".join(ct_names.get(c, c) for c in ct_list)
    text = (
        f"{bank['logo_emoji']} <b>{bank['name']}</b>\n\n"
        f"📊 Stavka: <b>{bank['min_rate']}% – {bank['max_rate']}%</b>\n"
        f"💵 Summa: {format_money(bank['min_amount'])} – {format_money(bank['max_amount'])}\n"
        f"📅 Muddat: {bank['min_term']} – {bank['max_term']} oy\n"
        f"💳 Kredit turlari: {ct_str}\n\n"
        f"📋 <b>Talablar:</b>\n{bank['requirements']}\n\n"
        f"✅ <b>Afzalliklar:</b>\n{bank['advantages']}\n\n"
        f"📞 {bank['phone']}\n"
        f"🌐 {bank['website']}"
    )
    await call.message.edit_text(text, reply_markup=kb.bank_detail_kb(bank_id))

@router.callback_query(F.data.startswith("docs_"))
async def cb_bank_docs(call: CallbackQuery):
    bank_id = int(call.data.split("_")[-1])
    bank = db.get_bank(bank_id)
    if not db.is_subscribed(call.from_user.id):
        await call.message.edit_text(
            "🔒 <b>Bu funksiya faqat obuna a'zolari uchun!</b>\n\n"
            f"💰 Bor-yo'g'i {config.PRICE_1_DAY:,} so'm/kun!",
            reply_markup=kb.subscription_kb(db.has_reconnect_discount(call.from_user.id))
        )
        return
    docs_text = get_required_docs(bank["name"] if bank else "")
    await call.message.edit_text(f"📄 <b>{bank['name']} uchun hujjatlar</b>\n\n{docs_text}", reply_markup=kb.bank_detail_kb(bank_id))

@router.callback_query(F.data.startswith("script_"))
async def cb_bank_script(call: CallbackQuery):
    bank_id = int(call.data.split("_")[-1])
    bank = db.get_bank(bank_id)
    if not db.is_subscribed(call.from_user.id):
        await call.message.edit_text("🔒 Bu funksiya obuna talab qiladi!", reply_markup=kb.subscription_kb(db.has_reconnect_discount(call.from_user.id)))
        return
    script = get_application_script(bank["name"] if bank else "Bank")
    await call.message.edit_text(script, reply_markup=kb.bank_detail_kb(bank_id))

@router.callback_query(F.data.startswith("branch_"))
async def cb_branch(call: CallbackQuery):
    bank_id = int(call.data.split("_")[-1])
    bank = db.get_bank(bank_id)
    if not db.is_subscribed(call.from_user.id):
        await call.message.edit_text("🔒 Bu funksiya obuna talab qiladi!", reply_markup=kb.subscription_kb(db.has_reconnect_discount(call.from_user.id)))
        return
    text = (
        f"📍 <b>{bank['name']} filiallari</b>\n\n"
        f"📞 Qo'ng'iroq markazi: <b>{bank['phone']}</b>\n"
        f"🌐 {bank['website']}\n\n"
        f"<i>Eng yaqin filial uchun sayt yoki qo'ng'iroq markaziga murojaat qiling.</i>"
    )
    await call.message.edit_text(text, reply_markup=kb.bank_detail_kb(bank_id))

@router.callback_query(F.data.startswith("timing_"))
async def cb_timing(call: CallbackQuery):
    bank_id = int(call.data.split("_")[-1])
    bank = db.get_bank(bank_id)
    if not db.is_subscribed(call.from_user.id):
        await call.message.edit_text("🔒 Bu funksiya obuna talab qiladi!", reply_markup=kb.subscription_kb(db.has_reconnect_discount(call.from_user.id)))
        return
    timings = {
        "Agrobank": "5–10 ish kuni", "Mikrokreditbank": "3–5 ish kuni",
        "Xalq Banki": "7–14 ish kuni", "Anor Bank": "1–3 ish kuni",
        "Kapitalbank": "3–7 ish kuni", "Ipoteka Bank": "10–15 ish kuni",
        "SQB": "7–14 ish kuni", "Asaka Bank": "3–7 ish kuni",
        "Hamkorbank": "3–5 ish kuni", "Tenge Bank": "1–3 ish kuni",
    }
    bname = bank["name"] if bank else ""
    timing = timings.get(bname, "3–14 ish kuni")
    text = (
        f"⏱️ <b>{bname} – Ko'rib chiqish muddati</b>\n\n"
        f"🕐 Taxminiy muddat: <b>{timing}</b>\n\n"
        "📝 <b>Bosqichlar:</b>\n"
        "1. Ariza topshirish\n"
        "2. Kredit tarixi tekshirish\n"
        "3. Garovni baholash\n"
        "4. Kredit qo'mitasi qarori\n"
        "5. Shartnoma imzolash\n"
        "6. Pul o'tkazilishi"
    )
    await call.message.edit_text(text, reply_markup=kb.bank_detail_kb(bank_id))

@router.callback_query(F.data == "application_helper")
async def cb_app_helper(call: CallbackQuery):
    if not db.is_subscribed(call.from_user.id):
        await call.message.edit_text(
            "🔒 <b>Ariza Yordamchisi – Pullik xizmat</b>\n\n"
            "✅ Kerakli hujjatlar ro'yxati\n"
            "✅ Bank bilan muloqot skripti\n"
            "✅ Filial manzili\n"
            "✅ Ko'rib chiqish muddati\n\n"
            f"💎 1 kun: {config.PRICE_1_DAY:,} so'm\n"
            f"📅 1 hafta: {config.PRICE_WEEKLY:,} so'm",
            reply_markup=kb.subscription_kb(db.has_reconnect_discount(call.from_user.id))
        )
        return
    banks = db.get_all_banks()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for b in banks[:10]:
        builder.row(InlineKeyboardButton(text=f"{b['logo_emoji']} {b['name']}", callback_data=f"bank_detail_{b['id']}"))
    builder.row(InlineKeyboardButton(text="🔙 Menyu", callback_data="main_menu"))
    await call.message.edit_text("📋 <b>Ariza Yordamchisi</b>\n\nQaysi bank uchun yordam kerak?", reply_markup=builder.as_markup())

@router.message(Command("profile"))
@router.callback_query(F.data == "my_profile")
async def show_profile(event, state: FSMContext = None):
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        send = event.message.edit_text
    else:
        user_id = event.from_user.id
        send = event.answer
    user = db.get_user(user_id)
    if not user:
        db.upsert_user(user_id)
        user = db.get_user(user_id)
    sub_status = "✅ Faol" if db.is_subscribed(user_id) else "❌ Faol emas"
    emp_map = {"employed": "Ishlayman", "unemployed": "Ishsizman", "entrepreneur": "Tadbirkorman", None: "Kiritilmagan"}
    text = (
        f"👤 <b>Mening Profilim</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Ism: {user.get('full_name') or '—'}\n"
        f"🎂 Yosh: {user.get('age') or 'Kiritilmagan'}\n"
        f"📍 Hudud: {user.get('region') or 'Kiritilmagan'}\n"
        f"💼 Ish holati: {emp_map.get(user.get('employment'))}\n\n"
        f"💎 Obuna: {sub_status}\n"
    )
    await send(text, reply_markup=kb.profile_kb(db.is_subscribed(user_id)))

@router.callback_query(F.data == "edit_profile")
async def cb_edit_profile(call: CallbackQuery):
    await call.message.edit_text("✏️ <b>Profilni tahrirlash</b>\n\nNimani o'zgartirmoqchisiz?", reply_markup=kb.edit_profile_kb())

@router.callback_query(F.data == "ep_age")
async def cb_ep_age(call: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.waiting_age)
    await call.message.edit_text("🎂 Yoshingizni kiriting:\n<i>Masalan: 35</i>")

@router.message(ProfileStates.waiting_age)
async def profile_get_age(message: Message, state: FSMContext):
    try:
        age = int(message.text.strip())
        if age < 16 or age > 100:
            await message.answer("❌ Yosh 16 dan 100 gacha bo'lishi kerak.")
            return
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting.")
        return
    db.update_user_profile(message.from_user.id, age=age)
    await state.clear()
    await message.answer(f"✅ Yosh saqlandi: <b>{age}</b>", reply_markup=kb.edit_profile_kb())

@router.callback_query(F.data == "ep_region")
async def cb_ep_region(call: CallbackQuery):
    await call.message.edit_text("📍 Hududingizni tanlang:", reply_markup=kb.regions_kb())

@router.callback_query(F.data.startswith("region_"))
async def cb_set_region(call: CallbackQuery):
    region = call.data[7:]
    db.update_user_profile(call.from_user.id, region=region)
    await call.message.edit_text(f"✅ Hudud saqlandi: <b>{region}</b>", reply_markup=kb.edit_profile_kb())

@router.callback_query(F.data == "ep_employment")
async def cb_ep_employment(call: CallbackQuery):
    await call.message.edit_text("💼 Ish holatini tanlang:", reply_markup=kb.employment_kb())

@router.callback_query(F.data.startswith("emp_"))
async def cb_set_employment(call: CallbackQuery):
    emp = call.data[4:]
    db.update_user_profile(call.from_user.id, employment=emp)
    names = {"employed": "Ishlayman", "unemployed": "Ishsizman", "entrepreneur": "Tadbirkorman"}
    await call.message.edit_text(f"✅ Ish holati saqlandi: <b>{names.get(emp, emp)}</b>", reply_markup=kb.edit_profile_kb())

@router.callback_query(F.data == "ai_advisor")
async def cb_ai_advisor(call: CallbackQuery, state: FSMContext):
    await state.set_state(AIStates.chatting)
    await call.message.edit_text(
        "🤖 <b>AI Maslahatchi</b>\n\n"
        "⏳ Bu funksiya tez orada ishga tushiriladi!\n\n"
        "Hozircha 🧮 <b>Kredit Kalkulyator</b>dan foydalaning.",
        reply_markup=kb.back_to_menu_kb()
    )

@router.message(AIStates.chatting)
async def ai_chat(message: Message, state: FSMContext):
    answer = await ai_advise(message.from_user.id, message.text)
    await message.answer(answer, reply_markup=kb.ai_actions_kb())

@router.callback_query(F.data == "ai_new")
async def cb_ai_new(call: CallbackQuery, state: FSMContext):
    await state.set_state(AIStates.chatting)
    await call.message.edit_text("🔄 <b>Yangi suhbat!</b>\n\nYozing 👇")

@router.callback_query(F.data == "subscription")
async def cb_subscription(call: CallbackQuery):
    has_discount = db.has_reconnect_discount(call.from_user.id)
    text = (
        f"💎 <b>Pulchi Bot Obunasi</b>\n\n"
        f"✅ Ariza yordamchisi\n✅ Hujjatlar ro'yxati\n✅ Murojaat skripti\n\n"
        f"💰 1 kun: {config.PRICE_1_DAY:,} so'm\n"
        f"📅 1 hafta: {config.PRICE_WEEKLY:,} so'm"
    )
    await call.message.edit_text(text, reply_markup=kb.subscription_kb(has_discount))

@router.callback_query(F.data.startswith("sub_"))
async def cb_sub_choose(call: CallbackQuery):
    parts = call.data.split("_")
    sub_type = parts[1]
    is_discount = len(parts) > 2 and parts[2] == "discount"
    price_map = {"1day": config.PRICE_RECONNECT if is_discount else config.PRICE_1_DAY, "weekly": config.PRICE_WEEKLY}
    name_map = {"1day": "1 kunlik", "weekly": "Haftalik"}
    price = price_map.get(sub_type, config.PRICE_1_DAY)
    name = name_map.get(sub_type, "1 kunlik")
    await call.message.edit_text(f"💳 <b>{name} obuna – {price:,} so'm</b>\n\nTo'lov usulini tanlang:", reply_markup=kb.payment_method_kb(sub_type))

@router.callback_query(F.data.startswith("pay_"))
async def cb_pay(call: CallbackQuery):
    _, provider, sub_type = call.data.split("_", 2)
    price_map = {"1day": config.PRICE_1_DAY, "3day": config.PRICE_3_DAY, "weekly": config.PRICE_WEEKLY}
    amount = price_map.get(sub_type, config.PRICE_1_DAY)
    payment_id = db.create_payment(call.from_user.id, provider, amount, sub_type)
    text = (
        f"💳 <b>To'lov</b>\n\n"
        f"Miqdor: <b>{amount:,} so'm</b>\n"
        f"To'lov ID: <code>{payment_id}</code>\n\n"
        f"To'lovdan so'ng admin @pulchi_support ga murojaat qiling."
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="subscription"))
    await call.message.edit_text(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery):
    text = (
        "❓ <b>Yordam</b>\n\n"
        "🧮 Kredit Kalkulyator\n"
        "🤖 AI Maslahatchi (tez orada)\n"
        "💳 Kredit Turlari\n"
        "💰 Omonat Foizlari\n"
        "📋 Ariza Yordamchisi (obuna)\n\n"
        "📞 @pulchi_support"
    )
    await call.message.edit_text(text, reply_markup=kb.back_to_menu_kb())
