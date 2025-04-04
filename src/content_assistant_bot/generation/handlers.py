import logging
from datetime import datetime
from pathlib import Path

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.states import State, StatesGroup

from ..account import service as account_services
from ..database.core import get_session
from .markup import (
    create_cancel_button,
    create_generation_menu_markup,
    create_post_actions_markup,
)
from .service import (
    create_post,
    create_style,
    edit_content,
    generate_with_style,
    publish_post,
    read_post,
    read_style,
    read_styles_by_owner,
    schedule_post,
    update_post,
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
class GenerationState(StatesGroup):
    """ Generation states """
    menu = State()
    select_style = State()
    create_style = State()
    style_examples = State()
    style_name = State()
    post_content = State()
    post_edit = State()
    post_title = State()
    post_schedule = State()
    post_actions = State()



def create_style_list_markup(lang, styles):
    """ Create markup with list of styles """
    markup = types.InlineKeyboardMarkup(row_width=1)
    for style in styles:
        markup.add(types.InlineKeyboardButton(style.name, callback_data=f"style_{style.id}"))
    markup.add(types.InlineKeyboardButton(strings[lang].back, callback_data="generation_menu"))
    return markup


def create_post_list_markup(lang, posts):
    """ Create markup with list of posts """
    markup = types.InlineKeyboardMarkup(row_width=1)
    for post in posts:
        title = post.title if post.title else post.content[:20] + "..."
        markup.add(types.InlineKeyboardButton(title, callback_data=f"post_{post.id}"))
    markup.add(types.InlineKeyboardButton(strings[lang].back, callback_data="generation_menu"))
    return markup


def create_cancel_button(lang):
    """ Create a cancel button """
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(strings[lang].cancel, callback_data="generation_menu"))
    return markup


def register_handlers(bot: TeleBot):
    """Register generation handlers"""
    logger.info("Registering generation handlers")

    @bot.callback_query_handler(func=lambda call: call.data == "generation")
    def generation_menu(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(GenerationState.menu)

        markup = create_generation_menu_markup(user.lang)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].generation_menu,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data == "generation_menu")
    def back_to_generation_menu(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(GenerationState.menu)

        markup = create_generation_menu_markup(user.lang)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].generation_menu,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data == "select_style")
    def select_style(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(GenerationState.select_style)

        styles = read_styles_by_owner(db_session, user.id)
        
        if not styles:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(strings[user.lang].create_style, callback_data="create_style"))
            markup.add(types.InlineKeyboardButton(strings[user.lang].back, callback_data="generation_menu"))
            
            bot.edit_message_text(
                chat_id=user.id,
                message_id=call.message.message_id,
                text=strings[user.lang].no_styles,
                reply_markup=markup
            )
            return
        
        markup = create_style_list_markup(user.lang, styles)
        
        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].select_style,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("style_"))
    def use_style(call: types.CallbackQuery, data: dict):
        user = data["user"]
        style_id = int(call.data.split("_")[1])
        style = read_style(db_session, style_id)
        
        if not style:
            bot.answer_callback_query(call.id, strings[user.lang].style_not_found)
            return
        
        data["state"].add_data(style_id=style_id)
        data["state"].set(GenerationState.post_content)
        
        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_post_content.format(style_name=style.name),
            reply_markup=create_cancel_button(user.lang)
        )

    @bot.callback_query_handler(func=lambda call: call.data == "create_style")
    def create_style_start(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(GenerationState.style_examples)
        data["state"].add_data(examples=[])  # Initialize empty examples list
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(strings[user.lang].done, callback_data="style_examples_done"),
            types.InlineKeyboardButton(strings[user.lang].cancel, callback_data="generation_menu")
        )
        
        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_style_examples_multiple,
            reply_markup=markup
        )

    @bot.message_handler(state=GenerationState.style_examples)
    def process_style_examples(message: types.Message, data: dict):
        user = data["user"]
        print("BLAH")
        with data["state"].data() as state_data:
            # Append new example to the list
            examples = state_data.get("examples", [])
            examples.append(message.text)
            state_data["examples"] = examples
        
        # Limit to 10 examples
        example_count = len(examples)
        
        if example_count >= 10:
            # If we reached limit, proceed to next state
            concatenated_examples = "\n\n---\n\n".join(examples)
            state_data["examples"] = concatenated_examples
            data["state"].set(GenerationState.style_name)
            
            bot.send_message(
                user.id,
                strings[user.lang].max_examples_reached + "\n" + strings[user.lang].enter_style_name,
                reply_markup=create_cancel_button(user.lang)
            )
        else:
            # Otherwise, allow adding more examples
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton(strings[user.lang].done, callback_data="create_style_examples_done"),
                types.InlineKeyboardButton(strings[user.lang].cancel, callback_data="generation_menu")
            )
            
            bot.send_message(
                user.id,
                strings[user.lang].example_added.format(count=example_count, max=10),
                reply_markup=markup
            )

    @bot.callback_query_handler(func=lambda call: call.data == "create_style_examples_done")
    def finalize_style_examples(call: types.CallbackQuery, data: dict):
        user = data["user"]
        
        with data["state"].data() as state_data:
            examples = state_data.get("examples", [])
            if not examples:
                bot.answer_callback_query(call.id, strings[user.lang].no_examples)
                return
            
            print("examples", examples)
            # Join all examples with separators
            concatenated_examples = "\n\n---\n\n".join(examples)
        
        data["state"].add_data(concatenated_examples=concatenated_examples)

        data["state"].set(GenerationState.style_name)
        
        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_style_name,
            reply_markup=create_cancel_button(user.lang)
        )

    @bot.message_handler(state=GenerationState.style_name)
    def process_style_name(message: types.Message, data: dict):
        user = data["user"]
        data["state"].add_data(name=message.text)

        with data["state"].data() as state_data:
            name = state_data["name"]
            concatenated_examples = state_data["concatenated_examples"]
            
        style = create_style(
            db_session,
            name=name,
            examples=concatenated_examples,
            owner_id=user.id
        )

        markup = create_generation_menu_markup(user.lang)

        bot.send_message(
            user.id,
            strings[user.lang].style_created.format(name=style.name),
            reply_markup=markup
        )
        data["state"].set(GenerationState.menu)


    @bot.message_handler(state=GenerationState.post_content)
    def process_post_content(message: types.Message, data: dict):
        user = data["user"]

        with data["state"].data() as state_data:
            style_id = state_data["style_id"]

            try:
                # Check user balance
                if user.balance < 1:
                    bot.send_message(
                        user.id,
                        strings[user.lang].not_enough_balance,
                        reply_markup=create_generation_menu_markup(user.lang)
                    )
                    data["state"].set(GenerationState.menu)
                    return

                # Send please wait message
                bot.send_message(
                    user.id,
                    strings[user.lang].please_wait
                )

                # Generate content based on style
                generated_content = generate_with_style(message.text, style_id, db_session)

                # Create a draft post
                post = create_post(
                    db_session,
                    title="",  # Empty title initially
                    content=generated_content,
                    style_id=style_id,
                    owner_id=user.id
                )

                markup = create_post_actions_markup(user.lang, post.id)

                bot.send_message(
                    user.id,
                    strings[user.lang].post_preview + "\n\n" + generated_content,
                    reply_markup=markup
                )
                
                # debit user balance
                # Debit balance
                account_services.debit_balance(user.id, 1)
        
            except Exception as e:
                bot.send_message(
                    user.id,
                    f"Error: {e}"
                )
        data["state"].set(GenerationState.post_actions)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_post_"))
    def edit_post_handler(call: types.CallbackQuery, data: dict):
        user = data["user"]
        post_id = int(call.data.split("_")[2])
        post = read_post(db_session, post_id)

        if not post:
            bot.answer_callback_query(call.id, strings[user.lang].post_not_found)
            return

        # Edit with AI
        edited_content = edit_content(post.content)
        post = update_post(db_session, post_id, post.title, edited_content)

        markup = create_post_actions_markup(user.lang, post.id)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].post_edited + "\n\n" + post.content,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("publish_post_"))
    def publish_post_handler(call: types.CallbackQuery, data: dict):
        user = data["user"]
        post_id = int(call.data.split("_")[2])
        post = read_post(db_session, post_id)

        if not post:
            bot.answer_callback_query(call.id, strings[user.lang].post_not_found)
            return

        # Here you would implement the actual publishing to the channel
        # For now, just mark as published
        publish_post(db_session, post_id)
        
        markup = create_generation_menu_markup(user.lang)
        
        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].post_published,
            reply_markup=markup
        )
        data["state"].set(GenerationState.menu)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("schedule_post_"))
    def schedule_post_handler(call: types.CallbackQuery, data: dict):
        user = data["user"]
        post_id = int(call.data.split("_")[2])
        post = read_post(db_session, post_id)
        
        if not post:
            bot.answer_callback_query(call.id, strings[user.lang].post_not_found)
            return
        
        data["state"].add_data(post_id=post_id)
        data["state"].set(GenerationState.post_schedule)
        
        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_schedule_time,
            reply_markup=create_cancel_button(user.lang)
        )

    @bot.message_handler(state=GenerationState.post_schedule)
    def process_schedule_time(message: types.Message, data: dict):
        user = data["user"]
        
        try:
            # Parse date format: YYYY-MM-DD HH:MM
            scheduled_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
            
            with data["state"].data() as state_data:
                post_id = state_data["post_id"]
                schedule_post(db_session, post_id, scheduled_time)
            
            markup = create_generation_menu_markup(user.lang)
            
            bot.send_message(
                user.id,
                strings[user.lang].post_scheduled.format(time=message.text),
                reply_markup=markup
            )
            data["state"].set(GenerationState.menu)
            
        except ValueError:
            bot.send_message(
                user.id,
                strings[user.lang].invalid_date_format,
                reply_markup=create_cancel_button(user.lang)
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("manual_edit_"))
    def manual_edit_handler(call: types.CallbackQuery, data: dict):
        user = data["user"]
        post_id = int(call.data.split("_")[2])
        post = read_post(db_session, post_id)
        
        if not post:
            bot.answer_callback_query(call.id, strings[user.lang].post_not_found)
            return
        
        data["state"].add_data(post_id=post_id)
        data["state"].set(GenerationState.post_edit)
        
        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].edit_post_manually + "\n\n" + post.content,
            reply_markup=create_cancel_button(user.lang)
        )

    @bot.message_handler(state=GenerationState.post_edit)
    def process_manual_edit(message: types.Message, data: dict):
        user = data["user"]
        
        with data["state"].data() as state_data:
            post_id = state_data["post_id"]
            post = read_post(db_session, post_id)
            
            if post:
                post = update_post(db_session, post_id, post.title, message.text, post.style_id)
                
                markup = create_post_actions_markup(user.lang, post.id)
                
                bot.send_message(
                    user.id,
                    strings[user.lang].post_updated + "\n\n" + post.content,
                    reply_markup=markup
                )
                data["state"].set(GenerationState.post_actions)
            else:
                bot.send_message(
                    user.id,
                    strings[user.lang].post_not_found,
                    reply_markup=create_generation_menu_markup(user.lang)
                )
                data["state"].set(GenerationState.menu)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("save_post_"))
    def save_post_handler(call: types.CallbackQuery, data: dict):
        user = data["user"]
        post_id = int(call.data.split("_")[2])
        
        # For saving, we need to add a title if it doesn't exist
        data["state"].add_data(post_id=post_id)
        data["state"].set(GenerationState.post_title)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_post_title,
            reply_markup=create_cancel_button(user.lang)
        )

    @bot.message_handler(state=GenerationState.post_title)
    def process_post_title(message: types.Message, data: dict):
        user = data["user"]
        
        with data["state"].data() as state_data:
            post_id = state_data["post_id"]
            post = read_post(db_session, post_id)
            
            if post:
                update_post(db_session, post_id, message.text, post.content, post.style_id)
                
                markup = create_generation_menu_markup(user.lang)
                
                bot.send_message(
                    user.id,
                    strings[user.lang].post_saved,
                    reply_markup=markup
                )
                data["state"].set(GenerationState.menu)
            else:
                bot.send_message(
                    user.id,
                    strings[user.lang].post_not_found,
                    reply_markup=create_generation_menu_markup(user.lang)
                )
                data["state"].set(GenerationState.menu)
