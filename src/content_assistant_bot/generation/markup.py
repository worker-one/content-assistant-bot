import logging
from pathlib import Path

from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def create_generation_menu_markup(lang):
    """ Create markup for generation menu """
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(strings[lang].select_saved, callback_data="select_style"),
        InlineKeyboardButton(strings[lang].create_style, callback_data="create_style"),
        InlineKeyboardButton(strings[lang].back_to_menu, callback_data="menu")
    )
    return markup


def create_post_actions_markup(lang, post_id):
    """ Create markup for post actions """
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        #InlineKeyboardButton(strings[lang].edit_post, callback_data=f"edit_post_{post_id}"),
        #InlineKeyboardButton(strings[lang].publish_post, callback_data=f"publish_post_{post_id}"),
        #InlineKeyboardButton(strings[lang].schedule_post, callback_data=f"schedule_post_{post_id}"),
        #InlineKeyboardButton(strings[lang].manual_edit, callback_data=f"manual_edit_{post_id}"),
        InlineKeyboardButton(strings[lang].save_post, callback_data=f"save_post_{post_id}"),
        InlineKeyboardButton(strings[lang].back, callback_data="generation_menu")
    )
    return markup


def create_style_list_markup(lang, styles):
    """ Create markup with list of styles """
    markup = InlineKeyboardMarkup(row_width=1)
    for style in styles:
        markup.add(InlineKeyboardButton(style.name, callback_data=f"view_style_{style.id}"))
    markup.add(InlineKeyboardButton(strings[lang].back, callback_data="generation_menu"))
    return markup

def create_cancel_button(lang):
    """ Create a cancel button """
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(strings[lang].cancel, callback_data="generation_menu"))
    return markup


def create_style_options_markup(lang: str, style_id: int) -> InlineKeyboardMarkup:
    """ Create options markup for a style (use or delete) """
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(strings[lang].use_style, callback_data=f"style_{style_id}"),
        InlineKeyboardButton(strings[lang].delete_style, callback_data=f"delete_style_{style_id}"),
        InlineKeyboardButton(strings[lang].back, callback_data="select_style")
    )
    return markup