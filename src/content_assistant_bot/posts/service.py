import logging
from datetime import datetime
from typing import Optional

from content_assistant_bot.channels.service import read_channel
from sqlalchemy.orm import Session

from .models import Post

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_post(db_session: Session, title: str, content: str, owner_id: int, photo_id: Optional[str] = None) -> Post:
    """ Create a new post """
    post = Post(
        title=title,
        content=content,
        owner_id=owner_id,
        photo_id=photo_id,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post

# Post related functions
def read_posts_by_owner(db_session: Session, owner_id: int, skip: int = 0, limit: int = 10):
    """ Get all posts by a specific owner """
    return db_session.query(Post).filter(Post.owner_id == owner_id).offset(skip).limit(limit).all()


def read_post(db_session: Session, post_id: int):
    """ Get a post by ID """
    return db_session.query(Post).filter(Post.id == post_id).first()


def publish_post(db_session, bot, post_id, channel_id=None):
    """
    Publish a post
    
    Args:
        db_session: SQLAlchemy database session
        post_id: ID of the post to publish
        channel_id: ID of the channel to publish to

    Returns:
        bool: True if post was published successfully, False otherwise
    """
    post = db_session.query(Post).filter(Post.id == post_id).first()

    if not post:
        return False

    try:
        # Send the post to the specified channel
        channel = read_channel(db_session, channel_id)
        channel_tag = f"@{channel.link.split('/')[-1]}"

        if post.photo_id:
            bot.send_photo(
                chat_id=channel_tag,
                photo=post.photo_id,
                caption=post.content
            )
        else:
            bot.send_message(
                chat_id=channel_tag,
                text=post.content
            )
    except Exception as e:
        logger.error(f"Error sending message to channel: {e}")
        return False
    try:

        post.is_published = True
        post.published_at = datetime.now()
        db_session.commit()

        return True
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error publishing post: {e}")
        return False


def schedule_post(db_session: Session, post_id: int, scheduled_time: datetime) -> bool:
    """ Schedule a post for future publishing """
    post = db_session.query(Post).filter(Post.id == post_id).first()
    if post:
        post.scheduled_time = scheduled_time
        db_session.commit()
        db_session.refresh(post)
        return True
    return False


def update_post_content(db_session: Session, post_id: int, title: str, content: str, photo_id: Optional[str] = None) -> Post:
    """ Update post content """
    post = db_session.query(Post).filter(Post.id == post_id).first()
    if post:
        post.title = title
        post.content = content
        post.photo_id = photo_id
        post.updated_at = datetime.utcnow()
        db_session.commit()
        db_session.refresh(post)
    return post
