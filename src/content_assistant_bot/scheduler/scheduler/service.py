import logging
from datetime import datetime, timedelta

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from ..database.core import get_session
from ..models import ScheduledGame
from .tasks import create_next_game_in_series, send_game_notifications, remove_past_scheduled_games

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a single instance of the scheduler
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///local_database.db')
}
scheduler = BackgroundScheduler(jobstores=jobstores)

scheduler.add_job(remove_past_scheduled_games, 'cron', hour=0)  # Runs daily at midnight

def init_scheduler():
    """Initialize the scheduler and start it"""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def schedule_series_creation(series_id, game_id, start_datetime, interval_weeks, max_occurrences=12):
    """
    Schedule creation of new game instances for a series
    
    Args:
        series_id: ID of the ScheduledGameSeries
        game_id: ID of the Game
        start_datetime: Starting datetime for scheduling
        interval_weeks: Number of weeks between instances (1 or 2)
        max_occurrences: Maximum number of future game instances to maintain
    """
    job_id = f"series_creation_{series_id}"
    
    # Remove existing job if it exists
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Schedule the job to run daily
    scheduler.add_job(
        create_next_game_in_series,
        'interval',
        hours=24,
        id=job_id,
        replace_existing=True,
        args=[series_id, game_id, max_occurrences]
    )

    logger.info(f"Scheduled series creation job for series ID {series_id}")


def schedule_game_notifications(game_id, game_datetime, user_ids):
    """
    Schedule notifications for a game
    
    Args:
        game_id: ID of the ScheduledGame
        game_datetime: Datetime of the game
        user_ids: List of user IDs who should receive notifications
    """
    # Schedule 24-hour notification
    notification_time = game_datetime - timedelta(hours=24)
    if datetime.now() < notification_time:
        job_id = f"notification_24h_{game_id}"
        scheduler.add_job(
            send_game_notifications,
            'date',
            run_date=notification_time,
            id=job_id,
            replace_existing=True,
            args=[game_id, 24, user_ids]
        )

    # Schedule 2-hour notification
    notification_time = game_datetime - timedelta(hours=2)
    if datetime.now() < notification_time:
        job_id = f"notification_2h_{game_id}"
        scheduler.add_job(
            send_game_notifications,
            'date',
            run_date=notification_time,
            id=job_id, 
            replace_existing=True,
            args=[game_id, 2, user_ids]
        )

    logger.info(f"Scheduled notifications for game ID {game_id}")


def reschedule_series_notifications(series_id):
    """
    Update all notification schedules for a series after player changes
    """
    db_session = get_session()
    series_games = db_session.query(ScheduledGame).filter(
        ScheduledGame.scheduled_game_series_id == series_id,
        ScheduledGame.skipped == False,
        ScheduledGame.datetime > datetime.now()
    ).all()
    
    for game in series_games:
        if game.player_ids:
            user_ids = game.player_ids.split(',')
            schedule_game_notifications(game.id, game.datetime, user_ids)
    
    logger.info(f"Rescheduled notifications for all games in series {series_id}")


def remove_series_schedules(series_id):
    """Remove all scheduled jobs related to a series when it's deleted"""
    # Remove series creation job
    job_id = f"series_creation_{series_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    # Remove notification jobs for all games in the series
    db_session = get_session()
    series_games = db_session.query(ScheduledGame).filter(
        ScheduledGame.scheduled_game_series_id == series_id
    ).all()
    
    for game in series_games:
        remove_game_schedules(game.id)
    
    logger.info(f"Removed all scheduled jobs for series {series_id}")


def remove_game_schedules(game_id):
    """Remove scheduled notifications for a specific game"""
    for hours in [24, 2]:
        job_id = f"notification_{hours}h_{game_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
    
    logger.info(f"Removed notification jobs for game {game_id}")
