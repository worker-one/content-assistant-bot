import random
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy.orm import Session

from .models import Post

fake = Faker()


def init_posts_table_data(db: Session, count: int = 3):
    """
    Generate fake posts for database initialization
    
    Args:
        db (Session): SQLAlchemy database session
        count (int, optional): Number of posts to generate. Defaults to 3.
    
    Returns:
        list: The created Post objects
    """
    

    posts = []
    
    for _ in range(count):
        # Generate random publish status
        is_published = False
        
        # Generate random scheduled time (between now and 7 days in future)
        scheduled_time = None
        if not is_published:
            days_ahead = random.randint(1, 7)
            scheduled_time = datetime.now() + timedelta(days=days_ahead)
        
        post = Post(
            title=fake.sentence(nb_words=6),
            content=' '.join(fake.paragraphs(nb=3)),
            owner_id=954020212,
            scheduled_time=scheduled_time,
            is_published=is_published
        )

        db.add(post)
        posts.append(post)
    
    db.commit()
    return posts
