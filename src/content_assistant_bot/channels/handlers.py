import logging
from pathlib import Path

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.states import State, StatesGroup

from ..database.core import get_session
from ..menu.markup import create_menu_markup
from .markup import (
    create_cancel_button, 
    create_channel_menu_markup, 
    create_channels_list_markup,
    create_channels_menu_markup,
    create_delete_channels_list_markup
)
from .service import (
    create_channel,
    delete_channel,
    read_channel,
    read_channels_by_owner,
    update_channel,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Load the database session
db_session = get_session()

# Define States
class ChannelState(StatesGroup):
    """ Channel states """
    menu = State()
    my_channels = State()
    add_channel = State()
    name = State()
    link = State()
    delete_channel = State()
    edit_channel = State()
    edit_name = State()
    edit_link = State()


def register_handlers(bot: TeleBot):
    """Register channel handlers"""
    logger.info("Registering channel handlers")

    @bot.callback_query_handler(func=lambda call: call.data == "channels")
    def channel_menu(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(ChannelState.menu)

        markup = create_channels_menu_markup(user.lang)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].channels_menu,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data == "add_channel")
    def start_add_channel(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(ChannelState.name)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_channel_name,
            reply_markup=create_cancel_button(user.lang)
        )

    @bot.message_handler(state=ChannelState.name)
    def process_name(message: types.Message, data: dict):
        user = data["user"]
        data["state"].add_data(name=message.text)

        bot.send_message(
            user.id,
            strings[user.lang].enter_channel_link,
            reply_markup=create_cancel_button(user.lang)
        )
        data["state"].set(ChannelState.link)
    
    @bot.message_handler(state=ChannelState.link)
    def process_link(message: types.Message, data: dict):
        user = data["user"]
        link = message.text.strip()

        # Verify link format
        if not link.startswith("https://t.me/") or len(link.split("/")) != 4:
            bot.send_message(
                user.id,
                strings[user.lang].enter_channel_link,
                reply_markup=create_cancel_button(user.lang)
            )
            return

        data["state"].add_data(link=link)
        
        with data["state"].data() as data_items:
            # Create channel in the database
            channel = create_channel(
                db_session,
                name=data_items['name'], 
                link=data_items['link'],
                owner_id=user.id
            )

        bot.send_message(
            user.id,
            strings[user.lang].channel_created.format(name=channel.name),
            reply_markup=create_menu_markup(user.lang),
            parse_mode="Markdown"
        )
        data["state"].delete()

    @bot.callback_query_handler(func=lambda call: call.data == "my_channels")
    def show_my_channels(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(ChannelState.my_channels)

        channels = read_channels_by_owner(db_session, user.id)

        if not channels:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(strings[user.lang].back_to_menu, callback_data="menu"))

            bot.edit_message_text(
                chat_id=user.id,
                message_id=call.message.message_id,
                text=strings[user.lang].no_channels,
                reply_markup=markup
            )
            return

        markup = create_channels_list_markup(user.lang, channels)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].your_channels,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("view_channel_"))
    def view_channel(call: types.CallbackQuery, data: dict):
        user = data["user"]
        channel_id = int(call.data.split("_")[2])
        channel = read_channel(db_session, channel_id)

        if not channel:
            bot.send_message(user.id, strings[user.lang].channel_not_found, reply_markup=create_menu_markup(user.lang))
            return

        message_text = strings[user.lang].channel_details.format(
            name=channel.name,
            link=channel.link,
            created_at=channel.created_at.strftime("%Y-%m-%d %H:%M")
        )

        markup = create_channel_menu_markup(user.lang, channel.id)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=message_text,
            reply_markup=markup,
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data == "delete_channel_list")
    def show_delete_channels(call: types.CallbackQuery, data: dict):
        user = data["user"]
        channels = read_channels_by_owner(db_session, user.id)

        if not channels:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(strings[user.lang].back_to_menu, callback_data="menu"))

            bot.edit_message_text(
                chat_id=user.id,
                message_id=call.message.message_id,
                text=strings[user.lang].no_channels,
                reply_markup=markup
            )
            return

        markup = create_delete_channels_list_markup(user.lang, channels)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].select_channel_to_delete,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_channel_"))
    def handler_delete_channel(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(ChannelState.delete_channel)
        channel_id = int(call.data.split("_")[2])
        channel_name = read_channel(db_session, channel_id).name
        
        delete_channel(db_session, channel_id)
        
        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].channel_deleted.format(name=channel_name),
            reply_markup=create_menu_markup(user.lang)
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_channel_"))
    def start_edit_channel(call: types.CallbackQuery, data: dict):
        user = data["user"]
        channel_id = int(call.data.split("_")[2])
        data["state"].set(ChannelState.edit_channel)
        data["state"].add_data(channel_id=channel_id)

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(strings[user.lang].edit_name, callback_data="edit_name"),
            types.InlineKeyboardButton(strings[user.lang].edit_link, callback_data="edit_link"),
            types.InlineKeyboardButton(strings[user.lang].cancel, callback_data=f"view_channel_{channel_id}")
        )

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].what_to_edit,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data == "edit_name", state=ChannelState.edit_channel)
    def edit_channel_name(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(ChannelState.edit_name)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_new_channel_name,
            reply_markup=create_cancel_button(user.lang)
        )

    @bot.message_handler(state=ChannelState.edit_name)
    def process_edit_name(message: types.Message, data: dict):
        user = data["user"]
        with data["state"].data() as data_items:
            channel_id = data_items['channel_id']
            channel = update_channel(db_session, channel_id, name=message.text)

        bot.send_message(
            user.id,
            strings[user.lang].channel_updated,
            reply_markup=create_menu_markup(user.lang)
        )
        data["state"].delete()

    @bot.callback_query_handler(func=lambda call: call.data == "edit_link", state=ChannelState.edit_channel)
    def edit_channel_link(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(ChannelState.edit_link)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_new_channel_link,
            reply_markup=create_cancel_button(user.lang)
        )

    @bot.message_handler(state=ChannelState.edit_link)
    def process_edit_link(message: types.Message, data: dict):
        user = data["user"]
        with data["state"].data() as data_items:
            channel_id = data_items['channel_id']
            channel = update_channel(db_session, channel_id, link=message.text)

        bot.send_message(
            user.id,
            strings[user.lang].channel_updated,
            reply_markup=create_menu_markup(user.lang)
        )
        data["state"].delete()