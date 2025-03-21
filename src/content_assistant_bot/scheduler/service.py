import logging
from datetime import datetime, timedelta

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from ..posts.models import Post
from .tasks import publish_post

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a single instance of the scheduler
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///local_database.db')
}
scheduler = BackgroundScheduler(jobstores=jobstores)

def init_scheduler():
    """Initialize the scheduler and start it"""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def schedule_publish_post(
    db_session: Session, channel_link: str,
    post_id: int, scheduled_time: datetime
    ):
    """
    Schedule a post to be published at a specific time.

    Args:
        db_session: SQLAlchemy database session
        bot: Bot instance
        post_id: ID of the post to schedule
        scheduled_time: Time to publish the post
    Returns:
        bool: True if the post was scheduled successfully, False otherwise
    """
    try:
        post = db_session.query(Post).filter(Post.id == post_id).first()
        print(f"Post: {post}")
        post.scheduled_time = scheduled_time
        db_session.commit()

        # Schedule the job
        scheduler.add_job(
            publish_post,
            'date',
            run_date=scheduled_time,
            args=[channel_link, post.content, post.photo_id],
        )
        logger.info(f"Post {post_id} scheduled for publication at {post.scheduled_time}.")
        db_session.commit()
        return True
    except Exception as e:
        logger.error(f"Error scheduling post {post_id}: {e}")
        return False
