import logging
from pathlib import Path
from re import M

from omegaconf import OmegaConf
from telebot.types import CallbackQuery

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


def register_handlers(bot):

    # The same for callback
    @bot.callback_query_handler(func=lambda call: call.data == "account")
    def account(call: CallbackQuery, data: dict):
        user = data["user"]
        bot.send_message(
            call.message.chat.id,
            strings[user.lang].account_info.format(
                user_id=user.id,
                username=user.username,
                balance=user.balance,
                registration_date=user.created_at.strftime("%Y-%m-%d")
            ),
            parse_mode="Markdown"
        )