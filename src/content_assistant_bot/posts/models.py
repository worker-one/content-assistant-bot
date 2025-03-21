from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..models import Base, TimeStampMixin


class Post(Base, TimeStampMixin):
    """ Post model for storing generated content """
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    style_id = Column(Integer, ForeignKey("styles.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    scheduled_time = Column(DateTime, nullable=True)
    is_published = Column(Boolean, default=False)
    photo_id = Column(String, nullable=True)

    # owner = relationship("User", back_populates="posts", lazy="joined")
    # style = relationship("Style", back_populates="posts", lazy="joined")
