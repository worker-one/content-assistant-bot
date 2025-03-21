import logging
from datetime import datetime, timedelta

from ..database.core import get_session
from ..posts.models import Post

logger = logging.getLogger(__name__)


def publish_post(channel_link: str, post_content: str, post_photo_id: str = None):
    """
    Schedule a post to be published at a specific time.

    Args:
        channel_link: Bot instance
        post_content: Content of the post to schedule
        post_photo_id: ID of the post to schedule
    """
    from ..main import bot  # Import here to avoid circular imports

    channel_tag = f"@{channel_link.split('/')[-1]}"
    if post_photo_id:
        # Schedule the post to be published in 5 minutes
        bot.send_photo(
            chat_id=channel_tag,
            photo=post_photo_id,
            caption=post_content
        )
    else:
        # Schedule the post to be published in 5 minutes
        bot.send_message(
            chat_id=channel_tag,
            text=post_content
        )
    return True
