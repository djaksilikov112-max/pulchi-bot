from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config

def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🧮 Kredit Kalkulyator", callback_data="calc"),
        InlineKeyboardButton(text="🤖 AI Maslahatchi", callback_data="ai_advisor"),
    )
    builder.row(
        InlineKeyboardButton(text="💳 Kredit Turlari", callback_data="credit_types"),
        InlineKeyboardButton(text="💰 Omonat Foizlari", callback_data="deposits"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Ariza Yordamchisi", callback_data="application_helper"),
    )
    builder.row(
        InlineKeyboardButton(text="👤 Mening Profilim", callback_data="my_profile"),
        InlineKeyboardButton(text="❓ Yordam", callback_data="help"),
    )
    return builder.as_markup()

def credit_types_kb():
    builder = InlineKeyboardBuilder()
    types = [
        ("💰 Mikrokredit", "ct_micro"),
        ("🏢 Biznes Kredit", "ct_business"),
        ("🏠 Ipoteka", "ct_ipoteka"),
        ("🚗 Avtokredit", "ct_auto"),
        ("📋 Ishsizlar uchun", "ct_unemployed"),
    ]
    for text, data in types:
        builder.add(InlineKeyboardButton(text=text, callback_data=data))
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu"))
    return builder.as_markup()

def bank_detail_kb(bank_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Hujjatlar", callback_data=f"docs_{bank_id}"),
        InlineKeyboardButton(text="🗣️ Skript", callback_data=f"script_{bank_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="📍 Filiallar", callback_data=f"branch_{bank_id}"),
        InlineKeyboardButton(text="⏱️ Muddat", callback_data=f"timing_{bank_id}"),
    )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="calc"))
    return builder.as_markup()

def subscription_kb(has_discount=False):
    builder = InlineKeyboardBuilder()
    if has_discount:
        builder.row(InlineKeyboardButton(
            text=f"⚡ 1 kun – {config.PRICE_RECONNECT:,} so'm (chegirma!)",
            callback_data="sub_1day_discount"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text=f"1️⃣ 1 kun – {config.PRICE_1_DAY:,} so'm",
            callback_data="sub_1day"
        ))
    builder.row(InlineKeyboardButton(
        text=f"📅 1 hafta – {config.PRICE_WEEKLY:,} so'm",
        callback_data="sub_weekly"
    ))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu"))
    return builder.as_markup()

def payment_method_kb(sub_type):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Payme", callback_data=f"pay_payme_{sub_type}"),
        InlineKeyboardButton(text="💳 Click", callback_data=f"pay_click_{sub_type}"),
    )
    builder.row(
        InlineKeyboardButton(text="🏦 Uzum Bank", callback_data=f"pay_uzum_{sub_type}"),
    )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="subscription"))
    return builder.as_markup()

def profile_kb(is_subscribed):
    builder = InlineKeyboardBuilder()
    if not is_subscribed:
        builder.row(InlineKeyboardButton(text="💎 Obuna sotib olish", callback_data="subscription"))
    builder.row(InlineKeyboardButton(text="✏️ Profilni tahrirlash", callback_data="edit_profile"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu"))
    return builder.as_markup()

def edit_profile_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎂 Yosh", callback_data="ep_age"),
        InlineKeyboardButton(text="📍 Hudud", callback_data="ep_region"),
    )
    builder.row(InlineKeyboardButton(text="💼 Ish holati", callback_data="ep_employment"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="my_profile"))
    return builder.as_markup()

def employment_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Ishlayman", callback_data="emp_employed"))
    builder.row(InlineKeyboardButton(text="❌ Ishsizman", callback_data="emp_unemployed"))
    builder.row(InlineKeyboardButton(text="🏢 Tadbirkorman", callback_data="emp_entrepreneur"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="edit_profile"))
    return builder.as_markup()

def regions_kb():
    regions = [
        "Toshkent","Samarqand","Farg'ona","Andijon","Namangan",
        "Buxoro","Xorazm","Qashqadaryo","Surxondaryo",
        "Sirdaryo","Jizzax","Navoiy","Nukus (QQR)",
    ]
    builder = InlineKeyboardBuilder()
    for r in regions:
        builder.add(InlineKeyboardButton(text=r, callback_data=f"region_{r}"))
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="edit_profile"))
    return builder.as_markup()

def ai_actions_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Yangi suhbat", callback_data="ai_new"),
        InlineKeyboardButton(text="🔙 Menyu", callback_data="main_menu"),
    )
    return builder.as_markup()

def admin_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats"),
        InlineKeyboardButton(text="🏦 Banklar", callback_data="adm_banks"),
    )
    builder.row(
        InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="adm_broadcast"),
        InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm_users"),
    )
    return builder.as_markup()

def back_to_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="main_menu"))
    return builder.as_markup()
