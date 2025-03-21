import logging
from pathlib import Path

from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from .models import Channel

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_channels_menu_markup(lang: str) -> InlineKeyboardMarkup:
    """ Create channels menu markup """
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(strings[lang].my_channels, callback_data="my_channels"),
        InlineKeyboardButton(strings[lang].add_channel, callback_data="add_channel"),
        InlineKeyboardButton(strings[lang].delete_channel, callback_data="delete_channel_list"),
        InlineKeyboardButton(strings[lang].back_to_menu, callback_data="menu")
    )
    return markup


def create_channels_list_markup(lang: str, channels: list) -> InlineKeyboardMarkup:
    """ Create channels list markup """
    markup = InlineKeyboardMarkup(row_width=1)
    for channel in channels:
        markup.add(InlineKeyboardButton(channel.name, callback_data=f"view_channel_{channel.id}"))
    markup.add(InlineKeyboardButton(strings[lang].back_to_menu, callback_data="channels"))
    return markup


def create_delete_channels_list_markup(lang: str, channels: list) -> InlineKeyboardMarkup:
    """ Create channels list markup for deletion """
    markup = InlineKeyboardMarkup(row_width=1)
    for channel in channels:
        markup.add(InlineKeyboardButton(channel.name, callback_data=f"delete_channel_{channel.id}"))
    markup.add(InlineKeyboardButton(strings[lang].back_to_menu, callback_data="channels"))
    return markup


def create_channel_menu_markup(lang: str, channel_id: int) -> InlineKeyboardMarkup:
    """ Create channel details menu markup """
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(strings[lang].edit_channel, callback_data=f"edit_channel_{channel_id}"),
        InlineKeyboardButton(strings[lang].delete_channel, callback_data=f"delete_channel_{channel_id}"),
        InlineKeyboardButton(strings[lang].back_to_channels, callback_data="my_channels"),
        InlineKeyboardButton(strings[lang].back_to_menu, callback_data="menu")
    )
    return markup


def create_cancel_button(lang: str) -> InlineKeyboardMarkup:
    """ Create a cancel button for the channels menu """
    cancel_button = InlineKeyboardMarkup(row_width=1)
    cancel_button.add(
        InlineKeyboardButton(strings[lang].cancel, callback_data="channels"),
    )
    return cancel_button