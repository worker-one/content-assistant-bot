import logging.config
from pathlib import Path

from omegaconf import OmegaConf
from telebot.types import Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


def register_handlers(bot):
    """Register menu handlers"""
    logger.info("Registering menu handlers")

    @bot.message_handler(commands=["start"])
    def menu_menu_command(message: Message, data: dict):
        user = data["user"]

        bot.send_message(
            chat_id=message.chat.id,
            text=strings[user.lang].start_message,
        )
