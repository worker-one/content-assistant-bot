import random
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy.orm import Session

from .models import Channel

fake = Faker()


def init_channels_table_data(db: Session, count: int = 3):
    """
    Generate fake posts for database initialization
    
    Args:
        db (Session): SQLAlchemy database session
        count (int, optional): Number of posts to generate. Defaults to 3.
    
    Returns:
        list: The created Post objects
    """
    

    channel = Channel(
        name="Test Channel",
        link="https://t.me/spamhameggs",
        owner_id=954020212
    )

    db.add(channel)
    db.commit()
