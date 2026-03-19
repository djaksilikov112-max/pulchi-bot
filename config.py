import os
from dataclasses import dataclass, field

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ADMIN_IDS: list = field(default_factory=list)
    DB_PATH: str = "pulchi_bot.db"
    PAYME_MERCHANT_ID: str = os.getenv("PAYME_MERCHANT_ID", "")
    PAYME_SECRET_KEY: str = os.getenv("PAYME_SECRET_KEY", "")
    CLICK_SERVICE_ID: str = os.getenv("CLICK_SERVICE_ID", "")
    CLICK_MERCHANT_ID: str = os.getenv("CLICK_MERCHANT_ID", "")
    PRICE_1_DAY: int = 1990
    PRICE_3_DAY: int = 4990
    PRICE_WEEKLY: int = 9990
    PRICE_RECONNECT: int = 1690
    BOT_USERNAME: str = "@PulchiBot"
    BOT_NAME: str = "Pulchi Bot"

    def __post_init__(self):
        raw = os.getenv("ADMIN_IDS", "123456789")
        self.ADMIN_IDS = [int(x.strip()) for x in raw.split(",") if x.strip()]

config = Config()
