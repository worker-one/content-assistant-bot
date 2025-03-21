import logging
from datetime import datetime, timedelta

from ..database.core import get_session
from ..models import ScheduledGame, ScheduledGameSeries
from ..host_game.service import schedule_single_game, get_game_details

logger = logging.getLogger(__name__)


def create_next_game_in_series(series_id: int, game_id: int, max_occurrences=3):
    """
    Create the next game in a series if we don't already have enough future instances
    
    Args:
        series_id: ID of the series
        game_id: ID of the game template
        max_occurrences: Maximum number of future instances to maintain
    """
    db_session = get_session()
    
    # Get the series
    series = db_session.query(ScheduledGameSeries).filter(
        ScheduledGameSeries.id == series_id
    ).first()
    
    if not series:
        logger.warning(f"Series {series_id} not found")
        return
    
    # Get the latest game in the series
    latest_game = db_session.query(ScheduledGame).filter(
        ScheduledGame.scheduled_game_series_id == series_id,
        ScheduledGame.skipped == False
    ).order_by(ScheduledGame.datetime.desc()).first()
    
    if not latest_game:
        logger.warning(f"No games found for series {series_id}")
        return
    
    # Count future games in this series
    future_games_count = db_session.query(ScheduledGame).filter(
        ScheduledGame.scheduled_game_series_id == series_id,
        ScheduledGame.datetime > datetime.now(),
        ScheduledGame.skipped == False
    ).count()
    
    # If we don't have enough future games, create a new one
    if future_games_count < max_occurrences:
        # Calculate the next date based on repeat interval
        if series.repeat_every_week:
            next_datetime = latest_game.datetime + timedelta(days=7)
        else:  # repeat_every_two_weeks
            next_datetime = latest_game.datetime + timedelta(days=14)
        
        # Create the new game
        new_game = schedule_single_game(
            db_session=db_session,
            game_id=latest_game.game_id,
            scheduled_datetime=next_datetime,
            initiator_id=latest_game.initiator_id,
            initiator_role_id=latest_game.initiator_role_id,
            use_steam=latest_game.use_steam,
            server_password=latest_game.server_password,
            serverdata=latest_game.server_data,
            discord_telegram_link=latest_game.discord_telegram_link,
            room=latest_game.room,
            repeat_every_week=latest_game.repeat_every_week,
            repeat_every_two_weeks=latest_game.repeat_every_two_weeks,
            max_players=latest_game.max_players,
            parent_id=latest_game.id,
            scheduled_game_series_id=series_id
        )

        # Update the child_id of the latest game
        latest_game.child_id = new_game.id
        db_session.commit()

        logger.info(f"Created new game instance in series {series_id} for date {next_datetime}")

        # Schedule notifications for the new game
        from .service import schedule_game_notifications
        if new_game.player_ids:
            user_ids = new_game.player_ids.split(',')
            schedule_game_notifications(new_game.id, new_game.datetime, user_ids)


def send_game_notifications(game_id, hours_before, user_ids):
    """
    Send notifications to users about an upcoming game
    
    Args:
        game_id: ID of the scheduled game
        hours_before: How many hours before the game (24 or 2)
        user_ids: List of user IDs to notify
    """
    from ..main import bot  # Import here to avoid circular imports
    
    db_session = get_session()
    game = db_session.query(ScheduledGame).filter(ScheduledGame.id == game_id).first()
    
    if not game or game.skipped:
        logger.warning(f"Game {game_id} not found or skipped")
        return
    
    game_details = get_game_details(db_session, game.game_id)
    if not game_details:
        logger.warning(f"Game details not found for game {game_id}")
        return
    
    # Format the notification message
    game_date = game.date.strftime('%d.%m.%Y')
    game_time = game.time.strftime('%H:%M')
    
    if hours_before == 24:
        message = (
            f"Напоминаю, что завтра в {game_time} (UTC+3 MSK) состоится игра:\n\n"
            f"<b>{game_details.name}</b>\n"
            f"Дата: <b>{game_date}</b>\n"
            f"Время: <b>{game_time}</b> (UTC+3 MSK)\n"
        )
    else:  # 2 hours
        message = (
            f"Игра скоро начнется!\n\n"
            f"<b>{game_details.name}</b>\n"
            f"Время: <b>{game_time}</b> (UTC+3 MSK)\n"
            f"До начала осталось {hours_before} часа"
        )

    # Add server info for online games
    if game.use_steam:
        message += f"\n\nСервер: {game.server_data}\n"
        message += f"Пароль: {game.server_password}\n"

    # Add meeting link if available
    if game.discord_telegram_link:
        message += f"\nСсылка для встречи: {game.discord_telegram_link}\n"

    # Send to all users in the list
    for user_id in user_ids:
        try:
            bot.send_message(int(user_id), message, parse_mode="HTML")
            logger.info(f"Sent {hours_before}h notification to user {user_id} for game {game_id}")
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")



def remove_past_scheduled_games():
    """
    Removes scheduled games that have already passed.
    """
    db_session = get_session()
    
    try:
        # Query games where the scheduled datetime has passed and they are not marked as skipped
        past_games = db_session.query(ScheduledGame).filter(
            ScheduledGame.datetime < datetime.now(),
            ScheduledGame.skipped == False
        ).all()

        if not past_games:
            logger.info("No past scheduled games found for removal.")
            return
        
        # Log the count and details for transparency
        logger.info(f"Found {len(past_games)} past scheduled games to remove.")

        # Deleting the games
        for game in past_games:
            logger.info(f"Deleting scheduled game with ID: {game.id} scheduled for {game.datetime}")
            db_session.delete(game)
        
        db_session.commit()
        logger.info("Successfully removed past scheduled games.")

    except Exception as e:
        logger.error(f"Error while removing past scheduled games: {e}")
        db_session.rollback()
    finally:
        db_session.close()