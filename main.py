#!/usr/bin/env python3
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import config
from database import init_db
from handlers import user, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Ma'lumotlar bazasi ishga tushirilmoqda...")
    init_db()
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(admin.router)
    dp.include_router(user.router)
    logger.info(f"{config.BOT_NAME} ishga tushdi!")
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"✅ {config.BOT_NAME} ishga tushdi!")
        except Exception as e:
            logger.warning(f"Admin {admin_id} ga xabar yuborib bolmadi: {e}")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot toxtatildi.")
