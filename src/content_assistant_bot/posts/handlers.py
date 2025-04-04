import logging
from datetime import datetime
from pathlib import Path

from omegaconf import OmegaConf
from telebot import TeleBot, types
from telebot.states import State, StatesGroup

from ..channels.models import Channel
from ..database.core import get_session
from ..menu.markup import create_menu_markup
from ..scheduler import service as scheduler_services
from .markup import (
    create_cancel_button,
    create_post_action_markup,
    create_post_edit_actions_markup,
    create_post_scheduling_markup,
    create_posts_list_markup,
)
from .service import create_post, publish_post, read_post, read_posts_by_owner, update_post_content

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings

# Load the database session
db_session = get_session()

class PostState(StatesGroup):
    """ Post states """
    menu = State()
    my_posts = State()
    view_post = State()
    edit_post = State()
    edit_title = State()
    edit_content = State()
    schedule_post = State()
    schedule_custom = State()
    select_channel = State() 
    create_post_title = State()
    create_post_content = State()


def register_handlers(bot: TeleBot):
    """Register item handlers"""
    logger.info("Registering item handlers")

    # Post management handlers
    @bot.callback_query_handler(func=lambda call: call.data == "create")
    def posts_menu(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(PostState.create_post_title)
        
        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_post_title,
            reply_markup=create_cancel_button(user.lang)
        )
    
    @bot.message_handler(state=PostState.create_post_title)
    def process_post_title(message: types.Message, data: dict):
        user = data["user"]
        title = message.text
        
        # Store the title in state data
        data["state"].add_data(post_title=title)
        data["state"].set(PostState.create_post_content)
        
        bot.send_message(
            chat_id=user.id,
            text=strings[user.lang].enter_post_content,
            reply_markup=create_cancel_button(user.lang)
        )
    
    @bot.message_handler(content_types=['text', 'photo'], state=PostState.create_post_content)
    def process_post_content(message: types.Message, data: dict):
        user = data["user"]
        
        # Get title from state data
        with data["state"].data() as data_items:
            title = data_items.get("post_title")
        
        # Get content and photo if exists
        content = message.text
        photo_id = None
        
        if message.photo:
            # Get the largest photo (last in array)
            photo_id = message.photo[-1].file_id
            # If caption exists, use it as content
            content = message.caption or ""
        
        # Create new post
        new_post = create_post(db_session, title, content, user.id, photo_id)
        
        if new_post:
            # Send success message and show the new post
            data["state"].set(PostState.view_post)
            data["post_id"] = new_post.id
            
            markup = create_post_action_markup(user.lang, new_post.id)
            
            message_text = (
                #f"<b>{new_post.title}</b>\n\n"
                f"{new_post.content}\n\n"
            )
            
            if photo_id:
                bot.send_photo(
                    chat_id=user.id,
                    photo=photo_id,
                    caption=message_text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
            else:
                bot.send_message(
                    chat_id=user.id,
                    text=message_text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
        else:
            bot.send_message(
                chat_id=user.id,
                text=strings[user.lang].post_creation_failed,
                reply_markup=create_menu_markup(user.lang)
            )

    @bot.callback_query_handler(func=lambda call: call.data == "list_posts")
    def my_posts(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(PostState.my_posts)

        posts = read_posts_by_owner(db_session, user.id)
        markup = create_posts_list_markup(user.lang, posts)

        if not posts:
            bot.edit_message_text(
                chat_id=user.id,
                message_id=call.message.message_id,
                text=strings[user.lang].no_posts,
                reply_markup=markup
            )
        else:
            bot.edit_message_text(
                chat_id=user.id,
                message_id=call.message.message_id,
                text=strings[user.lang].my_posts,
                reply_markup=markup
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("view_post_"))
    def view_post(call: types.CallbackQuery, data: dict):
        user = data["user"]
        post_id = int(call.data.split("_")[2])
        data["state"].set(PostState.view_post)
        data["post_id"] = post_id

        post = read_post(db_session, post_id)

        if not post:
            bot.edit_message_text(
                chat_id=user.id,
                message_id=call.message.message_id,
                text=strings[user.lang].post_not_found,
                reply_markup=create_posts_list_markup(user.lang, read_posts_by_owner(db_session, user.id))
            )
            return

        # Format post status info
        schedule_text = ""
        if post.scheduled_time:
            schedule_text = f"\n{strings[user.lang].scheduled_for}: {post.scheduled_time.strftime('%Y-%m-%d %H:%M')}"

        title = post.title if post.title else strings[user.lang].untitled_post

        # Prepare message text with post details
        message_text = (
            #f"<b>{title}</b>\n\n"
            f"{post.content}\n\n"
        )

        markup = create_post_action_markup(user.lang, post.id)


        if post.photo_id:
            bot.send_photo(
                chat_id=user.id,
                photo=post.photo_id,
                caption=message_text,
                reply_markup=markup,
                parse_mode="HTML"
            )
        else:
            bot.send_message(
                chat_id=user.id,
                text=message_text,
                reply_markup=markup,
                parse_mode="HTML"
            )
        # Set the state to view_post
        data["state"].set(PostState.view_post)
        data["post_id"] = post_id


    @bot.callback_query_handler(func=lambda call: call.data.startswith("publish_post_"))
    def handle_publish_post(call: types.CallbackQuery, data: dict):
        user = data["user"]
        post_id = int(call.data.split("_")[2])
        
        # Add post_id to data for later use
        data["post_id"] = post_id
        data["state"].set(PostState.select_channel)
        
        # Get user's channels
        channels = db_session.query(Channel).filter(Channel.owner_id == user.id).all()
        
        if not channels:
            bot.answer_callback_query(
                call.id,
                text=strings[user.lang].no_channels_available,
                show_alert=True
            )
            return

        # Create markup with user channels
        markup = types.InlineKeyboardMarkup(row_width=1)
        for channel in channels:
            markup.add(types.InlineKeyboardButton(
                text=channel.name,
                callback_data=f"channel_{channel.id}_post_{post_id}"
            ))
        
        # Add back button
        markup.add(types.InlineKeyboardButton(
            text=strings[user.lang].back_button,
            callback_data=f"view_post_{post_id}"
        ))
        
        bot.send_message(
            user.id,
            text=strings[user.lang].select_channel_for_publish,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("channel_"), state=PostState.select_channel)
    def handle_channel_selection(call: types.CallbackQuery, data: dict):
        user = data["user"]
        
        # Extract channel_id and post_id from callback data
        # Format: channel_{channel_id}_post_{post_id}
        parts = call.data.split("_")
        channel_id = int(parts[1])
        post_id = int(parts[3])
        
        # Get the selected channel to verify it exists and belongs to the user
        channel = db_session.query(Channel).filter(
            Channel.id == channel_id,
            Channel.owner_id == user.id
        ).first()
        
        if not channel:
            bot.answer_callback_query(
                call.id,
                text=strings[user.lang].channel_not_found,
                show_alert=True
            )
            return
        
        # Now publish the post to the selected channel
        success = publish_post(db_session, bot, post_id, channel_id)
        
        if success:
            bot.answer_callback_query(
                call.id,
                text=strings[user.lang].post_published_success,
                show_alert=True
            )
            # Return to my posts
            my_posts(call, data)
        else:
            bot.answer_callback_query(
                call.id,
                text=strings[user.lang].post_published_error,
                show_alert=True
            )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("schedule_post_"))
    def handle_schedule_post(call: types.CallbackQuery, data: dict):
        user = data["user"]
        post_id = int(call.data.split("_")[2])
        data["state"].add_data(post_id=post_id)
        
        # Get user's channels
        channels = db_session.query(Channel).filter(Channel.owner_id == user.id).all()
        
        if not channels:
            bot.answer_callback_query(
                call.id,
                text=strings[user.lang].no_channels_available,
                show_alert=True
            )
            return

        # Create markup with user channels
        markup = types.InlineKeyboardMarkup(row_width=1)
        for channel in channels:
            markup.add(types.InlineKeyboardButton(
                text=channel.name,
                callback_data=f"schedule_channel_{channel.id}_post_{post_id}"
            ))
        #markup.add(create_cancel_button(user.lang))

        bot.send_message(
            user.id,
            text=strings[user.lang].select_channel_for_publish,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("schedule_channel_"))
    def handle_schedule_channel_selection(call: types.CallbackQuery, data: dict):
        user = data["user"]
        # Extract channel_id and post_id from callback data
        # Format: schedule_channel_{channel_id}_post_{post_id}
        parts = call.data.split("_")
        channel_id = parts[2]
        post_id = int(parts[4])

        data["state"].add_data(channel_id=channel_id)
        data["state"].set(PostState.schedule_post)

        markup = create_post_scheduling_markup(user.lang)
        
        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].select_schedule_time,
            reply_markup=markup
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("schedule_time_"), state=PostState.schedule_post)
    def handle_schedule_time(call: types.CallbackQuery, data: dict):
        user = data["user"]

        # Extract time from callback data
        time_str = call.data[len("schedule_time_"):]
        scheduled_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')

        with data["state"].data() as data_items:
            post_id = data_items.get("post_id")
            channel_id = data_items.get("channel_id")
            channel = db_session.query(Channel).filter(
                Channel.id == channel_id,
                Channel.owner_id == user.id
            ).first()
            success = scheduler_services.schedule_publish_post(
                db_session, channel.link, post_id, scheduled_time
            )

        if success:
            bot.answer_callback_query(
                call.id,
                text=strings[user.lang].post_scheduled_success,
                show_alert=True
            )
            # Return to my posts
            my_posts(call, data)
        else:
            bot.answer_callback_query(
                call.id,
                text=strings[user.lang].post_scheduled_error,
                show_alert=True
            )


    @bot.callback_query_handler(func=lambda call: call.data == "schedule_custom", state=PostState.schedule_post)
    def handle_custom_schedule(call: types.CallbackQuery, data: dict):
        user = data["user"]
        data["state"].set(PostState.schedule_custom)

        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].enter_custom_time,
            reply_markup=create_cancel_button(user.lang)
        )

    @bot.message_handler(state=PostState.schedule_custom)
    def process_custom_schedule(message: types.Message, data: dict):
        user = data["user"]

        # Extract time from callback data
        time_str = message.text
        # Validate the time format
        try:
            scheduled_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        except:
            bot.send_message(
                chat_id=user.id,
                text=strings[user.lang].invalid_time_format,
                reply_markup=create_cancel_button(user.lang)
            )
            return

        with data["state"].data() as data_items:
            post_id = data_items.get("post_id")
            channel_id = data_items.get("channel_id")
            channel = db_session.query(Channel).filter(
                Channel.id == channel_id,
                Channel.owner_id == user.id
            ).first()
            success = scheduler_services.schedule_publish_post(
                db_session, channel.link, post_id, scheduled_time
            )

        if success:
            bot.send_message(
                chat_id=user.id,
                text=strings[user.lang].post_scheduled_success
            )
            # Return to my posts
            my_posts(message, data)
        else:
            bot.send_message(
                chat_id=user.id,
                text=strings[user.lang].post_scheduled_error,
                reply_markup=create_cancel_button(user.lang)
            )

    @bot.callback_query_handler(func=lambda call: call.data == "cancel_scheduling", state=PostState.schedule_post)
    def cancel_scheduling(call: types.CallbackQuery, data: dict):
        # Return to post view
        view_post(call, data)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_post_"))
    def handle_edit_post(call: types.CallbackQuery, data: dict):
        user = data["user"]
        post_id = int(call.data.split("_")[2])
        data["state"].add_data(post_id=post_id)
        data["state"].set(PostState.edit_post)

        post = read_post(db_session, post_id)

        if not post:
            bot.answer_callback_query(
                call.id,
                text=strings[user.lang].post_not_found,
                show_alert=True
            )
            return

        markup = create_post_edit_actions_markup(user.lang, post_id)
        bot.edit_message_text(
            chat_id=user.id,
            message_id=call.message.message_id,
            text=strings[user.lang].what_to_edit,
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data == "edit_title_post", state=PostState.edit_post)
    def edit_title_post(call: types.CallbackQuery, data: dict):
        user = data["user"]
        # The post_id is already in data from handle_edit_post
        with data["state"].data() as data_items:
            post_id = data_items.get("post_id")
            if not post_id:
                bot.answer_callback_query(
                    call.id,
                    text=strings[user.lang].post_not_found,
                    show_alert=True
                )
                return

            data["state"].set(PostState.edit_title)

            bot.edit_message_text(
                chat_id=user.id,
                message_id=call.message.message_id,
                text=strings[user.lang].enter_new_title,
                reply_markup=create_cancel_button(user.lang)
            )

    @bot.message_handler(state=PostState.edit_title)
    def process_edit_title(message: types.Message, data: dict):
        user = data["user"]
        with data["state"].data() as data_items:
            post_id = data_items.get("post_id")
            # Make sure post_id exists
            if not post_id:
                bot.send_message(
                    chat_id=user.id,
                    text=strings[user.lang].post_not_found,
                    reply_markup=create_menu_markup(user.lang)
                )
                return

            post = read_post(db_session, post_id)
            if not post:
                bot.send_message(
                    chat_id=user.id,
                    text=strings[user.lang].post_not_found,
                    reply_markup=create_menu_markup(user.lang)
                )
                return

            # Update post title
            updated_post = update_post_content(db_session, post_id, message.text, post.content)

            if updated_post:
                # Send success message and return to post view
                markup = create_post_action_markup(user.lang, post_id)

                # Prepare updated post message
                status_text = strings[user.lang].post_published if post.is_published else strings[user.lang].post_draft
                schedule_text = ""
                if post.scheduled_time:
                    schedule_text = f"\n{strings[user.lang].scheduled_for}: {post.scheduled_time.strftime('%Y-%m-%d %H:%M')}"

                message_text = (
                    #f"<b>{updated_post.title}</b>\n\n"
                    f"{updated_post.content}\n\n"
                )

                bot.send_message(
                    chat_id=user.id,
                    text=message_text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )

                data["state"].set(PostState.view_post)
            else:
                bot.send_message(
                    chat_id=user.id,
                    text=strings[user.lang].update_failed,
                    reply_markup=create_cancel_button(user.lang)
                )

    @bot.callback_query_handler(func=lambda call: call.data == "edit_content_post", state=PostState.edit_post)
    def edit_content_post(call: types.CallbackQuery, data: dict):
        user = data["user"]
        # The post_id is already in data from handle_edit_post
        with data["state"].data() as data_items:
            post_id = data_items.get("post_id")
            if not post_id:
                bot.answer_callback_query(
                    call.id,
                    text=strings[user.lang].post_not_found,
                    show_alert=True
                )
                return

            data["state"].set(PostState.edit_content)

            bot.send_message(
                user.id,
                text=strings[user.lang].enter_new_content,
                reply_markup=create_cancel_button(user.lang)
            )
            @bot.message_handler(content_types=['text', 'photo'], state=PostState.edit_content)
            def process_edit_content(message: types.Message, data: dict):
                user = data["user"]
                with data["state"].data() as data_items:
                    post_id = data_items.get("post_id")
                    post = read_post(db_session, post_id)

                    # Get content and photo if exists
                    content = message.text
                    photo_id = None
                    if message.photo:
                        # Get the largest photo (last in array)
                        photo_id = message.photo[-1].file_id
                        # If caption exists, use it as content
                        content = message.caption or ""

                    # Update post content
                    updated_post = update_post_content(db_session, post_id, post.title, content, photo_id)

                    if updated_post:
                        # Send success message and return to post view
                        markup = create_post_action_markup(user.lang, post_id)

                        # Prepare updated post message
                        status_text = strings[user.lang].post_published if post.is_published else strings[user.lang].post_draft
                        schedule_text = ""
                        if post.scheduled_time:
                            schedule_text = f"\n{strings[user.lang].scheduled_for}: {post.scheduled_time.strftime('%Y-%m-%d %H:%M')}"

                        title = updated_post.title if updated_post.title else strings[user.lang].untitled_post

                        message_text = (
                            #f"<b>{title}</b>\n\n"
                            f"{updated_post.content}\n\n"
                        )

                        if updated_post.photo_id:
                            bot.send_photo(
                                chat_id=user.id,
                                photo=updated_post.photo_id,
                                caption=message_text,
                                reply_markup=markup,
                                parse_mode="HTML"
                            )
                        else:
                            bot.send_message(
                                chat_id=user.id,
                                text=message_text,
                                reply_markup=markup,
                                parse_mode="HTML"
                            )

                        data["state"].set(PostState.view_post)
                    else:
                        bot.send_message(
                            chat_id=user.id,
                            text=strings[user.lang].update_failed,
                            reply_markup=create_cancel_button(user.lang)
                        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_edit_post_"), state=PostState.edit_post)
    def handle_save_post(call: types.CallbackQuery, data: dict):
        user = data["user"]
        post_id = int(call.data.split("_")[2])

        # Get the post
        post = read_post(db_session, post_id)

        if not post:
            bot.answer_callback_query(
                call.id,
                text=strings[user.lang].post_not_found,
                show_alert=True
            )
            return

        # Just return to post view with a confirmation message
        bot.answer_callback_query(
            call.id,
            text=strings[user.lang].post_saved,
            show_alert=True
        )

        # Return to post view
        data["state"].add_data(post_id = post_id)
        view_post(call, data)

    # handler for deleting a post
    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_post_"))
    def handle_delete_post(call: types.CallbackQuery, data: dict):
        user = data["user"]
        post_id = int(call.data.split("_")[2])
        post = read_post(db_session, post_id)

        if not post:
            bot.answer_callback_query(
                call.id,
                text=strings[user.lang].post_not_found,
                show_alert=True
            )
            return

        # Delete the post
        db_session.delete(post)
        db_session.commit()

        # Send confirmation message
        bot.answer_callback_query(
            call.id,
            text=strings[user.lang].post_deleted,
            show_alert=True
        )

        # Return to my posts
        my_posts(call, data)
