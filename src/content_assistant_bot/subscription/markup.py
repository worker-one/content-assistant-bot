from pathlib import Path

from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

def create_menu_markup(lang: str) -> InlineKeyboardMarkup:
    """Create the menu markup."""
    menu_markup = InlineKeyboardMarkup(row_width=1)
    for option in strings[lang].options:
        menu_markup.add(InlineKeyboardButton(option.label, callback_data=option.value))
    return menu_markup

def create_menu_button_markup(lang: str) -> InlineKeyboardMarkup:
    """Create the main menu button."""
    return InlineKeyboardMarkup().add(InlineKeyboardButton(strings[lang].title, callback_data="menu"))

def create_auth_button_markup(lang: str) -> InlineKeyboardMarkup:
    """Create the auth button."""
    return InlineKeyboardMarkup().add(InlineKeyboardButton(strings[lang].auth, callback_data="auth"))

def create_menu_reply_markup(lang: str):
    main_menu_button = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    main_menu_button.add(KeyboardButton(strings[lang].main_menu))
    return main_menu_button
