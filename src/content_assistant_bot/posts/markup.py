import logging
import logging.config
from pathlib import Path
from datetime import datetime

from omegaconf import OmegaConf
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from .models import Post

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_cancel_button(lang: str) -> InlineKeyboardMarkup:
    """ Create a cancel button for the items menu """
    cancel_button = InlineKeyboardMarkup(row_width=1)
    cancel_button.add(
        InlineKeyboardButton(strings[lang].cancel, callback_data="menu"),
    )
    return cancel_button


# Post related markups
def create_posts_menu_markup(lang: str) -> InlineKeyboardMarkup:
    """ Create the posts menu markup """
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(strings[lang].create_post, callback_data="create_post"))
    markup.add(InlineKeyboardButton(strings[lang].my_posts, callback_data="my_posts"))
    markup.add(InlineKeyboardButton(strings[lang].back_to_menu, callback_data="menu"))
    return markup


def create_posts_list_markup(lang: str, posts: list[Post]) -> InlineKeyboardMarkup:
    """ Create the posts list markup """
    markup = InlineKeyboardMarkup()
    for post in posts:
        # Show published status in the button title
        status = "📌" if post.is_published else "📝"
        title = post.title if post.title else f"Post #{post.id}"
        button_text = f"{status} {title}"
        markup.add(InlineKeyboardButton(button_text, callback_data=f"view_post_{post.id}"))

    markup.add(InlineKeyboardButton(strings[lang].back_to_menu, callback_data="menu"))
    return markup


def create_post_action_markup(lang: str, post_id: int) -> InlineKeyboardMarkup:
    """ Create the post action markup """
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(strings[lang].publish_post, callback_data=f"publish_post_{post_id}"))
    markup.add(InlineKeyboardButton(strings[lang].schedule_post, callback_data=f"schedule_post_{post_id}"))
    markup.add(InlineKeyboardButton(strings[lang].edit_post, callback_data=f"edit_post_{post_id}"))
    markup.add(InlineKeyboardButton(strings[lang].delete_post, callback_data=f"delete_post_{post_id}"))
    markup.add(InlineKeyboardButton(strings[lang].back_to_posts, callback_data="list_posts"))
    return markup


def create_post_scheduling_markup(lang: str) -> InlineKeyboardMarkup:
    """ Create markup for scheduling options """
    markup = InlineKeyboardMarkup(row_width=2)
    
    # Add time buttons for common scheduling options
    now = datetime.now()
    
    # Today options
    today = now.replace(hour=20, minute=0, second=0, microsecond=0)
    if now.hour < 20:
        markup.add(InlineKeyboardButton(
            strings[lang].today_evening, 
            callback_data=f"schedule_time_{today.strftime('%Y-%m-%d %H:%M:%S')}"
        ))
    
    # Tomorrow options
    tomorrow_morning = now.replace(day=now.day+1, hour=9, minute=0, second=0, microsecond=0)
    tomorrow_noon = now.replace(day=now.day+1, hour=12, minute=0, second=0, microsecond=0)
    tomorrow_evening = now.replace(day=now.day+1, hour=20, minute=0, second=0, microsecond=0)
    
    markup.add(InlineKeyboardButton(
        strings[lang].tomorrow_morning, 
        callback_data=f"schedule_time_{tomorrow_morning.strftime('%Y-%m-%d %H:%M:%S')}"
    ))
    
    markup.add(InlineKeyboardButton(
        strings[lang].tomorrow_noon, 
        callback_data=f"schedule_time_{tomorrow_noon.strftime('%Y-%m-%d %H:%M:%S')}"
    ))

    markup.add(InlineKeyboardButton(
        strings[lang].tomorrow_evening, 
        callback_data=f"schedule_time_{tomorrow_evening.strftime('%Y-%m-%d %H:%M:%S')}"
    ))

    # Custom time option
    markup.add(InlineKeyboardButton(strings[lang].custom_time, callback_data="schedule_custom"))

    # Cancel button
    markup.add(InlineKeyboardButton(strings[lang].cancel, callback_data="cancel_scheduling"))

    return markup


def create_post_edit_actions_markup(lang: str, post_id: int):
    # Ask which part to edit
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(strings[lang].edit_title, callback_data="edit_title_post"))
    markup.add(InlineKeyboardButton(strings[lang].edit_content, callback_data="edit_content_post"))
    markup.add(InlineKeyboardButton(strings[lang].save_post, callback_data=f"save_post_{post_id}"))
    markup.add(InlineKeyboardButton(strings[lang].back, callback_data=f"view_post_{post_id}"))
    return markup