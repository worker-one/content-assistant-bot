import logging.config
from pathlib import Path

from omegaconf import OmegaConf
from telebot.types import Message

from ..database.core import get_session
from ..auth.service import is_new_user
from ..subscription.service import credit_balance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the database session
db_session = get_session()

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

        if is_new_user(db_session, user.id):
            credit_balance(db_session, user.id, 25)
            bot.send_message(
                chat_id=message.chat.id,
                text="Вам доступно 25 постов бесплатно!",
            )
