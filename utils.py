import json
import logging
from typing import List, Dict
from config import config
from database import get_all_banks, get_banks_by_credit_type

logger = logging.getLogger(__name__)

def calculate_monthly_payment(principal, annual_rate, months):
    if annual_rate == 0:
        return principal / months
    monthly_rate = annual_rate / 100 / 12
    payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    return payment

def calculate_all_banks(amount, months, credit_type=None):
    if credit_type:
        banks = get_banks_by_credit_type(credit_type)
    else:
        banks = get_all_banks()
    results = []
    for bank in banks:
        if amount < bank["min_amount"] or amount > bank["max_amount"]:
            continue
        if months < bank["min_term"] or months > bank["max_term"]:
            continue
        min_payment = calculate_monthly_payment(amount, bank["min_rate"], months)
        max_payment = calculate_monthly_payment(amount, bank["max_rate"], months)
        total_min = min_payment * months
        total_max = max_payment * months
        results.append({
            "bank_id": bank["id"],
            "bank_name": bank["name"],
            "emoji": bank["logo_emoji"],
            "min_rate": bank["min_rate"],
            "max_rate": bank["max_rate"],
            "min_payment": min_payment,
            "max_payment": max_payment,
            "total_min": total_min,
            "total_max": total_max,
            "overpay_min": total_min - amount,
            "overpay_max": total_max - amount,
            "phone": bank["phone"],
            "website": bank["website"],
        })
    results.sort(key=lambda x: x["min_payment"])
    return results

def format_calc_results(results, amount, months):
    if not results:
        return "😔 Kechirasiz, berilgan parametrlar bo'yicha mos kredit topilmadi.\nSumma yoki muddatni o'zgartiring."
    lines = [
        f"🧮 <b>Kredit Hisob-Kitobi</b>\n",
        f"💵 Summa: <b>{amount:,.0f} so'm</b>",
        f"📅 Muddat: <b>{months} oy</b>\n",
        f"🏆 <b>Eng Qulay Banklar (top 3):</b>\n",
    ]
    for i, r in enumerate(results[:3], 1):
        medal = ["🥇", "🥈", "🥉"][i - 1]
        lines.append(
            f"{medal} <b>{r['bank_name']}</b> {r['emoji']}\n"
            f"   📊 Stavka: {r['min_rate']}% – {r['max_rate']}%\n"
            f"   💳 Oylik: {r['min_payment']:,.0f} – {r['max_payment']:,.0f} so'm\n"
            f"   📈 Ortiqcha: {r['overpay_min']:,.0f} – {r['overpay_max']:,.0f} so'm\n"
            f"   📞 {r['phone']}\n"
        )
    if len(results) > 3:
        lines.append(f"\n📋 Jami {len(results)} ta bank sizga kredit berishi mumkin.")
    lines.append("\n💡 <i>Batafsil ma'lumot uchun bankni tanlang:</i>")
    return "\n".join(lines)

def format_money(amount):
    if amount >= 1_000_000_000:
        return f"{amount/1_000_000_000:.1f} mlrd so'm"
    if amount >= 1_000_000:
        return f"{amount/1_000_000:.1f} mln so'm"
    return f"{amount:,.0f} so'm"

async def ai_advise(user_id, user_message):
    return (
        "🤖 <b>AI Maslahatchi</b>\n\n"
        "⏳ Bu funksiya tez orada ishga tushiriladi!\n\n"
        "Hozircha 🧮 <b>Kredit Kalkulyator</b>dan foydalaning."
    )

CREDIT_TYPE_INFO = {
    "micro": {
        "name": "💰 Mikrokredit",
        "desc": (
            "Mikrokredit – kichik miqdordagi qisqa muddatli kreditlar.\n\n"
            "<b>Kimlar uchun?</b>\n"
            "• Kichik biznes ochmoqchi bo'lganlar\n"
            "• Qishloq aholisi\n"
            "• Ishsiz fuqarolar\n\n"
            "<b>Asosiy shartlar:</b>\n"
            "• Summa: 500,000 – 100,000,000 so'm\n"
            "• Muddat: 3 – 60 oy\n"
            "• Stavka: 24% – 32% yillik"
        )
    },
    "business": {
        "name": "🏢 Biznes Kredit",
        "desc": (
            "Tadbirkorlik faoliyatini rivojlantirish uchun kredit.\n\n"
            "<b>Kimlar uchun?</b>\n"
            "• Mavjud tadbirkorlar\n"
            "• Biznes ochmoqchi bo'lganlar\n\n"
            "<b>Asosiy shartlar:</b>\n"
            "• Summa: 5,000,000 – 2,000,000,000 so'm\n"
            "• Muddat: 12 – 120 oy\n"
            "• Stavka: 23% – 33% yillik"
        )
    },
    "ipoteka": {
        "name": "🏠 Ipoteka",
        "desc": (
            "Uy-joy sotib olish yoki qurish uchun uzoq muddatli kredit.\n\n"
            "<b>Kimlar uchun?</b>\n"
            "• Uy-joy sotib olmoqchi bo'lganlar\n\n"
            "<b>Asosiy shartlar:</b>\n"
            "• Dastlabki to'lov: 20% dan\n"
            "• Muddat: 60 – 240 oy\n"
            "• Stavka: 25% – 28% yillik"
        )
    },
    "auto": {
        "name": "🚗 Avtokredit",
        "desc": (
            "Avtomobil sotib olish uchun kredit.\n\n"
            "<b>Kimlar uchun?</b>\n"
            "• Yangi avtomobil xarida qilmoqchi bo'lganlar\n\n"
            "<b>Asosiy shartlar:</b>\n"
            "• Summa: 5,000,000 – 500,000,000 so'm\n"
            "• Muddat: 12 – 84 oy\n"
            "• Stavka: 28% – 32% yillik"
        )
    },
    "unemployed": {
        "name": "📋 Ishsizlar uchun",
        "desc": (
            "Ishsiz fuqarolar uchun davlat dasturlari.\n\n"
            "<b>Dasturlar:</b>\n"
            "• Temir daftar\n"
            "• Ishga marhamat\n"
            "• Yoshlar startap\n\n"
            "<b>Asosiy shartlar:</b>\n"
            "• Summa: 500,000 – 500,000,000 so'm\n"
            "• Stavka: 24% – 27% (imtiyozli)"
        )
    },
}

def get_required_docs(bank_name, credit_type="micro"):
    base_docs = (
        "📄 <b>Asosiy hujjatlar:</b>\n"
        "1. Pasport (asl nusxa + fotokopiya)\n"
        "2. PINFL\n"
        "3. 3×4 fotosurat (2 ta)\n"
        "4. Ariza blanki\n"
    )
    type_docs = {
        "micro": "\n💼 <b>Qo'shimcha:</b>\n5. Biznes-reja\n6. Garov hujjatlari",
        "business": "\n💼 <b>Qo'shimcha:</b>\n5. Biznes-reja\n6. Soliq guvohnomasi\n7. Moliyaviy hisobot\n8. Garov hujjatlari",
        "ipoteka": "\n🏠 <b>Qo'shimcha:</b>\n5. Uy-joy hujjatlari\n6. Nikoh guvohnomasi\n7. Daromad ma'lumotномаsi",
        "auto": "\n🚗 <b>Qo'shimcha:</b>\n5. Haydovchilik guvohnomasi\n6. Avtomobil shartnomasi",
        "unemployed": "\n📋 <b>Qo'shimcha:</b>\n5. Mehnat birjasidan ma'lumotnoma\n6. Oilaviy holat ma'lumotnomasi",
    }
    return base_docs + type_docs.get(credit_type, "")

def get_application_script(bank_name):
    return (
        f"🗣️ <b>{bank_name} bilan muloqot skripti</b>\n\n"
        "Salom. Men kredit olish bo'yicha maslahat olmoqchi edim.\n\n"
        "<b>So'rashingiz kerak:</b>\n"
        "1. «Qanday kredit dasturlaringiz bor?»\n"
        "2. «Minimal foiz stavka qancha?»\n"
        "3. «Ariza ko'rib chiqish muddati?»\n"
        "4. «Garovsiz kredit bormi?»\n\n"
        "<b>Eslatma:</b>\n"
        "• Imzolashdan oldin shartnomasini o'qing\n"
        "• Yashirin to'lovlar borligini so'rang"
    )
