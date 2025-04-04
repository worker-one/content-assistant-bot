import logging
from datetime import datetime
import random
from typing import List, Optional
from pathlib import Path

from sqlalchemy.orm import Session
from omegaconf import OmegaConf

from ..posts.models import Post
from .models import Style
from ..openai.client import LLM
from ..openai import schemas as openai_schemas

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
CURRENT_DIR = Path(__file__).parent
config = OmegaConf.load(CURRENT_DIR / "config.yaml")
strings = config.strings


# Style services
def create_style(db_session: Session, name: str, examples: str, owner_id: int) -> Style:
    """ Create a new style """
    style = Style(
        name=name,
        examples=examples,
        owner_id=owner_id,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db_session.add(style)
    db_session.commit()
    db_session.refresh(style)
    return style


def read_style(db_session: Session, style_id: int) -> Optional[Style]:
    """ Get a style by ID """
    return db_session.query(Style).filter(Style.id == style_id).first()


def read_styles_by_owner(db_session: Session, owner_id: int, skip: int = 0, limit: int = 10) -> List[Style]:
    """ Get all styles by a specific owner """
    return db_session.query(Style).filter(Style.owner_id == owner_id).offset(skip).limit(limit).all()


def update_style(db_session: Session, style_id: int, name: str, description: str, examples: str) -> Optional[Style]:
    """ Update a style """
    style = db_session.query(Style).filter(Style.id == style_id).first()
    if style:
        style.name = name
        style.examples = examples
        style.updated_at = datetime.now()
        db_session.commit()
        db_session.refresh(style)
    return style


def delete_style(db_session: Session, style_id: int) -> bool:
    """ Delete a style """
    style = db_session.query(Style).filter(Style.id == style_id).first()
    if style:
        db_session.delete(style)
        db_session.commit()
        return True
    return False


# Post services
def create_post(db_session: Session, title: str, content: str, style_id: int, owner_id: int) -> Post:
    """ Create a new post """
    post = Post(
        title=title,
        content=content,
        style_id=style_id,
        owner_id=owner_id,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post


def read_post(db_session: Session, post_id: int) -> Optional[Post]:
    """ Get a post by ID """
    return db_session.query(Post).filter(Post.id == post_id).first()


def read_posts_by_owner(db_session: Session, owner_id: int, skip: int = 0, limit: int = 10) -> List[Post]:
    """ Get all posts by a specific owner """
    return db_session.query(Post).filter(Post.owner_id == owner_id).offset(skip).limit(limit).all()


def update_post(db_session: Session, post_id: int, title: str, content: str, style_id: Optional[int] = None) -> Optional[Post]:
    """ Update a post """
    post = db_session.query(Post).filter(Post.id == post_id).first()
    if post:
        post.title = title
        post.content = content
        if style_id:
            post.style_id = style_id
        post.updated_at = datetime.now()
        db_session.commit()
        db_session.refresh(post)
    return post


def schedule_post(db_session: Session, post_id: int, scheduled_time: datetime) -> Optional[Post]:
    """ Schedule a post for publishing """
    post = db_session.query(Post).filter(Post.id == post_id).first()
    if post:
        post.scheduled_time = scheduled_time
        db_session.commit()
        db_session.refresh(post)
    return post


def publish_post(db_session: Session, post_id: int) -> Optional[Post]:
    """ Mark a post as published """
    post = db_session.query(Post).filter(Post.id == post_id).first()
    if post:
        post.is_published = 1
        post.updated_at = datetime.now()
        db_session.commit()
        db_session.refresh(post)
    return post


def delete_post(db_session: Session, post_id: int) -> bool:
    """ Delete a post """
    post = db_session.query(Post).filter(Post.id == post_id).first()
    if post:
        db_session.delete(post)
        db_session.commit()
        return True
    return False


# AI generation services (mock implementations)
def generate_with_style(content: str, style_id: int, db_session: Session) -> str:
    """ Generate or edit content according to the specified style """
    style = read_style(db_session, style_id)
    if not style:
        return content
    
    # Load the LLM model
    llm = LLM(config.app.llm, system_prompt=config.app.llm.system_prompt)

    style_content = f"Примеры: {style.examples}"
    user_input = f"{style_content}\n\nИсходный текст: {content}"

    # Convert chat history to a list of Message objects using model_validate
    openai_chat_history = [
        openai_schemas.Message(
            id = random.randint(1, 10000),
            chat_id = style.owner_id,
            role = "user",
            content = user_input,
            created_at = datetime.now()
        )
    ]
    
    # This would be replaced with actual AI-based generation
    logger.info(f"Generating content with style: {style.name}")
    
    # Generate and send the final response
    response = llm.invoke(openai_chat_history)
    return response.content


def edit_content(content: str) -> str:
    """ Edit content to fix grammatical errors and improve style """
    # This would be replaced with actual AI-based editing
    logger.info("Editing content to fix errors")
    return content