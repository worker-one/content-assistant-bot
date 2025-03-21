import logging
from datetime import datetime

from sqlalchemy.orm import Session

from .models import Channel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Channel related functions
def create_channel(db_session: Session, name: str, link: str, owner_id: int) -> Channel:
    """ Create a new channel """
    channel = Channel(
        name=name,
        link=link,
        owner_id=owner_id
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


def read_channels_by_owner(db_session: Session, owner_id: int, skip: int = 0, limit: int = 100):
    """ Get all channels by a specific owner """
    return db_session.query(Channel).filter(Channel.owner_id == owner_id).offset(skip).limit(limit).all()


def read_channel(db_session: Session, channel_id: int):
    """ Get a channel by ID """
    return db_session.query(Channel).filter(Channel.id == channel_id).first()


def update_channel(db_session: Session, channel_id: int, name: str = None, link: str = None) -> Channel:
    """ Update channel information """
    channel = db_session.query(Channel).filter(Channel.id == channel_id).first()
    if channel:
        if name:
            channel.name = name
        if link:
            channel.link = link
        channel.updated_at = datetime.utcnow()
        db_session.commit()
        db_session.refresh(channel)
    return channel


def delete_channel(db_session: Session, channel_id: int) -> bool:
    """ Delete a channel """
    channel = db_session.query(Channel).filter(Channel.id == channel_id).first()
    if channel:
        db_session.delete(channel)
        db_session.commit()
        return True
    return False