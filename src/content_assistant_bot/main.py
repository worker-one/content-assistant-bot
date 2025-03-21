import logging
import os
from pathlib import Path

import telebot
from dotenv import find_dotenv, load_dotenv
from omegaconf import OmegaConf
from telebot.states.sync.middleware import StateMiddleware

from .account.handlers import register_handlers as account_handlers
from .admin.handlers import register_handlers as admin_handlers
from .auth.data import init_roles_table, init_superuser
from .channels.data import init_channels_table_data
from .channels.handlers import register_handlers as channels_handlers
from .chatgpt.handlers import register_handlers as llm_handlers
from .database.core import (
    create_tables,
    drop_tables,
    get_session,
)
from .generation.handlers import register_handlers as items_handlers
from .help.handlers import register_handlers as help_handlers
from .menu.handlers import register_handlers as menu_handlers
from .middleware.antiflood import AntifloodMiddleware
from .middleware.user import UserCallbackMiddleware, UserMessageMiddleware
from .posts.data import init_posts_table_data
from .posts.handlers import register_handlers as posts_handlers
from .public_message.handlers import register_handlers as public_message_handlers
from .scheduler.service import init_scheduler
from .start.handlers import register_handlers as start_handlers
from .subscription.data import init_subscription_plans
from .subscription.handlers import register_handlers as subscription_handlers
from .users.handlers import register_handlers as users_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")

# Load and get environment variables
load_dotenv(find_dotenv(usecwd=True))
SUPERUSER_USERNAME = os.getenv("SUPERUSER_USERNAME")
SUPERUSER_USER_ID = os.getenv("SUPERUSER_USER_ID")

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.critical("BOT_TOKEN is not set in environment variables")
    raise ValueError("BOT_TOKEN environment variable is required")
bot = telebot.TeleBot(BOT_TOKEN, use_class_middlewares=True)


def _setup_middlewares(bot):
    """Configure bot middlewares."""
    if config.antiflood.enabled:
        logger.info(f"Enabling antiflood (window: {config.antiflood.time_window_seconds}s)")
        bot.setup_middleware(AntifloodMiddleware(bot, config.antiflood.time_window_seconds))

    bot.setup_middleware(StateMiddleware(bot))
    bot.setup_middleware(UserMessageMiddleware(bot))
    bot.setup_middleware(UserCallbackMiddleware(bot))

def _register_handlers(bot):
    """Register all bot handlers."""
    handlers = [
        account_handlers,
        admin_handlers,
        channels_handlers,
        start_handlers,
        help_handlers,
        llm_handlers,
        posts_handlers,
        menu_handlers,
        public_message_handlers,
        subscription_handlers,
        users_handlers,
        items_handlers
    ]
    for handler in handlers:
        handler(bot)

def start_bot():
    """Start the Telegram bot with configuration, middlewares, and handlers."""
    global bot
    logger.info(f"Initializing {config.name} v{config.version}")

    try:
        _setup_middlewares(bot)
        _register_handlers(bot)
        bot.add_custom_filter(telebot.custom_filters.StateFilter(bot))

        bot_info = bot.get_me()
        logger.info(f"Bot {bot_info.username} (ID: {bot_info.id}) initialized successfully")

        bot.polling(none_stop=True, interval=0, timeout=60, long_polling_timeout=60)

    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}")
        raise


def init_db():
    """Initialize the database for applications."""
    # Create tables
    create_tables()

    db_session = get_session()

    init_roles_table(db_session)

    init_subscription_plans(db_session)
    
    init_posts_table_data(db_session, count=3)
    
    init_channels_table_data(db_session, count=3)

    # Add admin to user table
    if SUPERUSER_USER_ID:
        init_superuser(db_session, SUPERUSER_USER_ID, SUPERUSER_USERNAME)
        logger.info(f"Superuser {SUPERUSER_USERNAME} added successfully.")

    logger.info("Database initialized")


if __name__ == "__main__":
    drop_tables()
    init_db()
    init_scheduler()
    start_bot()
